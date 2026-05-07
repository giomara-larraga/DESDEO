"""Defines end-points to access functionalities related to the RXIMO method."""

from typing import Annotated

import numpy as np
import polars as pl
from fastapi import APIRouter, Depends, HTTPException, status

from desdeo.api.models import (
    RXIMOExplainRequest,
    RXIMOExplainResponse,
)
from desdeo.explanations import ShapExplainer, generate_biased_mean_data

from .utils import ContextField, SessionContext, SessionContextGuard

router = APIRouter(prefix="/method/rximo")


@router.post("/explain")
def explain_reference_point(
    request: RXIMOExplainRequest,
    context: Annotated[
        SessionContext,
        Depends(SessionContextGuard(require=[ContextField.PROBLEM]).post),
    ],
) -> RXIMOExplainResponse:
    """Explain an RPM reference point with SHAP values using stored background data."""
    problem_db = context.problem_db

    if problem_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem with ID {request.problem_id} not found for current user.",
        )

    linked_datasets = list(problem_db.background_datasets)
    if not linked_datasets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No background data found for this problem. "
                "Please generate background data first using POST /background_data/add."
            ),
        )

    if request.background_dataset_id is None:
        dataset = max(linked_datasets, key=lambda candidate: candidate.id)
    else:
        dataset = next(
            (
                candidate
                for candidate in linked_datasets
                if candidate.id == request.background_dataset_id
            ),
            None,
        )
        if dataset is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Background dataset with ID {request.background_dataset_id} is not linked to "
                    f"problem {request.problem_id}."
                ),
            )

    if dataset.preference_values is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selected background dataset does not contain preference_values.",
        )

    output_symbols = [objective.symbol for objective in problem_db.objectives]
    input_symbols = [f"z_{symbol}" for symbol in output_symbols]

    missing_preference_symbols = [
        symbol for symbol in input_symbols if symbol not in dataset.preference_values
    ]
    missing_objective_symbols = [
        symbol for symbol in output_symbols if symbol not in dataset.objective_values
    ]

    if missing_preference_symbols or missing_objective_symbols:
        details = []
        if missing_preference_symbols:
            details.append(f"missing preference symbols: {missing_preference_symbols}")
        if missing_objective_symbols:
            details.append(f"missing objective symbols: {missing_objective_symbols}")

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Background dataset symbols are incompatible with the selected problem ("
                + "; ".join(details)
                + ")."
            ),
        )

    normalized_reference_point: dict[str, float] = {}
    aspiration_levels = request.preference.aspiration_levels
    for objective_symbol, input_symbol in zip(
        output_symbols, input_symbols, strict=False
    ):
        if objective_symbol in aspiration_levels:
            normalized_reference_point[objective_symbol] = float(
                aspiration_levels[objective_symbol]
            )
            continue

        if input_symbol in aspiration_levels:
            normalized_reference_point[objective_symbol] = float(
                aspiration_levels[input_symbol]
            )
            continue

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Reference point is missing objective '{objective_symbol}'. "
                f"Accepted keys: '{objective_symbol}' or '{input_symbol}'."
            ),
        )

    problem_data = pl.DataFrame(
        {
            **{symbol: dataset.preference_values[symbol] for symbol in input_symbols},
            **{symbol: dataset.objective_values[symbol] for symbol in output_symbols},
        }
    )

    # Normalize all columns to [0, 1] so the KD-tree uses fair Euclidean distances.
    # Ideal/nadir are preferred as bounds; fall back to dataset min/max when not set.
    all_symbols = input_symbols + output_symbols
    col_min: dict[str, float] = {}
    col_max: dict[str, float] = {}
    for objective in problem_db.objectives:
        sym = objective.symbol
        z_sym = f"z_{sym}"
        lo = (
            min(float(objective.ideal), float(objective.nadir))
            if objective.ideal is not None and objective.nadir is not None
            else float(problem_data[z_sym].min())
        )
        hi = (
            max(float(objective.ideal), float(objective.nadir))
            if objective.ideal is not None and objective.nadir is not None
            else float(problem_data[z_sym].max())
        )
        col_min[z_sym] = col_min[sym] = lo
        col_max[z_sym] = col_max[sym] = hi
    col_range = {col: (col_max[col] - col_min[col]) or 1.0 for col in all_symbols}
    norm_problem_data = problem_data.with_columns(
        [
            ((pl.col(col) - col_min[col]) / col_range[col]).alias(col)
            for col in all_symbols
        ]
    )

    explainer = ShapExplainer(
        problem_data=norm_problem_data,
        input_symbols=input_symbols,
        output_symbols=output_symbols,
    )

    # If the problem data needs to be filtered, the code for that should be put here.
    # For now, we assume use the entire dataset as background data.

    explainer.setup(background_data=norm_problem_data)

    to_be_explained = pl.DataFrame(
        {
            f"z_{symbol}": [(value - col_min[f"z_{symbol}"]) / col_range[f"z_{symbol}"]]
            for symbol, value in normalized_reference_point.items()
        }
    )
    explanation = explainer.explain_input(to_be_explained)

    explanation_values = np.asarray(explanation.values)
    sample_values = np.asarray(explanation_values[0])
    if sample_values.ndim == 1:
        sample_values = sample_values.reshape(-1, 1)
    shap_matrix = sample_values.T

    base_values_array = np.asarray(explanation.base_values).reshape(-1)
    explained_output_array = np.asarray(
        explainer.evaluate(to_be_explained[input_symbols].to_numpy())
    ).reshape(-1)

    # Denormalize outputs back to original scale
    output_ranges = np.array([col_range[s] for s in output_symbols])
    output_mins = np.array([col_min[s] for s in output_symbols])
    explained_output_array = explained_output_array * output_ranges + output_mins
    base_values_array = base_values_array * output_ranges + output_mins
    shap_matrix = shap_matrix * output_ranges[:, np.newaxis]

    return RXIMOExplainResponse(
        problem_id=request.problem_id,
        background_dataset_id=dataset.id,
        input_symbols=input_symbols,
        output_symbols=output_symbols,
        reference_point=normalized_reference_point,
        explained_objective_values={
            symbol: float(explained_output_array[idx])
            for idx, symbol in enumerate(output_symbols)
        },
        base_values={
            symbol: float(base_values_array[idx])
            for idx, symbol in enumerate(output_symbols)
        },
        shap_values={
            output_symbol: {
                input_symbol: float(shap_matrix[out_idx, in_idx])
                for in_idx, input_symbol in enumerate(input_symbols)
            }
            for out_idx, output_symbol in enumerate(output_symbols)
        },
    )
