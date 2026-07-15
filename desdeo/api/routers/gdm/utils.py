"""Shared GDM utilities."""

from fastapi import HTTPException, status
from sqlmodel import Session, select

from desdeo.api.models import Group, GroupSessionDB, User

def get_group_session_or_404(
    group_session_id: int,
    session: Session,
) -> GroupSessionDB:
    group_session = session.exec(
        select(GroupSessionDB).where(GroupSessionDB.id == group_session_id)
    ).first()

    if group_session is None:
        raise HTTPException(
            detail=f"No group session with ID {group_session_id} found!",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return group_session


def get_group_or_404(
    group_session: GroupSessionDB,
    session: Session,
) -> Group:
    group = session.exec(
        select(Group).where(Group.id == group_session.group_id)
    ).first()

    if group is None:
        raise HTTPException(
            detail=f"No group with ID {group_session.group_id} found!",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return group


def get_group_member_ids(group: Group) -> list[int]:
    """Return all participants, including the group owner."""
    user_ids = {member.id for member in group.users}

    if group.owner_id is not None:
        user_ids.add(group.owner_id)

    return list(user_ids)


def check_group_access(user: User, group: Group):
    member_ids = get_group_member_ids(group)

    if user.id not in member_ids and user.id != group.owner_id:
        raise HTTPException(
            detail="Unauthorized user.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )