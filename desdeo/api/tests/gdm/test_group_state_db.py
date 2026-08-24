from desdeo.api.models import GNIMBUSVotingState, StateDB
from desdeo.tools import SolverResults

from desdeo.api.tests.gdm.factories import create_group, create_group_session, create_user


def test_group_state_links_to_group_session(
    db_session,
    problem_factory,
    solver_result_factory,
):
    owner = create_user(db_session, "owner")
    group = create_group(db_session, owner)
    problem = problem_factory(db_session, owner)

    group_session = create_group_session(
        db_session,
        group,
        problem,
    )

    method_state = GNIMBUSVotingState(
        votes={},
        solver_results=[solver_result_factory()],
    )

    state = StateDB.create(
        database_session=db_session,
        problem_id=problem.id,
        session_id=None,
        group_session_id=group_session.id,
        parent_id=None,
        state=method_state,
    )

    db_session.add(state)
    db_session.commit()
    db_session.refresh(state)

    assert state.group_session_id == group_session.id
    assert state.session_id is None
    assert state.problem_id == problem.id


def test_individual_and_group_session_are_not_mixed(
    db_session,
    problem_factory,
    solver_result_factory,
):
    owner = create_user(db_session, "owner")
    group = create_group(db_session, owner)
    problem = problem_factory(db_session, owner)

    group_session = create_group_session(
        db_session,
        group,
        problem,
    )

    state = StateDB.create(
        database_session=db_session,
        problem_id=problem.id,
        session_id=None,
        group_session_id=group_session.id,
        parent_id=None,
        state=GNIMBUSVotingState(
            votes={},
            solver_results=[solver_result_factory()],
        ),
    )

    db_session.add(state)
    db_session.commit()

    assert not (
        state.session_id is not None
        and state.group_session_id is not None
    )