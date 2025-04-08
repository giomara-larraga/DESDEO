"""Functions related to the reference point method.

This module contains functions related to the reference point method as
presented in Wierzbicki, A. P. (1982). A mathematical basis for satisficing
decision making. Mathematical modelling, 3(5), 391-405.
"""

import numpy as np
import shap
from desdeo.problem.testproblems import river_pollution_problem_discrete
from desdeo.shapley_values.utilities import generate_black_box


class ReferencePointError(Exception):
    """Raised when an error with the reference point method is encountered."""


def rximo_solve_solutions(
    reference_point: dict[str, float],
) -> list:
    """Finds (near) Pareto optimal solutions based on a reference point.

    Find a (near) Pareto optimal solution based on the given reference point by
    optimizing an achievement scalarizing function. The original reference point
    is also perturbed, and another k (near) Pareto optimal solutions are found.
    The k+1 solutions are then returned.

    Args:
        problem (Problem): the problem to be solved.
        reference_point (dict[str, float]): the reference point. The keys of the dict
            represent the objective function symbols defined in problem. The values
            represent the aspiration level values.
        scalarization_options (dict | None, optional): keyword arguments to be
            passed to the achievement scalarizing function. Defaults to None.
        solver (BaseSolver | None, optional): solver to optimize the achievement
            scalarizing function. If not given, the method tried to guess the
            most suitable solver based on the problem. Defaults to None.
        solver_options (SolverOptions | None, optional): options passed to the
            solver. If not given, the solver will use its default options. Defaults to None.
        kkt_multipliers (bool | False, optional): indicate if the KKT multipliers need to be computed. Default False.
    Raises:
        ReferencePointError: the reference point is ill-defined.

    Returns:
        list[SolverResults]: a list of results containing the solutions found using
            the reference point and the k perturbed reference points.

    Note:
        If the problem is twice differentiable, `add_asf_diff` is used from `desdeo.tools`.
            If the problem is not twice differentiable, then `add_asf_nondiff` is used.
    """
    # setup problem with ASF
    problem = river_pollution_problem_discrete()
    d_rep = problem.discrete_representation.objective_values

    # Extract values for each key in d_rep and store them in a list
    data = [d_rep[obj.symbol] for obj in problem.objectives]

    # Convert the list to a 2D NumPy array with values as columns
    pareto_front = np.column_stack(data)

    if not all(obj.symbol in reference_point for obj in problem.objectives):
        msg = f"The reference point {reference_point} is missing entries for one or more of the objective functions."
        raise ReferencePointError(msg)

    missing_data = shap.sample(pareto_front, nsamples=200)

    bb = generate_black_box(problem)
    explainer = shap.KernelExplainer(bb, missing_data)
    result = bb(reference_point)
    shap_values = np.array(explainer.shap_values(reference_point))
    # return the original solution and the solutions found with the perturbed reference points
    return result, shap_values
