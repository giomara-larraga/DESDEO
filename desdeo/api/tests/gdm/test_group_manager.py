import pytest

from desdeo.api.routers.gdm.gdm_base import GroupManager, ManagerError
from desdeo.api.tests.gdm.factories import create_group, create_group_session, create_user
from desdeo.api.tests.gdm.fakes import FakeWebSocket


def test_manager_builds_socket_map_from_group_members(
    db_session,
    problem_factory,
):
    owner = create_user(db_session, "owner")
    member = create_user(db_session, "member")
    group = create_group(db_session, owner, [member])
    problem = problem_factory(db_session, owner)

    group_session = create_group_session(
        db_session,
        group,
        problem,
    )

    manager = GroupManager(group_session.id, db_session)

    assert set(manager.sockets) == {
        owner.id,
        member.id,
    }


def test_manager_rejects_unknown_session(db_session):
    with pytest.raises(ManagerError):
        GroupManager(999_999, db_session)


@pytest.mark.asyncio
async def test_broadcast_only_sends_to_connected_users(
    db_session,
    problem_factory,
):
    owner = create_user(db_session, "owner")
    member = create_user(db_session, "member")
    group = create_group(db_session, owner, [member])
    problem = problem_factory(db_session, owner)

    group_session = create_group_session(
        db_session,
        group,
        problem,
    )

    manager = GroupManager(group_session.id, db_session)

    owner_socket = FakeWebSocket()
    manager.sockets[owner.id] = owner_socket
    manager.sockets[member.id] = None

    await manager.broadcast("test message")

    assert owner_socket.messages == ["test message"]