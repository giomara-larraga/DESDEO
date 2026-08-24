import pytest
from fastapi import HTTPException

from desdeo.api.routers.gdm.gnimbus.gnimbus_routers import (
    check_group_access,
)
from desdeo.api.tests.gdm.factories import create_group, create_user


def test_group_member_has_access(db_session):
    owner = create_user(db_session, "owner")
    member = create_user(db_session, "member")
    group = create_group(db_session, owner, [member])

    check_group_access(member, group)


def test_group_owner_has_access(db_session):
    owner = create_user(db_session, "owner")
    group = create_group(db_session, owner)

    check_group_access(owner, group)


def test_unrelated_user_has_no_access(db_session):
    owner = create_user(db_session, "owner")
    outsider = create_user(db_session, "outsider")
    group = create_group(db_session, owner)

    with pytest.raises(HTTPException) as error:
        check_group_access(outsider, group)

    assert error.value.status_code == 403


def test_get_group_member_ids(db_session):
    owner = create_user(db_session, "owner")
    member = create_user(db_session, "member")
    group = create_group(db_session, owner, [member])

    assert {user.id for user in group.users} == {
        member.id,
    }
