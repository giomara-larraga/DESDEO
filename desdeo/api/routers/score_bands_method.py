from typing import Annotated

import polars as pl
from fastapi import APIRouter, Depends, HTTPException, status

from desdeo.api.models import (
    SCOREBandsMethodState,
    StateDB,
)
from desdeo.api.routers.utils import (
    ContextField,
    SessionContext,
    SessionContextGuard,
)
from desdeo.problem import Problem
from desdeo.tools.score_bands import score_json

from desdeo.api.models.score_bands_method import (
    SCOREBandsMethodRequest,
    SCOREBandsMethodResponse,
)

router = APIRouter(prefix="/method/score_bands_method")


@router.post("/solve")
def calculate_score_bands(
    request: SCOREBandsMethodRequest,
    context: Annotated[
        SessionContext,
        Depends(
            SessionContextGuard(
                require=[ContextField.PROBLEM]
            ).post
        ),
    ],
) -> SCOREBandsMethodResponse:
    """Calculate SCORE Bands from a problem's discrete representation."""

    db_session = context.db_session
    problem_db = context.problem_db
    interactive_session = context.interactive_session
    parent_state = context.parent_state

    problem = Problem.from_problemdb(problem_db)

    discrete = problem.discrete_representation

    if discrete is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "SCORE Bands requires a problem with a "
                "discrete representation."
            ),
        )

    objective_values = discrete.objective_values

    # Use options.dimensions when explicitly provided.
    # Otherwise use all objectives in the order defined by the problem.
    if request.options.dimensions is not None:
        dimensions = request.options.dimensions
    else:
        dimensions = [
            objective.symbol
            for objective in problem.objectives
            if objective.symbol in objective_values
        ]

    if len(dimensions) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="SCORE Bands requires at least two objectives.",
        )

    unknown_dimensions = [
        symbol
        for symbol in dimensions
        if symbol not in objective_values
    ]

    if unknown_dimensions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "The discrete representation does not contain "
                f"these objectives: {unknown_dimensions}."
            ),
        )

    column_lengths = {
        symbol: len(objective_values[symbol])
        for symbol in dimensions
    }

    if len(set(column_lengths.values())) != 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Discrete objective columns have different "
                f"lengths: {column_lengths}."
            ),
        )

    data = pl.DataFrame(
        {
            symbol: objective_values[symbol]
            for symbol in dimensions
        }
    )

    objective_by_symbol = {
        objective.symbol: objective
        for objective in problem.objectives
    }

    # Copy so the request object itself is not modified.
    options = request.options.model_copy(deep=True)
    options.dimensions = dimensions

    # Fill display metadata from the problem only when not supplied.
    if options.descriptive_names is None:
        options.descriptive_names = {
            symbol: objective_by_symbol[symbol].name
            for symbol in dimensions
        }

    if options.units is None:
        options.units = {
            symbol: objective_by_symbol[symbol].unit or ""
            for symbol in dimensions
        }

    try:
        result = score_json(
            data=data,
            options=options,
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    score_state = SCOREBandsMethodState.from_result(result)

    state = StateDB.create(
        database_session=db_session,
        problem_id=problem_db.id,
        session_id=(
            interactive_session.id
            if interactive_session is not None
            else None
        ),
        parent_id=(
            parent_state.id
            if parent_state is not None
            else None
        ),
        state=score_state,
    )

    db_session.add(state)
    db_session.commit()
    db_session.refresh(state)

    return SCOREBandsMethodResponse(
        state_id=state.id,
        result=result,
    )