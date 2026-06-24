"""A base group manager structure for group decision making."""

import asyncio
import logging
import sys
from tokenize import group
from typing import Annotated

from desdeo.api.models.gdm.gdm_aggregate import GroupSessionDB, CreateGroupSessionRequest
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
    GroupInfoRequest,
    GroupIteration,
    GroupModifyRequest,
    GroupPublic,
    ProblemDB,
    User,
)
from desdeo.api.routers.user_authentication import get_current_user

from desdeo.api.models.user import User as UserDB

logging.basicConfig(
    stream=sys.stdout, format="[%(filename)s:%(lineno)d] %(levelname)s: %(message)s", level=logging.INFO
)

router = APIRouter(prefix="/gdm", tags=["GDM"])


class ManagerError(Exception):
    """If something goes awry with the manager."""


class GroupManager:
    """A group manager. Manages connections, disconnections, optimization and communication to users."""

    def __init__(self, group_session_id: int, db_session: Session):
        """Initializes the instance of the group manager."""
        self.lock = asyncio.Lock()
        self.sockets: dict[int, WebSocket] = {}
        self.group_session_id: int = group_session_id

        # Get session and make sure the group exists
        group_session = db_session.exec(select(GroupSessionDB).where(GroupSessionDB.id == group_session_id)).first()
        if group_session is None:
            #db_session.close()
            raise ManagerError(f"No group session with ID {group_session_id} found!")
        
        group = db_session.exec(
            select(Group).where(Group.id == group_session.group_id)
        ).first()
        if group is None:
            #db_session.close()
            raise ManagerError(f"No group with ID {group_session.group_id} found!")

        # Initialize the socket dict (at the very least to avoid KeyErrors)
        for user in group.users:
            self.sockets[user.id] = None

        # Include owner too, if owner is not already in group.users
        self.sockets.setdefault(group.owner_id, None)

        #db_session.close()

    async def send_message(self, message: str, websocket: WebSocket):
        """Notify the user of the existing results that have to be fetched."""
        try:
            await websocket.send_text(message)
        except WebSocketDisconnect:
            return

    async def connect(self, user_id: int, websocket: WebSocket, db_session: Session):
        """Connect to websocket.

        The connection has been accepted beforehand for sending error messages
        back to user, but here we attach it to the manager instance.
        """
        self.sockets[user_id] = websocket

        group_session = db_session.exec(
            select(GroupSessionDB).where(
                GroupSessionDB.id == self.group_session_id
            )
        ).first()

        if group_session is None:
            return

        head_iter = db_session.exec(
            select(GroupIteration).where(
                GroupIteration.id == group_session.head_iteration_id
            )
        ).first()

        if head_iter is None:
            return

        prev_iter = head_iter.parent
        if prev_iter is None:
            return

        notified = prev_iter.notified or {}
        if not notified.get(str(user_id), True):
            await self.send_message("Please fetch results.", websocket)

            notified = notified.copy()
            notified[str(user_id)] = True

            prev_iter.notified = notified
            db_session.add(prev_iter)
            db_session.commit()


    async def disconnect(self, user_id: int, websocket: WebSocket):
        """Disconnect from websocket.

        The connection has been closed beforehand, but here we detach the WebSocket
        object from the manager instance.
        """
        if self.sockets[user_id] == websocket:
            self.sockets[user_id] = None

    async def broadcast(self, message: str):
        """Send message to all connected websockets."""
        for _, socket in self.sockets.items():
            if socket is not None:
                try:
                    await socket.send_text(message)
                except WebSocketDisconnect:
                    continue

    async def notify(
        self,
        user_ids: list[int],
        message: str,
    ) -> dict[int, bool]:
        """Notify all users with [message]."""
        notified = {}
        for user_id in user_ids:
            try:
                socket: WebSocket = self.sockets[user_id]
                if socket is not None:
                    await self.send_message(message, socket)
                    notified[user_id] = True
                else:
                    notified[user_id] = False
            except KeyError:
                notified[user_id] = False
        return notified

    async def run_method(
        self,
        user_id: int,
        data: str,
    ):
        """The function to run the method.

        One could derive different managers from this GroupManager
        class and implement method and manager-specific "run_method" functions.
        """


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
    #problem = session.exec(select(ProblemDB).where(ProblemDB.id == request.problem_id)).first()
    #if problem is None:
    #    raise HTTPException(
    #        detail=f"There's no problem with ID {request.problem_id}!", status_code=status.HTTP_404_NOT_FOUND
    #    )

    owner = session.exec(
        select(UserDB).where(UserDB.id == user.id)
    ).first()


    if owner is None:
        raise HTTPException(status_code=404, detail="Owner not found.")
    
    # Fetch requested members
    members = session.exec(
        select(UserDB).where(UserDB.id.in_(request.user_ids))
    ).all()

    found_user_ids = {user.id for user in members}
    requested_user_ids = set(request.user_ids)

    missing_user_ids = requested_user_ids - found_user_ids

    if missing_user_ids:
        raise HTTPException(
            status_code=404,
            detail=f"Users not found: {sorted(missing_user_ids)}",
        )

    # Ensure owner is also a member
    if owner.id not in found_user_ids:
        members.append(owner)

    group = Group(
        name=request.name,
        owner_id=owner.id,
        users=members,
    )

    session.add(group)
    session.commit()
    session.refresh(group)

    #group_ids = user.group_ids.copy() if user.group_ids is not None else []
    #group_ids.append(group.id)
    #user.group_ids = group_ids

    #session.add(user)
    #session.commit()

    return JSONResponse(content={"message": f"Group with ID {group.id} created."}, status_code=status.HTTP_201_CREATED)


@router.post("/groups/{group_id}/sessions")
def create_group_session(
    group_id: int,
    request: CreateGroupSessionRequest,
    session: Session = Depends(get_session),
):
    group_session = GroupSessionDB(
        group_id=group_id,
        problem_id=request.problem_id,
        method=request.method,
        status="active",
    )

    session.add(group_session)
    session.commit()
    session.refresh(group_session)

    initial_iteration = GroupIteration(
        session_id=group_session.id,
        parent_id=None,
        state_id=None,
        info_container=request.initial_info_container,
    )

    session.add(initial_iteration)
    session.commit()
    session.refresh(initial_iteration)

    group_session.head_iteration_id = initial_iteration.id
    session.add(group_session)
    session.commit()

    return group_session


@router.post("/delete_group")
def delete_group(
    request: GroupInfoRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> JSONResponse:
    """Delete the group with given ID.

    Args:
        request (GroupInfoRequest): Contains the ID of the group to be deleted
        user (Annotated[User, Depends(get_current_user)]): The user (in this case must be owner for anything to happen)
        session (Annotated[Session, Depends(get_session)]): The database session

    Returns:
        JSONResponse: Acknowledgement of the deletion

    Raises:
        HTTPException: Insufficient authorization etc.
    """
    group: Group = session.exec(select(Group).where(Group.id == request.group_id)).first()
    if group is None:
        raise HTTPException(detail=f"No group with ID {request.group_id} found.", status_code=status.HTTP_404_NOT_FOUND)

    if user.id != group.owner_id:
        raise HTTPException(
            detail="Only the owner of a group may delete the group.", status_code=status.HTTP_401_UNAUTHORIZED
        )

    # Remove the group from users
    user_ids = group.user_ids
    for uid in user_ids:
        group_user = session.exec(select(User).where(User.id == uid)).first()
        ugids = group_user.group_ids.copy()
        ugids.remove(group.id)
        group_user.group_ids = ugids
        session.add(group_user)
        session.commit()

    ugids = user.group_ids.copy()
    ugids.remove(group.id)
    user.group_ids = ugids
    session.add(user)
    session.commit()
    session.refresh(user)

    # Get the root iteration
    # TODO: Adapt this to the new cascade with multiple children
    head: GroupIteration = session.exec(
        select(GroupIteration).where(GroupIteration.id == group.head_iteration_id)
    ).first()
    iter_count = 0
    if head is not None:
        while head.parent is not None:
            head = head.parent
            iter_count += 1

        # First delete the corresponding group iterations
        # This deletes the rest of the iterations due to cascades
        session.delete(head)
        session.commit()

    # Then delete the group
    session.delete(group)
    session.commit()

    # Make sure that the group IS deleted!
    group = session.exec(select(Group).where(Group.id == request.group_id)).first()
    if group is not None:
        raise HTTPException(
            detail="Couldn't delete group from the database!", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return JSONResponse(
        content={"message": f"Group with ID {request.group_id} and its {iter_count} iterations have been deleted."},
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
    group: Group = session.exec(select(Group).where(Group.id == request.group_id)).first()
    # Make sure the group exists
    if group is None:
        raise HTTPException(
            detail=f"There's no group with ID {request.group_id}", status_code=status.HTTP_404_NOT_FOUND
        )
    # Make sure of proper authorization
    if not group.owner_id == user.id:
        raise HTTPException(detail="Unauthorized user", status_code=status.HTTP_401_UNAUTHORIZED)

    if request.user_id in group.user_ids:
        raise HTTPException(
            detail=f"User with ID {request.user_id} already in this group!", status_code=status.HTTP_400_BAD_REQUEST
        )

    addee = session.exec(select(User).where(User.id == request.user_id)).first()
    # Make sure the user to be added exists
    if addee is None:
        raise HTTPException(
            detail=f"There is no user with ID {request.user_id}!", status_code=status.HTTP_404_NOT_FOUND
        )

    users = group.user_ids.copy()
    users.append(request.user_id)
    group.user_ids = users
    session.add(group)
    session.commit()
    session.refresh(group)

    if addee.group_ids is None:
        addee.group_ids = [group.id]
    else:
        groups = addee.group_ids.copy()
        groups.append(group.id)
        addee.group_ids = groups

    session.add(addee)
    session.commit()
    session.refresh(addee)

    return JSONResponse(
        content={"message": f"Added user {group.user_ids[-1]} to group {group.id}."}, status_code=status.HTTP_200_OK
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
    group: Group = session.exec(select(Group).where(Group.id == request.group_id)).first()
    # Make sure the group exists
    if group is None:
        raise HTTPException(detail=f"No group with ID {request.group_id} found.", status_code=status.HTTP_404_NOT_FOUND)
    # Make sure of proper authorization
    authorized = user.id in (group.owner_id, request.user_id)

    if not authorized:
        raise HTTPException(detail="Unauthorized user", status_code=status.HTTP_401_UNAUTHORIZED)

    if request.user_id not in group.user_ids:
        raise HTTPException(
            detail=f"User with ID {request.user_id} is not in this group!", status_code=status.HTTP_400_BAD_REQUEST
        )

    user_ids = group.user_ids.copy()
    user_ids.remove(request.user_id)
    group.user_ids = user_ids
    session.add(group)
    session.commit()
    session.refresh(group)

    removed_user = session.exec(select(User).where(User.id == request.user_id)).first()
    ugids = removed_user.group_ids.copy()
    ugids.remove(group.id)
    removed_user.group_ids = ugids
    session.add(removed_user)
    session.commit()

    if request.user_id in group.user_ids:
        raise HTTPException(
            detail=f"Could not remove User {request.user_id} from group {request.group_id}.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return JSONResponse(
        content={"message": f"User {request.user_id} removed from group {request.group_id}."},
        status_code=status.HTTP_200_OK,
    )


@router.post("/get_group_info")
def get_group_info(
    request: GroupInfoRequest,
    session: Annotated[Session, Depends(get_session)],
) -> GroupPublic:
    """Get information about the group.

    Args:
        request (GroupInfoRequest): the id of the group for which we desire info on
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

    return group


