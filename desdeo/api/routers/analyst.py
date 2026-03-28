"""Analyst endpoints for experiment result summaries."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from desdeo.api.db import get_session
from desdeo.api.models import User, UserRole
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.api.utils_experiment_xnimbus import (
    build_experiment_group_summaries,
    build_group_user_summary,
)

router = APIRouter(prefix="/analyst/experiment-results", tags=["Analyst"])


def _require_analyst_or_admin(user: User) -> None:
    """Ensure the current user can access analyst experiment summaries."""
    if user.role not in {UserRole.analyst, UserRole.admin}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only analysts and admins can access experiment summaries.",
        )


@router.get("/groups")
def get_experiment_group_results(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    include_action_details: bool = Query(default=False),
) -> dict[str, list[dict]]:
    """Return grouped experiment summaries for the analyst dashboard."""
    _require_analyst_or_admin(user)
    return {
        "groups": build_experiment_group_summaries(
            session,
            include_action_details=include_action_details,
        )
    }


@router.get("/users/{user_id}")
def get_experiment_user_results(
    user_id: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    experiment_group: int | None = Query(default=None),
    include_action_details: bool = Query(default=True),
) -> dict:
    """Return one user's experiment summary within a given experiment group."""
    _require_analyst_or_admin(user)

    user_summary = build_group_user_summary(
        session,
        experiment_group,
        user_id,
        include_action_details=include_action_details,
    )
    if user_summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User summary was not found for the requested experiment group.",
        )

    return user_summary
