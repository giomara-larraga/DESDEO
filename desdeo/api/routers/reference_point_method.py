"""Defines end-points to access functionalities related to the reference point method."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from desdeo.api.db import get_session
from desdeo.api.models import (
    InteractiveSessionDB,
    PreferenceDB,
    ProblemDB,
    RPMSolveRequest,
    RPMExplainRequest,
    RPMExplanationResponse,
    RPMState,
    StateDB,
    User,
)
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.api.explainers import ExplainerRXIMO
from desdeo.mcdm import rpm_solve_solutions
from desdeo.problem import Problem
from desdeo.tools import SolverResults

router = APIRouter(prefix="/method/rpm")


@router.post("/solve")
def solve_solutions(
    request: RPMSolveRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> RPMState:
    """."""

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

    # optimize for solutions
    solver_results: list[SolverResults] = rpm_solve_solutions(
        problem,
        request.preference.aspiration_levels,
        request.scalarization_options,
        request.solver,
        request.solver_options,
    )

    # create DB preference
    preference_db = PreferenceDB(
        user_id=user.id, problem_id=problem_db.id, preference=request.preference
    )

    session.add(preference_db)
    session.commit()
    session.refresh(preference_db)

    # fetch parent state
    if request.parent_state_id is None:
        # parent state is assumed to be the last sate added to the session.
        parent_state = (
            interactive_session.states[-1]
            if (interactive_session is not None and len(interactive_session.states) > 0)
            else None
        )

    else:
        # request.parent_state_id is not None
        statement = session.select(StateDB).where(StateDB.id == request.parent_state_id)
        parent_state = session.exec(statement).first()

        if parent_state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find state with id={request.parent_state_id}",
            )

    # create state and add to DB
    rpm_state = RPMState(
        scalarization_options=request.scalarization_options,
        solver=request.solver,
        solver_options=request.solver_options,
        solver_results=solver_results,
    )

    # create DB state and add it to the DB
    state = StateDB(
        problem_id=problem_db.id,
        preference_id=preference_db.id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=rpm_state,
    )

    session.add(state)
    session.commit()
    session.refresh(state)

    return rpm_state


@router.post("/explain")
def explain_solutions(
    request: RPMExplainRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> RPMExplanationResponse:
    """Generate explanations for a specific solution from a previous RPM solve."""

    # Fetch the state containing the solutions
    statement = select(StateDB).where(StateDB.id == request.state_id)
    state_db = session.exec(statement).first()

    if state_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"State with id={request.state_id} could not be found.",
        )

    # Verify the state belongs to the user
    statement = select(ProblemDB).where(
        ProblemDB.id == state_db.problem_id, ProblemDB.user_id == user.id
    )
    problem_db = session.exec(statement).first()

    if problem_db is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this state.",
        )

    # Get the problem
    problem = Problem.from_problemdb(problem_db)

    # Extract solutions from the state
    rpm_state = state_db.state
    if not hasattr(rpm_state, "solver_results") or not rpm_state.solver_results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No solutions found in the specified state.",
        )

    if request.solution_index >= len(rpm_state.solver_results):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solution index {request.solution_index} out of range. Available solutions: {len(rpm_state.solver_results)}",
        )

    solution_to_explain = rpm_state.solver_results[request.solution_index]

    try:
        # Get or create cached explainer from database using problem_id
        explainer, problem_data, cache_status = ExplainerRXIMO.get_or_create_explainer(
            problem, user.id, problem_db.id, session, n_samples=200
        )

        # Extract symbols for consistency
        variable_symbols = [var.symbol for var in problem.variables]
        objective_symbols = [obj.symbol for obj in problem.objectives]

        # Generate explanation using the service
        explanation_result = ExplainerRXIMO.generate_explanation(
            explainer=explainer,
            problem_data=problem_data,
            solution_variables=solution_to_explain.optimal_variables,
            solution_objectives=solution_to_explain.optimal_objectives,
            variable_symbols=variable_symbols,
            objective_symbols=objective_symbols,
        )

        if explanation_result is not None:
            return RPMExplanationResponse(
                state_id=request.state_id,
                solution_index=request.solution_index,
                explanations={
                    "shap_values": explanation_result["shap_values"],
                    "base_values": explanation_result["base_values"],
                    "data": explanation_result["data"],
                    "variable_symbols": variable_symbols,
                    "objective_symbols": objective_symbols,
                    "cache_status": cache_status,
                    "problem_id": problem_db.id,
                },
                variable_importance=explanation_result["variable_importance"],
                success=True,
                message=f"Explanations generated successfully using {cache_status.replace('_', ' ')}",
            )
        else:
            return RPMExplanationResponse(
                state_id=request.state_id,
                solution_index=request.solution_index,
                explanations={},
                variable_importance={},
                success=False,
                message="Failed to generate background data for explanations",
            )

    except Exception as e:
        return RPMExplanationResponse(
            state_id=request.state_id,
            solution_index=request.solution_index,
            explanations={},
            variable_importance={},
            success=False,
            message=f"Error generating explanations: {str(e)}",
        )


@router.delete("/explainer/cache/{problem_id}")
async def clear_explainer_cache(
    problem_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Clear the cached explainer data for a specific problem."""
    try:
        success = ExplainerRXIMO.clear_cache(problem_id, current_user.id, session)

        if success:
            return {
                "success": True,
                "message": f"Cache cleared for problem {problem_id}",
            }
        else:
            return {
                "success": False,
                "message": f"No cache found for problem {problem_id}",
            }

    except Exception as e:
        return {"success": False, "message": f"Error clearing cache: {str(e)}"}


@router.get("/explainer/cache/status")
async def get_explainer_cache_status(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Get status of all cached explainers for the current user."""
    try:
        cache_status = ExplainerRXIMO.get_cache_status(current_user.id, session)
        return {"success": True, "cache_entries": cache_status}

    except Exception as e:
        return {"success": False, "message": f"Error getting cache status: {str(e)}"}
