import copy
import logging

from typing import Annotated

import polars as pl
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from desdeo.api.db import get_session
from desdeo.api.models.problem import ProblemDB
from desdeo.api.models.session import InteractiveSessionDB
from desdeo.api.models.user import User
from desdeo.api.routers.gdm.utils import check_decision_maker
from desdeo.api.routers.user_authentication import get_current_user
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
from desdeo.emo.operators.selection import ReferenceVectorOptions
from desdeo.problem import Problem
from desdeo.tools.score_bands import score_json

from desdeo.api.models.score_bands_method import (
    SCOREBandsMethodInitializeRequest,
    SCOREBandsMethodInitializeResponse,
    SCOREBandsMethodIterationRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/method/score_bands_method")


def get_objective_ranges(problem: Problem, relevant_solutions):
    """Get the ranges for each objective from the relevant solutions."""
    objective_ranges = {}
    for objective in problem.objectives:
        symbol = objective.symbol
        if symbol in relevant_solutions:
            values = relevant_solutions[symbol]
            objective_ranges[symbol] = [min(values), max(values)]
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Objective {symbol} not found in relevant solutions.",
            )
    return objective_ranges


@router.post("/initialize")
def initialize_or_get_score_bands_method(
    request: SCOREBandsMethodInitializeRequest,
    context: Annotated[
        SessionContext,
        Depends(SessionContextGuard(require=[ContextField.PROBLEM]).post),
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
            StateDB.session_id
            == (
                interactive_session.id
                if interactive_session
                else user.active_session_id
            ),
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

    if request.optimization_options.optimize:
        return initialize_score_bands_method_with_optimization(
            request, context
        )

    return initialize_score_bands_method_without_optimization(
        request, context
    )


def initialize_score_bands_method_without_optimization(
    request: SCOREBandsMethodInitializeRequest,
    context: Annotated[
        SessionContext,
        Depends(SessionContextGuard(require=[ContextField.PROBLEM]).post),
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
                "SCORE Bands requires a problem with a " "discrete representation."
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
        symbol for symbol in dimensions if symbol not in objective_values
    ]

    if unknown_dimensions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "The discrete representation does not contain "
                f"these objectives: {unknown_dimensions}."
            ),
        )

    column_lengths = {symbol: len(objective_values[symbol]) for symbol in dimensions}

    if len(set(column_lengths.values())) != 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Discrete objective columns have different "
                f"lengths: {column_lengths}."
            ),
        )

    data = pl.DataFrame({symbol: objective_values[symbol] for symbol in dimensions})

    objective_by_symbol = {
        objective.symbol: objective for objective in problem.objectives
    }

    # Copy so the request object itself is not modified.
    scorebands_options = request.scorebands_options.model_copy(deep=True)
    scorebands_options.dimensions = dimensions

    # Fill display metadata from the problem only when not supplied.
    if scorebands_options.descriptive_names is None:
        scorebands_options.descriptive_names = {
            symbol: objective_by_symbol[symbol].name for symbol in dimensions
        }

    if scorebands_options.units is None:
        scorebands_options.units = {
            symbol: objective_by_symbol[symbol].unit or "" for symbol in dimensions
        }

    score_state, result = get_score_bands_state(data, scorebands_options)

    state = StateDB.create(
        database_session=db_session,
        problem_id=problem_db.id,
        session_id=(
            interactive_session.id if interactive_session is not None else None
        ),
        parent_id=(parent_state.id if parent_state is not None else None),
        state=score_state,
    )

    db_session.add(state)
    db_session.commit()
    db_session.refresh(state)

    return SCOREBandsMethodInitializeResponse(
        state_id=state.id,
        result=result,
    )


def compute_score_bands_with_optimization(
    problem: Problem,
    request: (
        SCOREBandsMethodInitializeRequest
        | SCOREBandsMethodIterationRequest
    ),
    preferred_ranges: dict[str, tuple[float, float]] | None = None,
):
    """Solve the problem using an evolutionary algorithm."""

    algorithm = request.optimization_options.algorithm or "nsga3"

    if algorithm == "nsga3":
        options = algorithms.nsga3_options()
    elif algorithm == "rvea":
        options = algorithms.rvea_options()
    else:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported optimization algorithm: {algorithm}",
        )

    if preferred_ranges is not None:
        aspiration_levels = {}
        reservation_levels = {}

        for objective in problem.objectives:
            symbol = objective.symbol

            if symbol not in preferred_ranges:
                raise HTTPException(
                    status_code=422,
                    detail=f"Missing preferred range for {symbol}.",
                )

            lower, upper = preferred_ranges[symbol]

            if lower > upper:
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid preferred range for {symbol}.",
                )

            if objective.maximize:
                aspiration_levels[symbol] = upper
                reservation_levels[symbol] = lower
            else:
                aspiration_levels[symbol] = lower
                reservation_levels[symbol] = upper

        options.preference = (
            preference_handling.DesirableRangesOptions(
                aspiration_levels=aspiration_levels,
                reservation_levels=reservation_levels,
            )
        )

    algorithm_options = (
        request.optimization_options.algorithm_options or {}
    )

    if "number_of_vectors" in algorithm_options:
        options.template.selection.reference_vector_options.number_of_vectors = (
            int(algorithm_options["number_of_vectors"])
        )

    solver, extras = algorithms.emo_constructor(
        emo_options=options,
        problem=problem,
    )

    return solver()


def get_dataset_from_solver_result(problem: Problem, result_optimizer):
    """Extract the dataset from the solver result for SCORE Bands calculation."""
    dimensions = [
        objective.symbol
        for objective in problem.objectives
        if objective.symbol in result_optimizer.optimal_outputs
    ]

    data = pl.DataFrame(
        {symbol: result_optimizer.optimal_outputs[symbol] for symbol in dimensions}
    )

    return data, dimensions


def get_score_bands_state(
    data: pl.DataFrame,
    scorebands_options,
    relevant_solution_ids: list[int] | None = None,
):
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

    score_state = SCOREBandsMethodState.from_result(
        result,
        relevant_solution_ids=relevant_solution_ids,
    )

    return score_state, result


def initialize_score_bands_method_with_optimization(
    request: SCOREBandsMethodInitializeRequest,
    context: Annotated[
        SessionContext,
        Depends(SessionContextGuard(require=[ContextField.PROBLEM]).post),
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
        # Here you would implement the logic to run the optimization algorithm based on the request.
        # For example, you might call a function that runs NSGA-III or RVEA and returns the results.
        result_optimizer = compute_score_bands_with_optimization(problem, request)
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Optimization options must be provided when optimization is requested."
            ),
        )

    # Get the data from the solver result for SCORE Bands calculation. This assumes that the solver result contains the necessary objective values in a suitable format.
    data, dimensions = get_dataset_from_solver_result(problem, result_optimizer)

    objective_by_symbol = {
        objective.symbol: objective for objective in problem.objectives
    }

    # Copy so the request object itself is not modified.
    scorebands_options = request.scorebands_options.model_copy(deep=True)
    scorebands_options.dimensions = dimensions

    # Fill display metadata from the problem only when not supplied.
    if scorebands_options.descriptive_names is None:
        scorebands_options.descriptive_names = {
            symbol: objective_by_symbol[symbol].name for symbol in dimensions
        }

    if scorebands_options.units is None:
        scorebands_options.units = {
            symbol: objective_by_symbol[symbol].unit or "" for symbol in dimensions
        }

    score_state, result = get_score_bands_state(data, scorebands_options)

    state = StateDB.create(
        database_session=db_session,
        problem_id=problem_db.id,
        session_id=(
            interactive_session.id if interactive_session is not None else None
        ),
        parent_id=(parent_state.id if parent_state is not None else None),
        state=score_state,
    )

    db_session.add(state)
    db_session.commit()
    db_session.refresh(state)

    return SCOREBandsMethodInitializeResponse(
        state_id=state.id,
        result=result,
    )


def score_bands_method_iterate(
    request: SCOREBandsMethodInitializeRequest,
    context: Annotated[
        SessionContext,
        Depends(SessionContextGuard(require=[ContextField.PROBLEM]).post),
    ],
) -> SCOREBandsMethodInitializeResponse:
    """Iterate the SCORE Bands method for a problem, calculating and persisting new SCORE Bands."""
    # This function can be implemented to perform iterative calculations of SCORE Bands if needed.
    # For now, it simply calls the initialize function to get or calculate the latest SCORE Bands.
    return initialize_or_get_score_bands_method(request, context)


@router.post("/iterate")
def score_bands_method_iteration(
    request: SCOREBandsMethodIterationRequest,
    context: Annotated[
        SessionContext,
        Depends(
            SessionContextGuard(
                require=[
                    ContextField.PROBLEM,
                    ContextField.PARENT_STATE,
                ]
            ).post
        ),
    ],
) -> SCOREBandsMethodInitializeResponse:
    """Run a new evolutionary search using a selected SCORE band."""

    db_session = context.db_session
    problem_db = context.problem_db
    parent_state_db = context.parent_state
    interactive_session = context.interactive_session

    if problem_db is None or parent_state_db is None:
        raise HTTPException(
            status_code=400,
            detail="Problem or parent state is missing.",
        )

    if interactive_session is None:
        raise HTTPException(
            status_code=400,
            detail="An active interactive session is required.",
        )

    if interactive_session.user_id != context.user.id:
        raise HTTPException(
            status_code=403,
            detail="The interactive session does not belong to this user.",
        )

    if (
        parent_state_db.id != request.parent_state_id
        or parent_state_db.problem_id != problem_db.id
        or parent_state_db.session_id != interactive_session.id
    ):
        raise HTTPException(
            status_code=403,
            detail="The parent state does not belong to this session.",
        )

    parent_state = parent_state_db.state

    if not isinstance(parent_state, SCOREBandsMethodState):
        raise HTTPException(
            status_code=400,
            detail="The parent state is not a SCORE Bands state.",
        )

    if not request.optimization_options.optimize:
        raise HTTPException(
            status_code=422,
            detail="Evolutionary optimization must be enabled.",
        )

    parent_result = parent_state.result

    selected_ranges = parent_result.bands.get(
        request.selected_cluster_id
    )

    if selected_ranges is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Band {request.selected_cluster_id} "
                "does not exist in the parent state."
            ),
        )

    # Use the selected band's objective ranges as preferences.
    preferred_ranges = {
        symbol: (float(bounds[0]), float(bounds[1]))
        for symbol, bounds in selected_ranges.items()
    }

    problem = Problem.from_problemdb(problem_db)

    # Run NSGA-III or RVEA with the selected preferences.
    optimizer_result = compute_score_bands_with_optimization(
        problem=problem,
        request=request,
        preferred_ranges=preferred_ranges,
    )

    # Extract newly generated objective values.
    new_data, dimensions = get_dataset_from_solver_result(
        problem,
        optimizer_result,
    )

    if new_data.height == 0:
        raise HTTPException(
            status_code=422,
            detail="The evolutionary algorithm returned no solutions.",
        )

    # Inherit the SCORE Bands configuration from the parent.
    scorebands_options = parent_result.options.model_copy(
        deep=True
    )

    scorebands_options.dimensions = dimensions

    # Create new SCORE Bands from the new solutions.
    score_state, result = get_score_bands_state(
        data=new_data,
        scorebands_options=scorebands_options,
    )

    # Persist the new SCORE Bands state as a child of the previous one.
    state_db = StateDB.create(
        database_session=db_session,
        problem_id=problem_db.id,
        session_id=interactive_session.id,
        parent_id=parent_state_db.id,
        state=score_state,
    )

    db_session.add(state_db)
    db_session.commit()
    db_session.refresh(state_db)

    return SCOREBandsMethodInitializeResponse(
        state_id=state_db.id,
        result=result,
    )
