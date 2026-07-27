"""Comprehensive manager tests for GDM SCORE Bands.

Role contract tested here:

* ``group.users`` contains decision makers.
* ``group.owner_id`` identifies the facilitator/administrator.
* Decision makers provide learning completion, votes, and confirmations.
* The owner may observe and perform facilitator operations, but must not be
  counted as a decision maker.

Place this file at::

    desdeo/api/tests/gdm/test_gdm_score_bands.py
"""

from __future__ import annotations

import copy
from datetime import datetime

import polars as pl
import pytest
from sqlmodel import Session, select

from desdeo.api.models import GroupIteration
from desdeo.api.models.gdm.gdm_score_bands import (
    GDMSCOREBandsConsensusPreference,
    GDMSCOREBandsDecisionPreference,
    GDMSCOREBandsLearningPreference,
)
from desdeo.api.models.generic_states import StateDB
from desdeo.api.models.state import (
    GDMSCOREBandsConsensusState,
    GDMSCOREBandsDecisionState,
    GDMSCOREBandsLearningState,
)
from desdeo.api.routers.gdm.gdm_base import ManagerError
from desdeo.api.routers.gdm.gdm_score_bands.gdm_score_bands_manager import (
    GDMScoreBandsManager,
)
from desdeo.gdm.score_bands import SCOREBandsGDMConfig, score_bands_gdm

from desdeo.api.tests.gdm.factories import (
    create_group,
    create_group_session,
    create_user,
)

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _initial_result(manager: GDMScoreBandsManager, config: SCOREBandsGDMConfig):
    """Create a real SCORE Bands result from the fixture problem."""
    objectives = pl.DataFrame(manager.discrete_representation.objective_values)
    results = score_bands_gdm(
        data=objectives,
        config=config,
        state=None,
    )
    assert results
    return results[-1]


def _persist_phase(
    *,
    db_session: Session,
    manager: GDMScoreBandsManager,
    group_session,
    preference,
    state,
    parent_iteration: GroupIteration | None = None,
    parent_state: StateDB | None = None,
) -> tuple[GroupIteration, StateDB]:
    """Persist one state and its corresponding group iteration."""
    state_db = manager._create_state(
        session=db_session,
        group_session=group_session,
        state=state,
        parent_state_id=None if parent_state is None else parent_state.id,
    )
    iteration = manager._create_iteration(
        session=db_session,
        group_session=group_session,
        info_container=preference,
        state_id=state_db.id,
        parent_iteration_id=(None if parent_iteration is None else parent_iteration.id),
    )
    db_session.commit()
    db_session.refresh(state_db)
    db_session.refresh(iteration)
    db_session.refresh(group_session)
    return iteration, state_db


@pytest.fixture
def score_bands_context(db_session, problem_factory):
    """Create an owner, two decision makers, an outsider, and a session."""
    owner = create_user(db_session, "score-owner")
    dm1 = create_user(db_session, "score-dm-1")
    dm2 = create_user(db_session, "score-dm-2")
    outsider = create_user(db_session, "score-outsider")

    group = create_group(
        db_session,
        owner,
        members=[dm1, dm2],
        name="SCORE Bands test group",
    )
    problem = problem_factory(db_session, owner)
    group_session = create_group_session(
        db_session,
        group,
        problem,
        method="gdm-score-bands",
    )
    manager = GDMScoreBandsManager(group_session.id, db_session)

    return {
        "owner": owner,
        "dm1": dm1,
        "dm2": dm2,
        "outsider": outsider,
        "group": group,
        "problem": problem,
        "group_session": group_session,
        "manager": manager,
    }


@pytest.fixture
def learning_context(db_session, score_bands_context):
    """Create an initialized learning iteration."""
    ctx = score_bands_context
    manager = ctx["manager"]
    group_session = ctx["group_session"]

    config = SCOREBandsGDMConfig(
        from_iteration=None,
    )
    result = _initial_result(manager, config)

    learning_state = GDMSCOREBandsLearningState(
        config=config.model_dump(mode="json"),
        result=result.model_dump(mode="json"),
    )
    learning_preference = GDMSCOREBandsLearningPreference(
        completed_user_ids=[],
    )

    iteration, state_db = _persist_phase(
        db_session=db_session,
        manager=manager,
        group_session=group_session,
        preference=learning_preference,
        state=learning_state,
    )

    return {
        **ctx,
        "iteration": iteration,
        "state_db": state_db,
        "config": config,
        "result": result,
    }


@pytest.fixture
def consensus_context(db_session, learning_context):
    """Create a consensus child of a learning iteration."""
    ctx = learning_context
    manager = ctx["manager"]
    group_session = ctx["group_session"]

    consensus_state = GDMSCOREBandsConsensusState(
        config=ctx["config"].model_dump(mode="json"),
        result=ctx["result"].model_dump(mode="json"),
        selected_band_indices=[],
    )
    consensus_preference = GDMSCOREBandsConsensusPreference(
        user_votes={},
        user_confirms=[],
    )
    iteration, state_db = _persist_phase(
        db_session=db_session,
        manager=manager,
        group_session=group_session,
        preference=consensus_preference,
        state=consensus_state,
        parent_iteration=ctx["iteration"],
        parent_state=ctx["state_db"],
    )

    return {
        **ctx,
        "learning_iteration": ctx["iteration"],
        "learning_state_db": ctx["state_db"],
        "iteration": iteration,
        "state_db": state_db,
    }


@pytest.fixture
def decision_context(db_session, consensus_context):
    """Create a final decision iteration with three candidates."""
    ctx = consensus_context
    manager = ctx["manager"]
    group_session = ctx["group_session"]

    decision_state = GDMSCOREBandsDecisionState(
        solution_variables={
            "x1": [1.0, 2.0, 3.0],
            "x2": [4.0, 5.0, 6.0],
        },
        solution_objectives={
            "f1": [10.0, 20.0, 30.0],
            "f2": [40.0, 50.0, 60.0],
        },
    )
    decision_preference = GDMSCOREBandsDecisionPreference(
        user_votes={},
        user_confirms=[],
    )
    iteration, state_db = _persist_phase(
        db_session=db_session,
        manager=manager,
        group_session=group_session,
        preference=decision_preference,
        state=decision_state,
        parent_iteration=ctx["iteration"],
        parent_state=ctx["state_db"],
    )

    return {
        **ctx,
        "consensus_iteration": ctx["iteration"],
        "consensus_state_db": ctx["state_db"],
        "iteration": iteration,
        "state_db": state_db,
    }


# ---------------------------------------------------------------------------
# Roles and initialization
# ---------------------------------------------------------------------------


def test_owner_is_not_a_decision_maker(score_bands_context):
    ctx = score_bands_context
    member_ids = {user.id for user in ctx["group"].users}

    assert member_ids == {ctx["dm1"].id, ctx["dm2"].id}
    assert ctx["owner"].id not in member_ids
    assert ctx["group"].owner_id == ctx["owner"].id


def test_manager_sockets_include_owner_and_decision_makers(score_bands_context):
    ctx = score_bands_context

    assert set(ctx["manager"].sockets) == {
        ctx["owner"].id,
        ctx["dm1"].id,
        ctx["dm2"].id,
    }
    assert ctx["outsider"].id not in ctx["manager"].sockets


def test_learning_iteration_has_persisted_state(db_session, learning_context):
    ctx = learning_context
    iteration = ctx["iteration"]

    assert ctx["group_session"].head_iteration_id == iteration.id
    assert iteration.state_id is not None
    assert iteration.parent_id is None
    assert isinstance(
        iteration.info_container,
        GDMSCOREBandsLearningPreference,
    )

    state_db = db_session.get(StateDB, iteration.state_id)
    assert state_db is not None
    assert state_db.group_session_id == ctx["group_session"].id
    assert isinstance(state_db.state, GDMSCOREBandsLearningState)


# ---------------------------------------------------------------------------
# Learning phase
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_decision_maker_can_complete_learning(
    db_session,
    learning_context,
):
    ctx = learning_context

    await ctx["manager"].mark_learning_complete(
        user=ctx["dm1"],
        group_session=ctx["group_session"],
        session=db_session,
    )

    db_session.refresh(ctx["iteration"])
    preference = ctx["iteration"].info_container
    assert preference.completed_user_ids == [ctx["dm1"].id]


@pytest.mark.asyncio
async def test_learning_completion_is_idempotent(
    db_session,
    learning_context,
):
    ctx = learning_context

    for _ in range(2):
        await ctx["manager"].mark_learning_complete(
            user=ctx["dm1"],
            group_session=ctx["group_session"],
            session=db_session,
        )

    db_session.refresh(ctx["iteration"])
    preference = ctx["iteration"].info_container
    assert preference.completed_user_ids == [ctx["dm1"].id]


@pytest.mark.asyncio
async def test_owner_cannot_complete_learning(
    db_session,
    learning_context,
):
    ctx = learning_context

    with pytest.raises(ManagerError):
        await ctx["manager"].mark_learning_complete(
            user=ctx["owner"],
            group_session=ctx["group_session"],
            session=db_session,
        )


@pytest.mark.asyncio
async def test_outsider_cannot_complete_learning(
    db_session,
    learning_context,
):
    ctx = learning_context

    with pytest.raises(ManagerError):
        await ctx["manager"].mark_learning_complete(
            user=ctx["outsider"],
            group_session=ctx["group_session"],
            session=db_session,
        )


@pytest.mark.asyncio
async def test_advance_requires_every_decision_maker(
    db_session,
    learning_context,
):
    ctx = learning_context

    await ctx["manager"].mark_learning_complete(
        user=ctx["dm1"],
        group_session=ctx["group_session"],
        session=db_session,
    )

    with pytest.raises(
        ManagerError,
        match="Every decision maker must complete learning",
    ):
        await ctx["manager"].advance_learning_phase(
            user=ctx["owner"],
            group_session=ctx["group_session"],
            session=db_session,
        )


@pytest.mark.asyncio
async def test_advance_does_not_require_owner_completion(
    db_session,
    learning_context,
):
    ctx = learning_context

    for decision_maker in (ctx["dm1"], ctx["dm2"]):
        await ctx["manager"].mark_learning_complete(
            user=decision_maker,
            group_session=ctx["group_session"],
            session=db_session,
        )

    old_iteration = ctx["iteration"]
    old_state_db = ctx["state_db"]

    await ctx["manager"].advance_learning_phase(
        user=ctx["owner"],
        group_session=ctx["group_session"],
        session=db_session,
    )

    db_session.refresh(ctx["group_session"])
    new_iteration = db_session.get(
        GroupIteration,
        ctx["group_session"].head_iteration_id,
    )
    assert new_iteration is not None
    assert new_iteration.id != old_iteration.id
    assert new_iteration.parent_id == old_iteration.id
    assert isinstance(
        new_iteration.info_container,
        GDMSCOREBandsConsensusPreference,
    )

    new_state_db = db_session.get(StateDB, new_iteration.state_id)
    assert new_state_db is not None
    assert new_state_db.parent_id == old_state_db.id
    assert isinstance(new_state_db.state, GDMSCOREBandsConsensusState)

    # The historical learning iteration must remain a learning iteration.
    db_session.refresh(old_iteration)
    assert isinstance(
        old_iteration.info_container,
        GDMSCOREBandsLearningPreference,
    )


@pytest.mark.asyncio
async def test_learning_warning_is_persisted(
    db_session,
    learning_context,
):
    ctx = learning_context
    message = "Five minutes of learning time remain."

    await ctx["manager"].warn_learning_deadline(
        group_session=ctx["group_session"],
        session=db_session,
        message=message,
    )

    db_session.refresh(ctx["iteration"])
    preference = ctx["iteration"].info_container
    assert preference.last_warning_message == message
    assert preference.last_warning_at is not None
    # Validate that the timestamp is an ISO-8601 value.
    datetime.fromisoformat(preference.last_warning_at)


@pytest.mark.asyncio
async def test_learning_operations_fail_after_consensus(
    db_session,
    consensus_context,
):
    ctx = consensus_context

    with pytest.raises(ManagerError):
        await ctx["manager"].mark_learning_complete(
            user=ctx["dm1"],
            group_session=ctx["group_session"],
            session=db_session,
        )

    with pytest.raises(ManagerError):
        await ctx["manager"].warn_learning_deadline(
            group_session=ctx["group_session"],
            session=db_session,
        )


# ---------------------------------------------------------------------------
# Voting and confirmation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_voting_is_not_available_during_learning(
    db_session,
    learning_context,
):
    ctx = learning_context

    with pytest.raises(ManagerError, match="Voting is only available"):
        await ctx["manager"].vote(
            user=ctx["dm1"],
            group_session=ctx["group_session"],
            voted_index=0,
            session=db_session,
        )


@pytest.mark.asyncio
async def test_decision_maker_vote_is_stored(
    db_session,
    consensus_context,
):
    ctx = consensus_context

    await ctx["manager"].vote(
        user=ctx["dm1"],
        group_session=ctx["group_session"],
        voted_index=0,
        session=db_session,
    )

    db_session.refresh(ctx["iteration"])
    preference = ctx["iteration"].info_container
    assert preference.user_votes == {str(ctx["dm1"].id): 0}


@pytest.mark.asyncio
async def test_owner_cannot_vote(db_session, consensus_context):
    ctx = consensus_context

    with pytest.raises(ManagerError):
        await ctx["manager"].vote(
            user=ctx["owner"],
            group_session=ctx["group_session"],
            voted_index=0,
            session=db_session,
        )


@pytest.mark.asyncio
async def test_outsider_cannot_vote(db_session, consensus_context):
    ctx = consensus_context

    with pytest.raises(ManagerError):
        await ctx["manager"].vote(
            user=ctx["outsider"],
            group_session=ctx["group_session"],
            voted_index=0,
            session=db_session,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_vote", [-1, 100_000])
async def test_vote_index_must_be_in_range(
    db_session,
    consensus_context,
    invalid_vote,
):
    ctx = consensus_context

    with pytest.raises(ManagerError, match="outside the valid range"):
        await ctx["manager"].vote(
            user=ctx["dm1"],
            group_session=ctx["group_session"],
            voted_index=invalid_vote,
            session=db_session,
        )


@pytest.mark.asyncio
async def test_changed_vote_removes_previous_confirmation(
    db_session,
    decision_context,
):
    ctx = decision_context

    await ctx["manager"].vote(
        user=ctx["dm1"],
        group_session=ctx["group_session"],
        voted_index=0,
        session=db_session,
    )
    await ctx["manager"].confirm(
        user=ctx["dm1"],
        group_session=ctx["group_session"],
        session=db_session,
    )
    await ctx["manager"].vote(
        user=ctx["dm1"],
        group_session=ctx["group_session"],
        voted_index=1,
        session=db_session,
    )

    db_session.refresh(ctx["iteration"])
    preference = ctx["iteration"].info_container
    assert preference.user_votes[str(ctx["dm1"].id)] == 1
    assert ctx["dm1"].id not in preference.user_confirms


@pytest.mark.asyncio
async def test_confirmation_requires_vote(
    db_session,
    consensus_context,
):
    ctx = consensus_context

    with pytest.raises(ManagerError, match="hasn't voted"):
        await ctx["manager"].confirm(
            user=ctx["dm1"],
            group_session=ctx["group_session"],
            session=db_session,
        )


@pytest.mark.asyncio
async def test_owner_cannot_confirm(db_session, decision_context):
    ctx = decision_context

    # Store an owner vote manually so the test specifically checks the role,
    # rather than failing only because no vote exists.
    preference = copy.deepcopy(ctx["iteration"].info_container)
    preference.user_votes[str(ctx["owner"].id)] = 0
    ctx["iteration"].info_container = preference
    db_session.add(ctx["iteration"])
    db_session.commit()

    with pytest.raises(ManagerError):
        await ctx["manager"].confirm(
            user=ctx["owner"],
            group_session=ctx["group_session"],
            session=db_session,
        )


@pytest.mark.asyncio
async def test_duplicate_confirmation_is_rejected(
    db_session,
    decision_context,
):
    ctx = decision_context

    await ctx["manager"].vote(
        user=ctx["dm1"],
        group_session=ctx["group_session"],
        voted_index=0,
        session=db_session,
    )
    await ctx["manager"].confirm(
        user=ctx["dm1"],
        group_session=ctx["group_session"],
        session=db_session,
    )

    with pytest.raises(ManagerError, match="already confirmed"):
        await ctx["manager"].confirm(
            user=ctx["dm1"],
            group_session=ctx["group_session"],
            session=db_session,
        )


@pytest.mark.asyncio
async def test_partial_confirmation_does_not_advance(
    db_session,
    decision_context,
):
    ctx = decision_context
    original_head_id = ctx["group_session"].head_iteration_id

    await ctx["manager"].vote(
        user=ctx["dm1"],
        group_session=ctx["group_session"],
        voted_index=0,
        session=db_session,
    )
    await ctx["manager"].confirm(
        user=ctx["dm1"],
        group_session=ctx["group_session"],
        session=db_session,
    )

    db_session.refresh(ctx["group_session"])
    assert ctx["group_session"].head_iteration_id == original_head_id


@pytest.mark.asyncio
async def test_all_decision_makers_select_final_winner(
    db_session,
    decision_context,
):
    ctx = decision_context

    for decision_maker in (ctx["dm1"], ctx["dm2"]):
        await ctx["manager"].vote(
            user=decision_maker,
            group_session=ctx["group_session"],
            voted_index=1,
            session=db_session,
        )
        await ctx["manager"].confirm(
            user=decision_maker,
            group_session=ctx["group_session"],
            session=db_session,
        )

    db_session.refresh(ctx["state_db"])
    state = ctx["state_db"].state
    assert isinstance(state, GDMSCOREBandsDecisionState)
    assert state.winner_index == 1
    assert state.winner_solution_variables == {
        "x1": 2.0,
        "x2": 5.0,
    }
    assert state.winner_solution_objectives == {
        "f1": 20.0,
        "f2": 50.0,
    }


# ---------------------------------------------------------------------------
# State and iteration lineage
# ---------------------------------------------------------------------------


def test_consensus_state_and_iteration_have_learning_parents(
    consensus_context,
):
    ctx = consensus_context

    assert ctx["iteration"].parent_id == ctx["learning_iteration"].id
    assert ctx["state_db"].parent_id == ctx["learning_state_db"].id
    assert ctx["group_session"].head_iteration_id == ctx["iteration"].id


def test_result_history_excludes_decision_states(
    db_session,
    decision_context,
):
    ctx = decision_context

    history = ctx["manager"]._get_result_history(
        group_session=ctx["group_session"],
        session=db_session,
    )

    # The fixtures contain learning + consensus + decision. Only the first two
    # carry SCORE Bands clustering results.
    assert len(history) == 2
    assert all(result.iteration >= 0 for result in history)


@pytest.mark.asyncio
async def test_revert_creates_new_consensus_child(
    db_session,
    consensus_context,
):
    ctx = consensus_context
    old_head = ctx["iteration"]
    target = ctx["learning_iteration"]

    await ctx["manager"].revert(
        user=ctx["owner"],
        group_session=ctx["group_session"],
        session=db_session,
        group_iteration_id=target.id,
    )

    db_session.refresh(ctx["group_session"])
    restored_iteration = db_session.get(
        GroupIteration,
        ctx["group_session"].head_iteration_id,
    )
    assert restored_iteration is not None
    assert restored_iteration.id not in {old_head.id, target.id}
    assert restored_iteration.parent_id == old_head.id
    assert isinstance(
        restored_iteration.info_container,
        GDMSCOREBandsConsensusPreference,
    )

    restored_state_db = db_session.get(
        StateDB,
        restored_iteration.state_id,
    )
    assert restored_state_db is not None
    assert restored_state_db.parent_id == old_head.state_id
    assert isinstance(
        restored_state_db.state,
        GDMSCOREBandsConsensusState,
    )


@pytest.mark.asyncio
async def test_decision_maker_cannot_revert(
    db_session,
    consensus_context,
):
    ctx = consensus_context

    with pytest.raises(ManagerError):
        await ctx["manager"].revert(
            user=ctx["dm1"],
            group_session=ctx["group_session"],
            session=db_session,
            group_iteration_id=ctx["learning_iteration"].id,
        )


@pytest.mark.asyncio
async def test_revert_rejects_current_head(
    db_session,
    consensus_context,
):
    ctx = consensus_context

    with pytest.raises(ManagerError, match="already the current iteration"):
        await ctx["manager"].revert(
            user=ctx["owner"],
            group_session=ctx["group_session"],
            session=db_session,
            group_iteration_id=ctx["iteration"].id,
        )


@pytest.mark.asyncio
async def test_configure_creates_child_state_and_iteration(
    db_session,
    consensus_context,
):
    ctx = consensus_context
    old_iteration = ctx["iteration"]
    old_state_db = ctx["state_db"]

    new_config = copy.deepcopy(ctx["config"])

    await ctx["manager"].configure(
        group_session=ctx["group_session"],
        config=new_config,
        session=db_session,
    )

    db_session.refresh(ctx["group_session"])
    new_iteration = db_session.get(
        GroupIteration,
        ctx["group_session"].head_iteration_id,
    )
    assert new_iteration is not None
    assert new_iteration.id != old_iteration.id
    assert new_iteration.parent_id == old_iteration.id
    assert isinstance(
        new_iteration.info_container,
        GDMSCOREBandsConsensusPreference,
    )

    new_state_db = db_session.get(StateDB, new_iteration.state_id)
    assert new_state_db is not None
    assert new_state_db.parent_id == old_state_db.id
    assert isinstance(new_state_db.state, GDMSCOREBandsConsensusState)


@pytest.mark.asyncio
async def test_configure_fails_during_learning(
    db_session,
    learning_context,
):
    ctx = learning_context

    with pytest.raises(ManagerError, match="Cannot reconfigure"):
        await ctx["manager"].configure(
            group_session=ctx["group_session"],
            config=copy.deepcopy(ctx["config"]),
            session=db_session,
        )


# ---------------------------------------------------------------------------
# Corrupt or invalid persistence
# ---------------------------------------------------------------------------


def test_get_head_iteration_requires_initialization(
    db_session,
    score_bands_context,
):
    ctx = score_bands_context

    with pytest.raises(ManagerError, match="not been initialized"):
        ctx["manager"]._get_head_iteration(
            ctx["group_session"],
            db_session,
        )


def test_iteration_state_requires_state_id(
    db_session,
    score_bands_context,
):
    ctx = score_bands_context
    iteration = GroupIteration(
        session_id=ctx["group_session"].id,
        info_container=GDMSCOREBandsLearningPreference(),
        notified={},
        state_id=None,
        parent_id=None,
    )
    db_session.add(iteration)
    db_session.commit()
    db_session.refresh(iteration)

    with pytest.raises(ManagerError, match="has no state"):
        ctx["manager"]._get_iteration_state(
            iteration=iteration,
            session=db_session,
        )


def test_state_rows_belong_to_group_session(
    db_session,
    decision_context,
):
    ctx = decision_context

    states = db_session.exec(
        select(StateDB).where(StateDB.group_session_id == ctx["group_session"].id)
    ).all()
    iterations = db_session.exec(
        select(GroupIteration).where(
            GroupIteration.session_id == ctx["group_session"].id
        )
    ).all()

    assert len(states) == 3
    assert len(iterations) == 3
    assert all(iteration.state_id is not None for iteration in iterations)
