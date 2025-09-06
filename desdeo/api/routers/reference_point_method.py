"""Defines end-points to access functionalities related to the reference point method."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from desdeo.api.models.generic import SolutionInfo

from desdeo.mcdm.nimbus import generate_starting_point

from desdeo.api.db import get_session
from desdeo.api.models import (
    InteractiveSessionDB,
    PreferenceDB,
    ProblemDB,
    RPMSolveRequest,
    RPMState,
    RPMSolveResponse,
    RPMSaveRequest,
    RPMSaveResponse,
    RPMInitializationRequest,
    RPMInitializationResponse,
    RPMSolveState,
    RPMInitializationState,
    RPMSaveState,
    SolutionReference,
    StateDB,
    User,
    UserSavedSolutionDB,
    ReferencePoint,
)
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.mcdm import rpm_solve_solutions
from desdeo.problem import Problem
from desdeo.tools import SolverResults
from desdeo.api.routers.nimbus import (
    filter_duplicates,
    collect_saved_solutions,
    collect_all_solutions,
)

router = APIRouter(prefix="/method/rpm")


@router.post("/solve")
def solve_solutions(
    request: RPMSolveRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> RPMSolveResponse:
    """Solve the problem using the RPM method."""
    if request.session_id is not None:
        statement = select(InteractiveSessionDB).where(
            InteractiveSessionDB.id == request.session_id
        )
        interactive_session = session.exec(statement)

        if interactive_session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find interactive session with id={request.session_id}.",
            )
    else:
        # request.session_id is None:
        # use active session instead
        statement = select(InteractiveSessionDB).where(
            InteractiveSessionDB.id == user.active_session_id
        )

        interactive_session = session.exec(statement).first()

    # fetch the problem from the DB
    statement = select(ProblemDB).where(
        ProblemDB.user_id == user.id, ProblemDB.id == request.problem_id
    )
    problem_db = session.exec(statement).first()

    if problem_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem with id={request.problem_id} could not be found.",
        )

    problem = Problem.from_problemdb(problem_db)

    # fetch parent state
    if request.parent_state_id is None:
        # parent state is assumed to be the last state added to the session.
        parent_state = (
            interactive_session.states[-1]
            if (interactive_session is not None and len(interactive_session.states) > 0)
            else None
        )

    else:
        # request.parent_state_id is not None
        statement = select(StateDB).where(StateDB.id == request.parent_state_id)
        parent_state = session.exec(statement).first()

        if parent_state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find state with id={request.parent_state_id}",
            )

    solver_results: list[SolverResults] = rpm_solve_solutions(
        problem,
        request.preference.aspiration_levels,
        request.scalarization_options,
        request.solver,
        request.solver_options,
    )

    rpm_state = RPMSolveState(
        preferences=request.preference,
        scalarization_options=request.scalarization_options,
        solver=request.solver,
        solver_options=request.solver_options,
        solver_results=solver_results,
        previous_preferences=request.preference,  # why?
    )

    # create DB state and add it to the DB
    state = StateDB.create(
        database_session=session,
        problem_id=problem_db.id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=rpm_state,
    )

    session.add(state)
    session.commit()
    session.refresh(state)

    # Collect all current solutions
    current_solutions: list[SolutionReference] = []
    for i, result in enumerate(solver_results):
        current_solutions.append(SolutionReference(state=state, solution_index=i))

    saved_solutions = collect_saved_solutions(user, request.problem_id, session)
    all_solutions = collect_all_solutions(user, request.problem_id, session)

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
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> RPMSaveResponse:
    """Save solutions."""
    if request.session_id is not None:
        statement = select(InteractiveSessionDB).where(
            InteractiveSessionDB.id == request.session_id
        )
        interactive_session = session.exec(statement)

        if interactive_session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find interactive session with id={request.session_id}.",
            )
    else:
        # request.session_id is None:
        # use active session instead
        statement = select(InteractiveSessionDB).where(
            InteractiveSessionDB.id == user.active_session_id
        )

        interactive_session = session.exec(statement).first()

    # fetch parent state
    if request.parent_state_id is None:
        # parent state is assumed to be the last state added to the session.
        parent_state = (
            interactive_session.states[-1]
            if (interactive_session is not None and len(interactive_session.states) > 0)
            else None
        )

    else:
        # request.parent_state_id is not None
        statement = select(StateDB).where(StateDB.id == request.parent_state_id)
        parent_state = session.exec(statement).first()

        if parent_state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find state with id={request.parent_state_id}",
            )

    # Check for duplicate solutions and update names instead of saving duplicates
    updated_solutions: list[UserSavedSolutionDB] = []
    new_solutions: list[UserSavedSolutionDB] = []

    for info in request.solution_info:
        existing_solution = session.exec(
            select(UserSavedSolutionDB).where(
                UserSavedSolutionDB.origin_state_id == info.state_id,
                UserSavedSolutionDB.solution_index == info.solution_index,
            )
        ).first()

        if existing_solution is not None:
            # Update the name of the existing solution
            existing_solution.name = info.name

            session.add(existing_solution)

            updated_solutions.append(existing_solution)
        else:
            # This is a new solution
            new_solution = UserSavedSolutionDB.from_state_info(
                session,
                user.id,
                request.problem_id,
                info.state_id,
                info.solution_index,
                info.name,
            )

            session.add(new_solution)

            new_solutions.append(new_solution)

    # Commit existing and new solutions
    if updated_solutions or new_solution:
        session.commit()
        [session.refresh(row) for row in updated_solutions + new_solutions]

    # save solver results for state in SolverResults format just for consistency (dont save name field to state)
    save_state = RPMSaveState(solutions=updated_solutions + new_solutions)

    # create DB state
    state = StateDB.create(
        database_session=session,
        problem_id=request.problem_id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=save_state,
    )

    session.add(state)
    session.commit()
    session.refresh(state)

    return RPMSaveResponse(state_id=state.id)


@router.post("/get-or-initialize")
def get_or_initialize(
    request: RPMInitializationRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> RPMInitializationResponse | RPMSolveResponse:
    """Get the latest NIMBUS state if it exists, or initialize a new one if it doesn't."""
    if request.session_id is not None:
        statement = select(InteractiveSessionDB).where(
            InteractiveSessionDB.id == request.session_id
        )
        interactive_session = session.exec(statement)

        if interactive_session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find interactive session with id={request.session_id}.",
            )
    else:
        # use active session instead
        statement = select(InteractiveSessionDB).where(
            InteractiveSessionDB.id == user.active_session_id
        )
        interactive_session = session.exec(statement).first()

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
    states = session.exec(statement).all()

    # Find the latest relevant state (NIMBUS classification, initialization, or intermediate with NIMBUS context)
    latest_state = None
    for state in states:
        if isinstance(state.state, (RPMSolveState | RPMInitializationState)):
            latest_state = state
            break

    if latest_state is not None:
        saved_solutions = collect_saved_solutions(user, request.problem_id, session)
        all_solutions = collect_all_solutions(user, request.problem_id, session)
        # Handle both single result and list of results cases
        solver_results = latest_state.state.solver_results
        if isinstance(solver_results, list):
            current_solutions = [
                SolutionReference(state=latest_state, solution_index=i)
                for i in range(len(solver_results))
            ]
        else:
            # Single result case (NIMBUSInitializationState)
            current_solutions = [
                SolutionReference(state=latest_state, solution_index=0)
            ]

        if isinstance(latest_state.state, RPMSolveState):
            return RPMSolveResponse(
                state_id=latest_state.id,
                previous_preference=latest_state.state.preferences,
                previous_objectives=latest_state.state.current_objectives,
                current_solutions=current_solutions,
                saved_solutions=saved_solutions,
                all_solutions=all_solutions,
            )

        # RPMInitializationState
        return RPMInitializationResponse(
            state_id=latest_state.id,
            current_solutions=current_solutions,
            saved_solutions=saved_solutions,
            all_solutions=all_solutions,
        )

    # No relevant state found, initialize a new one
    return initialize(request, user, session)


@router.post("/initialize")
def initialize(
    request: RPMInitializationRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> RPMInitializationResponse:
    """Initialize the problem for the RPM method."""
    if request.session_id is not None:
        statement = select(InteractiveSessionDB).where(
            InteractiveSessionDB.id == request.session_id
        )
        interactive_session = session.exec(statement)

        if interactive_session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find interactive session with id={request.session_id}.",
            )
    else:
        # request.session_id is None:
        # use active session instead
        statement = select(InteractiveSessionDB).where(
            InteractiveSessionDB.id == user.active_session_id
        )

        interactive_session = session.exec(statement).first()

    # fetch the problem from the DB
    statement = select(ProblemDB).where(
        ProblemDB.user_id == user.id, ProblemDB.id == request.problem_id
    )
    problem_db = session.exec(statement).first()

    if problem_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem with id={request.problem_id} could not be found.",
        )

    problem = Problem.from_problemdb(problem_db)

    if isinstance(ref_point := request.starting_point, ReferencePoint):
        # ReferencePoint
        starting_point = ref_point.aspiration_levels

    elif isinstance(info := request.starting_point, SolutionInfo):
        # SolutionInfo
        # fetch the solution
        statement = select(StateDB).where(StateDB.id == info.state_id)
        state = session.exec(statement).first()

        if state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"StateDB with index {info.state_id} could not be found.",
            )

        starting_point = state.state.result_objective_values[info.solution_index]

    else:
        # if not starting point is provided, generate it
        starting_point = None

    start_result = generate_starting_point(
        problem=problem,
        reference_point=starting_point,
        scalarization_options=request.scalarization_options,
        solver=request.solver,
        solver_options=request.solver_options,
    )

    # fetch parent state if it is given
    if request.parent_state_id is None:
        parent_state = None
    else:
        statement = session.select(StateDB).where(StateDB.id == request.parent_state_id)
        parent_state = session.exec(statement).first()

        if parent_state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find state with id={request.parent_state_id}",
            )

    initialization_state = RPMInitializationState(
        reference_point=starting_point,
        scalarization_options=request.scalarization_options,
        solver=request.solver,
        solver_results=start_result,
    )

    # create DB state and add it to the DB
    state = StateDB.create(
        database_session=session,
        problem_id=problem_db.id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=initialization_state,
    )

    session.add(state)
    session.commit()
    session.refresh(state)

    current_solutions = [SolutionReference(state=state, solution_index=0)]
    saved_solutions = collect_saved_solutions(user, request.problem_id, session)
    all_solutions = collect_all_solutions(user, request.problem_id, session)

    return RPMInitializationResponse(
        state_id=state.id,
        current_solutions=current_solutions,
        saved_solutions=saved_solutions,
        all_solutions=all_solutions,
    )
