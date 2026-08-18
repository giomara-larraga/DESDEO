from typing import Annotated

import polars as pl
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select

from desdeo.emo import algorithms, preference_handling


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
    SCOREBandsMethodInitializeRequest,
    SCOREBandsMethodInitializeResponse,
)

router = APIRouter(prefix="/method/score_bands_method")


@router.post("/initialize")
def initialize_or_get_score_bands_method(
    request: SCOREBandsMethodInitializeRequest,
    context: Annotated[
        SessionContext,
        Depends(
            SessionContextGuard(
                require=[ContextField.PROBLEM]
            ).post
        ),
    ],
) -> SCOREBandsMethodInitializeResponse:

    """Get the latest SCOREBandsMethodState for a problem, or calculate and persist SCORE Bands if none exists."""

    db_session = context.db_session
    user = context.user
    problem_db = context.problem_db
    interactive_session = context.interactive_session
    parent_state = context.parent_state

    # Look for latest relevant state in the session
    statement = (
        select(StateDB)
        .where(
            StateDB.problem_id == request.problem_id,
            StateDB.session_id == (interactive_session.id if interactive_session else user.active_session_id),
        )
        .order_by(StateDB.id.desc())
    )
    states = db_session.exec(statement).all()

    # Find the latest state that is a SCOREBandsMethodState
    latest_state = None
    for state in states:
        if isinstance(state.state, SCOREBandsMethodState):
            latest_state = state
            break

    if latest_state is not None:
        # If a relevant state exists, return it without recalculating
        return SCOREBandsMethodInitializeResponse(
            state_id=latest_state.id,
            result=latest_state.state.result,
        )

    # If no relevant state exists, proceed to calculate and persist SCORE Bands

    # Check the optimization options in the request. If optimization is requested, we need to check if the problem is suitable for optimization.
    if request.optimization_options is not None:
        return initialize_score_bands_method_with_optimization(request, context)
    else:
        # If optimization is not requested, we can proceed with SCORE Bands calculation without additional checks.
        return initialize_score_bands_method_without_optimization(request, context)

    
def initialize_score_bands_method_without_optimization(
    request: SCOREBandsMethodInitializeRequest,
    context: Annotated[
        SessionContext,
        Depends(
            SessionContextGuard(
                require=[ContextField.PROBLEM]
            ).post
        ),
    ],
) -> SCOREBandsMethodInitializeResponse:

    """Get the latest SCOREBandsMethodState for a problem, or calculate and persist SCORE Bands if none exists."""

    db_session = context.db_session
    user = context.user
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

    # Use scorebands_options.dimensions when explicitly provided.
    # Otherwise use all objectives in the order defined by the problem.
    if request.scorebands_options.dimensions is not None:
        dimensions = request.scorebands_options.dimensions
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
    scorebands_options = request.scorebands_options.model_copy(deep=True)
    scorebands_options.dimensions = dimensions

    # Fill display metadata from the problem only when not supplied.
    if scorebands_options.descriptive_names is None:
        scorebands_options.descriptive_names = {
            symbol: objective_by_symbol[symbol].name
            for symbol in dimensions
        }

    if scorebands_options.units is None:
        scorebands_options.units = {
            symbol: objective_by_symbol[symbol].unit or ""
            for symbol in dimensions
        }

    try:
        result = score_json(
            data=data,
            options=scorebands_options,
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

    return SCOREBandsMethodInitializeResponse(
        state_id=state.id,
        result=result,
    )

def initialize_score_bands_method_with_optimization(
    request: SCOREBandsMethodInitializeRequest,
    context: Annotated[
        SessionContext,
        Depends(
            SessionContextGuard(
                require=[ContextField.PROBLEM]
            ).post
        ),
    ],
) -> SCOREBandsMethodInitializeResponse:

    """Get the latest SCOREBandsMethodState for a problem, or calculate and persist SCORE Bands if none exists."""

    db_session = context.db_session
    problem_db = context.problem_db
    interactive_session = context.interactive_session
    parent_state = context.parent_state

    problem = Problem.from_problemdb(problem_db)

    # Use NSGA-III or RVEA optimization algorithm based on the request. If no algorithm is specified, use the default algorithm.
    if request.optimization_options is not None:
        algorithm = request.optimization_options.algorithm
        algorithm_options = request.optimization_options.algorithm_options

        if algorithm is None:
            # Use default algorithm (e.g., NSGA-III)
            algorithm = "nsga3"
        else:
            # Validate the specified algorithm
            if algorithm not in ["nsga3", "rvea"]:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Invalid optimization algorithm: {algorithm}. "
                        "Supported algorithms are 'nsga3' and 'rvea'."
                    ),
                )
        match algorithm:
            case "nsga3":
                # Set up NSGA-III optimization algorithm with provided options
                options = algorithms.nsga3_options()

            case "rvea":
                # Set up RVEA optimization algorithm with provided options
                options = algorithms.rvea_options()

        solver, extras = algorithms.emo_constructor(emo_options=options, problem=problem)

        result_optimizer = solver()
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Optimization options must be provided when optimization is requested."
            ),
        )

    # Get the data from the solver result for SCORE Bands calculation. This assumes that the solver result contains the necessary objective values in a suitable format.
    dimensions = [
                objective.symbol
                for objective in problem.objectives
                if objective.symbol in result_optimizer.optimal_outputs
            ]
    
    data = pl.DataFrame(
        {
            symbol: result_optimizer.optimal_outputs[symbol]
            for symbol in dimensions
        }
    )

    objective_by_symbol = {
        objective.symbol: objective
        for objective in problem.objectives
    }

    # Copy so the request object itself is not modified.
    scorebands_options = request.scorebands_options.model_copy(deep=True)
    scorebands_options.dimensions = dimensions

    # Fill display metadata from the problem only when not supplied.
    if scorebands_options.descriptive_names is None:
        scorebands_options.descriptive_names = {
            symbol: objective_by_symbol[symbol].name
            for symbol in dimensions
        }

    if scorebands_options.units is None:
        scorebands_options.units = {
            symbol: objective_by_symbol[symbol].unit or ""
            for symbol in dimensions
        }

    try:
        result = score_json(
            data=data,
            options=scorebands_options,
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

    return SCOREBandsMethodInitializeResponse(
        state_id=state.id,
        result=result,
    )