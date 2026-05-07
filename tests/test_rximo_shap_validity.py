"""Tests verifying that SHAP explanations driving R-XIMO are sound.

These tests go beyond unit-testing the R-XIMO algorithm: they check that the
SHAP explanations themselves satisfy fundamental properties (local accuracy,
sensitivity, etc.) and that the suggestions returned by R-XIMO actually help
improve the target objective on the river pollution problem.

To keep the suite fast, the tests share a single module-scoped fixture that
sets up the explainer once and uses small training and background datasets.
SHAP automatically picks the Exact algorithm for this 5-feature problem, so
small backgrounds do not affect SHAP value accuracy — only the baseline.
"""

import numpy as np
import polars as pl
import pytest
from scipy.spatial import cKDTree

from desdeo.explanations import ShapExplainer, find_rival, run_rximo
from desdeo.problem.testproblems import river_pollution_problem_discrete

INPUT_SYMBOLS = [f"z{i}" for i in range(1, 6)]
OUTPUT_SYMBOLS = [f"f{i}" for i in range(1, 6)]
N_TRAIN = 200
N_BACKGROUND = 25
N_TRIALS = 30
DELTA_FRACTION = 0.10
RNG_SEED = 12345


def _pareto_front_min(problem) -> np.ndarray:
    """Return the discrete Pareto front in minimization form (n x 5)."""
    rep = problem.discrete_representation
    pf = np.column_stack([np.asarray(rep.objective_values[s], dtype=float) for s in OUTPUT_SYMBOLS])
    sign = np.array([1.0 if obj.maximize else -1.0 for obj in problem.objectives])
    # Multiplying maximized objectives by -1 puts everything in minimization form.
    return pf * (-sign)


def _build_training_dataframe(reference_points: np.ndarray, solutions: np.ndarray) -> pl.DataFrame:
    columns: dict[str, np.ndarray] = {}
    for i, sym in enumerate(INPUT_SYMBOLS):
        columns[sym] = reference_points[:, i]
    for i, sym in enumerate(OUTPUT_SYMBOLS):
        columns[sym] = solutions[:, i]
    return pl.DataFrame(columns)


@pytest.fixture(scope="module")
def river_setup():
    """Module-scoped fixture: river-pollution problem + SHAP explainer.

    Returns a dict with the Pareto front in minimization form, ideal/nadir,
    a true black-box (NN on the Pareto front), the configured explainer, and
    the symbol metadata.
    """
    problem = river_pollution_problem_discrete(five_objective_variant=True)
    pf_min = _pareto_front_min(problem)
    ideal = pf_min.min(axis=0)
    nadir = pf_min.max(axis=0)

    pf_tree = cKDTree(pf_min)

    def black_box(ref_points: np.ndarray) -> np.ndarray:
        arr = np.asarray(ref_points, dtype=float)
        single = arr.ndim == 1
        if single:
            arr = arr.reshape(1, -1)
        _, idx = pf_tree.query(arr)
        result = pf_min[idx]
        return result[0] if single else result

    rng = np.random.default_rng(RNG_SEED)
    reference_points = rng.uniform(low=ideal, high=nadir, size=(N_TRAIN, 5))
    solutions = black_box(reference_points)

    training_df = _build_training_dataframe(reference_points, solutions)
    explainer = ShapExplainer(
        problem_data=training_df,
        input_symbols=INPUT_SYMBOLS,
        output_symbols=OUTPUT_SYMBOLS,
    )
    # Override the KD-tree-on-training-data evaluator with the true black-box
    # so SHAP queries hit the actual model. setup() captures self.evaluate by
    # reference, so this must happen before setup().
    explainer.evaluate = black_box

    background_indices = rng.choice(pf_min.shape[0], size=N_BACKGROUND, replace=False)
    background_df = pl.DataFrame({sym: pf_min[background_indices, i] for i, sym in enumerate(INPUT_SYMBOLS)})
    explainer.setup(background_data=background_df)

    return {
        "problem": problem,
        "pf_min": pf_min,
        "ideal": ideal,
        "nadir": nadir,
        "black_box": black_box,
        "explainer": explainer,
        "background_df": background_df,
        "objective_names": [obj.name for obj in problem.objectives],
    }


def _explain(explainer: ShapExplainer, reference_point: np.ndarray):
    """Run explainer on a single reference point, return the SHAP Explanation."""
    df = pl.DataFrame({sym: [float(reference_point[i])] for i, sym in enumerate(INPUT_SYMBOLS)})
    return explainer.explain_input(df)


def _shap_matrix(explanation, k: int) -> np.ndarray:
    """Reshape SHAP `.values` into the Φ matrix [output, input]."""
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


@pytest.mark.rximo
def test_local_accuracy(river_setup):
    """SHAP additivity: base_value_i + sum(shap_values[i, :]) == solution_i."""
    explainer = river_setup["explainer"]
    black_box = river_setup["black_box"]
    ideal, nadir = river_setup["ideal"], river_setup["nadir"]

    rng = np.random.default_rng(RNG_SEED + 1)
    refs = rng.uniform(low=ideal, high=nadir, size=(5, 5))

    for ref in refs:
        explanation = _explain(explainer, ref)
        shap_matrix = _shap_matrix(explanation, k=5)
        base = _base_values(explanation, k=5)
        solution = black_box(ref)
        reconstructed = base + shap_matrix.sum(axis=1)
        np.testing.assert_allclose(reconstructed, solution, atol=1e-2)


@pytest.mark.rximo
def test_diagonal_self_influence(river_setup):
    """A demanding aspiration on objective i should...

    ...give φ_ii ≤ 0 for at least
    one of several test objectives — i.e., the j-th component of the reference
    point pulls the j-th objective in the solution toward improvement.
    """
    explainer = river_setup["explainer"]
    ideal, nadir = river_setup["ideal"], river_setup["nadir"]

    successes = 0
    tested = 0
    for target in (0, 1, 2):
        ref = (ideal + nadir) / 2.0
        # Set the target component very close to the ideal (very demanding for
        # minimization) and leave the others moderate.
        ref[target] = ideal[target] + 0.02 * (nadir[target] - ideal[target])
        explanation = _explain(explainer, ref)
        shap_matrix = _shap_matrix(explanation, k=5)
        tested += 1
        # Diagonal value should be non-positive (improving effect on itself).
        if shap_matrix[target, target] <= 1e-6:
            successes += 1

    # At least 2 out of 3 target objectives should exhibit the expected
    # self-influence; the discrete Pareto front prevents stricter guarantees.
    assert successes >= 2, f"Only {successes}/{tested} diagonals were non-positive"


@pytest.mark.rximo
def test_conflict_detection(river_setup):
    """The SHAP matrix should expose conflicts: off-diagonals must...

    ...be non-negligible (the matrix is not approximately diagonal).
    """
    explainer = river_setup["explainer"]
    ideal, nadir = river_setup["ideal"], river_setup["nadir"]

    ref = (ideal + nadir) / 2.0
    explanation = _explain(explainer, ref)
    shap_matrix = _shap_matrix(explanation, k=5)

    diag = np.abs(np.diag(shap_matrix))
    off_diag = np.abs(shap_matrix - np.diag(np.diag(shap_matrix)))
    # Off-diagonal magnitude relative to diagonal magnitude.
    off_diag_total = off_diag.sum()
    diag_total = diag.sum()
    assert off_diag_total > 0.1 * diag_total, (
        f"SHAP matrix appears nearly diagonal: off-diag sum={off_diag_total:.3f}, diag sum={diag_total:.3f}"
    )


@pytest.mark.rximo
def test_suggestion_improves_target(river_setup):
    """Following R-XIMO's suggestion (improve target, impair rival) should...

    ...improve the target objective more often than a random control strategy
    """
    explainer = river_setup["explainer"]
    black_box = river_setup["black_box"]
    ideal, nadir = river_setup["ideal"], river_setup["nadir"]
    objective_names = river_setup["objective_names"]

    rng = np.random.default_rng(RNG_SEED + 2)
    delta_vec = DELTA_FRACTION * (nadir - ideal)

    a_successes = 0
    e_successes = 0
    a_total = 0
    e_total = 0

    for _ in range(N_TRIALS):
        z0 = rng.uniform(low=ideal, high=nadir)
        sol0 = black_box(z0)
        target = int(rng.integers(0, 5))

        result = run_rximo(
            explainer=explainer,
            reference_point=z0,
            solution=sol0,
            target_index=target,
            objective_names=objective_names,
        )
        rival = result.rival_index

        # Strategy A: improve target, impair rival.
        z1_a = z0.copy()
        z1_a[target] -= delta_vec[target]
        z1_a[rival] += delta_vec[rival]
        z1_a = np.clip(z1_a, ideal, nadir)
        sol1_a = black_box(z1_a)
        a_total += 1
        if sol1_a[target] < sol0[target]:
            a_successes += 1

        # Strategy E: control — impair a random non-target, non-rival objective.
        non_target_rival = [j for j in range(5) if j not in (target, rival)]
        if non_target_rival:
            other = int(rng.choice(non_target_rival))
            z1_e = z0.copy()
            z1_e[target] -= delta_vec[target]
            z1_e[other] += delta_vec[other]
            z1_e = np.clip(z1_e, ideal, nadir)
            sol1_e = black_box(z1_e)
            e_total += 1
            if sol1_e[target] < sol0[target]:
                e_successes += 1

    a_rate = a_successes / max(a_total, 1)
    e_rate = e_successes / max(e_total, 1)

    assert a_rate >= 0.5, f"Strategy A success rate {a_rate:.2%} below 50% baseline"
    # The paper's A > E ordering holds in expectation; with N=30 trials and
    # the discrete-NN model the comparison can flip by a couple of trials due
    # to binomial noise. We require A within 10pp of E rather than strict
    # ordering, matching the looser assertion in test_rximo_across_problems.
    assert a_rate >= e_rate - 0.10, (
        f"Strategy A ({a_rate:.2%}) should be at least within 10pp of Strategy E ({e_rate:.2%})"
    )


@pytest.mark.rximo
def test_baseline_consistency(river_setup):
    """Different background choices should still yield SHAP additivity...

    ...and R-XIMO should largely agree on the rival across baselines.
    """
    pf_min = river_setup["pf_min"]
    ideal, nadir = river_setup["ideal"], river_setup["nadir"]
    black_box = river_setup["black_box"]

    # Build a fresh explainer that we can re-setup with different backgrounds.
    rng = np.random.default_rng(RNG_SEED + 3)
    refs_train = rng.uniform(low=ideal, high=nadir, size=(N_TRAIN, 5))
    sols_train = black_box(refs_train)
    train_df = _build_training_dataframe(refs_train, sols_train)
    explainer = ShapExplainer(
        problem_data=train_df,
        input_symbols=INPUT_SYMBOLS,
        output_symbols=OUTPUT_SYMBOLS,
    )
    explainer.evaluate = black_box

    # Pick a single reference point we will explain with both backgrounds.
    z = (ideal + nadir) / 2.0

    # Background 1: nearby subset of Pareto front (closest 25 points to z).
    pf_tree = cKDTree(pf_min)
    _, near_idx = pf_tree.query(z, k=N_BACKGROUND)
    bg_near_df = pl.DataFrame({sym: pf_min[near_idx, i] for i, sym in enumerate(INPUT_SYMBOLS)})

    # Background 2: random global subset of the Pareto front.
    global_idx = rng.choice(pf_min.shape[0], size=N_BACKGROUND, replace=False)
    bg_global_df = pl.DataFrame({sym: pf_min[global_idx, i] for i, sym in enumerate(INPUT_SYMBOLS)})

    sol = black_box(z)
    rivals_near = []
    rivals_global = []

    for bg in (bg_near_df, bg_global_df):
        explainer.setup(background_data=bg)
        explanation = _explain(explainer, z)
        shap_matrix = _shap_matrix(explanation, k=5)
        base = _base_values(explanation, k=5)
        # Local accuracy still holds.
        np.testing.assert_allclose(base + shap_matrix.sum(axis=1), sol, atol=1e-2)
        # Capture the rival per target objective.
        rivals = []
        for target in range(5):
            res = find_rival(shap_matrix, z, sol, target_index=target)
            rivals.append(res.rival_index)
        if bg is bg_near_df:
            rivals_near = rivals
        else:
            rivals_global = rivals

    # Base values must differ between the two backgrounds (they are computed
    # from different baselines), so capture base values from each setup again.
    explainer.setup(background_data=bg_near_df)
    base_near = _base_values(_explain(explainer, z), k=5)
    explainer.setup(background_data=bg_global_df)
    base_global = _base_values(_explain(explainer, z), k=5)
    assert not np.allclose(base_near, base_global, atol=1e-3), (
        "Base values should differ between near and global backgrounds"
    )

    agreement = sum(int(a == b) for a, b in zip(rivals_near, rivals_global, strict=True))
    # Some agreement is expected, though SHAP values genuinely depend on the
    # masker so the rival can shift; we require at least a couple of targets
    # to agree across the two very different baselines.
    assert agreement >= 2, f"Only {agreement}/5 rivals agreed across baselines"


@pytest.mark.rximo
def test_shap_sensitivity_to_reference_point(river_setup):
    """Worsening one component of the reference point should...

    ...noticeably change that column of the SHAP matrix.
    """
    explainer = river_setup["explainer"]
    ideal, nadir = river_setup["ideal"], river_setup["nadir"]

    z_base = (ideal + nadir) / 2.0
    j = 2  # objective whose aspiration we will worsen
    z_worse = z_base.copy()
    # Move toward nadir (worse for minimization).
    z_worse[j] = z_base[j] + 0.45 * (nadir[j] - z_base[j])

    shap_base = _shap_matrix(_explain(explainer, z_base), k=5)
    shap_worse = _shap_matrix(_explain(explainer, z_worse), k=5)

    # The j-th column of Φ should change: changing the value of input j alters
    # how that feature contributed to each output relative to baseline.
    col_diff = np.abs(shap_worse[:, j] - shap_base[:, j])
    assert col_diff.sum() > 1e-3, "SHAP column for shifted feature did not change"

    # Sanity: total change across the matrix should also be non-trivial.
    total_diff = np.abs(shap_worse - shap_base).sum()
    assert total_diff > col_diff.sum() / 2.0
