"""A base group manager structure for group decision making.

``Group.users`` contains the decision makers who participate in learning,
preference elicitation, voting, and confirmation.

``Group.owner_id`` identifies the facilitator/administrator. The owner may
create and manage sessions, observe progress, configure a method, and perform
other facilitator actions, but is not automatically a decision maker.
"""

import asyncio
import logging
import sys
from tokenize import group
from typing import Annotated

from desdeo.api.models.gdm.gdm_aggregate import (
    GroupInfoRequest,
    GroupSessionDB,
    CreateGroupSessionRequest,
    GroupSessionPublic,
)
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from desdeo.api.db import get_session
from desdeo.api.models import (
    Group,
    GroupCreateRequest,
    GroupSessionInfoRequest,
    GroupIteration,
    GroupModifyRequest,
    GroupPublic,
    ProblemDB,
    User,
)
from desdeo.api.models.gdm.group_user_link import GroupUserLink
from desdeo.api.models.generic_states import StateDB
from desdeo.api.routers.gdm.utils import group_to_public
from desdeo.api.routers.user_authentication import get_current_user

from desdeo.api.models.user import User as UserDB

logging.basicConfig(
    stream=sys.stdout,
    format="[%(filename)s:%(lineno)d] %(levelname)s: %(message)s",
    level=logging.INFO,
)

router = APIRouter(prefix="/gdm", tags=["GDM"])


class ManagerError(Exception):
    """If something goes awry with the manager."""


def _decision_maker_ids(group: Group) -> set[int]:
    """Return the IDs of the group's decision makers only."""
    return {member.id for member in group.users if member.id is not None}


def _check_group_access(user: User, group: Group) -> None:
    """Allow the facilitator or a decision maker to access the group."""
    if user.id != group.owner_id and user.id not in _decision_maker_ids(group):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized user.",
        )


def _check_group_owner(user: User, group: Group) -> None:
    """Require the authenticated user to be the group facilitator."""
    if user.id != group.owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the group owner may perform this action.",
        )


class GroupManager:
    """Manage a group session's connections and communication."""

    def __init__(
        self,
        group_session_id: int,
        db_session: Session,
    ):
        """Initialize a manager for one group decision-making session."""
        self.lock = asyncio.Lock()
        self.sockets: dict[int, WebSocket | None] = {}
        self.group_session_id = group_session_id

        group_session = db_session.exec(
            select(GroupSessionDB).where(GroupSessionDB.id == group_session_id)
        ).first()

        if group_session is None:
            raise ManagerError(f"No group session with ID {group_session_id} found!")

        group = db_session.exec(
            select(Group).where(Group.id == group_session.group_id)
        ).first()

        if group is None:
            raise ManagerError(f"No group with ID {group_session.group_id} found!")

        # Decision makers participate in the method.
        for decision_maker in group.users:
            if decision_maker.id is not None:
                self.sockets[decision_maker.id] = None

        # The owner may be an observer and may not be in Group.users.
        if group.owner_id is not None:
            self.sockets.setdefault(group.owner_id, None)

    async def send_message(
        self,
        message: str,
        websocket: WebSocket,
    ) -> None:
        """Send a message to one connected user."""
        try:
            await websocket.send_text(message)
        except (WebSocketDisconnect, RuntimeError):
            return

    async def connect(
        self,
        user_id: int,
        websocket: WebSocket,
        db_session: Session,
    ) -> None:
        """Attach a WebSocket to this manager."""
        if user_id not in self.sockets:
            raise ManagerError(
                f"User with ID {user_id} does not belong to "
                f"group session {self.group_session_id}."
            )

        self.sockets[user_id] = websocket

        group_session = db_session.exec(
            select(GroupSessionDB).where(GroupSessionDB.id == self.group_session_id)
        ).first()

        if group_session is None:
            return

        if group_session.head_iteration_id is None:
            return

        head_iteration = db_session.exec(
            select(GroupIteration).where(
                GroupIteration.id == group_session.head_iteration_id,
                GroupIteration.session_id == group_session.id,
            )
        ).first()

        if head_iteration is None or head_iteration.parent is None:
            return

        previous_iteration = head_iteration.parent

        # JSON object keys are strings after persistence.
        notified = dict(previous_iteration.notified or {})
        user_key = str(user_id)

        if not notified.get(user_key, True):
            await self.send_message(
                "Please fetch results.",
                websocket,
            )

            notified[user_key] = True
            previous_iteration.notified = notified

            db_session.add(previous_iteration)
            db_session.commit()
            db_session.refresh(previous_iteration)

    async def disconnect(
        self,
        user_id: int,
        websocket: WebSocket,
    ) -> None:
        """Detach a WebSocket from this manager."""
        if self.sockets.get(user_id) is websocket:
            self.sockets[user_id] = None

    async def broadcast(
        self,
        message: str,
    ) -> None:
        """Send a message to every connected user."""
        for user_id, socket in list(self.sockets.items()):
            if socket is None:
                continue

            try:
                await socket.send_text(message)
            except (WebSocketDisconnect, RuntimeError):
                self.sockets[user_id] = None

    async def notify(
        self,
        user_ids: list[int],
        message: str,
    ) -> dict[str, bool]:
        """Notify users and return persisted notification statuses."""
        notified: dict[str, bool] = {}

        for user_id in user_ids:
            socket = self.sockets.get(user_id)
            user_key = str(user_id)

            if socket is None:
                notified[user_key] = False
                continue

            try:
                await self.send_message(message, socket)
                notified[user_key] = True
            except RuntimeError:
                self.sockets[user_id] = None
                notified[user_key] = False

        return notified

    async def run_method(
        self,
        user_id: int,
        data: str,
        db_session: Session,
    ) -> None:
        """Run the method-specific action.

        Derived managers must override this method.
        """
        raise NotImplementedError


@router.post("/create_group")
def create_group(
    request: GroupCreateRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> JSONResponse:
    """Create group.

    Args:
        request (GroupCreateRequest): a request that holds information to be used in creation of the group.
        user (Annotated[User, Depends(get_current_user)]): the current user.
        session (Annotated[Session, Depends(get_session)]): the database session.

    Returns:
        JSONResponse: Acknowledgement that the group was created

    Raises:
        HTTPException
    """
    # problem = session.exec(select(ProblemDB).where(ProblemDB.id == request.problem_id)).first()
    # if problem is None:
    #    raise HTTPException(
    #        detail=f"There's no problem with ID {request.problem_id}!", status_code=status.HTTP_404_NOT_FOUND
    #    )

    owner = session.exec(select(UserDB).where(UserDB.id == user.id)).first()

    if owner is None:
        raise HTTPException(status_code=404, detail="Owner not found.")

    # Fetch requested members
    requested_user_ids = set(request.user_ids)

    if owner.id in request.user_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "The group owner is the facilitator and cannot "
                "also be added as a decision maker."
            ),
        )

    members = list(
        session.exec(select(UserDB).where(UserDB.id.in_(requested_user_ids))).all()
    )

    found_user_ids = {member.id for member in members if member.id is not None}

    missing_user_ids = requested_user_ids - found_user_ids

    if missing_user_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Users not found: {sorted(missing_user_ids)}",
        )

    group = Group(
        name=request.group_name,
        owner_id=owner.id,
        users=members,
    )

    session.add(group)
    session.commit()
    session.refresh(group)

    # group_ids = user.group_ids.copy() if user.group_ids is not None else []
    # group_ids.append(group.id)
    # user.group_ids = group_ids

    # session.add(user)
    # session.commit()

    return JSONResponse(
        content={"message": f"Group with ID {group.id} created."},
        status_code=status.HTTP_201_CREATED,
    )


@router.post(
    "/groups/{group_id}/sessions",
    response_model=GroupSessionPublic,
)
def create_group_session(
    group_id: int,
    request: CreateGroupSessionRequest,
    user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_session)],
) -> GroupSessionPublic:
    """Create a decision-making session for a group."""

    group = db_session.exec(select(Group).where(Group.id == group_id)).first()

    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No group with ID {group_id} found.",
        )

    _check_group_owner(user, group)

    problem = db_session.exec(
        select(ProblemDB).where(ProblemDB.id == request.problem_id)
    ).first()

    if problem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No problem with ID {request.problem_id} found.",
        )

    supported_methods = {
        "gnimbus",
        "gdm-score-bands",
    }

    if request.method not in supported_methods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported group method: {request.method}",
        )

    group_session = GroupSessionDB(
        group_id=group.id,
        problem_id=problem.id,
        method=request.method,
        head_iteration_id=None,
    )

    db_session.add(group_session)
    db_session.commit()
    db_session.refresh(group_session)

    return GroupSessionPublic(
        id=group_session.id,
        group_id=group_session.group_id,
        problem_id=group_session.problem_id,
        method=group_session.method,
        head_iteration_id=group_session.head_iteration_id,
    )


@router.post("/delete_group")
def delete_group(
    request: GroupSessionInfoRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> JSONResponse:
    """Delete the group with given ID.

    Args:
        request (GroupSessionInfoRequest): Contains the ID of the group to be deleted
        user (Annotated[User, Depends(get_current_user)]): The user (in this case must be owner for anything to happen)
        session (Annotated[Session, Depends(get_session)]): The database session

    Returns:
        JSONResponse: Acknowledgement of the deletion

    Raises:
        HTTPException: Insufficient authorization etc.
    """
    group: Group = session.exec(
        select(Group).where(Group.id == request.group_id)
    ).first()
    if group is None:
        raise HTTPException(
            detail=f"No group with ID {request.group_id} found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    _check_group_owner(user, group)

    group_sessions = list(
        session.exec(
            select(GroupSessionDB).where(GroupSessionDB.group_id == group.id)
        ).all()
    )

    deleted_iteration_count = 0
    for group_session in group_sessions:
        iterations = list(
            session.exec(
                select(GroupIteration).where(
                    GroupIteration.session_id == group_session.id
                )
            ).all()
        )
        deleted_iteration_count += len(iterations)

        # Deleting root iterations removes descendants through the configured
        # GroupIteration.children delete-orphan cascade.
        root_iterations = [
            iteration for iteration in iterations if iteration.parent_id is None
        ]
        for root_iteration in root_iterations:
            session.delete(root_iteration)

        # StateDB has its own lineage and delete-orphan cascade. Remove roots
        # belonging to this group session after removing iteration references.
        state_roots = list(
            session.exec(
                select(StateDB).where(
                    StateDB.group_session_id == group_session.id,
                    StateDB.parent_id.is_(None),
                )
            ).all()
        )

        session.flush()

        for state_root in state_roots:
            session.delete(state_root)

        session.delete(group_session)

    # Clear the many-to-many relationship so GroupUserLink rows are removed.
    group.users.clear()
    session.add(group)
    session.flush()

    session.delete(group)
    session.commit()

    deleted_group = session.exec(
        select(Group).where(Group.id == request.group_id)
    ).first()

    if deleted_group is not None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete the group from the database.",
        )

    return JSONResponse(
        content={
            "message": (
                f"Group with ID {request.group_id} and its "
                f"{len(group_sessions)} sessions containing "
                f"{deleted_iteration_count} iterations were deleted."
            )
        },
        status_code=status.HTTP_200_OK,
    )


@router.post("/add_to_group")
def add_to_group(
    request: GroupModifyRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> JSONResponse:
    """Add a user to a group.

    Args:
        request (GroupModifyRequest): Request object that has group and user IDs.
        user (Annotated[User, Depends(get_current_user)]): the current user.
        session (Annotated[Session, Depends(get_session)]): the database session.

    Returns:
        JSONResponse: Aknowledge that user has been added to the group

    Raises:
        HTTPException: Authorization issues, group or user not found.
    """
    group: Group = session.exec(
        select(Group).where(Group.id == request.group_id)
    ).first()
    # Make sure the group exists
    if group is None:
        raise HTTPException(
            detail=f"There's no group with ID {request.group_id}",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    _check_group_owner(user, group)

    if request.user_id == group.owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "The group owner is the facilitator and cannot "
                "be added as a decision maker."
            ),
        )

    if request.user_id in _decision_maker_ids(group):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"User with ID {request.user_id} is already a decision "
                "maker in this group."
            ),
        )

    addee = session.exec(select(UserDB).where(UserDB.id == request.user_id)).first()

    if addee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No user with ID {request.user_id} found.",
        )

    group.users.append(addee)

    session.add(group)
    session.commit()
    session.refresh(group)

    return JSONResponse(
        content={
            "message": (
                f"Added user {request.user_id} as a decision maker "
                f"to group {group.id}."
            )
        },
        status_code=status.HTTP_200_OK,
    )


@router.post("/remove_from_group")
def remove_from_group(
    request: GroupModifyRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> JSONResponse:
    """Remove user from group.

    Args:
        request (GroupModifyRequest): Request object that has group and user IDs.
        user (Annotated[User, Depends(get_current_user)]): the current user.
        session (Annotated[Session, Depends(get_session)]): the database session.

    Returns:
        JSONResponse: Aknowledge that user has been removed from the group.

    Raises:
        HTTPException: Authorization issues, group or user not found.
    """
    group: Group = session.exec(
        select(Group).where(Group.id == request.group_id)
    ).first()
    # Make sure the group exists
    if group is None:
        raise HTTPException(
            detail=f"No group with ID {request.group_id} found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    # Make sure of proper authorization
    if user.id not in (group.owner_id, request.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized user.",
        )

    member = next(
        (
            decision_maker
            for decision_maker in group.users
            if decision_maker.id == request.user_id
        ),
        None,
    )

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"User with ID {request.user_id} "
                f"is not a decision maker in group {group.id}."
            ),
        )

    group.users.remove(member)
    session.add(group)
    session.commit()
    session.refresh(group)

    if request.user_id in _decision_maker_ids(group):
        raise HTTPException(
            detail=f"Could not remove User {request.user_id} from group {request.group_id}.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return JSONResponse(
        content={
            "message": f"User {request.user_id} removed from group {request.group_id}."
        },
        status_code=status.HTTP_200_OK,
    )


@router.post("/get_group_sessions_info")
def get_group_sessions_info(
    request: GroupSessionInfoRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> list[GroupSessionPublic]:
    """Get information about the sessions of a group.

    Args:
        request (GroupSessionInfoRequest): the id of the group for which we desire info on
        user (Annotated[User, Depends(get_current_user)]): the current user
        session (Annotated[Session, Depends(get_session)]): the database session

    Returns:
        list[GroupSessionPublic]: public info of the sessions of the group

    Raises:
        HTTPException: If there's no group with the requests group id
    """
    group = session.exec(select(Group).where(Group.id == request.group_id)).first()
    if group is None:
        raise HTTPException(
            detail=f"No group with ID {request.group_id} found!",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    _check_group_access(user, group)

    group_sessions = session.exec(
        select(GroupSessionDB).where(GroupSessionDB.group_id == request.group_id)
    ).all()

    return [
        GroupSessionPublic(
            id=group_session.id,
            group_id=group_session.group_id,
            problem_id=group_session.problem_id,
            method=group_session.method,
            head_iteration_id=group_session.head_iteration_id,
        )
        for group_session in group_sessions
    ]


@router.post("/get_group_info")
def get_group_info(
    request: GroupInfoRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> GroupPublic:
    """Get information about the group.

    Args:
        request (GroupInfoRequest): the id of the group for which we desire info on
        user (Annotated[User, Depends(get_current_user)]): the current user
        session (Annotated[Session, Depends(get_session)]): the database session

    Returns:
        GroupPublic: public info of the group

    Raises:
        HTTPException: If there's no group with the requests group id
    """
    group = session.exec(select(Group).where(Group.id == request.group_id)).first()
    if group is None:
        raise HTTPException(
            detail=f"No group with ID {request.group_id} found!",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    _check_group_access(user, group)
    return group_to_public(group)


@router.get(
    "/groups",
    response_model=list[GroupPublic],
)
def get_user_groups(
    user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_session)],
) -> list[GroupPublic]:
    """Return groups where the current user is an owner or member."""

    owned_groups = db_session.exec(select(Group).where(Group.owner_id == user.id)).all()

    member_groups = db_session.exec(
        select(Group)
        .join(GroupUserLink, GroupUserLink.group_id == Group.id)
        .where(GroupUserLink.user_id == user.id)
    ).all()

    groups_by_id: dict[int, Group] = {}

    for group in owned_groups:
        if group.id is not None:
            groups_by_id[group.id] = group

    for group in member_groups:
        if group.id is not None:
            groups_by_id[group.id] = group

    return [group_to_public(group) for group in groups_by_id.values()]


@router.get(
    "/groups/{group_id}/sessions",
    response_model=list[GroupSessionPublic],
)
def get_group_sessions(
    group_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_session)],
) -> list[GroupSessionPublic]:
    """Return all decision-making sessions belonging to a group."""

    group = db_session.exec(select(Group).where(Group.id == group_id)).first()

    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No group with ID {group_id} found.",
        )

    _check_group_access(user, group)

    group_sessions = db_session.exec(
        select(GroupSessionDB).where(GroupSessionDB.group_id == group_id)
    ).all()

    return [
        GroupSessionPublic(
            id=group_session.id,
            group_id=group_session.group_id,
            problem_id=group_session.problem_id,
            method=group_session.method,
            head_iteration_id=group_session.head_iteration_id,
        )
        for group_session in group_sessions
    ]


@router.get(
    "/group-sessions/{group_session_id}",
    response_model=GroupSessionPublic,
)
def get_group_session(
    group_session_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_session)],
) -> GroupSessionPublic:
    """Return one group decision-making session."""

    group_session = db_session.exec(
        select(GroupSessionDB).where(GroupSessionDB.id == group_session_id)
    ).first()

    if group_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No group session with ID {group_session_id} found.",
        )

    group = db_session.exec(
        select(Group).where(Group.id == group_session.group_id)
    ).first()

    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No group with ID {group_session.group_id} found.",
        )

    _check_group_access(user, group)

    return GroupSessionPublic(
        id=group_session.id,
        group_id=group_session.group_id,
        problem_id=group_session.problem_id,
        method=group_session.method,
        head_iteration_id=group_session.head_iteration_id,
    )
