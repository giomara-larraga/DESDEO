"""Necessary routers for GDM Score Bands.

I imagine these as simple interfaces to the GDMScoreBandsManager.
"""

import logging

# from shutil import copy
import sys
from typing import Annotated

from desdeo.api.models.gdm.gdm_score_bands import GDMSCOREBandsLearningPreference
from desdeo.api.models.generic_states import StateDB
from desdeo.api.models.state import GDMSCOREBandsLearningState
from desdeo.api.models.gdm.gdm_aggregate import GroupSessionDB
import polars as pl
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from desdeo.api.db import get_session
from desdeo.api.models import (
    ProblemDB,
    GDMSCOREBandsDecisionResponse,
    GDMSCOREBandsHistoryResponse,
    GDMSCOREBandsLearningAdvanceRequest,
    GDMSCOREBandsLearningStatusResponse,
    GDMSCOREBandsLearningWarningRequest,
    GDMScoreBandsInitializationRequest,
    GDMSCOREBandsResponse,
    GDMSCOREBandsRevertRequest,
    GDMScoreBandsVoteRequest,
    Group,
    GroupSessionInfoRequest,
    GroupIteration,
    User,
)
from desdeo.api.routers.gdm.gdm_aggregate import manager
from desdeo.api.routers.gdm.gdm_score_bands.gdm_score_bands_manager import (
    GDMScoreBandsManager,
)
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.gdm.score_bands import (
    SCOREBandsGDMConfig,
    SCOREBandsGDMResult,
    score_bands_gdm,
)

from desdeo.api.models.gdm.gdm_score_bands import (
    GDMSCOREBandsConsensusPreference,
    GDMSCOREBandsDecisionPreference,
    GDMSCOREBandsLearningPreference,
)

from desdeo.api.routers.gdm.utils import (
    check_decision_maker,
    check_group_access,
    check_group_owner,
    get_group_or_404,
    get_group_session_or_404,
)

logging.basicConfig(
    stream=sys.stdout,
    format="[%(filename)s:%(lineno)d] %(levelname)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gdm-score-bands", tags=["GDM Score Bands"])


def get_score_bands_head_iteration(
    group_session: GroupSessionDB,
    session: Session,
) -> GroupIteration:
    if group_session.head_iteration_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The SCORE Bands session has not been initialized.",
        )

    iteration = session.exec(
        select(GroupIteration).where(
            GroupIteration.id == group_session.head_iteration_id,
            GroupIteration.session_id == group_session.id,
        )
    ).first()

    if iteration is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "The group session head iteration is invalid or "
                "belongs to another group session."
            ),
        )

    return iteration


def get_score_bands_context(
    group_session_id: int,
    user: User,
    session: Session,
) -> tuple[GroupSessionDB, Group]:
    group_session = get_group_session_or_404(
        group_session_id,
        session,
    )

    if group_session.method != "gdm-score-bands":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Group session {group_session.id} uses method "
                f"'{group_session.method}', not 'gdm-score-bands'."
            ),
        )

    group = get_group_or_404(group_session, session)
    check_group_access(user, group)

    return group_session, group


@router.post("/vote")
async def vote_for_a_band(
    request: GDMScoreBandsVoteRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Vote for a band using this endpoint.

    Args:
        request (GDMScoreBandsVoteRequest): A container for the group id and the vote.
        user (Annotated[User, Depends): the current user.
        session (Annotated[Session, Depends): database session

    Raises:
        HTTPException: If something goes wrong. It hopefully let's you know what went wrong.

    Returns:
        JSONResponse: A quick confirmation that vote went through.
    """
    group_session, group = get_score_bands_context(
        request.group_session_id,
        user,
        session,
    )

    check_decision_maker(user, group)

    group_mgr: GDMScoreBandsManager = await manager.get_group_manager(
        group_session_id=group_session.id,
        method="gdm-score-bands",
        db_session=session,
    )

    # This would be the better way to do things.
    try:
        await group_mgr.vote(
            user=user,
            group_session=group_session,
            voted_index=request.vote,
            session=session,
        )
    except Exception as e:
        logger.exception("Found an error when issuing a vote for a band.")
        raise HTTPException(
            detail=f"Internal server error: {e}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from e

    return {"message": (f"User {user.id} voted for band {request.vote}.")}


@router.post("/confirm")
async def confirm_vote(
    request: GroupSessionInfoRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Confim the vote. If all confirm, the clustering and new iteration begins.

    Args:
        request (GroupSessionInfoRequest): Simple request to get the group ID.
        user (Annotated[User, Depends): The current user.
        session (Annotated[Session, Depends): Database session.

    Raises:
        HTTPException: If something goes awry. It should let you know what went wrong, though.

    Returns:
        JSONResponse: A simple confirmation that everything went ok and that vote went in.
    """
    group_session, group = get_score_bands_context(
        request.group_session_id,
        user,
        session,
    )

    check_decision_maker(user, group)

    group_mgr = await manager.get_group_manager(
        group_session_id=group_session.id,
        method="gdm-score-bands",
        db_session=session,
    )
    try:
        await group_mgr.confirm(
            user=user,
            group_session=group_session,
            session=session,
        )
    except Exception as e:
        logger.exception("Found and error when trying to confirm a vote.")
        raise HTTPException(
            detail=f"Internal server error: {e}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from e

    return JSONResponse(
        content={"message": f"Confirmed vote and moving on for user with ID {user.id}"}
    )


@router.post("/get-or-initialize")
async def get_or_initialize(
    request: GDMScoreBandsInitializationRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> GDMSCOREBandsHistoryResponse:
    """An endpoint for two things: Initializing the GDM Score Bands things and Fetching results.

    If a group hasn't been initialized, initialize and then return initial clustering information.
    If it has been initialized, just fetch the latest iteration's information (clustering, etc.)

    Args:
        request (GDMScoreBandsInitializationRequest): Request that contains necessary information for initialization.
        user (Annotated[User, Depends): The current user.
        session (Annotated[Session, Depends): Database session.

    Raises:
        HTTPException: It'll let you know.

    Returns:
        GDMSCOREBandsResponse: A response containing Group id, group iter id and ScoreBandsResponse.
    """
    group_session, group = get_score_bands_context(
        request.group_session_id,
        user,
        session,
    )
    if not group_session:
        raise HTTPException(
            detail=f"Group session with ID {request.group_session_id} not found!",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if group_session.head_iteration_id is not None:
        # Actually, just return the newest score band data.
        print("Group session already initialized!")
        group_iterations = session.exec(
            select(GroupIteration)
            .where(GroupIteration.session_id == group_session.id)
            .order_by(GroupIteration.id)
        ).all()
        responses: list[GDMSCOREBandsResponse | GDMSCOREBandsDecisionResponse] = []

        for giter in group_iterations:
            if giter.state_id is None:
                logger.warning(
                    "GroupIteration %s has no state_id",
                    giter.id,
                )
                continue

            state_db = session.get(StateDB, giter.state_id)

            if state_db is None:
                logger.warning(
                    "StateDB %s not found for iteration %s",
                    giter.state_id,
                    giter.id,
                )
                continue

            state = state_db.state
            info = giter.info_container

            phase = getattr(info, "phase", None)

            if phase is None:
                preference_name = type(info).__name__

                if preference_name == "GDMSCOREBandsLearningPreference":
                    phase = "learning"
                elif preference_name == "GDMSCOREBandsDecisionPreference":
                    phase = "decision"
                else:
                    phase = "consensus"

            if phase == "decision":
                responses.append(
                    GDMSCOREBandsDecisionResponse(
                        phase="decision",
                        group_session_id=group_session.id,
                        group_iter_id=giter.id,
                        result=state,
                    )
                )
                continue

            typed_result = SCOREBandsGDMResult.model_validate(state.result)

            responses.append(
                GDMSCOREBandsResponse(
                    phase=phase,
                    group_session_id=group_session.id,
                    group_iter_id=giter.id,
                    latest_iteration=typed_result.iteration,
                    result=typed_result.score_bands_result,
                )
            )

        return GDMSCOREBandsHistoryResponse(history=responses)

    group_mgr: GDMScoreBandsManager = await manager.get_group_manager(
        group_session_id=group_session.id, method="gdm-score-bands", db_session=session
    )

    score_bands_config = (
        SCOREBandsGDMConfig()
        if request.score_bands_config is None
        else request.score_bands_config
    )

    # initial clustering for the objectives
    problem = session.get(
        ProblemDB,
        group_session.problem_id,
    )

    if problem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Problem {group_session.problem_id} "
                "was not found."
            ),
        )

    if problem.discrete_representation is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "The problem has no discrete representation."
            ),
        )

    discrete_representation_obj = (
        problem.discrete_representation.objective_values
    )

    objs = pl.DataFrame(
        discrete_representation_obj
    )
    results = score_bands_gdm(
        data=objs,
        config=score_bands_config,
        state=None,
    )

    if not results:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SCORE Bands returned no initial result.",
        )

    result = SCOREBandsGDMResult.model_validate(results[-1])

    score_bands_config.score_bands_config.axis_positions = (
        result.score_bands_result.axis_positions
    )

    # store necessary data to the database. Currently all "voting" related is null bc no voting has happened yet.
    learning_preference = GDMSCOREBandsLearningPreference(
        completed_user_ids=[],
    )

    learning_state = GDMSCOREBandsLearningState(
        config=score_bands_config.model_dump(mode="json"),
        result=result.model_dump(mode="json"),
    )

    state_db = StateDB.create(
        database_session=session,
        problem_id=group_session.problem_id,
        group_session_id=group_session.id,
        parent_id=None,
        state=learning_state,
    )
    session.refresh(state_db)

    # Add group iteration and related stuff, then set new iteration to head.
    iteration = GroupIteration(
        session_id=group_session.id,
        info_container=learning_preference,
        notified={},
        state_id=state_db.id,
        parent_id=None,
    )

    session.add(iteration)
    session.flush()

    group_session.head_iteration_id = iteration.id
    session.add(group_session)

    session.commit()
    session.refresh(iteration)
    session.refresh(group_session)

    # Actually, return just the newly created score band data.
    return GDMSCOREBandsHistoryResponse(
        history=[
            GDMSCOREBandsResponse(
                phase="learning",
                group_session_id=group_session.id,
                group_iter_id=group_session.head_iteration_id,
                latest_iteration=result.iteration,
                result=result.score_bands_result,
            )
        ]
    )


@router.post("/get-votes-and-confirms")
def get_votes_and_confirms(
    request: GroupSessionInfoRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> JSONResponse:
    """Returns the current status of votes and confirmations in current iteration.

    Args:
        request (GroupSessionInfoRequest): The group we'd like the info on.
        user (Annotated[User, Depends): The user that requests the data.
        session (Annotated[Session, Depends): The database session.

    Raises:
        HTTPException: If group doesn't exists etc errors.

    Returns:
        JSONResponse: A response containing the votes and confirmations.
    """
    group_session, group = get_score_bands_context(
        request.group_session_id,
        user,
        session,
    )

    if group_session.head_iteration_id is None:
        raise HTTPException(
            detail="Group hasn't been initialized!",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    iteration = get_score_bands_head_iteration(
        group_session,
        session,
    )
    info = iteration.info_container

    votes = getattr(info, "user_votes", {})
    confirms = getattr(info, "user_confirms", [])

    if isinstance(info, GDMSCOREBandsLearningPreference):
        phase = "learning"
    elif isinstance(info, GDMSCOREBandsDecisionPreference):
        phase = "decision"
    elif isinstance(info, GDMSCOREBandsConsensusPreference):
        phase = "consensus"
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unknown SCORE Bands preference type.",
        )

    return JSONResponse(
        content={
            "votes": votes,
            "confirms": confirms,
            "phase": phase,
            "learning_completed_user_ids": getattr(
                info,
                "completed_user_ids",
                [],
            ),
            "learning_started_at": getattr(
                info,
                "started_at",
                None,
            ),
            "learning_duration_seconds": getattr(
                info,
                "duration_seconds",
                None,
            ),
            "learning_last_warning_at": getattr(
                info,
                "last_warning_at",
                None,
            ),
            "learning_last_warning_message": getattr(
                info,
                "last_warning_message",
                None,
            ),
        }
    )


@router.post("/learning/complete")
async def complete_learning_phase(
    request: GroupSessionInfoRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> GDMSCOREBandsLearningStatusResponse:
    """Mark the current user as done with the private learning phase."""
    group_session, group = get_score_bands_context(
        request.group_session_id,
        user,
        session,
    )

    check_decision_maker(user, group)

    group_mgr: GDMScoreBandsManager = await manager.get_group_manager(
        group_session_id=group_session.id,
        method="gdm-score-bands",
        db_session=session,
    )

    try:
        await group_mgr.mark_learning_complete(
            user=user, group_session=group_session, session=session
        )
    except Exception as e:
        logger.exception("Found an error when completing the learning phase.")
        raise HTTPException(
            detail=f"Internal server error: {e}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from e

    # iteration = session.exec(select(GroupIteration).where(GroupIteration.id == group.head_iteration_id)).first()

    iteration = get_score_bands_head_iteration(
        group_session,
        session,
    )

    info = iteration.info_container
    return GDMSCOREBandsLearningStatusResponse(
        phase=getattr(info, "phase", "consensus"),
        learning_completed_user_ids=getattr(
            info,
            "completed_user_ids",
            [],
        ),
        learning_started_at=getattr(
            info,
            "started_at",
            None,
        ),
        learning_duration_seconds=getattr(
            info,
            "duration_seconds",
            None,
        ),
        learning_last_warning_at=getattr(
            info,
            "last_warning_at",
            None,
        ),
        learning_last_warning_message=getattr(
            info,
            "last_warning_message",
            None,
        ),
    )


@router.post("/learning/warn")
async def warn_learning_phase(
    request: GDMSCOREBandsLearningWarningRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> GDMSCOREBandsLearningStatusResponse:
    """Broadcast a learning-phase warning to connected users."""
    group_session, group = get_score_bands_context(
        request.group_session_id,
        user,
        session,
    )

    if user.id != group.owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the group owner may perform this action.",
        )

    group_mgr: GDMScoreBandsManager = await manager.get_group_manager(
        group_session_id=group_session.id,
        method="gdm-score-bands",
        db_session=session,
    )

    try:
        await group_mgr.warn_learning_deadline(
            group_session=group_session, session=session, message=request.message
        )
    except Exception as e:
        logger.exception("Found an error when warning about the learning deadline.")
        raise HTTPException(
            detail=f"Internal server error: {e}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from e

    iteration = get_score_bands_head_iteration(
        group_session,
        session,
    )
    info = iteration.info_container
    return GDMSCOREBandsLearningStatusResponse(
        phase=getattr(info, "phase", "consensus"),
        learning_completed_user_ids=getattr(
            info,
            "completed_user_ids",
            [],
        ),
        learning_started_at=getattr(
            info,
            "started_at",
            None,
        ),
        learning_duration_seconds=getattr(
            info,
            "duration_seconds",
            None,
        ),
        learning_last_warning_at=getattr(
            info,
            "last_warning_at",
            None,
        ),
        learning_last_warning_message=getattr(
            info,
            "last_warning_message",
            None,
        ),
    )


@router.post("/learning/advance")
async def advance_learning_phase(
    request: GDMSCOREBandsLearningAdvanceRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> GDMSCOREBandsLearningStatusResponse:
    """Move the group from private learning to the consensus phase."""
    group_session, group = get_score_bands_context(
        request.group_session_id,
        user,
        session,
    )

    check_group_owner(user, group)

    group_mgr: GDMScoreBandsManager = await manager.get_group_manager(
        group_session_id=group_session.id,
        method="gdm-score-bands",
        db_session=session,
    )

    try:
        await group_mgr.advance_learning_phase(
            user=user,
            group_session=group_session,
            session=session,
        )
    except Exception as e:
        logger.exception("Found an error when advancing to the consensus phase.")
        raise HTTPException(
            detail=f"Internal server error: {e}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from e

    iteration = get_score_bands_head_iteration(
        group_session,
        session,
    )
    info = iteration.info_container
    return GDMSCOREBandsLearningStatusResponse(
        phase=getattr(info, "phase", "consensus"),
        learning_completed_user_ids=getattr(
            info,
            "completed_user_ids",
            [],
        ),
        learning_started_at=getattr(
            info,
            "started_at",
            None,
        ),
        learning_duration_seconds=getattr(
            info,
            "duration_seconds",
            None,
        ),
        learning_last_warning_at=getattr(
            info,
            "last_warning_at",
            None,
        ),
        learning_last_warning_message=getattr(
            info,
            "last_warning_message",
            None,
        ),
    )


@router.post("/revert")
async def revert(
    request: GDMSCOREBandsRevertRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> JSONResponse:
    """Revert to a previous iteration. Usable only by the analyst.

    This implies that we're gonna need to see ALL previous iterations I'd say.

    Args:
        request (GDMSCOREBandsRevertRequest): The request containing group id and iteration number.
        user (Annotated[User, Depends): The current user.
        session (Annotated[Session, Depends): The database session.

    Returns:
        JSONResponse: Acknowledgement of the revert.
    """
    group_session, group = get_score_bands_context(
        request.group_session_id,
        user,
        session,
    )

    check_group_owner(user, group)

    group_mgr: GDMScoreBandsManager = await manager.get_group_manager(
        group_session_id=group_session.id,
        method="gdm-score-bands",
        db_session=session,
    )

    try:
        await group_mgr.revert(
            user=user,
            group_session=group_session,
            session=session,
            group_iteration_id=request.group_iteration_id,
        )
    except Exception as e:
        logger.exception(
            "Found an error when trying to revert to a previous iteration."
        )
        raise HTTPException(
            detail=f"Internal server error: {e}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from e

    return JSONResponse(content={"message": "Reverted iteration."})


@router.post("/configure")
async def configure_gdm(
    config: SCOREBandsGDMConfig,
    group_session_id: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> JSONResponse:
    """Configure the SCORE Bands settings.

    Args:
        config (SCOREBandsGDMConfig): The configuration object
        group_session_id (int): The ID of the group session
        user (Annotated[User, Depends): The user doing the request
        session (Annotated[Session, Depends): The database session.

    Returns:
        JSONResponse: Acknowledgement that yeah ok reconfigured.
    """
    group_session, group = get_score_bands_context(
        group_session_id,
        user,
        session,
    )

    check_group_owner(user, group)

    group_mgr: GDMScoreBandsManager = await manager.get_group_manager(
        group_session_id=group_session.id,
        method="gdm-score-bands",
        db_session=session,
    )

    try:
        await group_mgr.configure(
            config=config,
            group_session=group_session,
            session=session,
        )
    except Exception as e:
        logger.exception("Found an error when trying to configure SCORE band settings.")
        raise HTTPException(
            detail=f"Internal server error: {e}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from e

    return JSONResponse(content={"message": "Configured. Re-clustered."})
