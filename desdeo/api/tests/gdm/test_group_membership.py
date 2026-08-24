from sqlmodel import select

from desdeo.api.models.gdm.group_user_link import GroupUserLink

from desdeo.api.tests.gdm.factories import create_group, create_user


def test_group_membership_uses_link_table(db_session):
    owner = create_user(db_session, "owner")
    dm1 = create_user(db_session, "dm1")
    dm2 = create_user(db_session, "dm2")

    group = create_group(
        db_session,
        owner=owner,
        members=[dm1, dm2],
    )

    links = db_session.exec(
        select(GroupUserLink).where(
            GroupUserLink.group_id == group.id
        )
    ).all()

    assert {link.user_id for link in links} == {
        dm1.id,
        dm2.id,
    }

    assert group.owner_id == owner.id

def test_user_can_belong_to_multiple_groups(db_session):
    owner1 = create_user(db_session, "owner-1")
    owner2 = create_user(db_session, "owner-2")
    shared_user = create_user(db_session, "shared-user")

    group1 = create_group(
        db_session,
        owner=owner1,
        members=[shared_user],
        name="Group 1",
    )

    group2 = create_group(
        db_session,
        owner=owner2,
        members=[shared_user],
        name="Group 2",
    )

    db_session.refresh(shared_user)

    assert {group.id for group in shared_user.groups} == {
        group1.id,
        group2.id,
    }


def test_removing_member_does_not_delete_user(db_session):
    owner = create_user(db_session, "owner")
    member = create_user(db_session, "member")

    group = create_group(
        db_session,
        owner=owner,
        members=[member],
    )

    group.users.remove(member)
    db_session.add(group)
    db_session.commit()
    db_session.refresh(group)

    assert member.id not in {user.id for user in group.users}
    assert db_session.get(type(member), member.id) is not None