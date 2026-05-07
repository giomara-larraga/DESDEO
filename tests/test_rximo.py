"""Tests related to the R-XIMO method."""

import numpy as np
import polars as pl
import pytest

from desdeo.explanations import (
    RXIMOResult,
    ShapExplainer,
    find_rival,
    generate_biased_mean_data,
    run_rximo,
    why_objective_i,
)


@pytest.mark.rximo
def test_why_objective_i_mixed():
    """Mixed positive and negative SHAP values: both effects exist."""
    shap_values = np.array(
        [
            [-0.5, 0.3, 0.1],
            [0.4, -0.2, -0.1],
            [0.0, -0.3, 0.6],
        ]
    )

    best, worst = why_objective_i(shap_values, 0)
    assert best == 0  # most negative in row 0
    assert worst == 1  # most positive in row 0

    best, worst = why_objective_i(shap_values, 1)
    assert best == 1
    assert worst == 0

    best, worst = why_objective_i(shap_values, 2)
    assert best == 1
    assert worst == 2


@pytest.mark.rximo
def test_why_objective_i_all_positive():
    """All-positive row: no improving effect (best_effect = -1)."""
    shap_values = np.array(
        [
            [0.1, 0.5, 0.3],
            [0.2, 0.1, 0.4],
        ]
    )
    best, worst = why_objective_i(shap_values, 0)
    assert best == -1
    assert worst == 1


@pytest.mark.rximo
def test_why_objective_i_all_negative():
    """All-negative row: no impairing effect (worst_effect = -1)."""
    shap_values = np.array(
        [
            [-0.1, -0.5, -0.3],
            [-0.2, -0.1, -0.4],
        ]
    )
    best, worst = why_objective_i(shap_values, 0)
    assert best == 1
    assert worst == -1


@pytest.mark.rximo
def test_find_rival_case1_all_worse_worst_not_target():
    """All worse, worst_effect != target -> rival = worst_effect."""
    shap = np.array(
        [
            [0.1, 0.6, 0.2],
            [0.2, 0.1, 0.3],
            [0.0, 0.2, 0.1],
        ]
    )
    ref = np.array([1.0, 1.0, 1.0])
    sol = np.array([2.0, 2.0, 2.0])  # all worse

    result = find_rival(shap, ref, sol, target_index=0)
    assert isinstance(result, RXIMOResult)
    assert result.explanation_index == 1
    assert result.rival_index == 1


@pytest.mark.rximo
def test_find_rival_case2_all_worse_worst_is_target():
    """All worse, worst_effect == target -> rival = second_worst (excluding target)."""
    shap = np.array(
        [
            [0.6, 0.4, 0.1],
            [0.2, 0.1, 0.3],
            [0.0, 0.2, 0.1],
        ]
    )
    ref = np.array([1.0, 1.0, 1.0])
    sol = np.array([2.0, 2.0, 2.0])  # all worse

    result = find_rival(shap, ref, sol, target_index=0)
    assert result.explanation_index == 2
    assert result.rival_index == 1  # second largest in row 0 excluding column 0


@pytest.mark.rximo
def test_find_rival_case3_all_better_worst_is_target():
    """All better, with target having the largest (least negative) value -> case 3."""
    # Row 0 is all negative, but column 0 is the largest in row 0.
    shap = np.array(
        [
            [-0.1, -0.4, -0.5],
            [-0.2, -0.1, -0.3],
            [0.0, -0.2, -0.1],
        ]
    )
    ref = np.array([5.0, 5.0, 5.0])
    sol = np.array([1.0, 1.0, 1.0])  # all improved

    result = find_rival(shap, ref, sol, target_index=0)
    assert result.explanation_index == 3
    # second_worst excluding target (col 0): argmax of row[1:] is column 1 (-0.4 > -0.5)
    assert result.rival_index == 1


@pytest.mark.rximo
def test_find_rival_case4_all_better_worst_not_target():
    """All better, worst_effect (over full row) != target -> rival = worst_effect."""
    shap = np.array(
        [
            [-0.5, -0.1, -0.3],
            [-0.2, -0.1, -0.3],
            [0.0, -0.2, -0.1],
        ]
    )
    ref = np.array([5.0, 5.0, 5.0])
    sol = np.array([1.0, 1.0, 1.0])  # all improved

    result = find_rival(shap, ref, sol, target_index=0)
    assert result.explanation_index == 4
    assert result.rival_index == 1  # least negative in row 0


@pytest.mark.rximo
def test_find_rival_case5_mixed_no_best_effect():
    """Mixed objectives, target row has no negative values -> case 5."""
    shap = np.array(
        [
            [0.1, 0.5, 0.2],
            [-0.2, -0.1, -0.3],
            [0.0, 0.2, 0.1],
        ]
    )
    ref = np.array([3.0, 3.0, 3.0])
    sol = np.array([4.0, 2.0, 4.0])  # objective 1 better, others worse -> mixed

    result = find_rival(shap, ref, sol, target_index=0)
    assert result.explanation_index == 5
    assert result.rival_index == 1


@pytest.mark.rximo
def test_find_rival_case6_mixed_no_worst_effect():
    """Mixed objectives, target row all-non-positive -> case 6, rival = least negative."""
    ref = np.array([3.0, 3.0, 3.0])
    sol = np.array([2.0, 4.0, 4.0])  # objective 0 better, others worse -> mixed

    # target = 1 (so target is neither best nor worst in row 1, since row 1 worst exists)
    # We need target to be one where best/worst != target. Pick target=2 with row 2 = [0, 0.2, 0.1].
    # Row 2: worst=1 (0.2 positive), best=0 (0 not <0). Actually 0 <= 0 so best=argmin=col 0.
    # Both exist, target=2, neither is target -> case 7 not 6. Need target row with no positive.

    shap2 = np.array(
        [
            [-0.5, -0.1, -0.3],
            [0.2, 0.1, 0.3],
            [-0.5, -0.1, -0.3],
        ]
    )
    result = find_rival(shap2, ref, sol, target_index=2)
    # Row 2 is all-negative -> worst_effect = -1; mixed branch with worst_effect = -1.
    # best_effect = argmin of row 2 = col 0; target=2. Both exist? worst=-1 so case 5/6.
    # best_effect != -1, worst_effect == -1 -> case 6.
    # least_negative excluding target: argmax of row[0:2] = col 1 (-0.1 > -0.5).
    assert result.explanation_index == 6
    assert result.rival_index == 1


@pytest.mark.rximo
def test_find_rival_case7_mixed_both_exist():
    """Mixed objectives, both best and worst exist and neither equals target -> case 7."""
    shap = np.array(
        [
            [-0.5, 0.4, 0.1],
            [0.2, 0.1, 0.3],
            [0.0, 0.2, 0.1],
        ]
    )
    ref = np.array([3.0, 3.0, 3.0])
    # Mixed: f1 improved, f2 worse, f3 same? Let's be concrete: solution improves only objective 1.
    sol = np.array([4.0, 2.0, 4.0])

    # target = 2 -> row 2: best = 0 (0 == 0, since <=0 condition), worst = 1.
    # neither is target=2 -> case 7. rival = worst = 1.
    result = find_rival(shap, ref, sol, target_index=2)
    assert result.explanation_index == 7
    assert result.rival_index == 1


@pytest.mark.rximo
def test_find_rival_case8_target_is_worst():
    """Mixed, i_target equals worst_effect -> case 8, rival = second_worst."""
    shap = np.array(
        [
            [0.6, 0.3, -0.1],
            [-0.2, 0.1, -0.3],
            [0.0, 0.2, 0.1],
        ]
    )
    ref = np.array([3.0, 3.0, 3.0])
    sol = np.array([4.0, 2.0, 4.0])  # mixed

    # target = 0 -> row 0: best = 2 (-0.1), worst = 0 (0.6). target == worst -> case 8.
    # second_worst excluding target=0: argmax of row[1:] = col 1 (0.3).
    result = find_rival(shap, ref, sol, target_index=0)
    assert result.explanation_index == 8
    assert result.rival_index == 1


@pytest.mark.rximo
def test_find_rival_case9_target_is_best():
    """Mixed, i_target equals best_effect, worst_effect != -1 -> case 9, rival = worst."""
    shap = np.array(
        [
            [-0.5, 0.4, 0.1],
            [0.2, 0.1, 0.3],
            [0.0, 0.2, 0.1],
        ]
    )
    ref = np.array([3.0, 3.0, 3.0])
    sol = np.array([4.0, 2.0, 4.0])  # mixed

    # target = 0 -> row 0: best = 0 (-0.5), worst = 1 (0.4). target == best -> case 9.
    result = find_rival(shap, ref, sol, target_index=0)
    assert result.explanation_index == 9
    assert result.rival_index == 1


@pytest.mark.rximo
def test_find_rival_uses_objective_names():
    """Explanations should use provided objective names."""
    shap = np.array(
        [
            [0.1, 0.6, 0.2],
            [0.2, 0.1, 0.3],
            [0.0, 0.2, 0.1],
        ]
    )
    ref = np.array([1.0, 1.0, 1.0])
    sol = np.array([2.0, 2.0, 2.0])

    names = ["price", "quality", "speed"]
    result = find_rival(shap, ref, sol, target_index=0, objective_names=names)
    assert "price" in result.suggestion
    assert "quality" in result.suggestion
    assert "Objective" not in result.explanation


@pytest.mark.rximo
def test_find_rival_validates_inputs():
    """find_rival should raise on shape mismatches."""
    bad_shap = np.zeros((3, 4))
    with pytest.raises(ValueError):
        find_rival(bad_shap, np.zeros(3), np.zeros(3), target_index=0)

    shap = np.zeros((3, 3))
    with pytest.raises(ValueError):
        find_rival(shap, np.zeros(2), np.zeros(3), target_index=0)

    with pytest.raises(ValueError):
        find_rival(shap, np.zeros(3), np.zeros(3), target_index=5)


@pytest.mark.rximo
@pytest.mark.slow
def test_run_rximo_integration():
    """Smoke test that wires up a ShapExplainer and runs the full R-XIMO flow."""
    rng = np.random.default_rng(seed=1)
    n = 100
    x1 = rng.uniform(0, 10, n)
    x2 = rng.uniform(0, 10, n)
    x3 = rng.uniform(0, 10, n)
    data = pl.DataFrame({"z1": x1, "z2": x2, "z3": x3, "f1": x1 + x2 + x3, "f2": x1 - x2 - x3, "f3": x3 - x2})

    explainer = ShapExplainer(
        problem_data=data,
        input_symbols=["z1", "z2", "z3"],
        output_symbols=["f1", "f2", "f3"],
    )

    z_ref = np.array([10.0, 2.0, 4.0])
    target = np.array([z_ref[0], z_ref[1], z_ref[2]])
    background = generate_biased_mean_data(data[["f1", "f2", "f3"]].to_numpy(), target)
    explainer.setup(background_data=pl.DataFrame(data[background]))

    reference = {"z1": float(z_ref[0]), "z2": float(z_ref[1]), "z3": float(z_ref[2])}
    # Use the explainer's evaluate to obtain a "solution" consistent with the simulated black-box.
    solution_array = explainer.evaluate(z_ref.reshape(1, -1))[0]
    solution = {
        "f1": float(solution_array[0]),
        "f2": float(solution_array[1]),
        "f3": float(solution_array[2]),
    }

    result = run_rximo(
        explainer=explainer,
        reference_point=reference,
        solution=solution,
        target_index=0,
    )

    assert isinstance(result, RXIMOResult)
    assert result.shap_values.shape == (3, 3)
    assert 1 <= result.explanation_index <= 9
    assert 0 <= result.rival_index < 3
    assert result.target_index == 0
    assert result.suggestion.startswith("Try improving")
