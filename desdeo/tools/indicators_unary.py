"""This module implements unary indicators that can be used to evaluate the quality of a single solution set.

It assumes that the solution set has been normalized just that _some_ ideal point (not necessarily the ideal point
of the set) is the origin and _some_ nadir point (not necessarily the nadir point of the set) is (1, 1, ..., 1).
The normalized solution set is assumed to be inside the bounding box [0, 1]^k where k is the number of objectives.
If these conditions are not met, the results of the indicators will not be meaningful.

Additionally, the set may be assumed to only contain mutually non-dominated solutions, depending on the indicator.

For now, we rely on pymoo for the implementation of some of the indicators.

Find more information about the indicators in:
Audet, Charles, et al. "Performance indicators in multiobjective optimization."
European journal of operational research 292.2 (2021): 397-422.
"""

from warnings import warn

import numpy as np
from moocore import Hypervolume
from pydantic import BaseModel, Field
from pymoo.indicators.rmetric import RMetric
from scipy.spatial.distance import cdist


def hv(solution_set: np.ndarray, reference_point_component: float) -> float:
    """Calculate the hypervolume indicator for a set of solutions.

    Args:
        solution_set (np.ndarray): A 2D numpy array where each row is a solution and each column is an objective value.
            The solutions are assumed to be non-dominated. The solutions are assumed to be normalized within the unit
            hypercube. The ideal and nadir of the set itself can lie within the hypercube, but not outside it.
        reference_point_component (float): The value of the reference point component. The reference point is assumed to
            be the same for all objectives. The reference point must be at least 1.

    Returns:
        float: The hypervolume indicator value.

    Notes:
        For PHI, ``reference_point`` should be the dystopian point z^dy.
    """
    hv = Hypervolume(reference_point_component)
    ind = hv(solution_set)

    if ind is None:
        raise ValueError("Hypervolume calculation failed.")

    return float(ind)


def hv_batch(
    solution_sets: dict[str, np.ndarray], reference_points_component: list[float]
) -> dict[str, list[float | None]]:
    """Calculate the hypervolume indicator for a set of solutions over a range of reference points.

    Args:
        solution_sets (dict[str, np.ndarray]): A dict of strings mapped to 2D numpy arrays where each array contains a
            set of solutions.
            Each row is a solution and each column is an objective value. The solutions are assumed to be non-dominated
            within their respective sets. The solutions are assumed to be normalized within the unit hypercube. The
            ideal and nadir of the set itself can lie within the hypercube, but not outside it. The sets must have the
            same number of objectives/columns but can have different number of solutions/rows.
            The keys of the dict are the names of the sets.
        reference_points_component (list[float]): A list of the value of the reference point component. The
            hypervolume is calculated for each set of solutions for each reference point component. The reference point
            is assumed to be the same for all objectives. The reference point must be at least 1.

    Returns:
        dict[str, list[float | None]]: A dict of strings mapped to lists of hypervolume indicator values. The keys of
            the dict are the names of the sets. The lists contain the hypervolume indicator values for each reference
            point component. If the calculation fails, the value is set to None, and should be handled by the user.
    """
    hvs = {key: [] for key in solution_sets}
    solution_sets[next(iter(solution_sets.keys()))].shape[1]

    for rp in reference_points_component:
        hv = Hypervolume(rp)
        for set_name, sols in solution_sets.items():
            ind = hv(sols)
            if ind is None:
                warn("Hypervolume calculation failed. Setting value to None", category=RuntimeWarning, stacklevel=2)
                hvs[set_name].append(None)
            else:
                hvs[set_name].append(float(ind))

    return hvs


class DistanceIndicators(BaseModel):
    """A container for closely related distance based indicators."""

    igd: float = Field(description="The inverted generational distance (IGD) indicator value.")
    "The inverted generational distance (IGD) indicator value."
    igd_p: float = Field(
        description=(
            "The IGD_p indicator, where instead of the arithmetic mean of the distances, the "
            "generalized (power) mean of order p is taken. Equals `igd` when p == 1."
        )
    )
    "The IGD_p indicator, where instead of the arithmetic mean of the distances, the generalized (power) mean"
    " of order p is taken. Equals `igd` when p == 1."
    gd: float = Field(description="The generational distance (GD) indicator value.")
    "The generational distance (GD) indicator value."
    gd_p: float = Field(
        description=(
            "The GD_p indicator, where instead of the arithmetic mean of the distances, the "
            "generalized (power) mean of order p is taken. Equals `gd` when p == 1."
        )
    )
    "The GD_p indicator, where instead of the arithmetic mean of the distances, the generalized (power) mean"
    " of order p is taken. Equals `gd` when p == 1."
    ahd: float = Field(description="The averaged Hausdorff distance (Delta_p) indicator value, max(igd_p, gd_p).")
    "The averaged Hausdorff distance (Delta_p) indicator value, max(igd_p, gd_p)."


def _power_mean(distances: np.ndarray, p: float) -> float:
    """Computes the generalized (power) mean of order p of a 1D array of non-negative distances.

    Args:
        distances (np.ndarray): A 1D array of non-negative distances.
        p (float): The order of the mean. Must be positive. np.inf (or math.inf) yields the maximum.

    Returns:
        float: The generalized mean of order p.
    """
    if np.isinf(p):
        return float(distances.max())
    return float(np.mean(distances**p) ** (1 / p))


def distance_indicators(
    solution_set: np.ndarray, reference_set: np.ndarray, p: float = 2.0, distance_p: float = 2.0
) -> DistanceIndicators:
    """Calculates various distance based indicators between a solution set and a reference set.

    Given the point-to-set distances `d_i`, the indicators are

        IGD   = mean over the reference set of the distance to the closest solution,
        GD    = mean over the solution set of the distance to the closest reference point,
        IGD_p = (mean(d_i**p))**(1/p) over the reference set,
        GD_p  = (mean(d_i**p))**(1/p) over the solution set,
        AHD   = max(IGD_p, GD_p), the averaged Hausdorff distance Delta_p.

    Note that `p` only controls the averaging; the point-to-point distance is controlled separately by
    `distance_p` and defaults to the Euclidean distance, matching the definitions used by `moocore` and by
    Schuetze et al. Consequently, IGD_p and GD_p coincide with IGD and GD when `p == 1`.

    Args:
        solution_set (np.ndarray): A 2D numpy array where each row is a solution and each column is an objective value.
            The solutions are assumed to be normalized within the unit hypercube. The ideal and nadir of the set itself
            can lie within the hypercube, but not outside it. The solutions are assumed to be non-dominated.
        reference_set (np.ndarray): A 2D numpy array where each row is a solution and each column is an objective value.
            The solutions are assumed to be normalized within the unit hypercube. The ideal and nadir of the reference
            set should probably be (0, 0, ..., 0) and (1, 1, ..., 1) respectively. The reference set is assumed to be
            non-dominated.
        p (float, optional): The order of the generalized mean used to aggregate the distances into IGD_p, GD_p, and
            AHD. Must be positive; np.inf (or math.inf) aggregates by taking the maximum distance, giving the
            (non-averaged) Hausdorff distance. Defaults to 2.0.
        distance_p (float, optional): The power of the Minkowski metric used for the point-to-point distances. Set to 1
            for Manhattan distance, 2 for Euclidean distance, and np.inf (or math.inf) for Chebyshev distance. Defaults
            to 2.0, i.e., the Euclidean distance used by the standard definitions of these indicators.

    Returns:
        DistanceIndicators: A Pydantic class containing the IGD, IGD_p, GD, GD_p, and AHD indicator values.

    Raises:
        ValueError: If `p` or `distance_p` is not positive.
    """
    if p <= 0:
        raise ValueError(f"'p' must be positive, got {p}.")
    if distance_p <= 0:
        raise ValueError(f"'distance_p' must be positive, got {distance_p}.")

    distance_matrix = cdist(solution_set, reference_set, metric="minkowski", p=distance_p)
    # For each reference point, the distance to the closest solution, and vice versa.
    igd_distances = np.min(distance_matrix, axis=0)
    gd_distances = np.min(distance_matrix, axis=1)

    _igd = float(igd_distances.mean())
    _gd = float(gd_distances.mean())
    _igd_p = _power_mean(igd_distances, p)
    _gd_p = _power_mean(gd_distances, p)
    _ahd = max(_igd_p, _gd_p)
    return DistanceIndicators(igd=_igd, igd_p=_igd_p, gd=_gd, gd_p=_gd_p, ahd=_ahd)


def distance_indicators_batch(
    solution_sets: dict[str, np.ndarray], reference_set: np.ndarray, p: float = 2.0, distance_p: float = 2.0
) -> dict[str, DistanceIndicators]:
    """Calculate the IGD, GD, GD_p, IGD_p, and AHD for a sets of solutions.

    Args:
        solution_sets (dict[str, np.ndarray]): A dict of strings mapped to 2D numpy arrays where each array contains a
            set of solutions. Each row is a solution and each column is an
            objective value. The solutions are assumed to be normalized within
            the unit hypercube. The ideal and nadir of the set itself can lie
            within the hypercube, but not outside it. The solutions are assumed
            to be non-dominated within their respective sets. The sets must have
            the same number of objectives/columns but can have different number
            of solutions/rows. The keys of the dict are the names of the sets.
        reference_set (np.ndarray): A 2D numpy array where each row is a solution and each column is an objective value.
            The solutions are assumed to be normalized within the unit hypercube. The ideal and nadir of the reference
            set should probably be (0, 0, ..., 0) and (1, 1, ..., 1) respectively. The reference set is assumed to be
            non-dominated.
        p (float, optional): The order of the generalized mean used to aggregate the distances into IGD_p, GD_p, and
            AHD. Must be positive; np.inf (or math.inf) aggregates by taking the maximum distance. Defaults to 2.0.
        distance_p (float, optional): The power of the Minkowski metric used for the point-to-point distances. Set to 1
            for Manhattan distance, 2 for Euclidean distance, and np.inf (or math.inf) for Chebyshev distance. Defaults
            to 2.0, i.e., the Euclidean distance used by the standard definitions of these indicators.

    Returns:
        dict[str, DistanceIndicators]: A dict of strings mapped to DistanceIndicators objects. The keys of the dict are
            the names of the sets. The DistanceIndicators objects contain the IGD, IGD_p, GD, GD_p, and AHD indicator
            values. This data structure can be easily converted to a DataFrame or saved to disk as a JSON file.
    """
    inds = {}
    for set_name, sols in solution_sets.items():
        inds[set_name] = distance_indicators(sols, reference_set, p=p, distance_p=distance_p)
    return inds


class IGDPlusIndicators(BaseModel):
    """A container for the IGD+ distance-based indicator."""

    igd_plus: float = Field(description="The modified inverted generational distance (IGD+) indicator value.")


def igd_plus_indicator(solution_set: np.ndarray, reference_set: np.ndarray, p: float = 2.0) -> IGDPlusIndicators:
    """Computes the IGD+ indicator for a given solution set.

    Notes:
        The minimization of the objective function values is assumed.

        IGD+ is defined by Ishibuchi et al. (2015) in terms of the Euclidean distance, i.e., p == 2, which is the
        default here. Other values of `p` give a non-standard generalization that will not match the IGD+ values
        reported by, e.g., `moocore` or `pymoo`.

    Args:
        solution_set (np.ndarray): The solution set being evaluated.
        reference_set (np.ndarray): The reference Pareto front.
        p (float, optional): The power of the Minkowski metric. Defaults to 2.0 (Euclidean distance).

    Returns:
        IGDPlusIndicators: A Pydantic class containing the IGD+ indicator value.
    """
    num_ref_points = reference_set.shape[0]
    total_distance = 0.0

    for y_p in reference_set:
        min_distance = float("inf")

        for y_n in solution_set:
            # Compute IGD+ distance (only positive differences)
            distance = np.sum(np.maximum(0, y_n - y_p) ** p)  # Sum over objectives
            min_distance = min(min_distance, distance)  # Store the closest one

        total_distance += min_distance ** (1 / p)  # Apply the root AFTER summing over objectives

    igd_plus_value = total_distance / num_ref_points
    return IGDPlusIndicators(igd_plus=igd_plus_value)


def igd_plus_batch(
    solution_sets: dict[str, np.ndarray], reference_set: np.ndarray, p: float = 2.0
) -> dict[str, IGDPlusIndicators]:
    """Computes the IGD+ indicator for multiple solution sets.

    Notes:
        The minimization of the objective function values is assumed.

    Args:
        solution_sets (dict[str, np.ndarray]): A dictionary of solution sets.
        reference_set (np.ndarray): The reference Pareto front.
        p (float, optional): The power of the Minkowski metric. Defaults to 2.0 (Euclidean distance).

    Returns:
        dict[str, IGDPlusIndicators]: A dictionary of IGDPlusIndicators.
    """
    results = {}
    for set_name, solution_set in solution_sets.items():
        results[set_name] = igd_plus_indicator(solution_set, reference_set, p)
    return results


class R2Indicator(BaseModel):
    """Container for the R2 indicator value of a solution set."""

    r2_value: float
    """The R2 indicator value. **Higher is better, and the value is always negative.**

    This is the utility form of R2, and it is the opposite orientation to every other indicator in
    this module. See `r2_indicator` for why, and do not put it on a chart beside IGD+ or GD without
    flipping its sign first."""


def tchebycheff_utility(fx: np.ndarray, lambd: np.ndarray, z_star: np.ndarray, rho: float = 0.05) -> float:
    """Calculates the augmented Tchebycheff utility of a solution.

    A *utility*, so it is the negated achievement scalarising value and **higher is better**. It is
    always negative, reaching zero only for a solution sitting on the ideal point.
    """
    diff = np.abs(z_star - fx)
    max_term = np.max(lambd * diff)
    sum_term = np.sum(diff)
    return -(max_term + rho * sum_term)


def r2_indicator(
    solution_set: np.ndarray, lambda_set: np.ndarray, z_star: np.ndarray, rho: float = 0.05
) -> R2Indicator:
    """Computes the unary R2 indicator for a given solution set.

    **Higher is better, and the value is always negative** -- the opposite of every other indicator
    in this module, and the single most likely thing to be got wrong about it.

    Two conventions for unary R2 are in use and they differ by a sign. This is the *utility* form of
    Brockhoff, Wagner and Trautmann: the mean over weight vectors of the best utility any solution
    achieves, where the utility is a negated Tchebycheff distance. PlatEMO and jMetal report the
    *distance* form instead -- the mean over weight vectors of the smallest Tchebycheff distance --
    which is non-negative and minimised. The two are exact negations of each other, so
    `-r2_value` converts this to the value those frameworks print.

    Args:
        solution_set (np.ndarray): The Pareto front approximation.
        lambda_set (np.ndarray): The set of normalized weight vectors (λ).
        z_star (np.ndarray): The ideal point (must dominate or weakly dominate all solutions).
        rho (float, optional): Small positive number for augmented Tchebycheff. Default is 0.05.

    Returns:
        R2IndicatorResult: Pydantic class with R2 value. Higher is better; see above.

    References:
        Brockhoff, D., Wagner, T., & Trautmann, H. (2012). On the properties of the R2 indicator.
            In Proceedings of the 14th Annual Conference on Genetic and Evolutionary Computation
            (pp. 465-472). https://doi.org/10.1145/2330163.2330230

        Hansen, M. P., & Jaszkiewicz, A. (1998). Evaluating the quality of approximations to the
            non-dominated set. IMM Technical Report IMM-REP-1998-7, Technical University of Denmark.
    """
    total_score = 0.0
    for lambd in lambda_set:
        best_score = max(tchebycheff_utility(fx, lambd, z_star, rho) for fx in solution_set)
        total_score += best_score

    r2_value = total_score / len(lambda_set)
    return R2Indicator(r2_value=r2_value)


def r2_batch(
    solution_sets: dict[str, np.ndarray], lambda_set: np.ndarray, z_star: np.ndarray, rho: float = 0.05
) -> dict[str, R2Indicator]:
    """Computes the R2 indicator for multiple solution sets.

    Args:
        solution_sets (dict[str, np.ndarray]): Dictionary of solution sets.
        lambda_set (np.ndarray): Set of weight vectors.
        z_star (np.ndarray): Ideal point.
        rho (float, optional): Augmented Tchebycheff parameter.

    Returns:
        dict[str, R2IndicatorResult]: Dictionary of results.
    """
    return {name: r2_indicator(solution_set, lambda_set, z_star, rho) for name, solution_set in solution_sets.items()}


class RMetricIndicators(BaseModel):
    """A container for R-metric indicators: R-HV and R-IGD."""

    r_hv: float = Field(description="The R-HV indicator value, based on hypervolume.")
    "The R-HV indicator value, based on hypervolume."
    r_igd: float = Field(description="The R-IGD indicator value, based on inverted generational distance.")
    "The R-IGD indicator value, based on inverted generational distance."


def r_metric_indicator(
    solution_set: np.ndarray, ref_points: np.ndarray, w: np.ndarray = None, delta: float = 0.2
) -> RMetricIndicators:
    """Calculate the R-metric (either R-HV or R-IGD) for a given solution set.

    Parameters:
    solution_set : np.ndarray
        The set of solutions.

    ref_points : np.ndarray
        A set of reference points..

    w : np.ndarray, optional
        Weights for each objective.

    delta : float, optional
        Region of interest for the metric calculation.

    Returns:
    RMetricIndicators
        An object containing the computed R-HV and R-IGD values.
    """
    # Calculate the Pareto front
    pareto_front = get_pareto_front(solution_set)

    rmetric = RMetric(problem=None, ref_points=ref_points, w=w, delta=delta, pf=pareto_front)
    r_igd, r_hv = rmetric.do(solution_set)
    return RMetricIndicators(r_hv=r_hv, r_igd=r_igd)


def r_metric_indicators_batch(
    solution_set: dict[str, np.ndarray], ref_points: np.ndarray, w: np.ndarray = None, delta: float = 0.2
) -> dict[str, RMetricIndicators]:
    """Calculate the R-metrics (R-HV and R-IGD) for a batch of solution sets."""
    inds = {}
    for set_name, sols in solution_set.items():
        inds[set_name] = r_metric_indicator(sols, ref_points, w, delta)
    return inds


def is_dominated(solution, other_solutions):
    """Check if a solution is dominated by any other solution."""
    return any(np.all(other <= solution) and np.any(other < solution) for other in other_solutions)


def get_pareto_front(solutions):
    """Extract the Pareto front from a set of solutions."""
    pareto_front = []
    for i, solution in enumerate(solutions):
        remaining_solutions = np.delete(solutions, i, axis=0)
        if not is_dominated(solution, remaining_solutions):
            pareto_front.append(solution)
    return np.array(pareto_front)


def get_pareto_front_indices(solutions: np.ndarray) -> np.ndarray:
    """Extract the indices of the non-dominated (Pareto front) solutions."""
    nd = []
    for i, solution in enumerate(solutions):
        remaining_solutions = np.delete(solutions, i, axis=0)
        if not is_dominated(solution, remaining_solutions):
            nd.append(i)
    return np.array(nd, dtype=int)



class PHIResult(BaseModel):
    """PHI assessment for one solution set and one reference point."""

    phi: float = Field(description="PHI defined by Eq. (6).")

    v_prec: float = Field(
        description="Positive contribution v^prec defined in Eq. (3)."
    )

    v_succ: float = Field(
        description="Positive contribution v^succ defined in Eq. (4)."
    )

    v_minus: float = Field(
        description="Negative hypervolume contribution v^- from Eq. (2)."
    )

    v_plus: float = Field(
        description="Total positive contribution v+ = v^prec + v^succ."
    )

    solution_hypervolume: float = Field(
        description="HV(P, z^dy)."
    )

    reference_point_hypervolume: float = Field(
        description="HV(z-hat, z^dy)."
    )

    reference_point_is_dominated: bool = Field(
        description=(
            "True when at least one solution in P dominates z-hat."
        )
    )


class PHILearningResult(BaseModel):
    """PHI-based assessment of a complete learning phase."""

    rs: float = Field(
        description="Responsiveness and stability measure RS from Eq. (7)."
    )
    phi_values: list[float] = Field(
        description="PHI value at each evaluated generation."
    )

class PHIDecisionResult(BaseModel):
    """PHI-based assessment of a complete decision phase."""

    fd: float = Field(
        description="Fine-tuning measure FD from Eq. (10)."
    )
    weights: list[float] = Field(
        description="Similarity coefficients lambda^j from Eq. (9)."
    )
    phi_values: list[float] = Field(
        description="PHI value for each decision-phase interaction."
    )


def _reference_point_dominance_mask(solution_set: np.ndarray, reference_point: np.ndarray)-> tuple[bool, list[bool]]:
    """Check whether at least one solution dominates the reference point.

    Parameters
    ----------
    solution_set : np.ndarray
        Solution set P with shape (n_solutions, n_objectives).
        Minimization is assumed.
    reference_point : np.ndarray
        Decision maker's reference point z-hat with shape
        (n_objectives,).
    Returns

    -------
    tuple[bool, list[bool]]
        First value is True when at least one solution dominates the reference point.
        Second value contains one dominance flag per solution.
    """
    doms = [
        bool(np.all(solution <= reference_point) and np.any(solution < reference_point))
        for solution in solution_set
    ]
    return any(doms), doms


def _phi_dominated_reference_point(solution_set:np.ndarray, reference_point: np.ndarray, dystopian_point: np.ndarray, dominance_mask: list[bool])-> PHIResult:
    """Calculate PHI when at least one solution dominates the RP.

    This corresponds to the second branch of Eq. (6):

        PHI = 1 + v^succ / HV(P, z^dy)

    where

        v^succ = HV(P^succ, z^dy) - HV(RP, z^dy).

    ``nadir`` is the legacy parameter name; it must contain z^dy.
    """

    # P^succ: solutions that dominate the reference point.
    dominating_solutions = np.asarray(solution_set)[dominance_mask]
    stacked = np.vstack([solution_set, reference_point])
    nondoms = stacked[get_pareto_front_indices(stacked)]

    #3max_phv = hv(ideal_point.reshape(1, -1), dystopian_point)  # HV(ideal, z^dy)
    all_phv = hv(nondoms, dystopian_point)  # HV(P, z^dy)
    rp_phv = hv(reference_point.reshape(1, -1), dystopian_point)

        # v^succ from Eq. (4).
    pos_phv = hv(dominating_solutions, dystopian_point) - rp_phv

    # v^- from Eq. (2).
    neg_phv = all_phv - pos_phv - rp_phv

    if all_phv <= 0:
        raise ValueError(
            "HV(P, z^dy) is zero. Check that the supplied hypervolume "
            "reference point is a valid dystopian point."
        )
    phi_value = 1.0 + pos_phv / all_phv

    # if max_phv <= 0:
    #     raise ValueError(
    #         "HV(ideal, z^dy) is zero. The ideal and dystopian points "
    #         "do not define a valid hypervolume region."
    #     )
    
    return PHIResult(
        phi=phi_value,
        v_prec=rp_phv,
        v_succ=pos_phv,
        v_minus=neg_phv,
        v_plus=rp_phv + pos_phv,
        solution_hypervolume=all_phv,
        reference_point_hypervolume=rp_phv,
        reference_point_is_dominated=True,
    )

def _phi_nondominated_reference_point(solution_set:np.ndarray, reference_point: np.ndarray, dystopian_point: np.ndarray) -> PHIResult:
        """Calculate PHI when no solution dominates the RP.

        This corresponds to the first branch of Eq. (6):

            PHI = v^prec / HV(RP, z^dy).

        ``nadir`` is the legacy parameter name; it must contain z^dy.
        """

        stacked = np.vstack([solution_set, reference_point])
        nondoms = stacked[get_pareto_front_indices(stacked)]

        all_phv = hv(nondoms, dystopian_point)
        rp_phv = hv(reference_point.reshape(1, -1), dystopian_point)
        s_phv = hv(solution_set, dystopian_point)

        # Hypervolume contributed by RP outside HV(P).
        nondom_area = all_phv - s_phv

        # v^prec from Eq. (3).
        pos_phv = rp_phv - nondom_area

        # v^- from Eq. (2).
        neg_phv = all_phv - rp_phv


        if rp_phv <= 0:
            raise ValueError(
                "HV(RP, z^dy) is zero. PHI is undefined in this case. "
                "Check that z^dy is strictly worse than the reference point."
            )

        if all_phv <= 0:
            raise ValueError(
                "HV(P ∪ {RP}, z^dy) is zero. Check the dystopian point."
            )


        phi_value = pos_phv / rp_phv

        return PHIResult(
            phi=phi_value,
            v_prec=pos_phv,
            v_succ=0.0,
            v_minus=neg_phv,
            v_plus=pos_phv,
            solution_hypervolume=s_phv,
            reference_point_hypervolume=rp_phv,
            reference_point_is_dominated=False,
        )

def _phi_decision_weights(shared_areas, main_area):
    """Calculate lambda^j according to Eq. (9).

    lambda^j = v^j / HV(z_hat^d, z^dy)
    """
    if main_area <= 0:
        raise ValueError(
            "The final reference point has zero hypervolume with "
            "respect to the dystopian point."
        )
    return np.asarray(shared_areas, dtype=float) / main_area

def _calculate_fd(  weights: np.ndarray, assessment_values: np.ndarray) -> float:
    """Calculate FD according to Eq. (10)."""
    weights = np.asarray(weights, dtype=float)
    assessment_values = np.asarray(assessment_values, dtype=float)

    if weights.shape != assessment_values.shape:
        raise ValueError(
            "weights and assessment_values must have equal lengths."
        )

    return float(np.mean(weights * assessment_values))

def _shared_reference_point_hypervolume(reference_point1: np.ndarray, reference_point2: np.ndarray, dystopian_point: np.ndarray) -> float:
    """Return the shared HV area between two reference-point regions.

    The shared area is

        HV(rp1) + HV(rp2) - HV({rp1, rp2}).

    This is the quantity v^j used to calculate lambda^j in Eq. (9).
    The inclusion-exclusion expression handles dominating,
    non-dominating, and identical reference points uniformly.
    """

    if reference_point1.ndim == 1:
        reference_point1 = reference_point1.reshape(1, -1)
    if reference_point2.ndim == 1:
        reference_point2 = reference_point2.reshape(1, -1)

    dom21 = is_dominated(reference_point2.flatten(), reference_point1.flatten())
    dom12 = is_dominated(reference_point1.flatten(), reference_point2.flatten())
    hv_rp1 = hv(reference_point1, dystopian_point)
    hv_rp2 = hv(reference_point2, dystopian_point)
    hv_union = hv(np.vstack([reference_point1, reference_point2]), dystopian_point)

    if dom21:
        shared_area = hv_rp1
    elif dom12:
        shared_area = hv_rp2
    else:
        extra_area_in_rp1 = abs(hv_union - hv_rp2)
        shared_area = hv_rp1 - extra_area_in_rp1
    return shared_area

def phi_indicator(solution_set: np.ndarray, reference_point: np.ndarray, dystopian_point: np.ndarray) -> PHIResult:
    """Preference-based Hypervolume Indicator (PHI).

    Implements the PHI indicator introduced by Aghaei Pour et al. (2024)
    for minimization problems.

    Notes
    -----
    The hypervolume reference point passed to ``get_phi`` must be the
    dystopian point z^dy used by the PHI definition, not the mathematical
    nadir point. The parameter is named ``nadir`` only for compatibility
    with the legacy DESDEO API.

    ``ideal`` is retained for compatibility with the legacy implementation.
    It is not needed to calculate the PHI value itself; it is used only for
    some of the additional legacy diagnostic values returned by ``get_phi``.

    References
    ----------
    P. Aghaei Pour, S. Bandaru, B. Afsar, M. Emmerich, and K. Miettinen,
    "A Performance Indicator for Interactive Evolutionary Multiobjective
    Optimization Methods," IEEE Transactions on Evolutionary Computation,
    vol. 28, no. 3, 2024.


    Parameters
    ----------
    solution_set
        Solution set P, shape (n_solutions, n_objectives).
        Minimization is assumed.
    RP
        Reference point z-hat supplied by the decision maker.
    nadir
        Dystopian point z^dy used as the hypervolume reference point.
        The name ``nadir`` is retained only for backward compatibility.

    Returns
    -------
    tuple[float, float, float, float]
        Legacy four-value result. The first element is always the actual
        PHI value from Eq. (6). The remaining values are legacy
        hypervolume diagnostics and use different normalizations in the
        two PHI branches.

    Notes
    -----
    For a valid nondegenerate problem:

    * PHI is in [0, 1] when no solution dominates RP.
    * PHI is in (1, 2) when at least one solution dominates RP.
    """
            
    solution_set = np.asarray(solution_set, dtype=float)
    reference_point = np.asarray(reference_point, dtype=float)
    dystopian_point = np.asarray(dystopian_point, dtype=float)

    if solution_set.ndim != 2:
        raise ValueError("solution_set must be a 2D array.")

    if reference_point.ndim != 1 or dystopian_point.ndim != 1:
        raise ValueError("RP and the dystopian point must be 1D arrays.")

    if solution_set.shape[1] != reference_point.size or reference_point.size != dystopian_point.size:
        raise ValueError(
            "Solutions, RP, and dystopian point must have the same "
            "number of objectives."
        )

    is_rp_dominated, domination_mask  = _reference_point_dominance_mask(solution_set, reference_point)

    if is_rp_dominated:
        #check if the non-dominated solutions are empty
        #stacked = np.vstack([solution_set, reference_point])
        #nondoms = stacked[get_pareto_front_indices(stacked)]
        #if nondoms.size == 0:
        #    raise ValueError(
        #        "All solutions dominate the reference point. "
        #        "PHI is undefined in this case."
        #    )
        return _phi_dominated_reference_point(solution_set, reference_point, dystopian_point, domination_mask)

    return _phi_nondominated_reference_point(solution_set, reference_point, dystopian_point)


def phi_indicator_batch(
    solution_sets: dict[str, np.ndarray],
    reference_points: np.ndarray,
    dystopian_point: np.ndarray,
) -> dict[str, PHIResult]:
    """Compute PHI for multiple solution sets.

    Each solution set is evaluated using either the same reference point
    or its corresponding reference point.

    Args:
        solution_sets (dict[str, np.ndarray]):
            Dictionary mapping names to solution sets. Each solution set
            must be a 2D array of shape
            (n_solutions, n_objectives).

        reference_points (np.ndarray):
            Either:

            - a single 1D reference point with shape (n_objectives,),
              reused for every solution set, or
            - a 2D array with shape
              (n_solution_sets, n_objectives), containing one reference
              point for each solution set.

            When a 2D array is supplied, reference points are matched to
            solution sets according to dictionary iteration order.

        dystopian_point (np.ndarray):
            Dystopian point z^dy used as the hypervolume reference point.

    Returns:
        dict[str, PHIResult]:
            PHI results keyed by the same names as ``solution_sets``.

    Raises:
        ValueError:
            If ``solution_sets`` is empty, if the dimensions are
            inconsistent, or if the number of reference points does not
            match the number of solution sets.
    """
    if not solution_sets:
        raise ValueError("'solution_sets' cannot be empty.")

    reference_points = np.asarray(reference_points, dtype=float)
    dystopian_point = np.asarray(dystopian_point, dtype=float)

    if dystopian_point.ndim != 1:
        raise ValueError("'dystopian_point' must be a 1D array.")

    # One reference point shared by every solution set.
    if reference_points.ndim == 1:
        return {
            name: phi_indicator(
                solution_set=solution_set,
                reference_point=reference_points,
                dystopian_point=dystopian_point,
            )
            for name, solution_set in solution_sets.items()
        }

    # One reference point per solution set.
    if reference_points.ndim == 2:
        if len(reference_points) != len(solution_sets):
            raise ValueError(
                "When 'reference_points' is 2D, there must be exactly "
                "one reference point for every solution set."
            )

        return {
            name: phi_indicator(
                solution_set=solution_set,
                reference_point=reference_point,
                dystopian_point=dystopian_point,
            )
            for (name, solution_set), reference_point in zip(
                solution_sets.items(),
                reference_points,
                strict=True,
            )
        }

    raise ValueError(
        "'reference_points' must be either a 1D reference point or "
        "a 2D array of reference points."
    )

def phi_learning_phase(solution_sets: list, reference_points: list, dystopian_point: np.ndarray, generations: np.ndarray | None = None,) -> PHILearningResult:
    """Assess a learning phase using the PHI indicator.

    PHI is evaluated at every supplied generation. The responsiveness
    and stability measure RS is calculated as the area under the PHI
    curve, corresponding to Eq. (7) of Aghaei Pour et al. (2024).

    Args:
        solution_sets (list[np.ndarray]):
            Solution set P_t for every evaluated generation. Each item
            must have shape (n_solutions_t, n_objectives).

        reference_points (np.ndarray):
            Reference point associated with every evaluated generation.
            Shape must be (n_generations, n_objectives).

            A single one-dimensional reference point is also accepted;
            in that case, the same reference point is used for every
            generation.

        dystopian_point (np.ndarray):
            Dystopian point z^dy used as the hypervolume reference point.

        generations (np.ndarray | None):
            Generation coordinates corresponding to ``solution_sets``.
            If None, generations are assumed to be equally spaced as
            0, 1, ..., n_generations - 1.

    Returns:
        PHILearningResult:
            The RS value and PHI value at every evaluated generation.

    Raises:
        ValueError:
            If no solution sets are provided, if the number of reference
            points does not match the number of generations, or if
            ``generations`` has an incompatible length.

    References:
        P. Aghaei Pour, S. Bandaru, B. Afsar, M. Emmerich, and
        K. Miettinen, "A Performance Indicator for Interactive
        Evolutionary Multiobjective Optimization Methods,"
        IEEE Transactions on Evolutionary Computation, 2024.
    """
    if len(solution_sets) == 0:
        raise ValueError(
            "At least one solution set must be provided."
        )

    dystopian_point = np.asarray(
        dystopian_point,
        dtype=float,
    )

    reference_points = np.asarray(
        reference_points,
        dtype=float,
    )

    # Allow one RP to be reused for the whole learning interval.
    if reference_points.ndim == 1:
        reference_points = np.repeat(
            reference_points.reshape(1, -1),
            len(solution_sets),
            axis=0,
        )

    if reference_points.ndim != 2:
        raise ValueError(
            "'reference_points' must be a 1D or 2D array."
        )

    if len(reference_points) != len(solution_sets):
        raise ValueError(
            "There must be one reference point for every "
            "evaluated generation."
        )

    phi_results = [
        phi_indicator(
            solution_set,
            reference_point,
            dystopian_point,
        )
        for solution_set, reference_point in zip(
            solution_sets,
            reference_points,
            strict=True,
        )
    ]

    phi_values = np.asarray(
        [result.phi for result in phi_results],
        dtype=float,
    )

    if generations is None:
        generations = np.arange(
            len(phi_values),
            dtype=float,
        )
    else:
        generations = np.asarray(
            generations,
            dtype=float,
        )

    if generations.ndim != 1:
        raise ValueError(
            "'generations' must be a 1D array."
        )

    if len(generations) != len(phi_values):
        raise ValueError(
            "'generations' must contain one coordinate for "
            "every PHI value."
        )

    if np.any(np.diff(generations) <= 0):
        raise ValueError(
            "'generations' must be strictly increasing."
        )

    # Numerical area under PHI(t), corresponding to Eq. (7).
    rs = float(
        np.trapezoid(
            phi_values,
            x=generations,
        )
    )

    return PHILearningResult(
        rs=rs,
        phi_values=phi_values.tolist(),
    )

def phi_learning_phase_batch(
    solution_sets: dict[str, list[np.ndarray]],
    reference_points: np.ndarray,
    dystopian_point: np.ndarray,
    generations: np.ndarray | None = None,
) -> dict[str, PHILearningResult]:
    """Assess the PHI learning phase for multiple methods or runs."""

    return {
        name: phi_learning_phase(
            fronts,
            reference_points,
            dystopian_point,
            generations,
        )
        for name, fronts in solution_sets.items()
    }

def phi_decision_phase(solution_sets: list, reference_points: list, dystopian_point: np.ndarray) -> PHIDecisionResult:
    """Decision-phase assessment based on PHI.

    Implements the decision-phase similarity coefficients lambda^j
    from Eq. (9) and the fine-tuning decision-phase assessment FD
    from Eq. (10) of Aghaei Pour et al. (2024).

    Parameters
    ----------
    n_interactions
        Number d of interactions in the decision phase.
    indicator_values
        PHI values for the d decision-phase interactions.
    nadir
        Dystopian point z^dy used as the hypervolume reference point.
        The parameter name is retained for compatibility with the
        legacy DESDEO implementation.
    """
    reference_points = np.asarray(reference_points, dtype=float)
    if reference_points.ndim != 2:
        raise ValueError("reference_points must be a 2D array.")

    if len(solution_sets) != len(reference_points):
        raise ValueError(
            "There must be one solution set for every decision-phase "
            "reference point."
        )

    if len(solution_sets) == 0:
        raise ValueError("At least one solution set must be provided.")

    if len(reference_points) == 0:
        raise ValueError("At least one reference point must be provided.")

    phi_results = [
        phi_indicator(
            solution_set,
            reference_point,
            dystopian_point,
        )
        for solution_set, reference_point in zip(
            solution_sets,
            reference_points,
            strict=True,
        )
    ]

    phi_values = np.asarray(
        [result.phi for result in phi_results],
        dtype=float,
    )

    main_rp = reference_points[-1]

    main_area = hv(
        main_rp.reshape(1, -1),
        dystopian_point,
    )

    if main_area <= 0:
        raise ValueError(
            "The final reference point must have positive hypervolume."
        )

    shared_areas = np.asarray(
        [
            _shared_reference_point_hypervolume(
                rp,
                main_rp,
                dystopian_point,
            )
            for rp in reference_points
        ],
        dtype=float,
    )
    weights = _phi_decision_weights(shared_areas, main_area)

    fd = _calculate_fd(weights, phi_values)

    return PHIDecisionResult(fd=fd, weights=weights.tolist(), phi_values=phi_values.tolist())

def phi_decision_phase_batch(
    solution_sets: dict[str, list[np.ndarray]],
    reference_points: np.ndarray,
    dystopian_point: np.ndarray,
) -> dict[str, PHIDecisionResult]:
    """Assess the PHI decision phase for multiple methods or runs.

    Each method or run is evaluated using the same sequence of decision-maker
    reference points and the same dystopian point.

    Args:
        solution_sets (dict[str, list[np.ndarray]]):
            Dictionary mapping method/run names to their decision-phase
            solution sets. For each method, one solution set must be
            supplied for each decision-phase interaction.

            For example::

                {
                    "method_1": [P1, P2, P3],
                    "method_2": [P1, P2, P3],
                }

            where each Pj is a 2D array of shape
            (n_solutions, n_objectives).

        reference_points (np.ndarray):
            Decision-maker reference points, one per interaction.
            Shape must be (n_interactions, n_objectives). The final row
            is the final reference point z_hat^d used in Eqs. (8)-(10).

        dystopian_point (np.ndarray):
            Dystopian point z^dy used as the hypervolume reference point.

    Returns:
        dict[str, PHIDecisionResult]:
            Decision-phase results keyed by method/run name.
    """
    if not solution_sets:
        raise ValueError("'solution_sets' cannot be empty.")

    reference_points = np.asarray(reference_points, dtype=float)
    dystopian_point = np.asarray(dystopian_point, dtype=float)

    if reference_points.ndim != 2:
        raise ValueError(
            "'reference_points' must be a 2D array with shape "
            "(n_interactions, n_objectives)."
        )

    if dystopian_point.ndim != 1:
        raise ValueError("'dystopian_point' must be a 1D array.")

    if reference_points.shape[1] != dystopian_point.size:
        raise ValueError(
            "'reference_points' and 'dystopian_point' must have "
            "the same number of objectives."
        )

    results = {}

    for name, fronts in solution_sets.items():
        if len(fronts) != len(reference_points):
            raise ValueError(
                f"Method/run {name!r} has {len(fronts)} solution sets, "
                f"but {len(reference_points)} reference points were provided."
            )

        results[name] = phi_decision_phase(
            solution_sets=fronts,
            reference_points=reference_points,
            dystopian_point=dystopian_point,
        )

    return results



# Additional unary indicators can be added here.
# E.g. The IGD+ indicator, R2 indicator, averaged Hausdorff distance, etc.
# The function signature should be similar the already implemented functions, if reasonable.
# Optionally, a batch version of the indicator can be added as well.
# The methods should make similar assumptions about the input data as the already implemented functions.
