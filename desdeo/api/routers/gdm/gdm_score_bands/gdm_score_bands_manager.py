"""GDM Score Bands manager implementation."""

import copy
from datetime import datetime, timezone

from desdeo.api.models.gdm.gdm_aggregate import GroupSessionDB
import polars as pl
from sqlmodel import Session, select

from desdeo.api.models import (
    GDMSCOREBandFinalSelection,
    GDMSCOREBandInformation,
    Group,
    GroupIteration,
    ProblemDB,
    User,
)
from desdeo.api.routers.gdm.gdm_base import GroupManager, ManagerError
from desdeo.gdm.score_bands import SCOREBandsGDMConfig, SCOREBandsGDMResult, score_bands_gdm
from desdeo.gdm.voting_rules import consensus_rule, majority_rule
from desdeo.tools.score_bands import score_json


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
        return [user.id for user in group.users]

    def _check_user_in_group(self, user: User, group: Group):
        member_ids = self._get_member_ids(group)

        if user.id not in member_ids and user.id != group.owner_id:
            raise ManagerError(
                detail=f"User with ID {user.id} is not part of group with ID {group.id}",
            )

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
            self._check_user_in_group(user, group)

            group_iteration = self._get_head_iteration(group_session, session)

            info_container = copy.deepcopy(group_iteration.info_container)

            if info_container.method != "gdm-score-bands" or info_container.phase != "consensus":
                raise ManagerError("Voting is only allowed during the consensus phase.")

            info_container.user_votes[str(user.id)] = voted_index
            group_iteration.info_container = info_container

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
            self._check_user_in_group(user, group)

            group_iteration = self._get_head_iteration(group_session, session)

            info_container = copy.deepcopy(group_iteration.info_container)

            if info_container.method not in ("gdm-score-bands", "gdm-score-bands-final"):
                raise ManagerError("Vote confirmation is only allowed during SCORE Bands phases.")

            if info_container.method == "gdm-score-bands" and info_container.phase != "consensus":
                raise ManagerError("Vote confirmation is only allowed during the consensus phase.")

            if str(user.id) not in info_container.user_votes:
                raise ManagerError("User hasn't voted! Cannot confirm!")

            if user.id in info_container.user_confirms:
                raise ManagerError("User has already confirmed they want to move on!")

            info_container.user_confirms.append(user.id)
            group_iteration.info_container = info_container

            session.add(group_iteration)
            session.commit()
            session.refresh(group_iteration)

            member_ids = self._get_member_ids(group)

            for uid in member_ids:
                if uid not in info_container.user_confirms:
                    return

            if info_container.method == "gdm-score-bands":
                iterations = session.exec(
                    select(GroupIteration).where(
                        GroupIteration.session_id == group_session.id
                    ).order_by(GroupIteration.id)
                ).all()

                state: list[SCOREBandsGDMResult] = [
                    iteration.info_container.score_bands_result
                    for iteration in iterations
                    if iteration.info_container.method == "gdm-score-bands"
                ]

                score_bands_config = SCOREBandsGDMConfig(
                    score_bands_config=info_container.score_bands_config.score_bands_config,
                    from_iteration=state[-1].iteration,
                )

                discrete_repr = self.discrete_representation

                votes = group_iteration.info_container.user_votes
                winners = consensus_rule(votes, score_bands_config.minimum_votes)
                relevant_ids = state[-1].relevant_ids
                clustering = state[-1].score_bands_result.clusters

                solution_number_threshold = 10

                if (
                    len([x[0] for x in zip(relevant_ids, clustering, strict=True) if x[1] in winners])
                    <= solution_number_threshold
                ):
                    obj_keys = list(discrete_repr.objective_values)
                    var_keys = list(discrete_repr.variable_values)

                    objs = pl.DataFrame(discrete_repr.objective_values).with_row_index(name="index_")
                    varis = pl.DataFrame(discrete_repr.variable_values).with_row_index(name="index_")
                    indices = pl.DataFrame({"index_": relevant_ids, "cluster_": clustering}).filter(
                        pl.col("cluster_").is_in(winners)
                    )

                    objs = indices.join(
                        other=objs,
                        how="left",
                        left_on="index_",
                        right_on="index_",
                    ).select(obj_keys)

                    varis = indices.join(
                        other=varis,
                        how="left",
                        left_on="index_",
                        right_on="index_",
                    ).select(var_keys)

                    info_container = GDMSCOREBandFinalSelection(
                        user_votes={},
                        user_confirms=[],
                        solution_variables=varis.to_dict(),
                        solution_objectives=objs.to_dict(),
                        winner_solution_variables=None,
                        winner_solution_objectives=None,
                    )

                else:
                    discrete_repr_objectives = discrete_repr.objective_values
                    objective_keys = list(discrete_repr_objectives)

                    objs = pl.DataFrame(discrete_repr_objectives).with_row_index()
                    objs = objs.select(objective_keys)

                    result: list[SCOREBandsGDMResult] = score_bands_gdm(
                        data=objs,
                        config=score_bands_config,
                        state=state,
                        votes=votes,
                    )

                    info_container = GDMSCOREBandInformation(
                        user_votes={},
                        user_confirms=[],
                        score_bands_config=score_bands_config,
                        score_bands_result=result[-1],
                    )

                new_iteration = GroupIteration(
                    session_id=group_session.id,
                    info_container=info_container,
                    notified={},
                    state_id=None,
                    parent_id=group_session.head_iteration_id,
                )

                session.add(new_iteration)
                session.commit()
                session.refresh(new_iteration)

                group_session.head_iteration_id = new_iteration.id
                session.add(group_session)
                session.commit()
                session.refresh(group_session)

                await self.broadcast("UPDATE: A new iteration has begun.")

            elif info_container.method == "gdm-score-bands-final":
                winner = majority_rule(info_container.user_votes)

                varis = info_container.solution_variables
                vari_keys = list(varis)

                objs = info_container.solution_objectives
                obj_keys = list(objs)

                vari_d = {}
                for key in vari_keys:
                    vari_d[key] = varis[key][winner]

                obj_d = {}
                for key in obj_keys:
                    obj_d[key] = objs[key][winner]

                info_container.winner_solution_variables = vari_d
                info_container.winner_solution_objectives = obj_d

                group_iteration.info_container = info_container

                session.add(group_iteration)
                session.commit()

    async def mark_learning_complete(
        self,
        user: User,
        group_session: GroupSessionDB,
        session: Session,
    ):
        """Mark a decision maker as done with the private learning phase."""
        async with self.lock:
            group = self._get_group(group_session, session)
            self._check_user_in_group(user, group)

            group_iteration = self._get_head_iteration(group_session, session)

            info_container = copy.deepcopy(group_iteration.info_container)

            if info_container.method != "gdm-score-bands":
                raise ManagerError("Learning completion is unavailable in the decision phase.")

            if info_container.phase != "learning":
                raise ManagerError("Learning phase has already ended.")

            if user.id not in info_container.learning_completed_user_ids:
                info_container.learning_completed_user_ids.append(user.id)
                info_container.learning_completed_user_ids.sort()

            group_iteration.info_container = info_container

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

            info_container = copy.deepcopy(group_iteration.info_container)

            if info_container.method != "gdm-score-bands" or info_container.phase != "learning":
                raise ManagerError("Learning deadline warnings can only be sent during the learning phase.")

            info_container.learning_last_warning_at = datetime.now(timezone.utc).isoformat()
            info_container.learning_last_warning_message = (
                message.strip()
                if message and message.strip()
                else "Learning phase is about to expire."
            )

            group_iteration.info_container = info_container

            session.add(group_iteration)
            session.commit()
            session.refresh(group_iteration)

            await self.broadcast(f"NOTICE: {info_container.learning_last_warning_message}")

    async def advance_learning_phase(
        self,
        group_session: GroupSessionDB,
        session: Session,
    ):
        """Move the group from private learning to shared consensus once everyone is ready."""
        async with self.lock:
            group = self._get_group(group_session, session)
            group_iteration = self._get_head_iteration(group_session, session)

            info_container = copy.deepcopy(group_iteration.info_container)

            if info_container.method != "gdm-score-bands":
                raise ManagerError("Learning phase advancement is unavailable in the decision phase.")

            if info_container.phase != "learning":
                raise ManagerError("Group is no longer in the learning phase.")

            required_users = sorted(self._get_member_ids(group))
            completed_users = sorted(info_container.learning_completed_user_ids)

            if completed_users != required_users:
                raise ManagerError("Every decision maker must finish exploring before consensus can begin.")

            info_container.phase = "consensus"
            info_container.user_votes = {}
            info_container.user_confirms = []

            group_iteration.info_container = info_container

            session.add(group_iteration)
            session.commit()
            session.refresh(group_iteration)

            await self.broadcast("UPDATE: Consensus phase has started.")

    async def revert(
        self,
        user: User,
        group_session: GroupSessionDB,
        session: Session,
        group_iteration_id: int,
    ):
        """Revert to a different iteration."""
        async with self.lock:
            group = self._get_group(group_session, session)
            self._check_user_in_group(user, group)



            self._get_head_iteration(group_session, session)

            iterations = session.exec(
                select(GroupIteration)
                .where(GroupIteration.session_id == group_session.id)
                .order_by(GroupIteration.id)
            ).all()

            target_group_iteration = session.exec(
                select(GroupIteration).where(
                    GroupIteration.id == group_iteration_id,
                    GroupIteration.session_id == group_session.id,
                )
            ).first()

            if target_group_iteration is None:
                raise ManagerError(f"No group iteration with ID {group_iteration_id} found.")

            if target_group_iteration.info_container.method == "gdm-score-bands-final":
                raise ManagerError("We can only revert to a score bands iteration.")
            
            if target_group_iteration.id == group_session.head_iteration_id:
                raise ManagerError(
                    "The selected iteration is already the current iteration."
                )

            state: list[SCOREBandsGDMResult] = [
                iteration.info_container.score_bands_result
                for iteration in iterations
                if iteration.info_container.method == "gdm-score-bands"
            ]

            if not state:
                raise ManagerError(
                    "No SCORE Bands iterations exist in this group session."
                )

            prev_id = state[-1].iteration

            result = copy.deepcopy(
                target_group_iteration
                .info_container
                .score_bands_result
            )

            score_bands_config = copy.deepcopy(
                target_group_iteration.info_container.score_bands_config
            )

            result.previous_iteration = prev_id
            result.iteration = prev_id + 1

            info_container = GDMSCOREBandInformation(
                user_votes={},
                user_confirms=[],
                phase="consensus",
                learning_completed_user_ids=[],
                score_bands_config=score_bands_config,
                score_bands_result=result,
            )

            new_iteration = GroupIteration(
                session_id=group_session.id,
                info_container=info_container,
                notified={},
                state_id=None,
                parent_id=group_session.head_iteration_id,
            )

            session.add(new_iteration)
            session.flush()

            group_session.head_iteration_id = new_iteration.id
            session.add(group_session)

            session.commit()
            session.refresh(new_iteration)
            session.refresh(group_session)

            await self.broadcast("UPDATE: Iteration reverted.")

    async def configure(
        self,
        group_session: GroupSessionDB,
        config: SCOREBandsGDMConfig,
        session: Session,
    ):
        """Configure the SCORE Bands process."""
        async with self.lock:
            group_iteration = self._get_head_iteration(group_session, session)

            if group_iteration.info_container.method == "gdm-score-bands-final":
                raise ManagerError("Cannot reconfigure in a non SCORE Bands phase!")

            if group_iteration.info_container.phase != "consensus":
                raise ManagerError("Cannot reconfigure while the group is still in the learning phase!")

            iterations: list[GroupIteration] = session.exec(
                select(GroupIteration).where(
                    GroupIteration.session_id == group_session.id
                )
                .order_by(GroupIteration.id)
            ).all()

            state: list[SCOREBandsGDMResult] = [
                iteration.info_container.score_bands_result
                for iteration in iterations
                if iteration.info_container.method == "gdm-score-bands"
            ]

            relevant_indices = state[-1].relevant_ids
            iteration_number = state[-1].iteration

            index_df = pl.DataFrame({"index": relevant_indices})

            discrete_repr = self.discrete_representation.objective_values
            objective_keys = list(discrete_repr)

            objs_df = pl.DataFrame(discrete_repr).with_row_index()

            objs_df = index_df.join(
                how="left",
                left_on="index",
                right_on="index",
                other=objs_df,
            )

            objs_df = objs_df.select(objective_keys)

            score_bands_result = score_json(
                data=objs_df,
                options=config.score_bands_config,
            )

            score_bands_gdm_result = SCOREBandsGDMResult(
                score_bands_result=score_bands_result,
                relevant_ids=relevant_indices,
                iteration=iteration_number + 1,
                previous_iteration=iteration_number,
            )

            info_container = GDMSCOREBandInformation(
                user_votes={},
                user_confirms=[],
                phase="consensus",
                learning_completed_user_ids=[],
                score_bands_config=config,
                score_bands_result=score_bands_gdm_result,
            )

            new_iteration = GroupIteration(
                session_id=group_session.id,
                info_container=info_container,
                notified={},
                state_id=None,
                parent_id=group_session.head_iteration_id,
            )

            session.add(new_iteration)
            session.commit()
            session.refresh(new_iteration)

            group_session.head_iteration_id = new_iteration.id
            session.add(group_session)
            session.commit()
            session.refresh(group_session)

            await self.broadcast("UPDATE: Reconfigured SCORE Bands.")