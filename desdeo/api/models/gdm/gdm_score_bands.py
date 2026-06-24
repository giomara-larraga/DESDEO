"""Models for GDM Score Bands.

Idea is that in the very first iteration, the filtered indices contains the clustering
information on the entire data. Since on each iteration, the clustering is different,
we need to include the indices over and over again. Of course with time the amount of
indices will get smaller and smaller, and eventually be only ~10 solutions.

The names of the classes can be renamed to fit the purpose better, currently they are
more or less just the first thing that came to my mind.
"""

from datetime import datetime, timezone
from typing import Literal

from sqlmodel import JSON, Column, Field, SQLModel

from desdeo.api.models.gdm.gdm_base import BaseGroupInfoContainer
from desdeo.gdm.score_bands import SCOREBandsGDMConfig, SCOREBandsGDMResult
from desdeo.problem.schema import VariableType
from desdeo.tools.score_bands import SCOREBandsResult


class GDMSCOREBandInformation(BaseGroupInfoContainer):
    """Class for containing info on which band was voted for."""
    method: str = "gdm-score-bands"
    phase: Literal["learning", "consensus"] = Field(
        default="consensus", description="Current group phase for GDM SCORE-bands."
    )
    user_votes: dict[str, int] = Field(
        description="Dictionary of votes."
    )
    user_confirms: list[int] = Field(
        description="List of users who want to move on."
    )
    learning_completed_user_ids: list[int] = Field(
        default_factory=list,
        description="Decision makers who have finished their private learning-phase exploration.",
    )
    learning_started_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC timestamp at which the learning phase started.",
    )
    learning_duration_seconds: int = Field(
        default=900,
        description="Configured duration of the learning phase in seconds.",
    )
    learning_last_warning_at: str | None = Field(
        default=None,
        description="UTC timestamp of the latest owner warning about learning phase expiry.",
    )
    learning_last_warning_message: str | None = Field(
        default=None,
        description="Latest owner warning message sent during learning phase.",
    )
    score_bands_config: SCOREBandsGDMConfig = Field(
        description="The configuration that led to this classification."
    )
    score_bands_result: SCOREBandsGDMResult = Field(
        description="The results of the score bands."
    )


class GDMSCOREBandFinalSelection(BaseGroupInfoContainer):
    """Class for containing the final 10 or less solutions, the final solution and the votes that led to it."""
    method: str = "gdm-score-bands-final"
    phase: Literal["decision"] = Field(default="decision")
    user_votes: dict[str, int] = Field(
        description="Dictionary of votes."
    )
    user_confirms: list[int] = Field(
        description="List of users who want to move on."
    )

    """The 10 or less solutions to choose from"""
    solution_variables: dict[str, list[VariableType]] = Field(sa_column=Column(JSON))
    solution_objectives: dict[str, list[float]] = Field(sa_column=Column(JSON))

    """The selected (or generated??) of those 10 or less."""
    winner_solution_variables: dict[str, VariableType] = Field(sa_column=Column(JSON))
    winner_solution_objectives: dict[str, float] = Field(sa_column=Column(JSON))


class GDMScoreBandsInitializationRequest(SQLModel):
    """Request class for initialization of score bands."""
    group_session_id: int = Field(
        description="The group session to be initialized."
    )
    score_bands_config: SCOREBandsGDMConfig = Field(
        description="The configuration for the initial score banding."
    )

class GDMScoreBandsVoteRequest(SQLModel):
    """Request for voting for a band."""
    group_session_id: int = Field(
        description="ID of the group session in question"
    )
    vote: int = Field(
        description="The vote. Vaalisalaisuus."
    )


class GDMSCOREBandsLearningAdvanceRequest(SQLModel):
    """Request for moving the group from learning to consensus."""

    group_session_id: int = Field(description="Group Session ID.")


class GDMSCOREBandsLearningWarningRequest(SQLModel):
    """Request for sending a learning-phase warning to connected users."""

    group_session_id: int = Field(description="Group Session ID.")
    message: str | None = Field(default=None, description="Optional warning message.")


class GDMSCOREBandsLearningStatusResponse(SQLModel):
    """Response model for the persisted learning phase metadata."""

    phase: Literal["learning", "consensus", "decision"]
    learning_completed_user_ids: list[int] = Field(default_factory=list)
    learning_started_at: str | None = None
    learning_duration_seconds: int | None = None
    learning_last_warning_at: str | None = None
    learning_last_warning_message: str | None = None

class GDMSCOREBandsRevertRequest(SQLModel):
    """Request for reverting to a previous setup."""
    group_session_id: int = Field(
        description="Group Session ID."
    )
    iteration_number: int = Field(
        description="The number of the iteration that we want to revert to."
    )

class GDMSCOREBandsResponse(SQLModel):
    """Response class for GDMSCOREBands, whether it is initialization or not."""
    method: str = "gdm-score-bands"
    phase: Literal["learning", "consensus"] = Field(default="consensus")
    group_session_id: int = Field(
        description="The group session in question."
    )
    group_iter_id: int = Field(
        description="ID of the latest group iteration."
    )
    latest_iteration: int = Field(
        description="The latest GDM iteration number. Different from Group Iteration id."
    )
    result: SCOREBandsResult = Field(
        description="The results of the score bands procedure."
    )

class GDMSCOREBandsDecisionResponse(SQLModel):
    """Response class for gdm score bands that includes the last 10 or less solutions."""
    method: str = "gdm-score-bands-final"
    phase: Literal["decision"] = Field(default="decision")
    group_session_id: int = Field(
        description="The group session in question."
    )
    group_iter_id: int = Field(
        description="ID of the latest group iteration."
    )
    result: GDMSCOREBandFinalSelection = Field(
        description="The container for the solutions and the winner solution."
    )

class GDMSCOREBandsHistoryResponse(SQLModel):
    """Response class for all history. Allows for going to a previous iteration."""
    history: list[GDMSCOREBandsResponse | GDMSCOREBandsDecisionResponse]
