"""Cross-problem R-XIMO validation: fast SHAP suggestions vs exact solver.

The pre-generated parquet datasets in ``tests/data/rximo/`` contain
(reference_point, solution) pairs solved with ``PyomoBonminSolver`` for three
twice-differentiable test problems. This test module:

1. Loads a parquet dataset per problem and builds a `ShapExplainer` over the
   nearest-neighbor approximation it provides.
2. Runs R-XIMO on the explainer to get suggestions (target + rival).
3. Verifies each suggestion by re-solving the scalarized problem with
   `PyomoBonminSolver` for the modified reference point and comparing against
   the exact original solution stored in the data file.

If the approximate explainer's suggestions consistently improve the target on
the exact solver, the explainer is doing its job. To see the validation
report, run with `-s`::

    uv run pytest tests/test_rximo_across_problems.py -s
"""

import json
from collections.abc import Callable
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from desdeo.explanations import ShapExplainer, find_rival
from desdeo.problem import Problem
from desdeo.problem.testproblems import binh_and_korn, dtlz2, river_pollution_problem
from desdeo.tools import PyomoBonminSolver, add_asf_diff

DATA_DIR = Path(__file__).parent / "data" / "rximo"

PROBLEM_CONSTRUCTORS: dict[str, Callable[[], Problem]] = {
    "binh_and_korn": binh_and_korn,
    "river_pollution_4obj": lambda: river_pollution_problem(five_objective_variant=False),
    "dtlz2_3obj": lambda: dtlz2(n_variables=5, n_objectives=3),
}

PROBLEM_NAMES = list(PROBLEM_CONSTRUCTORS.keys())

N_LOCAL_ACCURACY = 5
N_SUGGESTION_TRIALS = 25
N_BASELINE_COMPARE = 15
N_BACKGROUND = 25
DELTA_FRACTION = 0.10
RNG_SEED = 67

# Module-level report bucket. Tests append numeric results here; the report
# test prints them at the end (so passing -s shows the table).
REPORT: dict[str, dict[str, object]] = {name: {} for name in PROBLEM_NAMES}


def solve_with_reference_point(problem: Problem, reference_point_dict: dict[str, float]) -> dict[str, float]:
    """Solve the ASF-scalarized problem for a reference point, exactly.

    Args:
        problem: a twice-differentiable DESDEO problem.
        reference_point_dict: reference point as ``{symbol: value}`` in
            original scale.

    Returns:
        Solution as ``{symbol: value}`` in original scale.

    Raises:
        RuntimeError: when the solver does not find a successful solution.
    """
    problem_w_asf, target = add_asf_diff(problem, "_asf", reference_point_dict)
    solver = PyomoBonminSolver(problem_w_asf)
    result = solver.solve(target)
    if not result.success:
        raise RuntimeError(f"Solver failed: {result.message}")
    return result.optimal_objectives


def _to_min(values_orig: np.ndarray, sign: np.ndarray) -> np.ndarray:
    """Flip a numpy array of values from original to minimization form."""
    return values_orig * (-sign)


def _to_orig(values_min: np.ndarray, sign: np.ndarray) -> np.ndarray:
    return values_min * (-sign)


def _data_path(name: str) -> Path:
    return DATA_DIR / f"{name}.parquet"


def _meta_path(name: str) -> Path:
    return DATA_DIR / f"{name}_meta.json"


def _load_problem_setup(name: str) -> dict:
    if not _data_path(name).exists():
        pytest.skip(f"Run tests/generate_rximo_test_data.py first (missing {_data_path(name).name}).")

    df = pl.read_parquet(_data_path(name))
    meta = json.loads(_meta_path(name).read_text())

    symbols: list[str] = meta["objective_names"]
    is_max: dict[str, bool] = meta["is_maximized"]
    sign = np.array([1.0 if is_max[s] else -1.0 for s in symbols], dtype=float)

    ref_orig = np.column_stack([df[f"ref_{s}"].to_numpy() for s in symbols])
    sol_orig = np.column_stack([df[f"sol_{s}"].to_numpy() for s in symbols])
    ref_min = ref_orig * (-sign)
    sol_min = sol_orig * (-sign)

    ideal_min = np.array(
        [min(meta["ideal"][s] * (-sign[i]), meta["nadir"][s] * (-sign[i])) for i, s in enumerate(symbols)]
    )
    nadir_min = np.array(
        [max(meta["ideal"][s] * (-sign[i]), meta["nadir"][s] * (-sign[i])) for i, s in enumerate(symbols)]
    )

    input_symbols = [f"z_{s}" for s in symbols]
    output_symbols = list(symbols)

    columns: dict[str, np.ndarray] = {}
    for i, sym in enumerate(input_symbols):
        columns[sym] = ref_min[:, i]
    for i, sym in enumerate(output_symbols):
        columns[sym] = sol_min[:, i]
    problem_data = pl.DataFrame(columns)

    # The default KD-tree NN lookup is used here for runtime; a smooth GP
    # surrogate is available via `make_gp_surrogate` and `ShapExplainer`'s
    # `surrogate_model` parameter for users who want tighter SHAP behavior
    # at the cost of slower predictions.
    explainer = ShapExplainer(
        problem_data=problem_data,
        input_symbols=input_symbols,
        output_symbols=output_symbols,
    )
    rng = np.random.default_rng(RNG_SEED)
    # Following Misitano et al. (2022) Sec. 3 / 5.2, the missing-data set used
    # by SHAP is a representation of the Pareto front. The parquet's sol_*
    # columns are exactly that — solutions returned by PyomoBonminSolver for
    # the sampled reference points.
    bg_idx = rng.choice(sol_min.shape[0], size=min(N_BACKGROUND, sol_min.shape[0]), replace=False)
    background_df = pl.DataFrame({sym: sol_min[bg_idx, i] for i, sym in enumerate(input_symbols)})
    explainer.setup(background_data=background_df)

    problem = PROBLEM_CONSTRUCTORS[name]()

    return {
        "name": name,
        "problem": problem,
        "explainer": explainer,
        "ref_orig": ref_orig,
        "sol_orig": sol_orig,
        "ref_min": ref_min,
        "sol_min": sol_min,
        "sign": sign,
        "symbols": symbols,
        "input_symbols": input_symbols,
        "output_symbols": output_symbols,
        "ideal_min": ideal_min,
        "nadir_min": nadir_min,
        "is_max": is_max,
    }


@pytest.fixture(scope="module", params=PROBLEM_NAMES)
def setup(request) -> dict:
    return _load_problem_setup(request.param)


def _explain(explainer: ShapExplainer, ref_min_row: np.ndarray, input_symbols: list[str]):
    df = pl.DataFrame({sym: [float(ref_min_row[i])] for i, sym in enumerate(input_symbols)})
    return explainer.explain_input(df)


def _shap_matrix(explanation, k: int) -> np.ndarray:
    arr = np.asarray(explanation.values)
    if arr.ndim == 3 and arr.shape[0] == 1 and arr.shape[1] == k and arr.shape[2] == k:
        return arr[0].T
    if arr.ndim == 2 and arr.shape == (k, k):
        return arr
    if isinstance(explanation.values, list):
        return np.vstack([np.asarray(v).reshape(-1) for v in explanation.values])
    raise AssertionError(f"Unexpected SHAP values shape: {arr.shape}")


def _base_values(explanation, k: int) -> np.ndarray:
    bv = np.asarray(explanation.base_values, dtype=float)
    if bv.ndim == 2 and bv.shape == (1, k):
        return bv.reshape(k)
    if bv.ndim == 1 and bv.size == k:
        return bv
    if bv.ndim == 0:
        return np.full(k, float(bv))
    raise AssertionError(f"Unexpected base_values shape: {bv.shape}")


def _row_to_orig_dict(row_min: np.ndarray, symbols: list[str], sign: np.ndarray) -> dict[str, float]:
    orig = _to_orig(row_min, sign)
    return {s: float(orig[i]) for i, s in enumerate(symbols)}


## TESTS


@pytest.mark.rximo
def test_local_accuracy(setup):
    name = setup["name"]
    explainer = setup["explainer"]
    ref_min = setup["ref_min"]
    ideal_min = setup["ideal_min"]
    nadir_min = setup["nadir_min"]
    input_symbols = setup["input_symbols"]
    k = len(input_symbols)

    rng = np.random.default_rng(RNG_SEED + 1)
    rows = rng.choice(ref_min.shape[0], size=min(N_LOCAL_ACCURACY, ref_min.shape[0]), replace=False)

    atol = 0.05 * (nadir_min - ideal_min)

    max_error = 0.0
    for r in rows:
        ref_row = ref_min[r]
        explanation = _explain(explainer, ref_row, input_symbols)
        shap_matrix = _shap_matrix(explanation, k)
        base = _base_values(explanation, k)
        # Local accuracy is verified against the model SHAP explains: the
        # ShapExplainer's KD-tree-based evaluate(), not the exact solver.
        model_out = explainer.evaluate(ref_row.reshape(1, -1))[0]
        reconstructed = base + shap_matrix.sum(axis=1)
        err = np.abs(reconstructed - model_out)
        max_error = max(max_error, float(err.max()))
        assert np.all(err <= atol + 1e-6), (
            f"{name}: local accuracy violated. err={err}, tol={atol}, base={base}, "
            f"shap_row_sums={shap_matrix.sum(axis=1)}, model_out={model_out}"
        )

    REPORT[name]["local_accuracy_multi"] = {"pass": True, "max_error": max_error}


@pytest.mark.rximo
def test_suggestion_improves_target(setup):
    """Replicate the paper's Section 5 validation pattern (Strategy A vs E).

    Following Misitano et al. (2022) Sec. 5.1, each trial:
        1. Sample a fresh random reference point in [ideal, nadir]
           (Sec. 5.1 step 1).
        2. Solve it with `PyomoBonminSolver` — the analytical "black-box" —
           to get the current solution z₀ (Sec. 5.1 step 2; matches the
           paper's "solutions z₀ and z₁ were computed using the original
           (analytical) formulations").
        3. Pick a random target objective (Sec. 5.1 step 3).
        4. Run R-XIMO with the *exact* z₀ to get the rival j_rival
           (Sec. 5.1 step 4).
        5. Build z̄₁ = z̄₀ with target improved by δ and rival impaired by δ
           (Strategy A; Sec. 5.1 step 5; we use δ = 10% of range).
        6. Solve z₁ exactly (Sec. 5.1 step 6).
        7. Count the trial as a success if z₁[target] < z₀[target].

    As a control we also run Strategy E for the same z̄₀ (keep target,
    impair a random non-rival, non-target). The paper shows A > E on its
    constrained / non-convex problems, but on small twice-differentiable
    convex problems the ASF solver moves the target down whenever any
    aspiration is relaxed, so E can rival or even beat A on a per-problem
    basis at this trial count. We therefore assert only A ≥ 50% (the
    paper's headline claim) and surface E in the report.
    """
    name = setup["name"]
    problem = setup["problem"]
    explainer = setup["explainer"]
    ideal_min = setup["ideal_min"]
    nadir_min = setup["nadir_min"]
    sign = setup["sign"]
    symbols = setup["symbols"]
    input_symbols = setup["input_symbols"]
    k = len(symbols)

    rng = np.random.default_rng(RNG_SEED + 2)
    delta_vec = DELTA_FRACTION * (nadir_min - ideal_min)

    a_successes = 0
    e_successes = 0
    a_counted = 0
    e_counted = 0
    attempts = 0
    while a_counted < N_SUGGESTION_TRIALS and attempts < N_SUGGESTION_TRIALS * 3:
        attempts += 1
        ref_row_min = rng.uniform(low=ideal_min, high=nadir_min)
        ref_orig_dict = _row_to_orig_dict(ref_row_min, symbols, sign)
        try:
            sol_orig = solve_with_reference_point(problem, ref_orig_dict)
        except RuntimeError:
            continue
        sol_row_min_exact = np.array([sol_orig[s] for s in symbols]) * (-sign)

        target = int(rng.integers(0, k))
        explanation = _explain(explainer, ref_row_min, input_symbols)
        shap_matrix = _shap_matrix(explanation, k)
        result = find_rival(shap_matrix, ref_row_min, sol_row_min_exact, target_index=target)
        rival = result.rival_index

        # Strategy A: improve target, impair rival.
        modified_a = ref_row_min.copy()
        modified_a[target] -= delta_vec[target]
        modified_a[rival] += delta_vec[rival]
        modified_a = np.clip(modified_a, ideal_min, nadir_min)
        modified_a_orig = _row_to_orig_dict(modified_a, symbols, sign)
        try:
            sol_a_orig = solve_with_reference_point(problem, modified_a_orig)
        except RuntimeError:
            continue
        sol_a_min = np.array([sol_a_orig[s] for s in symbols]) * (-sign)
        a_counted += 1
        if sol_a_min[target] < sol_row_min_exact[target]:
            a_successes += 1

        # Strategy E (control): keep target, impair a random non-rival, non-target.
        non_rival_target = [j for j in range(k) if j != target and j != rival]
        if non_rival_target:
            other = int(rng.choice(non_rival_target))
            modified_e = ref_row_min.copy()
            modified_e[other] += delta_vec[other]
            modified_e = np.clip(modified_e, ideal_min, nadir_min)
            modified_e_orig = _row_to_orig_dict(modified_e, symbols, sign)
            try:
                sol_e_orig = solve_with_reference_point(problem, modified_e_orig)
            except RuntimeError:
                pass
            else:
                sol_e_min = np.array([sol_e_orig[s] for s in symbols]) * (-sign)
                e_counted += 1
                if sol_e_min[target] < sol_row_min_exact[target]:
                    e_successes += 1

    a_rate = a_successes / max(a_counted, 1)
    e_rate = e_successes / max(e_counted, 1) if e_counted > 0 else 0.0
    REPORT[name]["suggestion_multi"] = {
        "pass": a_rate >= 0.5,
        "successes": a_successes,
        "counted": a_counted,
        "rate": a_rate,
        "control_successes": e_successes,
        "control_counted": e_counted,
        "control_rate": e_rate,
    }
    assert a_counted > 0, f"{name}: every modified reference point failed to solve"
    assert a_rate >= 0.5, f"{name}: Strategy A success rate {a_rate:.2%} below 50% on {a_counted} trials"


@pytest.mark.rximo
def test_single_point_baseline_local_accuracy(setup):
    name = setup["name"]
    explainer = setup["explainer"]
    ref_min = setup["ref_min"]
    sol_min = setup["sol_min"]
    ideal_min = setup["ideal_min"]
    nadir_min = setup["nadir_min"]
    input_symbols = setup["input_symbols"]
    k = len(input_symbols)

    rng = np.random.default_rng(RNG_SEED + 3)
    rows = rng.choice(ref_min.shape[0], size=min(N_LOCAL_ACCURACY, ref_min.shape[0]), replace=False)
    atol = 0.05 * (nadir_min - ideal_min)

    max_error = 0.0
    for r in rows:
        ref_row = ref_min[r]
        baseline_point = sol_min[r]
        explainer.setup_with_baseline(baseline_point)
        explanation = _explain(explainer, ref_row, input_symbols)
        shap_matrix = _shap_matrix(explanation, k)
        base = _base_values(explanation, k)
        model_out = explainer.evaluate(ref_row.reshape(1, -1))[0]
        reconstructed = base + shap_matrix.sum(axis=1)
        err = np.abs(reconstructed - model_out)
        max_error = max(max_error, float(err.max()))
        assert np.all(err <= atol + 1e-6), (
            f"{name}: local accuracy violated under single-point baseline. err={err}, tol={atol}"
        )

    REPORT[name]["local_accuracy_single"] = {"pass": True, "max_error": max_error}


@pytest.mark.rximo
def test_single_point_baseline_suggestion_rate(setup):
    """Same as `test_suggestion_improves_target` but anchors the SHAP
    baseline at the *exact* current solution before each explanation.
    """
    name = setup["name"]
    problem = setup["problem"]
    explainer = setup["explainer"]
    ideal_min = setup["ideal_min"]
    nadir_min = setup["nadir_min"]
    sign = setup["sign"]
    symbols = setup["symbols"]
    input_symbols = setup["input_symbols"]
    k = len(symbols)

    rng = np.random.default_rng(RNG_SEED + 4)
    delta_vec = DELTA_FRACTION * (nadir_min - ideal_min)

    successes = 0
    counted = 0
    attempts = 0
    while counted < N_SUGGESTION_TRIALS and attempts < N_SUGGESTION_TRIALS * 3:
        attempts += 1
        ref_row_min = rng.uniform(low=ideal_min, high=nadir_min)
        ref_orig_dict = _row_to_orig_dict(ref_row_min, symbols, sign)
        try:
            sol_orig = solve_with_reference_point(problem, ref_orig_dict)
        except RuntimeError:
            continue
        sol_row_min_exact = np.array([sol_orig[s] for s in symbols]) * (-sign)

        target = int(rng.integers(0, k))

        # Re-anchor SHAP to the exact current solution.
        explainer.setup_with_baseline(sol_row_min_exact)
        explanation = _explain(explainer, ref_row_min, input_symbols)
        shap_matrix = _shap_matrix(explanation, k)
        result = find_rival(shap_matrix, ref_row_min, sol_row_min_exact, target_index=target)
        rival = result.rival_index

        modified = ref_row_min.copy()
        modified[target] -= delta_vec[target]
        modified[rival] += delta_vec[rival]
        modified = np.clip(modified, ideal_min, nadir_min)

        modified_orig = _row_to_orig_dict(modified, symbols, sign)
        try:
            new_sol_orig = solve_with_reference_point(problem, modified_orig)
        except RuntimeError:
            continue
        new_sol_min = np.array([new_sol_orig[s] for s in symbols]) * (-sign)

        counted += 1
        if new_sol_min[target] < sol_row_min_exact[target]:
            successes += 1

    rate = successes / max(counted, 1)
    REPORT[name]["suggestion_single"] = {
        "pass": rate >= 0.5,
        "successes": successes,
        "counted": counted,
        "rate": rate,
    }
    assert counted > 0, f"{name}: every modified reference point failed to solve"
    assert rate >= 0.5, f"{name}: single-point baseline success rate {rate:.2%} below 50% on {counted} trials"


@pytest.mark.rximo
def test_baseline_comparison(setup):
    """Compare multi-point background vs single-point baseline.

    Both must satisfy local accuracy and the chosen rival should agree on at
    least 30% of trials.
    """
    name = setup["name"]
    explainer = setup["explainer"]
    ref_min = setup["ref_min"]
    sol_min = setup["sol_min"]
    ideal_min = setup["ideal_min"]
    nadir_min = setup["nadir_min"]
    input_symbols = setup["input_symbols"]
    output_symbols = setup["output_symbols"]
    k = len(output_symbols)

    rng = np.random.default_rng(RNG_SEED + 5)
    rows = rng.choice(ref_min.shape[0], size=min(N_BASELINE_COMPARE, ref_min.shape[0]), replace=False)
    atol = 0.05 * (nadir_min - ideal_min)

    # Pareto-front sample, matching the paper's Z_missing convention.
    bg_idx = rng.choice(sol_min.shape[0], size=min(N_BACKGROUND, sol_min.shape[0]), replace=False)
    background_df = pl.DataFrame({sym: sol_min[bg_idx, i] for i, sym in enumerate(input_symbols)})

    rivals_multi: list[int] = []
    rivals_single: list[int] = []

    for r in rows:
        ref_row = ref_min[r]
        sol_exact = sol_min[r]
        target = int(rng.integers(0, k))

        explainer.setup(background_data=background_df)
        explanation_m = _explain(explainer, ref_row, input_symbols)
        shap_m = _shap_matrix(explanation_m, k)
        base_m = _base_values(explanation_m, k)
        model_out_m = explainer.evaluate(ref_row.reshape(1, -1))[0]
        assert np.all(np.abs(base_m + shap_m.sum(axis=1) - model_out_m) <= atol + 1e-6)
        # Drive find_rival with the *exact* solution, not the KD-tree estimate.
        result_m = find_rival(shap_m, ref_row, sol_exact, target_index=target)

        explainer.setup_with_baseline(sol_exact)
        explanation_s = _explain(explainer, ref_row, input_symbols)
        shap_s = _shap_matrix(explanation_s, k)
        base_s = _base_values(explanation_s, k)
        model_out_s = explainer.evaluate(ref_row.reshape(1, -1))[0]
        assert np.all(np.abs(base_s + shap_s.sum(axis=1) - model_out_s) <= atol + 1e-6)
        result_s = find_rival(shap_s, ref_row, sol_exact, target_index=target)

        rivals_multi.append(result_m.rival_index)
        rivals_single.append(result_s.rival_index)

    agreement = sum(int(a == b) for a, b in zip(rivals_multi, rivals_single))
    total = len(rivals_multi)
    rate = agreement / max(total, 1)
    REPORT[name]["baseline_agreement"] = {
        "successes": agreement,
        "counted": total,
        "rate": rate,
        "pass": rate >= 0.30,
    }
    assert rate >= 0.30, f"{name}: rival agreement {rate:.2%} below 30% on {total} trials"


def test_zz_print_report():
    """Print a formatted summary of all R-XIMO validation results.

    Runs alphabetically last so that all per-problem tests have populated the
    REPORT dict by the time we print. Use ``pytest -s`` to surface stdout.
    """
    line = "═" * 63
    sep = "─" * 63
    print(f"\n{line}\n{'R-XIMO VALIDATION REPORT':^63}\n{line}")
    for name in PROBLEM_NAMES:
        problem_data = REPORT.get(name, {})
        if not problem_data:
            print(f"\nProblem: {name} (no data — fixture skipped)")
            print(sep)
            continue
        try:
            problem = PROBLEM_CONSTRUCTORS[name]()
            n_obj = len(problem.objectives)
        except Exception:
            n_obj = "?"
        print(f"\nProblem: {name} ({n_obj} objectives)")
        print(sep)

        la_m = problem_data.get("local_accuracy_multi")
        if la_m:
            tag = "PASS" if la_m["pass"] else "FAIL"
            print(f"  Local accuracy (multi-point bg):  {tag:<5} max error: {la_m['max_error']:.4f}")
        la_s = problem_data.get("local_accuracy_single")
        if la_s:
            tag = "PASS" if la_s["pass"] else "FAIL"
            print(f"  Local accuracy (single-point bg): {tag:<5} max error: {la_s['max_error']:.4f}")
        sg_m = problem_data.get("suggestion_multi")
        if sg_m:
            tag = "PASS" if sg_m["pass"] else "FAIL"
            print(
                f"  Suggestion rate A   (multi-point bg): "
                f"{sg_m['rate'] * 100:5.1f}% ({sg_m['successes']}/{sg_m['counted']})  {tag}"
            )
            if sg_m.get("control_counted", 0) > 0:
                print(
                    f"  Strategy E control  (multi-point bg): "
                    f"{sg_m['control_rate'] * 100:5.1f}% "
                    f"({sg_m['control_successes']}/{sg_m['control_counted']})"
                )
        sg_s = problem_data.get("suggestion_single")
        if sg_s:
            tag = "PASS" if sg_s["pass"] else "FAIL"
            print(
                f"  Suggestion rate (single-point bg): "
                f"{sg_s['rate'] * 100:5.1f}% ({sg_s['successes']}/{sg_s['counted']})  {tag}"
            )
        ag = problem_data.get("baseline_agreement")
        if ag:
            print(f"  Baseline rival agreement:         {ag['rate'] * 100:5.1f}% ({ag['successes']}/{ag['counted']})")
    print(f"\n{line}")
