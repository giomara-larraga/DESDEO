from sqlmodel import select

from desdeo.api.models.gdm.gdm_aggregate import (
    GroupIteration,
    GroupSessionDB,
)
from desdeo.api.models.gdm.gnimbus import OptimizationPreference

from desdeo.api.tests.gdm.factories import create_group, create_group_session, create_user


def test_group_can_have_multiple_sessions(
    db_session,
    problem_factory,
):
    owner = create_user(db_session, "owner")
    member = create_user(db_session, "member")
    group = create_group(db_session, owner, [member])

    problem1 = problem_factory(db_session, owner)
    problem2 = problem_factory(db_session, owner)

    session1 = create_group_session(
        db_session,
        group,
        problem1,
        method="gnimbus",
    )

    session2 = create_group_session(
        db_session,
        group,
        problem2,
        method="gdm-score-bands",
    )

    assert session1.id != session2.id
    assert session1.group_id == group.id
    assert session2.group_id == group.id
    assert session1.problem_id == problem1.id
    assert session2.problem_id == problem2.id


def test_iteration_belongs_to_group_session(
    db_session,
    problem_factory,
):
    owner = create_user(db_session, "owner")
    group = create_group(db_session, owner)
    problem = problem_factory(db_session, owner)

    group_session = create_group_session(
        db_session,
        group,
        problem,
    )

    iteration = GroupIteration(
        session_id=group_session.id,
        info_container=OptimizationPreference(
            set_preferences={},
        ),
        notified={},
        state_id=None,
        parent_id=None,
    )

    db_session.add(iteration)
    db_session.commit()
    db_session.refresh(iteration)

    assert iteration.session_id == group_session.id


def test_two_sessions_have_independent_heads(
    db_session,
    problem_factory,
):
    owner = create_user(db_session, "owner")
    group = create_group(db_session, owner)
    problem = problem_factory(db_session, owner)

    session1 = create_group_session(
        db_session,
        group,
        problem,
    )

    session2 = create_group_session(
        db_session,
        group,
        problem,
    )

    iteration1 = GroupIteration(
        session_id=session1.id,
        info_container=OptimizationPreference(
            set_preferences={},
        ),
        notified={},
    )

    iteration2 = GroupIteration(
        session_id=session2.id,
        info_container=OptimizationPreference(
            set_preferences={},
        ),
        notified={},
    )

    db_session.add(iteration1)
    db_session.add(iteration2)
    db_session.commit()
    db_session.refresh(iteration1)
    db_session.refresh(iteration2)

    session1.head_iteration_id = iteration1.id
    session2.head_iteration_id = iteration2.id

    db_session.add(session1)
    db_session.add(session2)
    db_session.commit()

    assert session1.head_iteration_id == iteration1.id
    assert session2.head_iteration_id == iteration2.id
    assert session1.head_iteration_id != session2.head_iteration_id


def test_query_iterations_only_returns_one_session(
    db_session,
    problem_factory,
):
    owner = create_user(db_session, "owner")
    group = create_group(db_session, owner)
    problem = problem_factory(db_session, owner)

    session1 = create_group_session(db_session, group, problem)
    session2 = create_group_session(db_session, group, problem)

    iteration1 = GroupIteration(
        session_id=session1.id,
        info_container=OptimizationPreference(set_preferences={}),
        notified={},
    )

    iteration2 = GroupIteration(
        session_id=session2.id,
        info_container=OptimizationPreference(set_preferences={}),
        notified={},
    )

    db_session.add(iteration1)
    db_session.add(iteration2)
    db_session.commit()

    iterations = db_session.exec(
        select(GroupIteration).where(
            GroupIteration.session_id == session1.id
        )
    ).all()

    assert len(iterations) == 1
    assert iterations[0].session_id == session1.id