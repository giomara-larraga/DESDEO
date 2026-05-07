"""R-XIMO: Reference point based eXplainable Interactive Multiobjective Optimization.

Implements Algorithm 1 from:
Misitano, G., Afsar, B., Lárraga, G., & Miettinen, K. (2022).
Towards explainable interactive multiobjective optimization: R-XIMO.
Autonomous Agents and Multi-Agent Systems, 36(43).

The algorithm consumes a square SHAP value matrix that describes how each
component of a reference point contributed to each component of the
solution returned by a reference point based interactive multiobjective
optimization method. By comparing the reference point with the solution
together with the SHAP matrix, R-XIMO produces a textual explanation and
an actionable suggestion for the decision maker.
"""

from collections.abc import Callable
from typing import Any

import numpy as np
import polars as pl
from pydantic import BaseModel, ConfigDict

from .explainer import ShapExplainer


class RXIMOResult(BaseModel):
    """Result of running the R-XIMO algorithm."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    rival_index: int
    """Index of the objective the DM should consider impairing."""
    explanation: str
    """Textual explanation of why the solution looks the way it does."""
    suggestion: str
    """Actionable suggestion for the DM (improve target, impair rival)."""
    explanation_index: int
    """Which of the 9 explanation cases (1-9) was triggered."""
    shap_values: np.ndarray
    """The k x k SHAP value matrix used to derive the explanation."""
    best_effect: int
    """Index of the most improving effect on the target objective (-1 if none)."""
    worst_effect: int
    """Index of the most impairing effect on the target objective (-1 if none)."""
    target_index: int
    """Index of the target objective for which the explanation was produced."""


def why_objective_i(shap_values: np.ndarray, objective_i: int) -> tuple[int, int]:
    """Determine the most improving and most impairing effects on objective `objective_i`.

    For minimization, a negative SHAP value implies an improving effect (the
    component of the reference point pushed the corresponding objective value
    in the solution down) while a positive SHAP value implies an impairing
    effect.

    Args:
        shap_values (np.ndarray): the SHAP value matrix of shape (k, k).
            Element [i, j] represents how the j-th component of the
            reference point affected the i-th objective in the solution.
        objective_i (int): index of the objective whose row is analyzed.

    Returns:
        tuple[int, int]: (best_effect_index, worst_effect_index). The
            best_effect_index is -1 when no value in the row is negative,
            and the worst_effect_index is -1 when no value in the row is
            positive.
    """
    row = np.asarray(shap_values)[objective_i]

    best_effect = int(np.argmin(row)) if np.any(row <= 0) else -1
    worst_effect = int(np.argmax(row)) if np.any(row > 0) else -1

    return best_effect, worst_effect


def _name(objective_names: list[str] | None, index: int) -> str:
    if objective_names is not None and 0 <= index < len(objective_names):
        return objective_names[index]
    return f"Objective {index + 1}"


def _suggestion_text(target_name: str, rival_name: str) -> str:
    return f"Try improving the component {target_name} and impairing the component {rival_name}."


def find_rival(
    shap_values: np.ndarray,
    reference_point: np.ndarray,
    solution: np.ndarray,
    target_index: int,
    objective_names: list[str] | None = None,
) -> RXIMOResult:
    """Run Algorithm 1 of R-XIMO to identify a rival objective and explanation.

    Args:
        shap_values (np.ndarray): square SHAP value matrix of shape (k, k).
        reference_point (np.ndarray): 1D array of length k with the reference
            point components. Assumes minimization.
        solution (np.ndarray): 1D array of length k with the corresponding
            solution. Assumes minimization.
        target_index (int): index of the objective the DM is interested in
            improving further.
        objective_names (list[str] | None): optional list of human readable
            objective names. When None, names like "Objective 1" are used.

    Returns:
        RXIMOResult: the rival objective index, the explanation text, the
            suggestion text and supporting metadata.
    """
    shap_matrix = np.asarray(shap_values, dtype=float)
    ref = np.asarray(reference_point, dtype=float).reshape(-1)
    sol = np.asarray(solution, dtype=float).reshape(-1)

    k = shap_matrix.shape[0]
    if shap_matrix.shape != (k, k):
        raise ValueError(f"shap_values must be a square matrix, got shape {shap_matrix.shape}.")
    if ref.size != k or sol.size != k:
        raise ValueError("reference_point and solution must have length matching shap_values dimension.")
    if not 0 <= target_index < k:
        raise ValueError(f"target_index {target_index} out of range for k={k}.")

    best_effect, worst_effect = why_objective_i(shap_matrix, target_index)

    # Convention: diff = reference_point - solution. For minimization, diff > 0 means
    # the solution improved over the reference point. diff <= 0 means the solution
    # got worse (or stayed equal) for that component.
    diff = ref - sol
    all_worse = bool(np.all(diff <= 0))
    all_better = bool(np.all(diff > 0))

    target_name = _name(objective_names, target_index)
    row = shap_matrix[target_index]

    def _argmax_excluding(target: int) -> int:
        mask = np.ones_like(row, dtype=bool)
        mask[target] = False
        # argmax over the remaining entries; map back to original index.
        candidate_indices = np.flatnonzero(mask)
        return int(candidate_indices[np.argmax(row[candidate_indices])])

    if all_worse:
        if worst_effect != target_index:
            rival = worst_effect
            rival_name = _name(objective_names, rival)
            explanation = (
                f"The reference point appears to be too demanding. The component {rival_name} of "
                f"the reference point has the most impairing effect on the component {target_name} "
                "in the solution."
            )
            suggestion = _suggestion_text(target_name, rival_name)
            case = 1
        else:
            rival = _argmax_excluding(target_index)
            rival_name = _name(objective_names, rival)
            explanation = (
                f"The reference point appears to be too demanding. The component {target_name} of "
                f"the reference point has the most impairing effect on itself, and the component "
                f"{rival_name} has the second most impairing effect on {target_name} in the solution."
            )
            suggestion = _suggestion_text(target_name, rival_name)
            case = 2
    elif all_better:
        # When everything has improved we redefine worst_effect over the full row
        # (including the diagonal) per the algorithm.
        worst_effect_all = int(np.argmax(row))
        if target_index == worst_effect_all:
            rival = _argmax_excluding(target_index)
            rival_name = _name(objective_names, rival)
            explanation = (
                f"The solution looks pessimistic relative to the reference point. The component "
                f"{target_name} of the reference point has the least improving effect on itself, "
                f"and the component {rival_name} has the second least improving effect on "
                f"{target_name} in the solution."
            )
            suggestion = _suggestion_text(target_name, rival_name)
            case = 3
        else:
            rival = worst_effect_all
            rival_name = _name(objective_names, rival)
            explanation = (
                f"The solution looks pessimistic relative to the reference point. The component "
                f"{rival_name} of the reference point has the least improving effect on the "
                f"component {target_name} in the solution."
            )
            suggestion = _suggestion_text(target_name, rival_name)
            case = 4
    elif target_index not in (best_effect, worst_effect):
        if best_effect == -1:
            rival = worst_effect
            rival_name = _name(objective_names, rival)
            explanation = (
                f"No component of the reference point had an improving effect on the component "
                f"{target_name} in the solution. The component {rival_name} has the most impairing "
                f"effect on {target_name}."
            )
            suggestion = _suggestion_text(target_name, rival_name)
            case = 5
        elif worst_effect == -1:
            rival = _argmax_excluding(target_index)
            rival_name = _name(objective_names, rival)
            explanation = (
                f"No component of the reference point had an impairing effect on the component "
                f"{target_name} in the solution. The component {rival_name} has the least improving "
                f"effect on {target_name}."
            )
            suggestion = _suggestion_text(target_name, rival_name)
            case = 6
        else:
            best_name = _name(objective_names, best_effect)
            rival = worst_effect
            rival_name = _name(objective_names, rival)
            explanation = (
                f"The component {best_name} of the reference point has the most improving effect "
                f"on the component {target_name} in the solution, while the component {rival_name} "
                f"has the most impairing effect on {target_name}."
            )
            suggestion = _suggestion_text(target_name, rival_name)
            case = 7
    elif target_index == worst_effect:
        rival = _argmax_excluding(target_index)
        rival_name = _name(objective_names, rival)
        explanation = (
            f"The component {target_name} of the reference point has the most impairing effect on "
            f"itself, and the component {rival_name} has the second most impairing effect on "
            f"{target_name} in the solution."
        )
        suggestion = _suggestion_text(target_name, rival_name)
        case = 8
    elif worst_effect == -1:
        rival = _argmax_excluding(target_index)
        rival_name = _name(objective_names, rival)
        explanation = (
            f"No component of the reference point had an impairing effect on the component "
            f"{target_name} in the solution. The component {rival_name} has the least improving "
            f"effect on {target_name}."
        )
        suggestion = _suggestion_text(target_name, rival_name)
        case = 6
    else:
        # target_index == best_effect
        rival = worst_effect
        rival_name = _name(objective_names, rival)
        explanation = (
            f"The component {target_name} of the reference point has the most improving effect on "
            f"itself, and the component {rival_name} has the most impairing effect on "
            f"{target_name} in the solution."
        )
        suggestion = _suggestion_text(target_name, rival_name)
        case = 9

    return RXIMOResult(
        rival_index=int(rival),
        explanation=explanation,
        suggestion=suggestion,
        explanation_index=case,
        shap_values=shap_matrix,
        best_effect=best_effect,
        worst_effect=worst_effect,
        target_index=target_index,
    )


def generate_reference_point_data(
    n_samples: int,
    ideal: np.ndarray,
    nadir: np.ndarray,
    scalarization_callable: Callable[[np.ndarray], np.ndarray],
    seed: int | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate (reference_point, solution) pairs for training a SHAP explainer.

    Reference points are sampled uniformly from the box defined by the ideal
    and nadir points. For each sampled reference point, `scalarization_callable`
    is invoked to produce the corresponding solution.

    Args:
        n_samples (int): number of reference point/solution pairs to generate.
        ideal (np.ndarray): 1D array of length k containing the ideal point.
        nadir (np.ndarray): 1D array of length k containing the nadir point.
        scalarization_callable (Callable): function that maps a single
            reference point (1D array of length k) to a solution (1D array of
            length k).
        seed (int | None): optional random seed for reproducibility.

    Returns:
        tuple[np.ndarray, np.ndarray]: (reference_points, solutions). Both are
            2D arrays of shape (n_samples, k).
    """
    ideal_arr = np.asarray(ideal, dtype=float).reshape(-1)
    nadir_arr = np.asarray(nadir, dtype=float).reshape(-1)
    if ideal_arr.shape != nadir_arr.shape:
        raise ValueError("ideal and nadir must have matching shapes.")

    rng = np.random.default_rng(seed)
    low = np.minimum(ideal_arr, nadir_arr)
    high = np.maximum(ideal_arr, nadir_arr)

    reference_points = rng.uniform(low=low, high=high, size=(n_samples, ideal_arr.size))
    solutions = np.empty_like(reference_points)
    for i in range(n_samples):
        solutions[i] = np.asarray(scalarization_callable(reference_points[i]), dtype=float).reshape(-1)

    return reference_points, solutions


def _to_array(
    value: np.ndarray | dict[str, float] | list[float],
    symbols: list[str] | None,
) -> np.ndarray:
    if isinstance(value, dict):
        if symbols is None:
            raise ValueError("Symbols must be provided when reference_point/solution is a dict.")
        return np.array([float(value[s]) for s in symbols], dtype=float)
    return np.asarray(value, dtype=float).reshape(-1)


def _stack_shap_values(raw_values: Any, k: int) -> np.ndarray:
    """Build a k x k matrix from a SHAP Explanation `.values` payload.

    The returned matrix has rows indexed by output (objective) and columns
    indexed by input (reference point component): Φ[i, j] = effect of the
    j-th reference point component on the i-th objective in the solution.

    `.values` may take several shapes depending on the SHAP version:
    - a 3D array of shape (n_samples, n_features, n_outputs) — the modern
      multi-output convention. We squeeze the sample axis and transpose to
      put outputs on the rows.
    - a list of `k` arrays each of shape (1, k) — older multi-output
      convention with one entry per output. Stacking yields rows = outputs.
    - a 2D array of shape (k, k) already arranged as Φ.
    """
    if isinstance(raw_values, list):
        rows = [np.asarray(v).reshape(-1) for v in raw_values]
        matrix = np.vstack(rows)
        if matrix.shape != (k, k):
            raise ValueError(f"Stacked SHAP values have shape {matrix.shape}, expected {(k, k)}.")
        return matrix

    arr = np.asarray(raw_values)
    if arr.ndim == 3 and arr.shape[0] == 1 and arr.shape[1] == k and arr.shape[2] == k:  # noqa: PLR2004
        # (1, n_features, n_outputs) -> (n_outputs, n_features) so rows are objectives.
        return arr[0].T
    if arr.ndim == 2 and arr.shape == (k, k):  # noqa: PLR2004
        return arr
    raise ValueError(f"Cannot interpret SHAP values with shape {arr.shape} for k={k}.")


def run_rximo(
    explainer: ShapExplainer,
    reference_point: np.ndarray | dict[str, float],
    solution: np.ndarray | dict[str, float],
    target_index: int,
    input_symbols: list[str] | None = None,
    output_symbols: list[str] | None = None,
    objective_names: list[str] | None = None,
) -> RXIMOResult:
    """Run the full R-XIMO flow given a configured `ShapExplainer`.

    Computes the SHAP values for the supplied reference point, extracts the
    k x k matrix of effects of each reference point component on each
    objective, and runs `find_rival` to obtain the explanation and suggestion.

    Args:
        explainer (ShapExplainer): a `ShapExplainer` whose `setup` method has
            been called with appropriate background data.
        reference_point: the reference point as a 1D array, list, or as a
            dict mapping input symbols to values.
        solution: the corresponding solution as a 1D array, list, or as a
            dict mapping output symbols to values.
        target_index (int): index of the target objective in the row order of
            the SHAP matrix.
        input_symbols (list[str] | None): symbols defining the order of the
            reference point components. Falls back to
            `explainer.input_symbols` when None.
        output_symbols (list[str] | None): symbols defining the order of the
            solution components. Falls back to `explainer.output_symbols`
            when None.
        objective_names (list[str] | None): optional human readable names for
            the objectives, used in the textual explanation. Falls back to
            `output_symbols` when None.

    Returns:
        RXIMOResult: the explanation, suggestion and supporting metadata.
    """
    in_syms = input_symbols if input_symbols is not None else explainer.input_symbols
    out_syms = output_symbols if output_symbols is not None else explainer.output_symbols
    if objective_names is None:
        objective_names = list(out_syms)

    ref_array = _to_array(reference_point, in_syms)
    sol_array = _to_array(solution, out_syms)

    k = len(out_syms)

    explanation = explainer.explain_input(
        pl.DataFrame({s: [float(v)] for s, v in zip(in_syms, ref_array, strict=True)})
    )
    shap_matrix = _stack_shap_values(explanation.values, k)

    return find_rival(
        shap_values=shap_matrix,
        reference_point=ref_array,
        solution=sol_array,
        target_index=target_index,
        objective_names=objective_names,
    )
