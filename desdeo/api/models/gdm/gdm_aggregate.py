"""Classes for group decision making, aggregating all different types of data classes."""

from datetime import datetime
import json
from typing import Optional

from sqlalchemy.types import TypeDecorator
from sqlmodel import JSON, Column, Field, Relationship, SQLModel


from desdeo.api.models.gdm.gdm_base import BaseGroupInfoContainer
from desdeo.api.models.gdm.gnimbus import EndProcessPreference, OptimizationPreference, VotingPreference
from desdeo.tools import SolverResults
from typing import TYPE_CHECKING
from desdeo.api.models.gdm.group_user_link import GroupUserLink

from desdeo.api.models.gdm.gdm_score_bands import (
    GDMSCOREBandsConsensusPreference,
    GDMSCOREBandsDecisionPreference,
    GDMSCOREBandsLearningPreference,
)

if TYPE_CHECKING:
    from desdeo.api.models.user import User

class PreferenceType(TypeDecorator):
    """A converter of Preference types."""

    impl = JSON
    cache_ok = True

    # Serialize
    def process_bind_param(self, value, dialect):
        """Turns a preference item into json."""
        if isinstance(value, BaseGroupInfoContainer):
            return value.model_dump_json()
        return None

    # Deserialize
    def process_result_value(self, value, dialect):
        """And the other way around."""
        if value is None:
            return None

        jsoned = (
            json.loads(value)
            if isinstance(value, str)
            else value
        )
        if jsoned is not None:
            match jsoned.get("method"):
                case "voting":
                    return VotingPreference.model_validate(jsoned)

                case "optimization":
                    return OptimizationPreference.model_validate(jsoned)

                case "end":
                    return EndProcessPreference.model_validate(jsoned)

                case "gdm-score-bands-learning":
                    return GDMSCOREBandsLearningPreference.model_validate(
                        jsoned
                    )

                case "gdm-score-bands-consensus":
                    return GDMSCOREBandsConsensusPreference.model_validate(
                        jsoned
                    )

                case "gdm-score-bands-decision":
                    return GDMSCOREBandsDecisionPreference.model_validate(
                        jsoned
                    )

                case _:
                    return None
        


class GroupBase(SQLModel):
    """Base class for group table model and group response model."""


class Group(GroupBase, table=True):
    """Table model for Group."""

    id: int | None = Field(primary_key=True, default=None)
    name: str | None = Field(default=None)

    owner_id: int | None = Field(foreign_key="user.id", default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    #user_ids: list[int] | None = Field(sa_column=Column(JSON))

    #problem_id: int = Field(default=None)

    """The id of the head GroupIteration."""
    #head_iteration_id: int | None
    # relationships
    #owner: "User" = Relationship(...)
    users: list["User"] = Relationship(
        link_model=GroupUserLink
    )

    sessions: list["GroupSessionDB"] = Relationship(
        back_populates="group"
    )

class GroupUserPublic(SQLModel):
    id: int
    username: str
class GroupPublic(GroupBase):
    """Response model for Group."""

    id: int
    name: str
    owner_id: int
    users: list[GroupUserPublic] = Field(default_factory=list)
    #users: list["User"]
    #user_ids: list[int]
    #problem_id: int

class GroupSessionPublic(SQLModel):
    id: int
    group_id: int
    problem_id: int
    method: str
    head_iteration_id: int | None = None


class GroupSessionDB(SQLModel, table=True):
    __tablename__ = "group_session"

    id: int = Field(default=None, primary_key=True)
    group_id: int = Field(foreign_key="group.id")
    problem_id: int = Field(foreign_key="problemdb.id")
    method: str
    #created_at: datetime = Field(default_factory=datetime.utcnow)
    head_iteration_id: int | None = Field(
        default=None,
    )
    group: Group = Relationship(back_populates="sessions")

    #current_iteration_id: Optional[int] = Field(
    #    default=None,
    #    foreign_key="group_iteration.id",
    #)


class GroupIteration(SQLModel, table=True):
    """Table model for Group Iteration (we could extend this in various ways)."""

    id: int | None = Field(primary_key=True, default=None)
    session_id: int | None = Field(foreign_key="group_session.id", default=None)
    #problem_id: int | None = Field(default=None)

    """ID of the associated Group."""
    #group_id: int

    """The preferences are stored in this item while the iteration is in progress."""
    info_container: BaseGroupInfoContainer = Field(sa_column=Column(PreferenceType))
    # NOTE: This used to be called "preferences" and the class used to be called "BasePreference"

    notified: dict[str, bool] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
    )
    """State for storing post optimization/voting related data (dec vars, objectives, etc.)"""
    #state_id: int | None = Field()

    """Linked list emerges."""
    parent_id: int | None = Field(foreign_key="groupiteration.id", default=None)
    state_id: int | None = Field(default=None, foreign_key="statedb.id")

    parent: "GroupIteration" = Relationship(
        back_populates="children", sa_relationship_kwargs={"remote_side": "GroupIteration.id"}
    )
    # If parent is removed, remove the child too
    children: list["GroupIteration"] = Relationship(
        back_populates="parent", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class GroupInfoRequest(SQLModel):
    """Class for requesting group information."""

    group_id: int

class GroupSessionInfoRequest(SQLModel):
    """Class for requesting group information."""

    group_session_id: int

class GroupSessionRevertRequest(SQLModel):
    """Class for requesting reverting to certain iteration."""

    group_session_id: int = Field(description="The ID of the group session we wish to revert.")
    state_id: int = Field(
        description="The state's ID to which we want to revert to. "\
            "Corresponds to state_id in GroupIteration."
    )


class GroupResult(SQLModel):
    """Class for group's result."""

    solver_results: list[SolverResults]


class GroupModifyRequest(SQLModel):
    """Used for adding a user into group and removing a user from group."""

    group_id: int
    user_id: int


class GroupCreateRequest(SQLModel):
    """Used for requesting a group to be created."""

    group_name: str
    user_ids: list[int]
    #problem_id: int
class CreateGroupSessionRequest(SQLModel):
    problem_id: int
    method: str
    #info_container: BaseGroupInfoContainer