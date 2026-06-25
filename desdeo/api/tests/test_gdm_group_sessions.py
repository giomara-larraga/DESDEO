from sqlmodel import Session, select

from desdeo.api.models import User, UserRole, ProblemDB
from desdeo.api.models.gdm.gdm_aggregate import Group, GroupSessionDB, GroupIteration
from desdeo.api.models.gdm.group_user_link import GroupUserLink
from desdeo.api.models.gdm.gnimbus import OptimizationPreference
from desdeo.api.models.generic_states import StateDB
from desdeo.problem.testproblems import river_pollution_problem_discrete


def make_user(session: Session, username: str, role: UserRole = UserRole.dm) -> User:
    user = User(username=username, password_hash="x", role=role)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_group_uses_group_user_link(session: Session):
    owner = make_user(session, "owner", UserRole.analyst)
    dm1 = make_user(session, "dm1")
    dm2 = make_user(session, "dm2")

    group = Group(name="test group", owner_id=owner.id, users=[owner, dm1, dm2])
    session.add(group)
    session.commit()
    session.refresh(group)

    links = session.exec(
        select(GroupUserLink).where(GroupUserLink.group_id == group.id)
    ).all()

    assert {link.user_id for link in links} == {owner.id, dm1.id, dm2.id}
    assert {user.id for user in group.users} == {owner.id, dm1.id, dm2.id}


def test_group_can_have_multiple_sessions(session: Session):
    owner = make_user(session, "owner", UserRole.analyst)
    dm1 = make_user(session, "dm1")

    problem1 = ProblemDB.from_problem(river_pollution_problem_discrete(False), user=owner)
    problem2 = ProblemDB.from_problem(river_pollution_problem_discrete(False), user=owner)

    session.add(problem1)
    session.add(problem2)
    session.commit()
    session.refresh(problem1)
    session.refresh(problem2)

    group = Group(name="test group", owner_id=owner.id, users=[owner, dm1])
    session.add(group)
    session.commit()
    session.refresh(group)

    s1 = GroupSessionDB(group_id=group.id, problem_id=problem1.id, method="gnimbus")
    s2 = GroupSessionDB(group_id=group.id, problem_id=problem2.id, method="gdm-score-bands")

    session.add(s1)
    session.add(s2)
    session.commit()
    session.refresh(s1)
    session.refresh(s2)

    assert s1.id != s2.id
    assert s1.group_id == group.id
    assert s2.group_id == group.id
    assert s1.problem_id != s2.problem_id


def test_iterations_belong_to_group_session(session: Session):
    owner = make_user(session, "owner", UserRole.analyst)
    problem = ProblemDB.from_problem(river_pollution_problem_discrete(False), user=owner)
    session.add(problem)
    session.commit()
    session.refresh(problem)

    group = Group(name="test group", owner_id=owner.id, users=[owner])
    session.add(group)
    session.commit()
    session.refresh(group)

    group_session = GroupSessionDB(
        group_id=group.id,
        problem_id=problem.id,
        method="gnimbus",
    )
    session.add(group_session)
    session.commit()
    session.refresh(group_session)

    iteration = GroupIteration(
        session_id=group_session.id,
        info_container=OptimizationPreference(set_preferences={}),
        notified={},
        state_id=None,
        parent_id=None,
    )
    session.add(iteration)
    session.commit()
    session.refresh(iteration)

    group_session.head_iteration_id = iteration.id
    session.add(group_session)
    session.commit()
    session.refresh(group_session)

    assert group_session.head_iteration_id == iteration.id
    assert iteration.session_id == group_session.id


def test_two_sessions_do_not_share_head_iteration(session: Session):
    owner = make_user(session, "owner", UserRole.analyst)
    problem = ProblemDB.from_problem(river_pollution_problem_discrete(False), user=owner)
    session.add(problem)
    session.commit()
    session.refresh(problem)

    group = Group(name="test group", owner_id=owner.id, users=[owner])
    session.add(group)
    session.commit()
    session.refresh(group)

    s1 = GroupSessionDB(group_id=group.id, problem_id=problem.id, method="gnimbus")
    s2 = GroupSessionDB(group_id=group.id, problem_id=problem.id, method="gnimbus")
    session.add(s1)
    session.add(s2)
    session.commit()
    session.refresh(s1)
    session.refresh(s2)

    i1 = GroupIteration(
        session_id=s1.id,
        info_container=OptimizationPreference(set_preferences={}),
        notified={},
    )
    i2 = GroupIteration(
        session_id=s2.id,
        info_container=OptimizationPreference(set_preferences={}),
        notified={},
    )

    session.add(i1)
    session.add(i2)
    session.commit()
    session.refresh(i1)
    session.refresh(i2)

    s1.head_iteration_id = i1.id
    s2.head_iteration_id = i2.id
    session.add(s1)
    session.add(s2)
    session.commit()

    assert s1.head_iteration_id != s2.head_iteration_id
    assert i1.session_id == s1.id
    assert i2.session_id == s2.id