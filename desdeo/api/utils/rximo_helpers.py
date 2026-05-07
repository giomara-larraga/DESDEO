"""R-XIMO helpers shared between API routers.

The SHAP-explainer endpoints (``/method/rximo/explain`` and
``/background_data/explain``) all follow the same pattern: build a SHAP
matrix from a `ShapExplainer`, then optionally run Algorithm 1 from
Misitano et al. (2022) to derive a textual rival/explanation/suggestion.
This module factors that second step out so the routers stay thin.
"""

import numpy as np

from desdeo.explanations.rximo import find_rival


def compute_rximo_results(
    shap_matrix: np.ndarray,
    reference_point: np.ndarray,
    solution: np.ndarray,
    is_maximized: np.ndarray,
    objective_symbols: list[str],
    objective_names: list[str],
    target_symbol: str | None = None,
) -> dict[str, dict]:
    """Run R-XIMO for one or every objective, in minimization form.

    The SHAP values, reference point, and solution are converted to
    minimization form (sign-flipped on maximized objectives) before
    `find_rival` is invoked, so the algorithm's "negative SHAP =
    improving" convention always holds. The returned dict carries each
    target's rival (as both index and symbol), the case-1..9 explanation
    index, and the textual explanation/suggestion strings.

    Args:
        shap_matrix (np.ndarray): square SHAP matrix of shape (k, k) in
            **original** scale, with rows = output objectives and columns
            = reference-point components.
        reference_point (np.ndarray): 1D array of length k with the
            reference point components in **original** scale.
        solution (np.ndarray): 1D array of length k with the corresponding
            solution components in **original** scale.
        is_maximized (np.ndarray): boolean 1D array of length k. ``True``
            entries flag maximized objectives whose sign must be flipped
            to obtain minimization form.
        objective_symbols (list[str]): output-symbol order matching the
            rows of `shap_matrix` and the entries of the other arrays.
        objective_names (list[str]): human-readable objective names used
            when rendering the textual explanations and suggestions.
        target_symbol (str | None): if given, R-XIMO is run only for that
            target objective. Otherwise it is run for every objective.

    Returns:
        dict[str, dict]: a mapping ``{target_symbol: result_dict}``. Each
            result_dict has the keys ``rival_index``, ``rival_symbol``,
            ``explanation``, ``suggestion``, ``explanation_index``,
            ``best_effect`` and ``worst_effect``.
    """
    shap_arr = np.asarray(shap_matrix, dtype=float)
    ref_arr = np.asarray(reference_point, dtype=float).reshape(-1)
    sol_arr = np.asarray(solution, dtype=float).reshape(-1)
    is_max = np.asarray(is_maximized, dtype=bool).reshape(-1)

    # Convert to minimization form. For maximized objective i, increasing the
    # original value is "better"; in min form, the same change becomes
    # "smaller is better", which is what `find_rival` assumes.
    sign_flip = np.where(is_max, -1.0, 1.0)
    min_ref = ref_arr * sign_flip
    min_sol = sol_arr * sign_flip
    # Row i of shap_matrix describes effects on output i. Flipping the sign of
    # output i means flipping the sign of every entry in row i.
    min_shap = shap_arr * sign_flip[:, None]

    if target_symbol is not None:
        if target_symbol not in objective_symbols:
            raise ValueError(f"target_symbol {target_symbol!r} not in objective_symbols {objective_symbols}.")
        targets = [target_symbol]
    else:
        targets = list(objective_symbols)

    results: dict[str, dict] = {}
    for sym in targets:
        target_idx = objective_symbols.index(sym)
        result = find_rival(
            shap_values=min_shap,
            reference_point=min_ref,
            solution=min_sol,
            target_index=target_idx,
            objective_names=objective_names,
        )
        results[sym] = {
            "rival_index": int(result.rival_index),
            "rival_symbol": objective_symbols[result.rival_index],
            "explanation": result.explanation,
            "suggestion": result.suggestion,
            "explanation_index": int(result.explanation_index),
            "best_effect": int(result.best_effect),
            "worst_effect": int(result.worst_effect),
        }
    return results
