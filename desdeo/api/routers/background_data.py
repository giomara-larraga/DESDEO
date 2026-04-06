"""Endpoints for storing and retrieving explainer background datasets."""

from typing import Annotated

import numpy as np
import polars as pl
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from desdeo.api.db import get_session
from desdeo.explanations import ShapExplainer
from desdeo.api.models import (
    BackgroundDatasetCreateRequest,
    BackgroundDatasetDB,
    BackgroundDatasetExplainRequest,
    BackgroundDatasetExplainResponse,
    BackgroundDatasetInfo,
    ProblemDB,
    User,
)
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.api.utils.database import (
    create_background_dataset,
    list_background_datasets,
)

from .utils import ContextField, SessionContext, SessionContextGuard

router = APIRouter(prefix="/background_data")


def _to_background_dataset_info(dataset: BackgroundDatasetDB) -> BackgroundDatasetInfo:
    """Convert a database model to the API response model."""
    return BackgroundDatasetInfo(
        id=dataset.id,
        problem_ids=[problem.id for problem in dataset.problems],
        name=dataset.name,
        kind=dataset.kind,
        num_samples=dataset.num_samples,
        preference_values=dataset.preference_values,
        objective_values=dataset.objective_values,
    )


@router.post("/add")
def add_background_dataset(
    request: BackgroundDatasetCreateRequest,
    user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_session)],
) -> BackgroundDatasetInfo:
    """Create a background dataset linked to one or more problems owned by the current user."""
    allowed_problem_ids = {
        problem.id
        for problem in db_session.exec(
            select(ProblemDB).where(
                ProblemDB.user_id == user.id, ProblemDB.id.in_(request.problem_ids)
            )
        ).all()
    }
    unauthorized_problem_ids = [
        problem_id
        for problem_id in request.problem_ids
        if problem_id not in allowed_problem_ids
    ]

    if unauthorized_problem_ids:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Unauthorized or unknown problem ids: {unauthorized_problem_ids}",
        )

    background_dataset = create_background_dataset(request, db_session)
    return _to_background_dataset_info(background_dataset)


@router.get("/problem/{problem_id}")
def get_problem_background_datasets(
    problem_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_session)],
) -> list[BackgroundDatasetInfo]:
    """List background datasets for a problem."""
    # Verify the user owns this problem
    problem_db = db_session.exec(
        select(ProblemDB).where(
            ProblemDB.id == problem_id,
            ProblemDB.user_id == user.id,
        )
    ).first()

    if problem_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem with ID {problem_id} not found or unauthorized.",
        )

    datasets = list_background_datasets(problem_id=problem_id, session=db_session)
    return [_to_background_dataset_info(dataset) for dataset in datasets]


@router.get("/{background_dataset_id}")
def get_background_dataset(
    background_dataset_id: int,
    context: Annotated[SessionContext, Depends(SessionContextGuard().get)],
) -> BackgroundDatasetInfo:
    """Fetch a single background dataset if it belongs to one of the current user's problems."""
    db_session = context.db_session
    user = context.user

    dataset = db_session.get(BackgroundDatasetDB, background_dataset_id)
    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Background dataset with ID {background_dataset_id} not found.",
        )

    if not any(problem.user_id == user.id for problem in dataset.problems):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized user."
        )

    return _to_background_dataset_info(dataset)


@router.post("/explain")
def explain_reference_point(
    request: BackgroundDatasetExplainRequest,
    user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_session)],
) -> BackgroundDatasetExplainResponse:
    """Explain a DM reference point using SHAP and background data stored in the database."""
    problem_db = db_session.exec(
        select(ProblemDB).where(
            ProblemDB.id == request.problem_id,
            ProblemDB.user_id == user.id,
        )
    ).first()

    if problem_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem with ID {request.problem_id} not found for current user.",
        )

    dataset = db_session.get(BackgroundDatasetDB, request.background_dataset_id)
    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Background dataset with ID {request.background_dataset_id} not found.",
        )

    if request.problem_id not in [problem.id for problem in dataset.problems]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Background dataset is not linked to the given problem.",
        )

    if dataset.preference_values is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Background dataset does not contain preference_values required for SHAP input symbols.",
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
    for objective_symbol, input_symbol in zip(
        output_symbols, input_symbols, strict=False
    ):
        if objective_symbol in request.reference_point:
            normalized_reference_point[objective_symbol] = float(
                request.reference_point[objective_symbol]
            )
            continue

        if input_symbol in request.reference_point:
            normalized_reference_point[objective_symbol] = float(
                request.reference_point[input_symbol]
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

    explainer = ShapExplainer(
        problem_data=problem_data,
        input_symbols=input_symbols,
        output_symbols=output_symbols,
    )
    explainer.setup(background_data=problem_data)

    to_be_explained = pl.DataFrame(
        {f"z_{symbol}": [value] for symbol, value in normalized_reference_point.items()}
    )
    explanation = explainer.explain_input(to_be_explained)

    explanation_values = np.asarray(explanation.values)
    sample_values = np.asarray(explanation_values[0])
    if sample_values.ndim == 1:
        sample_values = sample_values.reshape(-1, 1)

    # SHAP uses shape (inputs, outputs); convert to output -> input for readability.
    shap_matrix = sample_values.T

    base_values_array = np.asarray(explanation.base_values).reshape(-1)
    explained_output_array = np.asarray(
        explainer.evaluate(to_be_explained[input_symbols].to_numpy())
    ).reshape(-1)

    return BackgroundDatasetExplainResponse(
        problem_id=request.problem_id,
        background_dataset_id=request.background_dataset_id,
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
