#!/usr/bin/env python3
"""
Run synchronous NIMBUS directly with DESDEO and validate KKT-based local
trade-off estimates against independently estimated local geometry.

The script:

1. Creates DESDEO's four-objective river-pollution problem.
2. Generates a Pareto-optimal starting solution.
3. Runs one or more synchronous NIMBUS iterations with IPOPT.
4. Reconstructs the exact scalarization that produced each generated solution.
5. Reproduces XNIMBUS's objective-multiplier selection rule.
6. Determines the scaling attached to the selected DESDEO constraint.
7. Compares:
       raw KKT coefficients:        lambda_i
       corrected KKT coefficients:  lambda_i * w_i
   with an independent finite-difference estimate of the local objective-space
   normal.
8. Uses interior reference-point patterns designed to avoid extreme STOM
   scaling and determines participation from the selected raw KKT multipliers
   using the configured multiplier threshold.
9. Writes solution-, pairwise-, and constraint-level CSV diagnostics.

The reviewer-facing comparison is the pairwise CSV:

    KKT trade-off = -c_j / c_i

versus

    finite-difference trade-off = -n_j / n_i,

where c_i = lambda_i * w_i and n is estimated independently from the
finite-difference objective Jacobian.

Run this script from the DESDEO repository/environment. IPOPT must be installed
and available on PATH.

Example
-------
python evaluate_nimbus_tradeoffs_stom.py \
    --iterations 5 \
    --solutions 4 \
    --solution-csv solution_validation.csv \
    --tradeoff-csv tradeoff_validation.csv \
    --constraint-csv constraint_validation.csv
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import numpy as np

from desdeo.mcdm.nimbus import (
    generate_starting_point,
    infer_classifications,
    solve_sub_problems,
)
from desdeo.problem.sympy_evaluator import SympyEvaluator
from desdeo.problem.testproblems.river_pollution_problems import (
    river_pollution_problem,
)
from desdeo.tools.pyomo_solver_interfaces import (
    IpoptOptions,
    PyomoIpoptSolver,
)
from desdeo.tools.scalarization import (
    add_asf_diff,
    add_guess_sf_diff,
    add_nimbus_sf_diff,
    add_stom_sf_diff,
)

from desdeo.tools.utils import (
    flip_maximized_objective_values,
    get_corrected_ideal,
    get_corrected_nadir,
)


SCRIPT_VERSION = "2026-09-05-v3-stom-fix2"


MULTIPLIER_TOL = 1e-5


def compute_xnimbus_effective_multipliers(
    selected_multipliers,
    scalarization,
    ideal,
    nadir,
    reference_point,
    delta=1e-6,
):
    """Reproduce the production XNIMBUS effective-multiplier calculation."""
    effective = {}

    for symbol, (constraint_key, raw_lambda) in selected_multipliers.items():

        if constraint_key is None or abs(raw_lambda) <= MULTIPLIER_TOL:
            effective[symbol] = 0.0
            continue

        if scalarization == "NIMBUS":
            if (
                constraint_key.endswith("_lt")
                or constraint_key.endswith("_lte")
            ):
                coefficient = 1.0 / (
                    nadir[symbol] - (ideal[symbol] - delta)
                )
            elif (
                constraint_key.endswith("_eq")
                or constraint_key.endswith("_gte")
            ):
                coefficient = 1.0
            else:
                raise ValueError(
                    f"Unknown NIMBUS constraint: {constraint_key}"
                )

        elif scalarization == "STOM":
            coefficient = 1.0 / (
                reference_point[symbol]
                - ideal[symbol]
                + delta
            )

        elif scalarization == "ASF":
            coefficient = 1.0 / (
                nadir[symbol]
                - (ideal[symbol] - delta)
            )

        elif scalarization == "GUESS":
            coefficient = 1.0 / (
                nadir[symbol]
                - reference_point[symbol]
            )

        else:
            raise ValueError(
                f"Unknown scalarization: {scalarization}"
            )

        effective[symbol] = raw_lambda * coefficient

    return effective

# ---------------------------------------------------------------------------
# Synthetic preferences for repeated numerical-validation iterations
# ---------------------------------------------------------------------------


def make_reference_point(
    problem,
    current: dict[str, float],
    iteration: int,
) -> dict[str, float]:
    """
    Construct a deterministic NIMBUS-compatible reference point for validation.

    NIMBUS requires the classifications to allow at least one objective to
    improve and at least one objective to worsen.  Therefore, the reference
    point must be defined relative to the *current* solution, not only as an
    interior point between the ideal and nadir values.

    For every iteration, two objectives are moved toward their ideal values
    (improvement) and two are moved toward their nadir values
    (deterioration).  The roles and step sizes rotate across iterations.

    None of the reference components is placed exactly at the ideal or nadir
    point.  This avoids the extremely small STOM denominators that arise when
    a reference component coincides with the ideal/utopian value.

    These are synthetic diagnostic preferences only; they are not intended to
    model a human decision maker.
    """
    objectives = list(problem.objectives)
    n = len(objectives)
    if n != 4:
        raise ValueError(
            "Validation reference patterns are defined for the "
            "four-objective river problem."
        )

    # Positive values mean move toward the ideal; negative values mean move
    # toward the nadir.  Magnitudes are fractions of the remaining distance
    # from the current value to the corresponding bound.  Each pattern has
    # at least one improving and one worsening objective.
    patterns = np.array(
        [
            [ 0.20,  0.40, -0.35, -0.60],
            [-0.45,  0.25,  0.55, -0.30],
            [-0.35, -0.55,  0.20,  0.45],
            [ 0.50, -0.25, -0.45,  0.30],
            [ 0.30,  0.55, -0.20, -0.45],
            [-0.25,  0.45,  0.30, -0.55],
            [-0.50, -0.30,  0.45,  0.20],
            [ 0.40, -0.50, -0.25,  0.55],
        ],
        dtype=float,
    )

    pattern = patterns[iteration % len(patterns)]
    reference: dict[str, float] = {}

    for idx, obj in enumerate(objectives):
        symbol = obj.symbol
        current_value = float(current[symbol])
        ideal = float(obj.ideal)
        nadir = float(obj.nadir)
        step = float(pattern[idx])

        if step > 0.0:
            # Request an improvement, but stay strictly between current and
            # ideal whenever there is room to improve.
            value = current_value + step * (ideal - current_value)
        else:
            # Allow deterioration toward the nadir, but do not go all the way
            # to the nadir.
            value = current_value + abs(step) * (nadir - current_value)

        reference[symbol] = float(value)

    return reference


# ---------------------------------------------------------------------------
# Identify and rebuild the scalarization that generated a solution
# ---------------------------------------------------------------------------


def solution_kind(solution) -> str:
    values = solution.scalarization_values or {}
    keys = set(values.keys())

    if "nimbus_sf" in keys:
        return "NIMBUS"
    if "stom_sf" in keys:
        return "STOM"
    if "asf" in keys:
        return "ASF"
    if "guess_sf" in keys:
        return "GUESS"

    return "UNKNOWN"


def rebuild_scalar_problem(
    kind: str,
    base_problem,
    current_objectives: dict[str, float],
    reference_point: dict[str, float],
):
    """Reconstruct the same DESDEO scalarization used by solve_sub_problems."""
    if kind == "NIMBUS":
        classifications = infer_classifications(
            base_problem,
            current_objectives,
            reference_point,
        )
        return add_nimbus_sf_diff(
            base_problem,
            "nimbus_sf",
            classifications,
            current_objectives,
        )[0]

    if kind == "STOM":
        return add_stom_sf_diff(
            base_problem,
            "stom_sf",
            reference_point,
        )[0]

    if kind == "ASF":
        return add_asf_diff(
            base_problem,
            "asf",
            reference_point,
        )[0]

    if kind == "GUESS":
        return add_guess_sf_diff(
            base_problem,
            "guess_sf",
            reference_point,
        )[0]

    raise ValueError(f"Unsupported scalarization kind: {kind}")


# ---------------------------------------------------------------------------
# Reproduce XNIMBUS multiplier filtering while retaining constraint names
# ---------------------------------------------------------------------------


def selected_multiplier_entries(
    lagrange_multipliers: dict[str, float],
    objective_symbols: list[str],
) -> dict[str, tuple[str | None, float]]:
    """
    Reproduce XNIMBUS's filter_lagrange_multipliers() rule.

    For each objective:
      - group multiplier keys containing the objective symbol;
      - prefer the first key not ending in "eq";
      - otherwise use the first available key;
      - use 0 if no multiplier exists.

    Unlike the router function, this function also returns the selected
    multiplier key so that the associated DESDEO constraint can be inspected.
    """
    grouped = {symbol: [] for symbol in objective_symbols}

    for key, value in (lagrange_multipliers or {}).items():
        for symbol in objective_symbols:
            if symbol in key:
                grouped[symbol].append((key, float(value)))
                break

    selected = {}

    for symbol in objective_symbols:
        entries = grouped[symbol]

        preferred = next(
            (entry for entry in entries if not entry[0].endswith("eq")),
            None,
        )

        if preferred is None and entries:
            preferred = entries[0]

        selected[symbol] = (
            preferred if preferred is not None else (None, 0.0)
        )

    return selected


def grouped_multiplier_entries(
    lagrange_multipliers: dict[str, float],
    objective_symbols: list[str],
) -> dict[str, list[tuple[str, float]]]:
    """Return all multiplier entries whose keys are associated with each objective."""
    grouped = {symbol: [] for symbol in objective_symbols}

    for key, value in (lagrange_multipliers or {}).items():
        for symbol in objective_symbols:
            if symbol in key:
                grouped[symbol].append((key, float(value)))
                break

    return grouped


def multiplier_to_constraint(
    multiplier_key: str | None,
) -> str | None:
    """
    IPOPT multiplier names generated by DESDEO use mu_<constraint-symbol>.
    """
    if multiplier_key is None:
        return None

    if multiplier_key.startswith("mu_"):
        return multiplier_key[3:]

    return multiplier_key


# ---------------------------------------------------------------------------
# Finite-difference derivatives evaluated through DESDEO
# ---------------------------------------------------------------------------


def decision_variable_symbols(problem) -> list[str]:
    return [
        variable.symbol
        for variable in problem.variables
        if variable.symbol != "_alpha"
    ]


def decision_variable_bounds(
    problem,
) -> dict[str, tuple[float, float]]:
    return {
        variable.symbol: (
            float(variable.lowerbound),
            float(variable.upperbound),
        )
        for variable in problem.variables
        if variable.symbol != "_alpha"
    }


def finite_difference_derivative(
    function,
    values: dict[str, float],
    variable: str,
    bounds: tuple[float, float],
    h: float,
) -> float:
    """
    Finite-difference derivative of a scalar DESDEO expression.

    Central differences are used whenever possible. Near a decision-variable
    bound, a one-sided difference is used.
    """
    lower, upper = bounds
    x0 = float(values[variable])

    step = h * max(1.0, abs(x0))

    if x0 - step >= lower and x0 + step <= upper:
        plus = dict(values)
        minus = dict(values)

        plus[variable] = x0 + step
        minus[variable] = x0 - step

        return (
            float(function(plus)) - float(function(minus))
        ) / (2.0 * step)

    if x0 + step <= upper:
        plus = dict(values)
        plus[variable] = x0 + step

        return (
            float(function(plus)) - float(function(values))
        ) / step

    if x0 - step >= lower:
        minus = dict(values)
        minus[variable] = x0 - step

        return (
            float(function(values)) - float(function(minus))
        ) / step

    raise RuntimeError(
        f"Cannot form finite difference for {variable}={x0}."
    )


def objective_jacobian(
    evaluator,
    x_values: dict[str, float],
    variable_symbols: list[str],
    bounds: dict[str, tuple[float, float]],
    objective_symbols: list[str],
    h: float,
) -> np.ndarray:
    """
    Estimate the Jacobian of DESDEO's minimization-form objectives.

    Rows correspond to objectives and columns correspond to decision variables.
    """
    jacobian = np.empty(
        (len(objective_symbols), len(variable_symbols)),
        dtype=float,
    )

    for objective_index, objective in enumerate(objective_symbols):
        target = f"{objective}_min"

        def function(xx):
            return evaluator.evaluate_target(xx, target)

        for variable_index, variable in enumerate(variable_symbols):
            jacobian[objective_index, variable_index] = (
                finite_difference_derivative(
                    function,
                    x_values,
                    variable,
                    bounds[variable],
                    h,
                )
            )

    return jacobian


def scalarization_constraint_gradient(
    evaluator,
    constraint_symbol: str,
    values: dict[str, float],
    variable_symbols: list[str],
    bounds: dict[str, tuple[float, float]],
    h: float,
) -> np.ndarray:
    """Estimate the gradient of one scalarization constraint."""
    def function(xx):
        return evaluator.evaluate_target(
            xx,
            constraint_symbol,
        )

    return np.array(
        [
            finite_difference_derivative(
                function,
                values,
                variable,
                bounds[variable],
                h,
            )
            for variable in variable_symbols
        ],
        dtype=float,
    )


def infer_constraint_scale(
    objective_gradient: np.ndarray,
    constraint_gradient: np.ndarray,
) -> tuple[float, float]:
    """
    Infer w_i from

        grad(g_i) ~= w_i * grad(f_i).

    This derives the scaling from the actual DESDEO scalarization expression
    instead of hard-coding ideal/nadir/reference-point denominators.

    Returns
    -------
    scale
        Inferred scaling coefficient w_i.

    relative_fit_error
        Relative error in representing grad(g_i) as scale * grad(f_i).
        Values close to zero indicate that the relationship is valid.
    """
    denominator = float(
        np.dot(objective_gradient, objective_gradient)
    )

    if denominator <= 1e-28:
        return np.nan, np.nan

    scale = float(
        np.dot(
            constraint_gradient,
            objective_gradient,
        )
        / denominator
    )

    fitted = scale * objective_gradient

    fit_denominator = max(
        np.linalg.norm(constraint_gradient),
        1e-30,
    )

    relative_fit_error = float(
        np.linalg.norm(
            constraint_gradient - fitted
        )
        / fit_denominator
    )

    return scale, relative_fit_error


# ---------------------------------------------------------------------------
# Local objective-space geometry
# ---------------------------------------------------------------------------


def normalize(vector: np.ndarray) -> np.ndarray:
    vector = np.asarray(vector, dtype=float)
    norm = np.linalg.norm(vector)

    if norm == 0:
        raise ValueError("Cannot normalize a zero vector.")

    return vector / norm


def stationarity_residual(
    jacobian: np.ndarray,
    coefficients: np.ndarray,
) -> float:
    """
    Scale-free residual of

        J.T @ coefficients = 0.

    A vector describing the local objective-space normal should produce a
    residual close to zero.
    """
    numerator = np.linalg.norm(
        jacobian.T @ coefficients
    )

    denominator = (
        np.linalg.norm(jacobian, ord="fro")
        * np.linalg.norm(coefficients)
    )

    if denominator == 0:
        return np.nan

    return float(numerator / denominator)


def independent_local_normal(
    jacobian: np.ndarray,
) -> np.ndarray | None:
    """
    Estimate a unique local objective-space normal from the finite-difference
    objective Jacobian.

    For the river problem there are two decision variables. If three
    participating objectives have a rank-2 Jacobian, the nullspace of J.T is
    one-dimensional and therefore defines a unique local normal up to sign.

    Returns None if the nullspace is not one-dimensional.
    """
    rank = np.linalg.matrix_rank(jacobian.T)
    nullity = jacobian.shape[0] - rank

    if nullity != 1:
        return None

    _, _, vh = np.linalg.svd(
        jacobian.T,
        full_matrices=True,
    )

    return normalize(vh[-1])


def angle_degrees(
    first: np.ndarray,
    second: np.ndarray,
) -> float:
    """
    Acute angle between two vectors.

    Absolute value is used because a normal and its negative represent the
    same local tangent plane.
    """
    first = normalize(first)
    second = normalize(second)

    cosine = float(
        np.clip(
            abs(np.dot(first, second)),
            -1.0,
            1.0,
        )
    )

    return math.degrees(math.acos(cosine))


# ---------------------------------------------------------------------------
# Pairwise trade-off validation
# ---------------------------------------------------------------------------


def pairwise_tradeoff_comparisons(
    active_indices: np.ndarray,
    objective_symbols: list[str],
    raw_coefficients: np.ndarray,
    corrected_coefficients: np.ndarray,
    xnimbus_effective_coefficients: np.ndarray,
    aggregated_coefficients: np.ndarray,
    numerical_normal: np.ndarray,
) -> list[dict]:
    """
    Compare pairwise trade-offs with an independently estimated local normal.

    For coefficients c describing a local normal,

        T_(i -> j) = -c_j / c_i.

    Four estimates are reported:

      raw_multiplier_tradeoff
          Uses the one raw multiplier selected by the current XNIMBUS rule.

      selected_scaled_tradeoff
          Uses the selected multiplier multiplied by the inferred scale of
          its associated scalarization constraint.

      aggregated_scaled_tradeoff
          Sums lambda_c * w_c over all objective-related scalarization
          constraints associated with each objective.

      finite_difference_tradeoff
          Uses the local normal independently estimated from finite
          differences of the original objective functions.
    xnimbus_implementation_tradeoff
        Uses the scaling-adjusted coefficients calculated by the production
        XNIMBUS implementation.
    """
    comparisons = []

    for a in range(len(active_indices)):
        for b in range(a + 1, len(active_indices)):
            i = int(active_indices[a])
            j = int(active_indices[b])

            if (
                abs(raw_coefficients[a]) <= 1e-14
                or abs(corrected_coefficients[a]) <= 1e-14
                or abs(xnimbus_effective_coefficients[a]) <= 1e-14
                or abs(aggregated_coefficients[a]) <= 1e-14
                or abs(numerical_normal[a]) <= 1e-14
            ):
                continue

            raw_rate = -raw_coefficients[b] / raw_coefficients[a]
            selected_rate = (
                -corrected_coefficients[b] / corrected_coefficients[a]
            )
            aggregated_rate = (
                -aggregated_coefficients[b] / aggregated_coefficients[a]
            )
            finite_difference_rate = (
                -numerical_normal[b] / numerical_normal[a]
            )

            selected_absolute_error = abs(
                selected_rate - finite_difference_rate
            )
            aggregated_absolute_error = abs(
                aggregated_rate - finite_difference_rate
            )
            raw_absolute_error = abs(
                raw_rate - finite_difference_rate
            )

            if abs(finite_difference_rate) > 1e-12:
                selected_relative_error = (
                    selected_absolute_error
                    / abs(finite_difference_rate)
                )
                aggregated_relative_error = (
                    aggregated_absolute_error
                    / abs(finite_difference_rate)
                )
            else:
                selected_relative_error = np.nan
                aggregated_relative_error = np.nan

            xnimbus_rate = (
                -xnimbus_effective_coefficients[b]
                / xnimbus_effective_coefficients[a]
            )
            
            xnimbus_vs_independent_abs_diff = abs(
                xnimbus_rate - selected_rate
            )

            xnimbus_vs_independent_rel_diff = (
                xnimbus_vs_independent_abs_diff
                / max(abs(selected_rate), 1e-30)
            )

            xnimbus_vs_fd_abs_error = abs(
                xnimbus_rate - finite_difference_rate
            )

            xnimbus_vs_fd_rel_error = (
                xnimbus_vs_fd_abs_error
                / max(abs(finite_difference_rate), 1e-30)
            )

            comparisons.append(
                {
                    "from_objective": objective_symbols[i],
                    "to_objective": objective_symbols[j],
                    "raw_multiplier_tradeoff": float(raw_rate),
                    "selected_scaled_tradeoff": float(selected_rate),
                    "aggregated_scaled_tradeoff": float(aggregated_rate),
                    "finite_difference_tradeoff": float(
                        finite_difference_rate
                    ),
                    "selected_absolute_error": float(
                        selected_absolute_error
                    ),
                    "selected_relative_error": float(
                        selected_relative_error
                    ),
                    "aggregated_absolute_error": float(
                        aggregated_absolute_error
                    ),
                    "aggregated_relative_error": float(
                        aggregated_relative_error
                    ),
                    "raw_absolute_error": float(
                        raw_absolute_error
                    ),
                    "xnimbus_implementation_tradeoff": float(xnimbus_rate),
                    "xnimbus_vs_independent_abs_diff": float(
                        xnimbus_vs_independent_abs_diff
                    ),
                    "xnimbus_vs_independent_rel_diff": float(
                        xnimbus_vs_independent_rel_diff
                    ),
                    "xnimbus_vs_fd_abs_error": float(
                        xnimbus_vs_fd_abs_error
                    ),
                    "xnimbus_vs_fd_rel_error": float(
                        xnimbus_vs_fd_rel_error
                    ),
                }
            )

    return comparisons


# ---------------------------------------------------------------------------
# Evaluate one generated synchronous-NIMBUS solution
# ---------------------------------------------------------------------------


def evaluate_solution(
    iteration: int,
    solution_index: int,
    solution,
    base_problem,
    base_evaluator,
    current_objectives: dict[str, float],
    reference_point: dict[str, float],
    threshold: float,
    h: float,
):
    kind = solution_kind(solution)

    objective_symbols = [
        objective.symbol
        for objective in base_problem.objectives
    ]

    variable_symbols = decision_variable_symbols(
        base_problem
    )

    bounds = decision_variable_bounds(
        base_problem
    )

    if kind == "UNKNOWN":
        return None, [], [], "Unknown scalarization."

    scalar_problem = rebuild_scalar_problem(
        kind,
        base_problem,
        current_objectives,
        reference_point,
    )

    scalar_evaluator = SympyEvaluator(
        scalar_problem
    )

    selected = selected_multiplier_entries(
        solution.lagrange_multipliers,
        objective_symbols,
    )

    corrected_ideal = get_corrected_ideal(base_problem)
    corrected_nadir = get_corrected_nadir(base_problem)

    corrected_reference_point = flip_maximized_objective_values(
        base_problem,
        reference_point,
    )

    xnimbus_effective_dict = compute_xnimbus_effective_multipliers(
        selected_multipliers=selected,
        scalarization=kind,
        ideal=corrected_ideal,
        nadir=corrected_nadir,
        reference_point=corrected_reference_point,
    )

    xnimbus_effective_all = np.array(
        [
            xnimbus_effective_dict[symbol]
            for symbol in objective_symbols
        ],
        dtype=float,
    )

    grouped_entries = grouped_multiplier_entries(
        solution.lagrange_multipliers,
        objective_symbols,
    )

    constraint_rows = []

    lambdas = np.array(
        [
            selected[symbol][1]
            for symbol in objective_symbols
        ],
        dtype=float,
    )

    x_values = {
        variable: float(
            solution.optimal_variables[variable]
        )
        for variable in variable_symbols
    }

    scalar_values = dict(x_values)

    if "_alpha" in solution.optimal_variables:
        scalar_values["_alpha"] = float(
            solution.optimal_variables["_alpha"]
        )

    jacobian = objective_jacobian(
        base_evaluator,
        x_values,
        variable_symbols,
        bounds,
        objective_symbols,
        h,
    )

    # Inspect every objective-related multiplier, not only the one selected by
    # the current XNIMBUS filtering rule.  The scaled contribution of a
    # constraint is lambda_c * w_c, where w_c is inferred from the gradient of
    # the actual DESDEO scalarization constraint.
    aggregated_all = np.zeros(
        len(objective_symbols),
        dtype=float,
    )

    # Effective coefficients used by the explanation layer.  Participation is
    # determined from these scaled coefficients rather than from raw lambda
    # magnitudes, because STOM can legitimately combine a small raw multiplier
    # with a large scalarization weight.
    selected_scaled_all = np.zeros(
        len(objective_symbols),
        dtype=float,
    )

    for objective_index, objective in enumerate(objective_symbols):
        selected_key = selected[objective][0]

        for multiplier_key, multiplier_value in grouped_entries[objective]:
            constraint_symbol = multiplier_to_constraint(
                multiplier_key
            )

            scale = np.nan
            fit_error = np.nan
            scaled_contribution = np.nan
            scale_status = "ok"

            if constraint_symbol is None:
                scale_status = "no_constraint_symbol"
            else:
                try:
                    constraint_gradient = (
                        scalarization_constraint_gradient(
                            scalar_evaluator,
                            constraint_symbol,
                            scalar_values,
                            variable_symbols,
                            bounds,
                            h,
                        )
                    )

                    scale, fit_error = infer_constraint_scale(
                        jacobian[objective_index],
                        constraint_gradient,
                    )

                    if np.isfinite(scale):
                        scaled_contribution = (
                            float(multiplier_value)
                            * float(scale)
                        )
                        aggregated_all[objective_index] += (
                            scaled_contribution
                        )
                        if multiplier_key == selected_key:
                            selected_scaled_all[objective_index] = (
                                scaled_contribution
                            )
                    else:
                        scale_status = "nonfinite_scale"

                except Exception as exception:
                    scale_status = (
                        "scale_inference_failed: "
                        f"{exception}"
                    )

            constraint_rows.append(
                {
                    "iteration": iteration,
                    "solution_index": solution_index,
                    "scalarization": kind,
                    "objective": objective,
                    "multiplier_key": multiplier_key,
                    "constraint_symbol": (
                        constraint_symbol or ""
                    ),
                    "multiplier": float(
                        multiplier_value
                    ),
                    "abs_multiplier": abs(
                        float(multiplier_value)
                    ),
                    "above_threshold": bool(
                        abs(float(multiplier_value))
                        > threshold
                    ),
                    "selected_by_xnimbus": bool(
                        multiplier_key == selected_key
                    ),
                    "constraint_scale": float(scale),
                    "scale_fit_rel_error": float(
                        fit_error
                    ),
                    "scaled_contribution": float(
                        scaled_contribution
                    ),
                    "scale_status": scale_status,
                    "x_1": float(
                        x_values.get("x_1", np.nan)
                    ),
                    "x_2": float(
                        x_values.get("x_2", np.nan)
                    ),
                }
            )

    active = np.flatnonzero(
        np.abs(lambdas) > threshold
    )

    scales = np.full(
        len(objective_symbols),
        np.nan,
    )

    scale_fit_errors = np.full(
        len(objective_symbols),
        np.nan,
    )

    selected_constraints = [
        ""
        for _ in objective_symbols
    ]

    selected_multiplier_keys = [
        ""
        for _ in objective_symbols
    ]

    for index in active:
        objective = objective_symbols[index]

        multiplier_key, _ = selected[objective]

        constraint_symbol = (
            multiplier_to_constraint(
                multiplier_key
            )
        )

        if constraint_symbol is None:
            return (
                None,
                [],
                constraint_rows,
                (
                    "No selected scalarization constraint "
                    f"for active objective {objective}."
                ),
            )

        selected_multiplier_keys[index] = (
            multiplier_key
        )

        selected_constraints[index] = (
            constraint_symbol
        )

        constraint_gradient = (
            scalarization_constraint_gradient(
                scalar_evaluator,
                constraint_symbol,
                scalar_values,
                variable_symbols,
                bounds,
                h,
            )
        )

        scale, fit_error = infer_constraint_scale(
            jacobian[index],
            constraint_gradient,
        )

        if not np.isfinite(scale):
            return (
                None,
                [],
                constraint_rows,
                (
                    "Could not infer scalarization "
                    f"scale for {objective}."
                ),
            )

        scales[index] = scale
        scale_fit_errors[index] = fit_error


    # In a two-variable problem, three participating objectives give a
    # uniquely identifiable one-dimensional left nullspace when rank=2.
    # Constraint diagnostics have already been collected above, so they are
    # still written even when this geometric validation is skipped.
    if len(active) != 3:
        return (
            None,
            [],
            constraint_rows,
            (
                f"{len(active)} participating objectives using raw "
                f"multiplier threshold {threshold:.3e}; "
                "pairwise geometric validation requires exactly 3."
            ),
        )


    active_jacobian = jacobian[active]

    raw_coefficients = lambdas[active]

    corrected_coefficients = (
        lambdas[active]
        * scales[active]
    )

    xnimbus_effective_coefficients = xnimbus_effective_all[active]

    coefficient_absolute_differences = np.abs(
        xnimbus_effective_coefficients
        - corrected_coefficients
    )

    coefficient_relative_differences = (
        coefficient_absolute_differences
        / np.maximum(
            np.abs(corrected_coefficients),
            1e-30,
        )
    )

    max_xnimbus_coefficient_abs_diff = float(
        np.max(coefficient_absolute_differences)
    )

    max_xnimbus_coefficient_rel_diff = float(
        np.max(coefficient_relative_differences)
    )

    aggregated_coefficients = aggregated_all[active]

    raw_residual = stationarity_residual(
        active_jacobian,
        raw_coefficients,
    )

    corrected_residual = stationarity_residual(
        active_jacobian,
        corrected_coefficients,
    )

    aggregated_residual = stationarity_residual(
        active_jacobian,
        aggregated_coefficients,
    )

    numerical_normal = independent_local_normal(
        active_jacobian
    )

    if numerical_normal is None:
        return (
            None,
            [],
            constraint_rows,
            (
                "The active objective Jacobian does not "
                "have a one-dimensional left nullspace."
            ),
        )

    raw_angle = angle_degrees(
        raw_coefficients,
        numerical_normal,
    )

    corrected_angle = angle_degrees(
        corrected_coefficients,
        numerical_normal,
    )

    aggregated_angle = angle_degrees(
        aggregated_coefficients,
        numerical_normal,
    )

    tradeoffs = pairwise_tradeoff_comparisons(
        active,
        objective_symbols,
        raw_coefficients,
        corrected_coefficients,
        xnimbus_effective_coefficients,
        aggregated_coefficients,
        numerical_normal,
    )

    for comparison in tradeoffs:
        comparison["iteration"] = iteration
        comparison["solution_index"] = (
            solution_index
        )
        comparison["scalarization"] = kind
        comparison["x_1"] = float(
            x_values.get("x_1", np.nan)
        )
        comparison["x_2"] = float(
            x_values.get("x_2", np.nan)
        )

    if tradeoffs:
        max_tradeoff_absolute_error = max(
            comparison["selected_absolute_error"]
            for comparison in tradeoffs
        )

        finite_relative_errors = [
            comparison["selected_relative_error"]
            for comparison in tradeoffs
            if np.isfinite(
                comparison["selected_relative_error"]
            )
        ]

        max_tradeoff_relative_error = (
            max(finite_relative_errors)
            if finite_relative_errors
            else np.nan
        )
    else:
        max_tradeoff_absolute_error = np.nan
        max_tradeoff_relative_error = np.nan

    result = {
        "iteration": iteration,
        "solution_index": solution_index,
        "scalarization": kind,
        "x_1": float(
            x_values.get("x_1", np.nan)
        ),
        "x_2": float(
            x_values.get("x_2", np.nan)
        ),
        "active_objectives": ",".join(
            objective_symbols[index]
            for index in active
        ),
        "selected_multiplier_keys": ",".join(
            selected_multiplier_keys[index]
            for index in active
        ),
        "selected_constraints": ",".join(
            selected_constraints[index]
            for index in active
        ),
        "multipliers": ",".join(
            f"{lambdas[index]:.16g}"
            for index in active
        ),
        "constraint_scales": ",".join(
            f"{scales[index]:.16g}"
            for index in active
        ),
        "corrected_coefficients": ",".join(
            f"{corrected_coefficients[position]:.16g}"
            for position in range(
                len(corrected_coefficients)
            )
        ),
        "aggregated_coefficients": ",".join(
            f"{aggregated_coefficients[position]:.16g}"
            for position in range(
                len(aggregated_coefficients)
            )
        ),
        "objectives_with_multiple_above_threshold_constraints": ",".join(
            objective_symbols[index]
            for index in active
            if sum(
                abs(value) > threshold
                for _, value in grouped_entries[
                    objective_symbols[index]
                ]
            ) > 1
        ),
        "scale_fit_max_rel_error": float(
            np.nanmax(
                scale_fit_errors[active]
            )
        ),
        "raw_residual": float(
            raw_residual
        ),
        "corrected_residual": float(
            corrected_residual
        ),
        "aggregated_residual": float(
            aggregated_residual
        ),
        "raw_angle_deg": float(
            raw_angle
        ),
        "corrected_angle_deg": float(
            corrected_angle
        ),
        "aggregated_angle_deg": float(
            aggregated_angle
        ),
        "max_tradeoff_abs_error": float(
            max_tradeoff_absolute_error
        ),
        "max_tradeoff_rel_error": float(
            max_tradeoff_relative_error
        ),
        "success": bool(
            solution.success
        ),
        "solver_message": str(
            solution.message
        ),
        "xnimbus_effective_coefficients": ",".join(
            f"{value:.16g}"
            for value in xnimbus_effective_coefficients
        ),

        "max_xnimbus_coefficient_abs_diff": (
            max_xnimbus_coefficient_abs_diff
        ),

        "max_xnimbus_coefficient_rel_diff": (
            max_xnimbus_coefficient_rel_diff
        ),
    }

    return result, tradeoffs, constraint_rows, None


# ---------------------------------------------------------------------------
# Run multiple live synchronous-NIMBUS iterations
# ---------------------------------------------------------------------------


def run_experiment(
    iterations: int,
    solutions_per_iteration: int,
    next_solution: int,
    threshold: float,
    h: float,
):
    problem = river_pollution_problem(
        five_objective_variant=False
    )

    base_evaluator = SympyEvaluator(
        problem
    )

    solver_options = IpoptOptions(
        tol=1e-8,
        max_iter=3000,
        print_level=0,
    )

    print(
        "Generating starting Pareto-optimal solution..."
    )

    starting_solution = generate_starting_point(
        problem,
        solver=PyomoIpoptSolver,
        solver_options=solver_options,
    )

    if not starting_solution.success:
        raise RuntimeError(
            "Could not generate starting solution: "
            f"{starting_solution.message}"
        )

    current = {
        objective.symbol: float(
            starting_solution.optimal_objectives[
                objective.symbol
            ]
        )
        for objective in problem.objectives
    }

    print("\nStarting objective vector")

    for objective, value in current.items():
        print(
            f"  {objective}: {value:.10g}"
        )

    solution_results = []
    tradeoff_results = []
    constraint_results = []
    skipped = []

    for iteration_index in range(iterations):
        iteration = iteration_index + 1

        reference_point = make_reference_point(
            problem,
            current,
            iteration_index,
        )

        classifications = infer_classifications(
            problem,
            current,
            reference_point,
        )

        print(
            f"\nIteration {iteration}"
        )

        print("  classifications")

        for objective, classification in (
            classifications.items()
        ):
            print(
                f"    {objective}: "
                f"{classification}"
            )

        print("  reference point")

        for objective, value in (
            reference_point.items()
        ):
            print(
                f"    {objective}: {value:.10g}"
            )

        generated_solutions = solve_sub_problems(
            problem,
            current,
            reference_point,
            num_desired=solutions_per_iteration,
            solver=PyomoIpoptSolver,
            solver_options=solver_options,
        )

        for solution_index, solution in enumerate(
            generated_solutions,
            start=1,
        ):
            kind = solution_kind(
                solution
            )

            print(
                f"  solution {solution_index}: "
                f"{kind}, success={solution.success}"
            )

            try:
                (
                    result,
                    pairwise_results,
                    constraint_diagnostics,
                    reason,
                ) = evaluate_solution(
                    iteration,
                    solution_index,
                    solution,
                    problem,
                    base_evaluator,
                    current,
                    reference_point,
                    threshold,
                    h,
                )

            except Exception as exception:
                result = None
                pairwise_results = []
                constraint_diagnostics = []
                reason = (
                    "Evaluation failed: "
                    f"{exception}"
                )

            constraint_results.extend(
                constraint_diagnostics
            )

            if result is None:
                skipped.append(
                    {
                        "iteration": iteration,
                        "solution_index": (
                            solution_index
                        ),
                        "scalarization": kind,
                        "reason": reason,
                    }
                )

                print(
                    f"    diagnostic skipped: "
                    f"{reason}"
                )

                continue

            solution_results.append(
                result
            )

            tradeoff_results.extend(
                pairwise_results
            )

            print(
                "    local-normal residual: "
                f"raw={result['raw_residual']:.3e}, "
                "selected-scaled="
                f"{result['corrected_residual']:.3e}, "
                "aggregated="
                f"{result['aggregated_residual']:.3e}"
            )

            print(
                "    angle to finite-difference "
                "normal: "
                f"raw={result['raw_angle_deg']:.6g}°, "
                "selected-scaled="
                f"{result['corrected_angle_deg']:.6g}°, "
                "aggregated="
                f"{result['aggregated_angle_deg']:.6g}°"
            )

            for comparison in pairwise_results:
                print(
                    "    "
                    f"{comparison['from_objective']} -> "
                    f"{comparison['to_objective']}: "
                    "XNIMBUS="
                    f"{comparison['xnimbus_implementation_tradeoff']:.10g}, "
                    "independent="
                    f"{comparison['selected_scaled_tradeoff']:.10g}, "
                    "FD="
                    f"{comparison['finite_difference_tradeoff']:.10g}"
                )

        if next_solution > len(
            generated_solutions
        ):
            raise ValueError(
                f"--next-solution={next_solution}, "
                "but only "
                f"{len(generated_solutions)} "
                "solutions were generated."
            )

        chosen_solution = (
            generated_solutions[
                next_solution - 1
            ]
        )

        current = {
            objective.symbol: float(
                chosen_solution.optimal_objectives[
                    objective.symbol
                ]
            )
            for objective in problem.objectives
        }

        print(
            "  -> continuing from solution "
            f"{next_solution} "
            f"({solution_kind(chosen_solution)})"
        )

    return (
        solution_results,
        tradeoff_results,
        constraint_results,
        skipped,
    )


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def print_summary(
    solution_results: list[dict],
    tradeoff_results: list[dict],
    skipped: list[dict],
):
    print("\n" + "=" * 90)
    print("VALIDATION SUMMARY")
    print("=" * 90)

    if not solution_results:
        print("No solutions were eligible for validation.")
    else:
        raw_residuals = np.array(
            [r["raw_residual"] for r in solution_results],
            dtype=float,
        )
        selected_residuals = np.array(
            [r["corrected_residual"] for r in solution_results],
            dtype=float,
        )
        aggregated_residuals = np.array(
            [r["aggregated_residual"] for r in solution_results],
            dtype=float,
        )

        raw_angles = np.array(
            [r["raw_angle_deg"] for r in solution_results],
            dtype=float,
        )
        selected_angles = np.array(
            [r["corrected_angle_deg"] for r in solution_results],
            dtype=float,
        )
        aggregated_angles = np.array(
            [r["aggregated_angle_deg"] for r in solution_results],
            dtype=float,
        )

        print(f"Evaluated solutions: {len(solution_results)}")
        print(
            "Median local-normal residual: "
            f"raw={np.median(raw_residuals):.3e}, "
            f"selected-scaled={np.median(selected_residuals):.3e}, "
            f"aggregated={np.median(aggregated_residuals):.3e}"
        )
        print(
            "Median angle to independently estimated normal: "
            f"raw={np.median(raw_angles):.6g}°, "
            f"selected-scaled={np.median(selected_angles):.6g}°, "
            f"aggregated={np.median(aggregated_angles):.6g}°"
        )

        selected_better = int(
            np.sum(selected_residuals < raw_residuals)
        )
        aggregated_better = int(
            np.sum(aggregated_residuals < raw_residuals)
        )

        print(
            "Selected-scaled coefficients have a smaller residual than raw "
            f"in {selected_better}/{len(solution_results)} solutions."
        )
        print(
            "Aggregated coefficients have a smaller residual than raw "
            f"in {aggregated_better}/{len(solution_results)} solutions."
        )

        multiple = [
            r["objectives_with_multiple_above_threshold_constraints"]
            for r in solution_results
            if r.get(
                "objectives_with_multiple_above_threshold_constraints",
                "",
            )
        ]
        print(
            "Solutions with at least one objective having multiple "
            f"above-threshold constraint multipliers: {len(multiple)}"
        )

        xnimbus_coeff_rel = np.array(
            [
                r["max_xnimbus_coefficient_rel_diff"]
                for r in solution_results
            ],
            dtype=float,
        )

        print(
            "XNIMBUS implementation vs independently inferred scaling: "
            f"median max relative difference="
            f"{np.median(xnimbus_coeff_rel):.3e}, "
            f"overall max="
            f"{np.max(xnimbus_coeff_rel):.3e}"
        )

    if tradeoff_results:
        selected_abs = np.array(
            [r["selected_absolute_error"] for r in tradeoff_results],
            dtype=float,
        )
        aggregated_abs = np.array(
            [r["aggregated_absolute_error"] for r in tradeoff_results],
            dtype=float,
        )
        raw_abs = np.array(
            [r["raw_absolute_error"] for r in tradeoff_results],
            dtype=float,
        )

        selected_rel = np.array(
            [
                r["selected_relative_error"]
                for r in tradeoff_results
                if np.isfinite(r["selected_relative_error"])
            ],
            dtype=float,
        )
        aggregated_rel = np.array(
            [
                r["aggregated_relative_error"]
                for r in tradeoff_results
                if np.isfinite(r["aggregated_relative_error"])
            ],
            dtype=float,
        )

        print(
            f"\nPairwise trade-off comparisons: {len(tradeoff_results)}"
        )
        print(
            "Median absolute error: "
            f"raw={np.median(raw_abs):.3e}, "
            f"selected-scaled={np.median(selected_abs):.3e}, "
            f"aggregated={np.median(aggregated_abs):.3e}"
        )
        print(
            "Maximum absolute error: "
            f"raw={np.max(raw_abs):.3e}, "
            f"selected-scaled={np.max(selected_abs):.3e}, "
            f"aggregated={np.max(aggregated_abs):.3e}"
        )

        if len(selected_rel):
            print(
                "Selected-scaled relative error: "
                f"median={np.median(selected_rel):.3e}, "
                f"max={np.max(selected_rel):.3e}"
            )

        if len(aggregated_rel):
            print(
                "Aggregated relative error: "
                f"median={np.median(aggregated_rel):.3e}, "
                f"max={np.max(aggregated_rel):.3e}"
            )

    if skipped:
        print(f"\nSkipped diagnostics: {len(skipped)}")
        for item in skipped:
            print(
                f"  iteration {item['iteration']}, "
                f"solution {item['solution_index']}, "
                f"{item['scalarization']}: {item['reason']}"
            )



def write_csv(
    rows: list[dict],
    path: Path,
    fieldnames: list[str] | None = None,
):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if rows:
        names = list(rows[0].keys())
    elif fieldnames is not None:
        names = fieldnames
    else:
        # Still create the requested output so it is obvious that the
        # current script version ran.
        path.write_text("", encoding="utf-8")
        return

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=names,
        )
        writer.writeheader()
        if rows:
            writer.writerows(rows)


# ---------------------------------------------------------------------------
# Command-line entry point
# ---------------------------------------------------------------------------


def main():
    print(f"XNIMBUS trade-off validator version: {SCRIPT_VERSION}")
    parser = argparse.ArgumentParser(
        description=(
            "Run synchronous NIMBUS with DESDEO/IPOPT "
            "and validate scaling-corrected KKT local "
            "trade-offs against finite-difference geometry."
        )
    )

    parser.add_argument(
        "--iterations",
        type=int,
        default=20,
        help=(
            "Number of synchronous NIMBUS iterations "
            "to run (default: 4)."
        ),
    )

    parser.add_argument(
        "--solutions",
        type=int,
        choices=[1, 2, 3, 4],
        default=4,
        help=(
            "Number of solutions per iteration: "
            "1=NIMBUS, 2=+STOM, 3=+ASF, "
            "4=+GUESS (default: 4)."
        ),
    )

    parser.add_argument(
        "--next-solution",
        type=int,
        default=1,
        help=(
            "Generated solution used as the current "
            "solution in the next iteration "
            "(default: 1, NIMBUS)."
        ),
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=1e-5,
        help=(
            "Multiplier magnitude threshold for "
            "participating objectives "
            "(default: 1e-5)."
        ),
    )


    parser.add_argument(
        "--h",
        type=float,
        default=1e-6,
        help=(
            "Finite-difference step factor "
            "(default: 1e-6)."
        ),
    )

    parser.add_argument(
        "--solution-csv",
        type=Path,
        default=Path(
            "solution_validation.csv"
        ),
        help=(
            "Solution-level diagnostic CSV "
            "(default: solution_validation.csv)."
        ),
    )

    parser.add_argument(
        "--tradeoff-csv",
        type=Path,
        default=Path(
            "tradeoff_validation.csv"
        ),
        help=(
            "Pairwise trade-off comparison CSV "
            "(default: tradeoff_validation.csv)."
        ),
    )

    parser.add_argument(
        "--constraint-csv",
        type=Path,
        default=Path(
            "constraint_validation.csv"
        ),
        help=(
            "All objective-related constraint multipliers and scaled "
            "contributions (default: constraint_validation.csv)."
        ),
    )

    args = parser.parse_args()

    if args.iterations < 1:
        parser.error(
            "--iterations must be at least 1."
        )

    if (
        args.next_solution < 1
        or args.next_solution > args.solutions
    ):
        parser.error(
            "--next-solution must be between "
            "1 and --solutions."
        )

    (
        solution_results,
        tradeoff_results,
        constraint_results,
        skipped,
    ) = run_experiment(
        iterations=args.iterations,
        solutions_per_iteration=args.solutions,
        next_solution=args.next_solution,
        threshold=args.threshold,
        h=args.h,
    )

    print_summary(
        solution_results,
        tradeoff_results,
        skipped,
    )

    write_csv(
        solution_results,
        args.solution_csv,
    )

    write_csv(
        tradeoff_results,
        args.tradeoff_csv,
    )

    write_csv(
        constraint_results,
        args.constraint_csv,
        fieldnames=['iteration', 'solution_index', 'scalarization', 'objective', 'multiplier_key', 'constraint_symbol', 'multiplier', 'abs_multiplier', 'above_threshold', 'selected_by_xnimbus', 'constraint_scale', 'scale_fit_rel_error', 'scaled_contribution', 'scale_status', 'x_1', 'x_2'],
    )

    print(
        "\nSolution diagnostics output: "
        f"{args.solution_csv.resolve()}"
    )
    print(
        "Pairwise trade-off validation output: "
        f"{args.tradeoff_csv.resolve()}"
    )
    print(
        "Constraint-level diagnostics output: "
        f"{args.constraint_csv.resolve()} "
        f"({len(constraint_results)} rows)"
    )


if __name__ == "__main__":
    main()
