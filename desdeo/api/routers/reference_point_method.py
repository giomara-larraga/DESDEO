"""Defines end-points to access functionalities related to the reference point method."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from numpy import allclose
from sqlmodel import Session, select

from desdeo.api.models import (
    IntermediateSolutionRequest,
    RPMSolveRequest,
    RPMSolveResponse,
    RPMSolveState,
    RPMDeleteSaveRequest,
    RPMDeleteSaveResponse,
    RPMFinalizeRequest,
    RPMFinalizeResponse,
    RPMFinalState,
    RPMIntermediateSolutionResponse,
    RPMSaveRequest,
    RPMSaveResponse,
    RPMSaveState,
    SavedSolutionReference,
    SolutionReference,
    SolutionReferenceResponse,
    StateDB,
    User,
    UserSavedSolutionDB,
)
from desdeo.api.models.nimbus import NIMBUSClassificationResponse
from desdeo.api.routers.generic import solve_intermediate
from desdeo.api.routers.problem import check_solver
from desdeo.mcdm import rpm_solve_solutions
from desdeo.problem import Problem
from desdeo.tools import SolverResults

from .utils import ContextField, SessionContext, SessionContextGuard

router = APIRouter(prefix="/method/rpm")


# helper for collecting solutions
def filter_duplicates(
    solutions: list[SavedSolutionReference],
) -> list[SavedSolutionReference]:
    """Filters out the duplicate values of objectives."""
    # No solutions or only one solution. There can not be any duplicates.
    if len(solutions) < 2:  # noqa: PLR2004
        return solutions

    # Get the objective values
    objective_values_list = [sol.objective_values for sol in solutions]
    # Get the function symbols
    objective_keys = list(objective_values_list[0])
    # Get the corresponding values for functions into a list of lists of values
    valuelists = [
        [dictionary[key] for key in objective_keys]
        for dictionary in objective_values_list
    ]
    # Check duplicate indices
    duplicate_indices = []
    for i in range(len(solutions) - 1):
        for j in range(i + 1, len(solutions)):
            # If all values of the objective functions are (nearly) identical, that's a duplicate
            if allclose(
                valuelists[i], valuelists[j]
            ):  # TODO: "similarity tolerance" from problem metadata
                duplicate_indices.append(i)

    # Quite the memory hell. See If there's a smarter way to do this
    new_solutions = []
    for i in range(len(solutions)):
        if i not in duplicate_indices:
            new_solutions.append(solutions[i])

    return new_solutions


# for collecting solutions for responses in iterate and initialize endpoints
def collect_saved_solutions(
    user: User, problem_id: int, session: Session
) -> list[SavedSolutionReference]:
    """Collects all saved solutions for the user and problem."""
    user_saved_solutions = session.exec(
        select(UserSavedSolutionDB).where(
            UserSavedSolutionDB.problem_id == problem_id,
            UserSavedSolutionDB.user_id == user.id,
        )
    ).all()

    saved_solutions = [
        SavedSolutionReference(saved_solution=saved_solution)
        for saved_solution in user_saved_solutions
    ]

    return filter_duplicates(saved_solutions)


# for collecting solutions for responses in iterate and initialize endpoints
def collect_all_solutions(
    user: User, problem_id: int, session: Session
) -> list[SolutionReference]:
    """Collects all solutions for the user and problem."""
    statement = (
        select(StateDB)
        .where(
            StateDB.problem_id == problem_id,
            StateDB.session_id == user.active_session_id,
        )
        .order_by(StateDB.id.desc())
    )
    states = session.exec(statement).all()
    all_solutions = []
    for state in states:
        if isinstance(state.state, RPMSolveState):
            for i, _ in enumerate(state.state.solver_results):
                all_solutions.append(SolutionReference(state=state, solution_index=i))

    return filter_duplicates(all_solutions)


@router.post("/solve")
def solve_solutions(
    request: RPMSolveRequest,
    context: Annotated[
        SessionContext,
        Depends(SessionContextGuard(require=[ContextField.PROBLEM]).post),
    ],
) -> RPMSolveResponse:
    """Runs an iteration of the reference point method.

    Args:
        request (RPMSolveRequest): a request with the needed information to run the method.
        user (Annotated[User, Depends): the current user.
        context (Annotated[SessionContext, Depends): the current session context.

    Returns:
        RPMSolveResponse: a response with information on the results of iterating the reference point method
            once.
    """
    user = context.user
    db_session = context.db_session
    problem_db = context.problem_db
    interactive_session = context.interactive_session
    parent_state = context.parent_state

    solver = check_solver(problem_db=problem_db)
    problem = Problem.from_problemdb(problem_db)

    solver_results: list[SolverResults] = rpm_solve_solutions(
        problem,
        request.preference.aspiration_levels,
        request.scalarization_options,
        solver,
        request.solver_options,
    )

    # create state and add to DB
    rpm_state = RPMSolveState(
        preferences=request.preference,
        scalarization_options=request.scalarization_options,
        solver=request.solver,
        solver_options=request.solver_options,
        solver_results=solver_results,
        previous_preferences=request.preference,
    )

    # create DB state and add it to the DB
    state = StateDB.create(
        database_session=db_session,
        problem_id=problem_db.id,
        session_id=interactive_session.id if interactive_session else None,
        parent_id=parent_state.id if parent_state else None,
        state=rpm_state,
    )

    db_session.add(state)
    db_session.commit()
    db_session.refresh(state)

    current_solutions: list[SolutionReference] = []
    for i, _ in enumerate(solver_results):
        current_solutions.append(SolutionReference(state=state, solution_index=i))

    saved_solutions = collect_saved_solutions(user, request.problem_id, db_session)
    all_solutions = collect_all_solutions(user, request.problem_id, db_session)

    return RPMSolveResponse(
        state_id=state.id,
        previous_preference=request.preference,
        current_solutions=current_solutions,
        saved_solutions=saved_solutions,
        all_solutions=all_solutions,
    )


@router.post("/save")
def save(
    request: RPMSaveRequest,
    context: Annotated[SessionContext, Depends(SessionContextGuard().post)],
) -> RPMSaveResponse:
    """Save solutions."""
    db_session = context.db_session
    user = context.user
    interactive_session = context.interactive_session
    parent_state = context.parent_state

    if request.parent_state_id is None:
        parent_state = (
            interactive_session.states[-1]
            if (interactive_session is not None and len(interactive_session.states) > 0)
            else None
        )
    else:
        parent_state = db_session.exec(
            select(StateDB).where(StateDB.id == request.parent_state_id)
        ).first()

        if parent_state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find state with id={request.parent_state_id}",
            )

    # Check for duplicate solutions and update names instead of saving duplicates
    updated_solutions: list[UserSavedSolutionDB] = []
    new_solutions: list[UserSavedSolutionDB] = []

    for info in request.solution_info:
        existing_solution = db_session.exec(
            select(UserSavedSolutionDB).where(
                UserSavedSolutionDB.origin_state_id == info.state_id,
                UserSavedSolutionDB.solution_index == info.solution_index,
            )
        ).first()

        if existing_solution is not None:
            existing_solution.name = info.name
            db_session.add(existing_solution)
            updated_solutions.append(existing_solution)

        else:
            new_solution = UserSavedSolutionDB.from_state_info(
                db_session,
                user.id,
                request.problem_id,
                info.state_id,
                info.solution_index,
                info.name,
            )

            db_session.add(new_solution)
            new_solutions.append(new_solution)

    # Commit existing and new solutions
    if updated_solutions or new_solutions:
        db_session.commit()
        [db_session.refresh(row) for row in updated_solutions + new_solutions]

    # save solver results for state in SolverResults format just for consistency
    save_state = RPMSaveState(solutions=updated_solutions + new_solutions)

    # create DB state
    state = StateDB.create(
        database_session=db_session,
        problem_id=request.problem_id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=save_state,
    )

    db_session.add(state)
    db_session.commit()
    db_session.refresh(state)

    return RPMSaveResponse(state_id=state.id)


@router.post("/intermediate")
def solve_nimbus_intermediate(
    request: IntermediateSolutionRequest,
    context: Annotated[
        SessionContext,
        Depends(SessionContextGuard(require=[ContextField.PROBLEM]).post),
    ],
) -> RPMIntermediateSolutionResponse:
    """Solve intermediate solutions by forwarding the request to generic intermediate endpoint with context nimbus."""
    db_session = context.db_session
    user = context.user

    # Add RPM context to request
    request.context = "rpm"

    # Forward to generic endpoint
    intermediate_response = solve_intermediate(request, context)

    # Get saved solutions for this user and problem
    saved_solutions = collect_saved_solutions(user, request.problem_id, db_session)
    # Get all solutions including the newly generated intermediate ones
    all_solutions = collect_all_solutions(user, request.problem_id, db_session)

    return RPMIntermediateSolutionResponse(
        state_id=intermediate_response.state_id,
        reference_solution_1=intermediate_response.reference_solution_1.objective_values,
        reference_solution_2=intermediate_response.reference_solution_2.objective_values,
        current_solutions=intermediate_response.intermediate_solutions,
        saved_solutions=saved_solutions,
        all_solutions=all_solutions,
    )


@router.post("/finalize")
def finalize_nimbus(
    request: RPMFinalizeRequest,
    context: Annotated[
        SessionContext,
        Depends(SessionContextGuard(require=[ContextField.PROBLEM]).post),
    ],
) -> RPMFinalizeResponse:
    """An endpoint for finishing up the nimbus process.

    Args:
        request (RPMFinalizeRequest): The request containing the final solution, etc.
        context (Annotated[SessionContext, SessionContextGuard): The current context.

    Raises:
        HTTPException

    Returns:
        RPMFinalizeResponse: Response containing info on the final solution.
    """
    db_session = context.db_session
    user = context.user
    interactive_session = context.interactive_session
    parent_state = context.parent_state
    problem_db = context.problem_db

    solution_state_id = request.solution_info.state_id
    solution_index = request.solution_info.solution_index

    state = db_session.exec(
        select(StateDB).where(StateDB.id == solution_state_id)
    ).first()
    actual_state = state.state if state else None
    if actual_state is None:
        raise HTTPException(
            detail="No concrete substate!",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    final_state = RPMFinalState(
        solution_origin_state_id=solution_state_id,
        solution_result_index=solution_index,
        solver_results=actual_state.solver_results[solution_index],
    )

    state = StateDB.create(
        database_session=db_session,
        problem_id=problem_db.id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=final_state,
    )

    db_session.add(state)
    db_session.commit()
    db_session.refresh(state)

    solution_reference_response = SolutionReferenceResponse(
        solution_index=solution_index,
        state_id=solution_state_id,
        objective_values=final_state.solver_results.optimal_objectives,
        variable_values=final_state.solver_results.optimal_variables,
    )

    return RPMFinalizeResponse(
        state_id=state.id,
        final_solution=solution_reference_response,
        saved_solutions=collect_saved_solutions(
            user=user, problem_id=problem_db.id, session=db_session
        ),
        all_solutions=collect_all_solutions(
            user=user, problem_id=problem_db.id, session=db_session
        ),
    )


@router.post("/delete_save")
def delete_save(
    request: RPMDeleteSaveRequest,
    context: Annotated[SessionContext, Depends(SessionContextGuard().post)],
) -> RPMDeleteSaveResponse:
    """Endpoint for deleting saved solutions.

    Args:
        request (RPMDeleteSaveRequest): request containing necessary information for deleting a save
        context (Annotated[SessionContext, Depends): session context

    Raises:
        HTTPException

    Returns:
        RPMDeleteSaveResponse: Response acknowledging the deletion of save and other useful info.
    """
    db_session = context.db_session

    to_be_deleted = db_session.exec(
        select(UserSavedSolutionDB).where(
            UserSavedSolutionDB.origin_state_id == request.state_id,
            UserSavedSolutionDB.solution_index == request.solution_index,
        )
    ).first()

    if to_be_deleted is None:
        raise HTTPException(
            detail="Unable to find a saved solution!",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    db_session.delete(to_be_deleted)
    db_session.commit()

    to_be_deleted = db_session.exec(
        select(UserSavedSolutionDB).where(
            UserSavedSolutionDB.origin_state_id == request.state_id,
            UserSavedSolutionDB.solution_index == request.solution_index,
        )
    ).first()

    if to_be_deleted is not None:
        raise HTTPException(
            detail="Could not delete the saved solution!",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return RPMDeleteSaveResponse(message="Save deleted.")
