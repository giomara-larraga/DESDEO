"""A structure for group decision making.

When preferences are sent through the websockets, they are validated.
Then, the preferences are saved into a database. When all group members have articulated their
preferences, system begins optimization. The results are then saved into the database and the system notifies all
connected users that the solutions are ready to be fetched. If a user is not connected to the server, the server will
notify the user when they connect next time.

"""

import asyncio
import logging
import sys
from datetime import UTC, datetime
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from jose import ExpiredSignatureError, JWTError, jwt
from sqlmodel import Session, select

from desdeo.api import AuthConfig
from desdeo.api.db import get_session
from desdeo.api.models import (
    Group,
    User,
)
from desdeo.api.models.gdm.gdm_aggregate import GroupSessionDB
from desdeo.api.routers.gdm.gdm_base import GroupManager
from desdeo.api.routers.gdm.gdm_score_bands.gdm_score_bands_manager import GDMScoreBandsManager
from desdeo.api.routers.gdm.gnimbus.gnimbus_manager import GNIMBUSManager
from desdeo.api.routers.user_authentication import get_user

logging.basicConfig(
    stream=sys.stdout, format="[%(filename)s:%(lineno)d] %(levelname)s: %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gdm")


class ManagerManager:
    """A singleton class to manage group managers. Spawns them and deletes them.

    TODO: Also check on manager type! If a Group has a NIMBUSManager, but for
    example a RPMManager is requested, create it.
    """

    def __init__(self):
        """Class constructor."""
        # self.group_managers: dict[int, GroupManager] = {}
        self.group_managers: dict[int, dict[str, GroupManager]] = {}
        self.lock = asyncio.Lock()

    async def get_group_manager(
        self, group_id: int, method: str, db_session: Session
    ) -> GroupManager | GNIMBUSManager | GDMScoreBandsManager | None:
        """Return the correct group manager for the caller.

        Args:
            group_id (int): The ID of the group of the mgr
            method (str): The method of the group mgr
            db_session (Session): the database session passed to the manager.

        Returns:
            GroupManager | GNIMBUSManager | GDMScoreBandsManager | None: The manager (or not if not implemented.)
        """
        async with self.lock:
            if group_id in self.group_managers:
                managers = self.group_managers[group_id]
                if method in managers:
                    return managers[method]
                # If there is no manager, create it.
                match method:
                    case "gnimbus":
                        manager = GNIMBUSManager(group_id=group_id, db_session=db_session)
                        self.group_managers[group_id][method] = manager
                        return manager
                    case "gdm-score-bands":
                        manager = GDMScoreBandsManager(group_id=group_id, db_session=db_session)
                        self.group_managers[group_id][method] = manager
                        return manager
            else:
                self.group_managers[group_id] = {}
                match method:
                    case "gnimbus":
                        manager = GNIMBUSManager(group_id=group_id, db_session=db_session)
                        self.group_managers[group_id][method] = manager
                        return manager
                    case "gdm-score-bands":
                        manager = GDMScoreBandsManager(group_id=group_id, db_session=db_session)
                        self.group_managers[group_id][method] = manager
                        return manager

    async def check_disconnect(self, group_id: int, method: str):
        """Checks if a group manager has active connections. If no, delete it.

        Args:
            group_id (int): ID of the group
            method (str): method of the manager

        Returns:
            Nothing.
        """
        async with self.lock:
            # check if group has any managers
            if group_id in self.group_managers:
                managers = self.group_managers[group_id]
                # Check if method has a manager
                if method in managers:
                    manager = managers[method]
                    # check if the manager has any active websockets
                    for _, socket in manager.sockets.items():
                        if socket is not None:
                            return
                    # No active sockets, delete the manager.
                    async with manager.lock:
                        del self.group_managers[group_id][method]
                        # If group has no managers, delete the group entry.
                        if self.group_managers[group_id] == {}:
                            del self.group_managers[group_id]


manager = ManagerManager()


async def auth_user(token: str, session: Session, websocket: WebSocket) -> User:
    """Authenticate the user.

    token: str: the access token of the user.
    session: Session: the database session from where the user is received
    websocket: WebSocket: the websocket that the user has connected with

    """

    async def error_and_close():
        await websocket.send_text("Could not validate credencials. Try logging in again.")
        await websocket.close()

    try:
        payload = jwt.decode(token, AuthConfig.authjwt_secret_key, algorithms=[AuthConfig.authjwt_algorithm])
        username = payload.get("sub")
        expire_time: datetime = payload.get("exp")

        if username is None or expire_time is None or expire_time < datetime.now(UTC).timestamp():
            return await error_and_close()

    except ExpiredSignatureError:
        return await error_and_close()

    except JWTError:
        return await error_and_close()

    user = get_user(session, username=username)

    if user is None:
        return await error_and_close()

    return user


@router.websocket("/ws")
async def websocket_endpoint(
    session: Annotated[Session, Depends(get_session)],
    websocket: WebSocket,
    token: str = Query(),
    group_session_id: int = Query(),
    method: str = Query(),
):
    """Connect a user to a group decision-making session WebSocket.

    Example:

    ws://[DOMAIN]:[PORT]/gdm/ws
        ?token=[TOKEN]
        &group_session_id=[GROUP_SESSION_ID]
        &method=[METHOD]
    """
    await websocket.accept()

    user = await auth_user(token, session, websocket)
    if user is None:
        return

    group_session = session.exec(
        select(GroupSessionDB).where(
            GroupSessionDB.id == group_session_id
        )
    ).first()

    if group_session is None:
        await websocket.send_text(
            f"There is no group session with ID {group_session_id}."
        )
        await websocket.close()
        return

    if group_session.method != method:
        await websocket.send_text(
            f"Group session {group_session_id} uses method "
            f"'{group_session.method}', not '{method}'."
        )
        await websocket.close()
        return

    group = session.exec(
        select(Group).where(
            Group.id == group_session.group_id
        )
    ).first()

    if group is None:
        await websocket.send_text(
            f"There is no group with ID {group_session.group_id}."
        )
        await websocket.close()
        return

    participant_ids = {member.id for member in group.users}

    if group.owner_id is not None:
        participant_ids.add(group.owner_id)

    if user.id not in participant_ids:
        await websocket.send_text(
            f"User {user.username} does not belong to group {group.name}."
        )
        await websocket.close()
        return

    group_manager = await manager.get_group_manager(
        group_session_id=group_session_id,
        method=method,
        db_session=session,
    )

    if group_manager is None:
        await websocket.send_text(f"Unknown method: {method}")
        await websocket.close()
        return

    await group_manager.connect(
        user.id,
        websocket,
        db_session=session,
    )

    logger.info(
        "Group session ID %s manager active connections: %s",
        group_session_id,
        group_manager.sockets,
    )
    logger.info(
        "Existing GroupManagers: %s",
        manager.group_managers,
    )

    try:
        while True:
            data = await websocket.receive_text()

            # Only decision makers submit preferences.
            # The owner may still connect and observe.
            decision_maker_ids = {
                member.id for member in group.users
            }

            if user.id in decision_maker_ids:
                await group_manager.run_method(
                    user.id,
                    data,
                    session,
                )
            else:
                logger.warning(
                    "User %s is connected as group owner/observer "
                    "and cannot submit GNIMBUS preferences.",
                    user.username,
                )

    except WebSocketDisconnect:
        await group_manager.disconnect(
            user.id,
            websocket,
        )

        await manager.check_disconnect(
            group_session_id=group_session_id,
            method=method,
        )

        logger.info(
            "Group session ID %s manager active connections: %s",
            group_session_id,
            group_manager.sockets,
        )
        logger.info(
            "Existing GroupManagers: %s",
            manager.group_managers,
        )

    except RuntimeError as error:
        logger.warning("WebSocket RuntimeError: %s", error)

    finally:
        session.close()