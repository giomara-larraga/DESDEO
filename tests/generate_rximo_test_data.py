"""Pre-generate (reference_point, solution) pairs for the R-XIMO cross-problem tests.

Each pair is produced by sampling a reference point uniformly between the ideal
and nadir of a twice-differentiable test problem, then solving the
ASF-scalarized formulation with `PyomoBonminSolver` (the exact solver). The
resulting parquet + metadata pair is consumed by
`tests/test_rximo_across_problems.py`, which runs `ShapExplainer` and R-XIMO on
the *fast approximate* model and verifies the suggestions against the exact
solver again.

Run once via:

    uv run python tests/generate_rximo_test_data.py
"""

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl

from desdeo.problem import Problem
from desdeo.problem.testproblems import binh_and_korn, dtlz2, river_pollution_problem
from desdeo.tools import PyomoBonminSolver, add_asf_diff

N_SAMPLES = 1000
RNG_SEED = 42
DATA_DIR = Path(__file__).parent / "data" / "rximo"


@dataclass
class TestProblemConfig:
    """One row in the test catalog: a problem builder and the file stem."""

    name: str
    builder: Callable[[], Problem]


CATALOG: list[TestProblemConfig] = [
    TestProblemConfig(name="binh_and_korn", builder=binh_and_korn),
    TestProblemConfig(
        # The 5-objective variant uses Max(Abs(.), Abs(.)) for f_5 which is not
        # twice-differentiable, so PyomoBonminSolver rejects it. We use the
        # 4-objective variant (DO city, DO municipality, ROI fishery, ROI city)
        # which keeps the original spirit of the river-pollution example.
        name="river_pollution_4obj",
        builder=lambda: river_pollution_problem(five_objective_variant=False),
    ),
    TestProblemConfig(
        name="dtlz2_3obj",
        builder=lambda: dtlz2(n_variables=5, n_objectives=3),
    ),
]


def _objective_metadata(problem: Problem) -> tuple[list[str], dict[str, float], dict[str, float], dict[str, bool]]:
    symbols = [obj.symbol for obj in problem.objectives]
    ideal = {}
    nadir = {}
    is_max = {}
    for obj in problem.objectives:
        if obj.ideal is None or obj.nadir is None:
            raise ValueError(f"Objective {obj.symbol} is missing an ideal or nadir value.")
        ideal[obj.symbol] = float(obj.ideal)
        nadir[obj.symbol] = float(obj.nadir)
        is_max[obj.symbol] = bool(obj.maximize)
    return symbols, ideal, nadir, is_max


def _sample_reference_point(
    rng: np.random.Generator,
    symbols: list[str],
    ideal: dict[str, float],
    nadir: dict[str, float],
    is_max: dict[str, bool],
) -> dict[str, float]:
    """Sample a reference point uniformly between ideal and nadir, in original scale."""
    rp = {}
    for s in symbols:
        lo, hi = ideal[s], nadir[s]
        if is_max[s]:
            # Maximized objective: nadir is the smaller value, ideal the larger.
            lo, hi = min(lo, hi), max(lo, hi)
        else:
            lo, hi = min(lo, hi), max(lo, hi)
        rp[s] = float(rng.uniform(lo, hi))
    return rp


def generate_for_problem(cfg: TestProblemConfig, out_dir: Path) -> None:  # noqa: D103
    print(f"\n=== {cfg.name} ===")
    problem = cfg.builder()
    if not problem.is_twice_differentiable:
        raise RuntimeError(f"{cfg.name} is not twice differentiable; skipping.")

    symbols, ideal, nadir, is_max = _objective_metadata(problem)
    print(f"  objectives: {symbols}")
    print(f"  ideal: {ideal}")
    print(f"  nadir: {nadir}")
    print(f"  maximize flags: {is_max}")

    rng = np.random.default_rng(RNG_SEED)

    successes = 0
    failures = 0
    rows: list[dict[str, float]] = []
    start = time.time()

    for i in range(N_SAMPLES):
        rp = _sample_reference_point(rng, symbols, ideal, nadir, is_max)
        try:
            problem_w_asf, target = add_asf_diff(problem, "_asf", rp)
            solver = PyomoBonminSolver(problem_w_asf)
            result = solver.solve(target)
        except Exception as e:
            failures += 1
            if failures <= 3:
                print(f"  [{i:03d}] solver crashed: {type(e).__name__}: {e}")
            continue

        if not result.success:
            failures += 1
            if failures <= 3:
                print(f"  [{i:03d}] solver failed: {result.message}")
            continue

        sol = result.optimal_objectives
        row: dict[str, float] = {}
        for s in symbols:
            row[f"ref_{s}"] = float(rp[s])
            row[f"sol_{s}"] = float(sol[s])
        rows.append(row)
        successes += 1

        if (successes % 25) == 0:
            elapsed = time.time() - start
            print(f"  [{i + 1}/{N_SAMPLES}] {successes} successes, {failures} failures, {elapsed:.1f}s elapsed")

    elapsed = time.time() - start
    print(f"  done: {successes}/{N_SAMPLES} successes ({failures} failures) in {elapsed:.1f}s")

    if not rows:
        raise RuntimeError(f"No successful solves for {cfg.name}; refusing to write empty data.")

    df = pl.DataFrame(rows)
    parquet_path = out_dir / f"{cfg.name}.parquet"
    meta_path = out_dir / f"{cfg.name}_meta.json"
    df.write_parquet(parquet_path)
    meta = {
        "objective_names": symbols,
        "ideal": ideal,
        "nadir": nadir,
        "is_maximized": is_max,
    }
    meta_path.write_text(json.dumps(meta, indent=2))
    print(f"  wrote {parquet_path} ({df.height} rows) and {meta_path}")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {DATA_DIR}")
    for cfg in CATALOG:
        generate_for_problem(cfg, DATA_DIR)


if __name__ == "__main__":
    main()
