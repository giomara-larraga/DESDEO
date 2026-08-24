"""Shared GDM utilities."""

from fastapi import HTTPException, status
from sqlmodel import Session, select

from desdeo.api.models import (
    Group,
    GroupPublic,
    GroupSessionDB,
    GroupSessionPublic,
    GroupUserPublic,
    User,
)

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


def get_decision_maker_ids(group: Group) -> list[int]:
    """Return users participating in the decision-making process."""
    return [
        member.id
        for member in group.users
        if member.id is not None
    ]


def check_group_access(user: User, group: Group) -> None:
    """Allow decision makers and the facilitator to access the group."""
    decision_maker_ids = get_decision_maker_ids(group)

    if (
        user.id not in decision_maker_ids
        and user.id != group.owner_id
    ):
        raise HTTPException(
            detail="Unauthorized user.",
            status_code=status.HTTP_403_FORBIDDEN,
        )


def check_decision_maker(user: User, group: Group) -> None:
    """Require the user to be a decision maker."""
    if user.id not in get_decision_maker_ids(group):
        raise HTTPException(
            detail="Only decision makers may perform this action.",
            status_code=status.HTTP_403_FORBIDDEN,
        )


def check_group_owner(user: User, group: Group) -> None:
    """Require the user to be the group facilitator."""
    if user.id != group.owner_id:
        raise HTTPException(
            detail="Only the group owner may perform this action.",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
def group_to_public(group: Group) -> GroupPublic:
    """Convert a persisted Group into its public response model."""
    return GroupPublic(
        id=group.id,
        name=group.name,
        owner_id=group.owner_id,
        users=[
            GroupUserPublic(
                id=member.id,
                username=member.username,
            )
            for member in group.users
        ],
    )