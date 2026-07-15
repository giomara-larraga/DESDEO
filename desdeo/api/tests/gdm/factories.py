"""Factory helpers for GDM tests."""

from sqlmodel import Session

from desdeo.api.models import ProblemDB, User, UserRole
from desdeo.api.models.gdm.gdm_aggregate import Group, GroupSessionDB


def create_user(
    session: Session,
    username: str,
    role: UserRole = UserRole.dm,
) -> User:
    user = User(
        username=username,
        password_hash="test-password-hash",
        role=role,
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    return user


def create_group(
    session: Session,
    owner: User,
    members: list[User] | None = None,
    name: str = "Test group",
) -> Group:
    group = Group(
        name=name,
        owner_id=owner.id,
        users=list(members or []),
    )

    session.add(group)
    session.commit()
    session.refresh(group)

    return group


def create_group_session(
    session: Session,
    group: Group,
    problem: ProblemDB,
    method: str = "gnimbus",
) -> GroupSessionDB:
    group_session = GroupSessionDB(
        group_id=group.id,
        problem_id=problem.id,
        method=method,
        head_iteration_id=None,
    )

    session.add(group_session)
    session.commit()
    session.refresh(group_session)

    return group_session