"""Necessary routers for GDM Score Bands.

I imagine these as simple interfaces to the GDMScoreBandsManager.
"""

import logging
import copy

# from shutil import copy
import sys
from typing import Annotated
from desdeo.api.models.score_bands_method import SCOREBandsMethodInitializeResponse
from desdeo.api.models.session import InteractiveSessionDB
from desdeo.api.routers.gdm.gdm_base import ManagerError
from desdeo.api.models.gdm.gdm_score_bands import (
    GDMSCOREBandsLearningExploreRequest,
    GDMSCOREBandsLearningPreference,
    GDMSCOREBandsRestartRequest,
)
from desdeo.api.models.generic_states import StateDB
from desdeo.api.models.state import GDMSCOREBandsLearningState, SCOREBandsMethodState
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
from desdeo.api.routers.score_bands_method import get_score_bands_state
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
            detail=(f"Problem {group_session.problem_id} " "was not found."),
        )

    if problem.discrete_representation is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=("The problem has no discrete representation."),
        )

    discrete_representation_obj = problem.discrete_representation.objective_values

    objs = pl.DataFrame(discrete_representation_obj)
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


@router.post("/restart")
async def restart_score_bands(
    request: GDMSCOREBandsRestartRequest,
    user: Annotated[
        User,
        Depends(get_current_user),
    ],
    session: Annotated[
        Session,
        Depends(get_session),
    ],
) -> JSONResponse:
    """Restart a SCORE Bands process from scratch.

    Only the group owner may restart the process. The GroupSession,
    group, participants, problem, and method are preserved.
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
        await group_mgr.restart(
            user=user,
            group_session=group_session,
            session=session,
        )
    except ManagerError as error:
        session.rollback()

        logger.warning(
            "Could not restart SCORE Bands session %s: %s",
            group_session.id,
            error,
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    except Exception as error:
        session.rollback()

        logger.exception(
            "Unexpected error while restarting SCORE Bands session %s.",
            group_session.id,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to restart the SCORE Bands process.",
        ) from error

    return JSONResponse(
        content={
            "message": "SCORE Bands process restarted.",
            "group_session_id": group_session.id,
            "head_iteration_id": None,
        }
    )


def get_or_create_gdm_learning_session(
    *,
    user: User,
    group_session,
    db_session: Session,
) -> InteractiveSessionDB:
    """Get or create a private SCORE Bands session for a DM.

    The session belongs to one DM and one shared GDM learning
    iteration. It is used only for private SCORE Bands exploration.
    """

    if user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The current user has no database ID.",
        )

    if group_session.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The group session has no database ID.",
        )

    if group_session.head_iteration_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The GDM session has not been initialized.",
        )

    session_info = (
        "gdm-score-bands-learning:"
        f"{group_session.id}:"
        f"{group_session.head_iteration_id}"
    )

    personal_session = db_session.exec(
        select(InteractiveSessionDB).where(
            InteractiveSessionDB.user_id == user.id,
            InteractiveSessionDB.info == session_info,
        )
    ).first()

    if personal_session is not None:
        return personal_session

    personal_session = InteractiveSessionDB(
        user_id=user.id,
        info=session_info,
    )

    db_session.add(personal_session)
    db_session.commit()
    db_session.refresh(personal_session)

    return personal_session


@router.post("/learning/explore")
async def explore_learning_band(
    request: GDMSCOREBandsLearningExploreRequest,
    user: Annotated[
        User,
        Depends(get_current_user),
    ],
    session: Annotated[
        Session,
        Depends(get_session),
    ],
) -> SCOREBandsMethodInitializeResponse:
    """Privately explore a SCORE band during the learning phase.

    The first call drills into a cluster of the shared GDM learning result.

    Later calls may provide ``parent_state_id`` to drill further into a
    previously generated personal SCORE Bands state.

    Personal exploration is persisted in the decision maker's
    InteractiveSessionDB and does not create or modify GroupIteration rows.
    """

    # ---------------------------------------------------------------
    # 1. Validate GDM session and decision-maker role
    # ---------------------------------------------------------------

    group_session, group = get_score_bands_context(
        request.group_session_id,
        user,
        session,
    )

    check_decision_maker(user, group)

    if user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The current user has no database ID.",
        )

    # ---------------------------------------------------------------
    # 2. Validate the user's private interactive session
    # ---------------------------------------------------------------
    try:
        # ---------------------------------------------------------------
        # 2. Get or create this DM's private learning session
        # ---------------------------------------------------------------

        interactive_session = get_or_create_gdm_learning_session(
            user=user,
            group_session=group_session,
            db_session=session,
        )
    except ManagerError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    # ---------------------------------------------------------------
    # 3. SCORE Bands may only be explored privately during learning
    # ---------------------------------------------------------------

    shared_iteration = get_score_bands_head_iteration(
        group_session,
        session,
    )

    if not isinstance(
        shared_iteration.info_container,
        GDMSCOREBandsLearningPreference,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Personal SCORE Bands exploration is only available "
                "during the learning phase."
            ),
        )

    if shared_iteration.state_id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The learning iteration has no persisted state.",
        )

    shared_state_db = session.get(
        StateDB,
        shared_iteration.state_id,
    )

    if shared_state_db is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The learning state could not be found.",
        )

    shared_state = shared_state_db.state

    if not isinstance(
        shared_state,
        GDMSCOREBandsLearningState,
    ):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The current GDM state is not a learning state.",
        )

    # ---------------------------------------------------------------
    # 4. Determine which original solution IDs belong to the
    #    selected band.
    # ---------------------------------------------------------------

    parent_state_db: StateDB | None = None

    if request.parent_state_id is None:
        # First personal drill-down from the shared GDM learning result.

        shared_result = SCOREBandsGDMResult.model_validate(shared_state.result)

        relevant_ids = shared_result.relevant_ids

        cluster_assignments = shared_result.score_bands_result.clusters

        if len(relevant_ids) != len(cluster_assignments):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "The shared SCORE Bands result contains an "
                    "invalid solution-to-cluster mapping."
                ),
            )

        valid_clusters = set(cluster_assignments)

        if request.selected_cluster_id not in valid_clusters:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cluster {request.selected_cluster_id} "
                    "does not exist in the current SCORE Bands result."
                ),
            )

        selected_solution_ids = [
            solution_id
            for solution_id, cluster_id in zip(
                relevant_ids,
                cluster_assignments,
                strict=True,
            )
            if cluster_id == request.selected_cluster_id
        ]

        shared_config = SCOREBandsGDMConfig.model_validate(shared_state.config)

        scorebands_options = copy.deepcopy(shared_config.score_bands_config)
    else:
        # -----------------------------------------------------------
        # Recursive personal drill-down:
        #
        # Personal SCOREBandsMethodState
        #      -> selected personal cluster
        #      -> original solution IDs
        # -----------------------------------------------------------

        parent_state_db = session.get(
            StateDB,
            request.parent_state_id,
        )

        if parent_state_db is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Personal SCORE Bands state "
                    f"{request.parent_state_id} was not found."
                ),
            )

        # This is essential: another DM must not be able to use
        # somebody else's private state.
        if parent_state_db.session_id != interactive_session.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "The selected SCORE Bands state does not "
                    "belong to the current interactive session."
                ),
            )

        parent_state = parent_state_db.state

        if not isinstance(
            parent_state,
            SCOREBandsMethodState,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "The selected parent state is not a " "personal SCORE Bands state."
                ),
            )

        relevant_ids = parent_state.relevant_solution_ids
        cluster_assignments = parent_state.clusters

        if len(relevant_ids) != len(cluster_assignments):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "The personal SCORE Bands state contains "
                    "an invalid solution-to-cluster mapping."
                ),
            )

        valid_clusters = set(cluster_assignments)

        if request.selected_cluster_id not in valid_clusters:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cluster {request.selected_cluster_id} "
                    "does not exist in the selected personal state."
                ),
            )

        selected_solution_ids = [
            solution_id
            for solution_id, cluster_id in zip(
                relevant_ids,
                cluster_assignments,
                strict=True,
            )
            if cluster_id == request.selected_cluster_id
        ]

        # Reuse the configuration represented by the parent result.
        scorebands_options = parent_state.result.options.model_copy(deep=True)

    # ---------------------------------------------------------------
    # 5. Allow explicit personal configuration to override the
    #    inherited one.
    # ---------------------------------------------------------------

    if request.scorebands_options is not None:
        scorebands_options = request.scorebands_options.model_copy(deep=True)

    # ---------------------------------------------------------------
    # 6. Make sure there is enough data to run SCORE Bands
    # ---------------------------------------------------------------

    if len(selected_solution_ids) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "The selected band contains fewer than two "
                "solutions and cannot be subdivided further."
            ),
        )

    # ---------------------------------------------------------------
    # 7. Load the original discrete objective matrix
    # ---------------------------------------------------------------

    problem = session.get(
        ProblemDB,
        group_session.problem_id,
    )

    if problem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(f"Problem {group_session.problem_id} " "was not found."),
        )

    if problem.discrete_representation is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=("The problem does not have a discrete " "representation."),
        )

    objective_values = problem.discrete_representation.objective_values

    objective_names = list(objective_values)

    all_objectives = pl.DataFrame(objective_values).with_row_index(name="solution_id")

    # ---------------------------------------------------------------
    # 8. Select only the solutions contained in the chosen band
    # ---------------------------------------------------------------

    selected_id_frame = pl.DataFrame(
        {
            "solution_id": selected_solution_ids,
        }
    )

    selected_objectives = selected_id_frame.join(
        all_objectives,
        how="left",
        on="solution_id",
    ).select(objective_names)

    if selected_objectives.height != len(selected_solution_ids):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Could not reconstruct every selected solution "
                "from the problem's discrete representation."
            ),
        )

    # ---------------------------------------------------------------
    # 9. Run the normal single-DM SCORE Bands calculation
    # ---------------------------------------------------------------

    try:
        score_state, result = get_score_bands_state(
            data=selected_objectives,
            scorebands_options=scorebands_options,
            relevant_solution_ids=selected_solution_ids,
        )
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Failed to calculate personal SCORE Bands.")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=("Failed to calculate personal SCORE Bands."),
        ) from error

    # ---------------------------------------------------------------
    # 10. Persist as a NORMAL interactive-method StateDB.
    #
    #     Important:
    #       session_id       -> personal InteractiveSessionDB
    #       group_session_id -> NOT USED
    #
    #     Therefore this does not touch the shared GDM workflow.
    # ---------------------------------------------------------------

    state_db = StateDB.create(
        database_session=session,
        problem_id=group_session.problem_id,
        session_id=interactive_session.id,
        parent_id=(parent_state_db.id if parent_state_db is not None else None),
        state=score_state,
    )

    # session.add(state_db)

    try:
        session.commit()
        session.refresh(state_db)
    except Exception as error:
        session.rollback()

        logger.exception("Failed to persist personal SCORE Bands state.")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Personal SCORE Bands were calculated but " "could not be persisted."
            ),
        ) from error

    return SCOREBandsMethodInitializeResponse(
        state_id=state_db.id,
        result=result,
    )
