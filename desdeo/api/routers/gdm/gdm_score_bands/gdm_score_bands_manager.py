"""GDM Score Bands manager implementation."""

import copy
from datetime import datetime, timezone
from sqlmodel import SQLModel


from desdeo.api.models.gdm.gdm_base import BaseGroupInfoContainer
from desdeo.api.models.generic_states import StateDB
from desdeo.api.models.gdm.gdm_aggregate import GroupSessionDB
import polars as pl
from sqlmodel import Session, select

from desdeo.api.models.gdm.gdm_score_bands import (
    GDMSCOREBandsConsensusPreference,
    GDMSCOREBandsDecisionPreference,
    GDMSCOREBandsLearningPreference,
)

from desdeo.api.models import (
    GDMSCOREBandsFinalSelection,
    Group,
    GroupIteration,
    ProblemDB,
    User,
)

from desdeo.api.models.state import (
    GDMSCOREBandsConsensusState,
    GDMSCOREBandsDecisionState,
    GDMSCOREBandsLearningState,
)
from desdeo.api.routers.gdm.gdm_base import GroupManager, ManagerError
from desdeo.gdm.score_bands import SCOREBandsGDMConfig, SCOREBandsGDMResult, score_bands_gdm
from desdeo.gdm.voting_rules import consensus_rule, majority_rule
from desdeo.tools.score_bands import score_json

ScoreBandsPhaseState = (
    GDMSCOREBandsLearningState
    | GDMSCOREBandsConsensusState
    | GDMSCOREBandsDecisionState
)

class GDMScoreBandsManager(GroupManager):
    """The group manager implementation for GDM Score Bands."""

    def __init__(self, group_session_id: int, db_session: Session):
        """Initialize the group manager."""
        super().__init__(group_session_id, db_session)

        group_session = self._get_group_session(db_session)

        if group_session.method != "gdm-score-bands":
            raise ManagerError(
                f"Group session {group_session.id} uses method "
                f"'{group_session.method}', not 'gdm-score-bands'."
            )

        problem = db_session.exec(
            select(ProblemDB).where(ProblemDB.id == group_session.problem_id)
        ).first()

        if problem is None:
            raise ManagerError(f"No problem with ID {group_session.problem_id} found!")

        if problem.discrete_representation is None:
            raise ManagerError("The group's discrete representation does not exist!")

        self.discrete_representation = problem.discrete_representation

    def _create_state(
        self,
        *,
        session: Session,
        group_session: GroupSessionDB,
        state: SQLModel,
        parent_state_id: int | None,
    ) -> StateDB:
        state_db = StateDB.create(
            database_session=session,
            problem_id=group_session.problem_id,
            group_session_id=group_session.id,
            parent_id=parent_state_id,
            state=state,
        )

        session.add(state_db)
        session.flush()
        session.refresh(state_db)

        return state_db
    def _create_iteration(
        self,
        *,
        session: Session,
        group_session: GroupSessionDB,
        info_container: BaseGroupInfoContainer,
        state_id: int | None,
        parent_iteration_id: int | None,
    ) -> GroupIteration:
        iteration = GroupIteration(
            session_id=group_session.id,
            info_container=info_container,
            notified={},
            state_id=state_id,
            parent_id=parent_iteration_id,
        )

        session.add(iteration)
        session.flush()
        session.refresh(iteration)

        group_session.head_iteration_id = iteration.id
        session.add(group_session)

        return iteration
    def _get_group_session(self, session: Session) -> GroupSessionDB:
        group_session = session.exec(
            select(GroupSessionDB).where(
                GroupSessionDB.id == self.group_session_id
            )
        ).first()

        if group_session is None:
            raise ManagerError(
                f"No group session with ID {self.group_session_id} found!"
            )

        return group_session

    def _get_group(self, group_session: GroupSessionDB, session: Session) -> Group:
        group = session.exec(
            select(Group).where(Group.id == group_session.group_id)
        ).first()

        if group is None:
            raise ManagerError(
                f"No group with ID {group_session.group_id} found!"
            )

        return group

    def _get_head_iteration(
        self,
        group_session: GroupSessionDB,
        session: Session,
    ) -> GroupIteration:

        if group_session.head_iteration_id is None:
            raise ManagerError(
                "The group session has not been initialized."
            )

        group_iteration = session.exec(
            select(GroupIteration).where(
                GroupIteration.id == group_session.head_iteration_id,
                GroupIteration.session_id == group_session.id,
            )
        ).first()

        if group_iteration is None:
            raise ManagerError("No such Group Iteration! Did you initialize this group session?")

        return group_iteration

    def _get_member_ids(self, group: Group) -> list[int]:
        return [
            member.id
            for member in group.users
            if member.id is not None
        ]

    def _check_decision_maker(
        self,
        user: User,
        group: Group,
    ) -> None:
        if user.id not in self._get_member_ids(group):
            raise ManagerError(
                detail=(
                    f"User with ID {user.id} is not a decision "
                    f"maker in group {group.id}."
                ),
            )


    def _check_owner(
        self,
        user: User,
        group: Group,
    ) -> None:
        if user.id != group.owner_id:
            raise ManagerError(
                detail=(
                    f"User with ID {user.id} is not the owner "
                    f"of group {group.id}."
                ),
            )

    def _get_iteration_state(
        self,
        *,
        iteration: GroupIteration,
        session: Session,
    ) -> tuple[StateDB, ScoreBandsPhaseState]:
        """Load and validate the persisted state for an iteration."""
        if iteration.state_id is None:
            raise ManagerError(
                f"Group iteration {iteration.id} has no state."
            )

        state_db = session.get(StateDB, iteration.state_id)

        if state_db is None:
            raise ManagerError(
                f"State {iteration.state_id} for group iteration "
                f"{iteration.id} was not found."
            )

        state = state_db.state

        if not isinstance(
            state,
            (
                GDMSCOREBandsLearningState,
                GDMSCOREBandsConsensusState,
                GDMSCOREBandsDecisionState,
            ),
        ):
            raise ManagerError(
                f"State {state_db.id} is not a SCORE Bands state."
            )

        return state_db, state
    
    def _get_result_history(
        self,
        *,
        group_session: GroupSessionDB,
        session: Session,
    ) -> list[SCOREBandsGDMResult]:
        """Return SCORE Bands results in group-iteration order."""
        iterations = session.exec(
            select(GroupIteration)
            .where(GroupIteration.session_id == group_session.id)
            .order_by(GroupIteration.id)
        ).all()

        results: list[SCOREBandsGDMResult] = []

        for iteration in iterations:
            if iteration.state_id is None:
                continue

            state_db = session.get(StateDB, iteration.state_id)
            if state_db is None:
                continue

            state = state_db.state
            if isinstance(
                state,
                (
                    GDMSCOREBandsLearningState,
                    GDMSCOREBandsConsensusState,
                ),
            ):
                results.append(copy.deepcopy(state.result))

        return results
    
    async def run_method(
        self,
        user_id: int,
        data: str,
        db_session: Session,
    ):
        async with self.lock:
            websocket = self.sockets.get(user_id)

            if websocket is not None:
                await self.send_message(
                    "This method is used through the HTTP endpoints.",
                    websocket,
                )

    async def vote(
        self,
        user: User,
        group_session: GroupSessionDB,
        voted_index: int,
        session: Session,
    ):
        """Vote on a specific band."""
        async with self.lock:
            group = self._get_group(group_session, session)
            self._check_decision_maker(user, group)

            group_iteration = self._get_head_iteration(group_session, session)

            preferences = copy.deepcopy(
                group_iteration.info_container
            )

            if not isinstance(
                preferences,
                (GDMSCOREBandsConsensusPreference, GDMSCOREBandsDecisionPreference)
            ):
                raise ManagerError(
                    "Voting is only available during consensus or decision."
                )

            _, state = self._get_iteration_state(
                iteration=group_iteration,
                session=session,
            )

            if isinstance(state, GDMSCOREBandsConsensusState):
                number_of_choices = len(
                    set(state.result.score_bands_result.clusters)
                )
            elif isinstance(state, GDMSCOREBandsDecisionState):
                number_of_choices = len(
                    next(iter(state.solution_objectives.values()), [])
                )
            else:
                raise ManagerError(
                    "Voting is unavailable during the learning phase."
                )

            if voted_index < 0 or voted_index >= number_of_choices:
                raise ManagerError(
                    f"Vote index {voted_index} is outside the valid range."
                )
            preferences.user_votes[str(user.id)] = voted_index

            # A changed vote invalidates an earlier confirmation.
            if user.id in preferences.user_confirms:
                preferences.user_confirms.remove(user.id)

            group_iteration.info_container = preferences
            session.add(group_iteration)
            session.commit()
            session.refresh(group_iteration)

            await self.broadcast("UPDATE: A vote has been cast.")

    async def confirm(
        self,
        user: User,
        group_session: GroupSessionDB,
        session: Session,
    ):
        """Confirm the user's vote and advance if everyone has confirmed."""
        async with self.lock:
            group = self._get_group(group_session, session)
            self._check_decision_maker(user, group)

            group_iteration = self._get_head_iteration(group_session, session)

            preferences = copy.deepcopy(
                            group_iteration.info_container
                        )
            

            if not isinstance(
                preferences,
                (
                    GDMSCOREBandsConsensusPreference,
                    GDMSCOREBandsDecisionPreference,
                ),
            ):
                raise ManagerError(
                    "Vote confirmation is only allowed during "
                    "consensus or decision."
                )

            if str(user.id) not in preferences.user_votes:
                raise ManagerError("User hasn't voted! Cannot confirm!")

            if user.id in preferences.user_confirms:
                raise ManagerError("User has already confirmed they want to move on!")

            preferences.user_confirms.append(user.id)
            preferences.user_confirms.sort()
            group_iteration.info_container = preferences

            session.add(group_iteration)
            session.commit()
            session.refresh(group_iteration)

            member_ids = sorted(self._get_member_ids(group))
            confirmed_ids = sorted(preferences.user_confirms)

            if confirmed_ids != member_ids:
                await self.broadcast(
                    "UPDATE: A vote has been confirmed."
                )
                return

            current_state_db, current_state = (
                self._get_iteration_state(
                    iteration=group_iteration,
                    session=session,
                )
            )
            if isinstance(
                preferences,
                GDMSCOREBandsDecisionPreference,
            ):
                if not isinstance(
                    current_state,
                    GDMSCOREBandsDecisionState,
                ):
                    raise ManagerError("Invalid decision state.")

                winner = majority_rule(preferences.user_votes)
                current_state.winner_index = winner
                current_state.winner_solution_variables = {
                    key: values[winner]
                    for key, values in (
                        current_state.solution_variables.items()
                    )
                }
                current_state.winner_solution_objectives = {
                    key: values[winner]
                    for key, values in (
                        current_state.solution_objectives.items()
                    )
                }

                session.add(current_state)
                session.commit()
                session.refresh(current_state)

                await self.broadcast(
                    "UPDATE: The final solution has been selected."
                )
                return

            if not isinstance(
                current_state,
                GDMSCOREBandsConsensusState,
            ):
                raise ManagerError("Invalid consensus state.")

            current_result = current_state.result
            votes = preferences.user_votes
            winners = consensus_rule(
                votes,
                current_state.config.minimum_votes,
            )

            relevant_ids = current_result.relevant_ids
            clustering = current_result.score_bands_result.clusters
            selected_solution_ids = [
                solution_id
                for solution_id, cluster_id in zip(
                    relevant_ids,
                    clustering,
                    strict=True,
                )
                if cluster_id in winners
            ]

            solution_number_threshold = 10
            discrete_repr = self.discrete_representation

            if len(selected_solution_ids) <= solution_number_threshold:
                objective_keys = list(
                    discrete_repr.objective_values
                )
                variable_keys = list(
                    discrete_repr.variable_values
                )

                objectives = pl.DataFrame(
                    discrete_repr.objective_values
                ).with_row_index(name="index_")
                variables = pl.DataFrame(
                    discrete_repr.variable_values
                ).with_row_index(name="index_")
                selected_indices = pl.DataFrame(
                    {"index_": selected_solution_ids}
                )

                objectives = selected_indices.join(
                    objectives,
                    how="left",
                    on="index_",
                ).select(objective_keys)
                variables = selected_indices.join(
                    variables,
                    how="left",
                    on="index_",
                ).select(variable_keys)

                next_state: SQLModel = GDMSCOREBandsDecisionState(
                    solution_variables=variables.to_dict(
                        as_series=False
                    ),
                    solution_objectives=objectives.to_dict(
                        as_series=False
                    ),
                    winner_index=None,
                    winner_solution_variables=None,
                    winner_solution_objectives=None,
                )
                next_preferences: BaseGroupInfoContainer = (
                    GDMSCOREBandsDecisionPreference(
                        user_votes={},
                        user_confirms=[],
                    )
                )
            else:
                objective_keys = list(
                    discrete_repr.objective_values
                )
                objectives = pl.DataFrame(
                    discrete_repr.objective_values
                ).select(objective_keys)

                next_config = copy.deepcopy(
                    current_state.config
                )
                next_config.from_iteration = (
                    current_result.iteration
                )

                result_history = self._get_result_history(
                    group_session=group_session,
                    session=session,
                )
                next_results = score_bands_gdm(
                    data=objectives,
                    config=next_config,
                    state=result_history,
                    votes=votes,
                )

                if not next_results:
                    raise ManagerError(
                        "SCORE Bands did not produce a new result."
                    )

                next_state = GDMSCOREBandsConsensusState(
                    config=copy.deepcopy(next_config),
                    result=copy.deepcopy(next_results[-1]),
                    selected_band_indices=list(winners),
                )
                next_preferences = (
                    GDMSCOREBandsConsensusPreference(
                        user_votes={},
                        user_confirms=[],
                    )
                )

            next_state_db = self._create_state(
                session=session,
                group_session=group_session,
                state=next_state,
                parent_state_id=current_state_db.id,
            )
            new_iteration = self._create_iteration(
                session=session,
                group_session=group_session,
                info_container=next_preferences,
                state_id=next_state_db.id,
                parent_iteration_id=group_iteration.id,
            )

            session.commit()
            session.refresh(new_iteration)
            session.refresh(group_session)

            await self.broadcast(
                "UPDATE: A new SCORE Bands phase has begun."
            )
            
    async def mark_learning_complete(
        self,
        user: User,
        group_session: GroupSessionDB,
        session: Session,
    ):
        """Mark a decision maker as done with the private learning phase."""
        async with self.lock:
            group = self._get_group(group_session, session)
            self._check_decision_maker(user, group)

            group_iteration = self._get_head_iteration(group_session, session)

            learning_preferences = copy.deepcopy(
                group_iteration.info_container
            )
            if not isinstance(
                learning_preferences,
                GDMSCOREBandsLearningPreference,
            ):
                raise ManagerError(
                    "Learning completion is only available "
                    "during the learning phase."
                )
            
            if user.id not in learning_preferences.completed_user_ids:
                learning_preferences.completed_user_ids.append(user.id)
                learning_preferences.completed_user_ids.sort()

            group_iteration.info_container = learning_preferences

            session.add(group_iteration)
            session.commit()
            session.refresh(group_iteration)

            await self.broadcast("UPDATE: A user finished the learning phase.")

    async def warn_learning_deadline(
        self,
        group_session: GroupSessionDB,
        session: Session,
        message: str | None = None,
    ):
        """Send a learning-phase deadline warning to all connected users."""
        async with self.lock:
            group_iteration = self._get_head_iteration(group_session, session)

            learning_preferences = copy.deepcopy(
                group_iteration.info_container
            )

            if not isinstance(
                learning_preferences,
                GDMSCOREBandsLearningPreference,
            ):
                raise ManagerError(
                    "Learning deadline warnings can only be sent "
                    "during the learning phase."
                )
            
            learning_preferences.learning_last_warning_at = datetime.now(timezone.utc).isoformat()
            learning_preferences.learning_last_warning_message = (
                message.strip()
                if message and message.strip()
                else "Learning phase is about to expire."
            )

            group_iteration.info_container = learning_preferences

            session.add(group_iteration)
            session.commit()
            session.refresh(group_iteration)

            await self.broadcast(f"NOTICE: {learning_preferences.last_warning_message}")

    async def advance_learning_phase(
        self,
        user: User,
        group_session: GroupSessionDB,
        session: Session,
    ):
        async with self.lock:
            group = self._get_group(
                group_session,
                session,
            )
            self._check_owner(user, group)

            learning_iteration = self._get_head_iteration(
                group_session,
                session,
            )

            learning_preferences = copy.deepcopy(
                learning_iteration.info_container
            )

            if not isinstance(
                learning_preferences,
                GDMSCOREBandsLearningPreference,
            ):
                raise ManagerError(
                    "The group is not in the learning phase."
                )

            required_users = sorted(
                self._get_member_ids(group)
            )

            completed_users = sorted(
                learning_preferences.completed_user_ids
            )

            if completed_users != required_users:
                raise ManagerError(
                    "Every decision maker must complete learning."
                )

            learning_state_db, learning_state = (
                self._get_iteration_state(
                    iteration=learning_iteration,
                    session=session,
                )
            )

            if not isinstance(
                learning_state,
                GDMSCOREBandsLearningState,
            ):
                raise ManagerError(
                    "Invalid learning state."
                )

            consensus_state = GDMSCOREBandsConsensusState(
                config=copy.deepcopy(
                    learning_state.config
                ),
                result=copy.deepcopy(
                    learning_state.result
                ),
                selected_band_indices=[],
            )

            consensus_state_db = self._create_state(
                session=session,
                group_session=group_session,
                state=consensus_state,
                parent_state_id=learning_state_db.id,
            )

            consensus_preferences = (
                GDMSCOREBandsConsensusPreference(
                    user_votes={},
                    user_confirms=[],
                )
            )

            consensus_iteration = self._create_iteration(
                session=session,
                group_session=group_session,
                info_container=consensus_preferences,
                state_id=consensus_state_db.id,
                parent_iteration_id=learning_iteration.id,
            )

            session.commit()
            session.refresh(consensus_iteration)
            session.refresh(group_session)

            await self.broadcast(
                "UPDATE: Consensus phase has started."
            )
            
    async def revert(
        self,
        user: User,
        group_session: GroupSessionDB,
        session: Session,
        group_iteration_id: int,
    ) -> None:
        """Revert to a different iteration."""
        async with self.lock:
            group = self._get_group(group_session, session)
            self._check_owner(user, group)
            current_head = self._get_head_iteration(
                group_session,
                session,
            )

            target_iteration = session.exec(
                select(GroupIteration).where(
                    GroupIteration.id == group_iteration_id,
                    GroupIteration.session_id == group_session.id,
                )
            ).first()

            if target_iteration is None:
                raise ManagerError(f"No group iteration with ID {group_iteration_id} found.")

            if target_iteration.id == current_head.id:
                raise ManagerError(
                    "The selected iteration is already the current iteration."
                )

            target_state_db, target_state = (
                self._get_iteration_state(
                    iteration=target_iteration,
                    session=session,
                )
            )

            if not isinstance(
                target_state,
                (
                    GDMSCOREBandsLearningState,
                    GDMSCOREBandsConsensusState,
                ),
            ):
                raise ManagerError(
                    "Only learning or consensus classifications "
                    "can be restored."
                )

            result_history = self._get_result_history(
                group_session=group_session,
                session=session,
            )
            if not result_history:
                raise ManagerError(
                    "No SCORE Bands result history exists."
                )

            latest_result = max(
                result_history,
                key=lambda item: item.iteration,
            )
            restored_result = copy.deepcopy(
                target_state.result
            )
            restored_result.previous_iteration = (
                latest_result.iteration
            )
            restored_result.iteration = (
                latest_result.iteration + 1
            )

            restored_state = GDMSCOREBandsConsensusState(
                config=copy.deepcopy(target_state.config),
                result=restored_result,
                selected_band_indices=[],
            )
            restored_state_db = self._create_state(
                session=session,
                group_session=group_session,
                state=restored_state,
                parent_state_id=current_head.state_id,
            )
            restored_preferences = (
                GDMSCOREBandsConsensusPreference(
                    user_votes={},
                    user_confirms=[],
                )
            )
            restored_iteration = self._create_iteration(
                session=session,
                group_session=group_session,
                info_container=restored_preferences,
                state_id=restored_state_db.id,
                parent_iteration_id=current_head.id,
            )

            session.commit()
            session.refresh(restored_iteration)
            session.refresh(group_session)

            await self.broadcast("UPDATE: Iteration reverted.")
            
    async def configure(
        self,
        group_session: GroupSessionDB,
        config: SCOREBandsGDMConfig,
        session: Session,
    )-> None:
        """Configure the SCORE Bands process."""
        async with self.lock:
            group_iteration = self._get_head_iteration(group_session, session)
            if not isinstance(
                group_iteration.info_container,
                GDMSCOREBandsConsensusPreference,
            ):
                raise ManagerError("Cannot reconfigure while the group is still in the learning phase!")

            current_state_db, current_state = (
                self._get_iteration_state(
                    iteration=group_iteration,
                    session=session,
                )
            )

            if not isinstance(
                current_state,
                GDMSCOREBandsConsensusState,
            ):
                raise ManagerError("Invalid consensus state.")

            current_result = current_state.result
            relevant_indices = current_result.relevant_ids
            iteration_number = current_result.iteration

            index_frame = pl.DataFrame({"index": relevant_indices})

            discrete_objectives = (
                self.discrete_representation.objective_values
            )
            objective_keys = list(discrete_objectives)

            objs_df = pl.DataFrame(discrete_objectives).with_row_index(name="index")

            objectives = index_frame.join(
                objs_df,
                how="left",
                on="index",
            ).select(objective_keys)

            score_bands_result = score_json(
                data=objectives,
                options=config.score_bands_config,
            )

            next_result = SCOREBandsGDMResult(
                score_bands_result=score_bands_result,
                relevant_ids=relevant_indices,
                iteration=iteration_number + 1,
                previous_iteration=iteration_number,
            )

            next_state = GDMSCOREBandsConsensusState(
                config=copy.deepcopy(config),
                result=next_result,
                selected_band_indices=[],
            )
            next_state_db = self._create_state(
                session=session,
                group_session=group_session,
                state=next_state,
                parent_state_id=current_state_db.id,
            )
            next_preferences = (
                GDMSCOREBandsConsensusPreference(
                    user_votes={},
                    user_confirms=[],
                )
            )

            new_iteration = self._create_iteration(
                session=session,
                group_session=group_session,
                info_container=next_preferences,
                state_id=next_state_db.id,
                parent_iteration_id=group_session.id,
            )
            session.commit()
            session.refresh(new_iteration)
            session.refresh(group_session)

            await self.broadcast("UPDATE: Reconfigured SCORE Bands.")