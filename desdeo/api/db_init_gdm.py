"""Initialize the development database."""

import warnings

from sqlalchemy_utils import database_exists
from sqlmodel import Session, SQLModel

from desdeo.api.config import SettingsConfig
from desdeo.api.db import engine
from desdeo.api.models import ProblemDB, User, UserRole
from desdeo.api.models.gdm.gdm_aggregate import (
    Group,
    GroupIteration,
    GroupSessionDB,
)
from desdeo.api.models.gdm.gnimbus import OptimizationPreference
from desdeo.api.routers.user_authentication import get_password_hash
from desdeo.problem.testproblems import river_pollution_problem_discrete


problems = [
    river_pollution_problem_discrete(
        five_objective_variant=False,
    )
]

num_analysts = 1
num_dms = 2

usernames_analyst = [
    f"analyst{i + 1}" for i in range(num_analysts)
]
usernames_dm = [
    f"dm{i + 1}" for i in range(num_dms)
]


if __name__ == "__main__":
    if SettingsConfig.debug:
        print("Creating database tables.")

        if not database_exists(engine.url):
            SQLModel.metadata.create_all(engine)
        else:
            warnings.warn(
                "Database already exists. Clearing it.",
                stacklevel=1,
            )
            SQLModel.metadata.reflect(bind=engine)
            SQLModel.metadata.drop_all(bind=engine)
            SQLModel.metadata.create_all(engine)

        print("Database tables created.")

        with Session(engine) as session:
            users: list[User] = []

            for username in usernames_analyst:
                analyst = User(
                    username=username,
                    password_hash=get_password_hash("12345"),
                    role=UserRole.analyst,
                    group="test",
                )
                session.add(analyst)
                users.append(analyst)

            for username in usernames_dm:
                dm = User(
                    username=username,
                    password_hash=get_password_hash("12345"),
                    role=UserRole.dm,
                    group="test",
                )
                session.add(dm)
                users.append(dm)

            session.commit()

            for user in users:
                session.refresh(user)

            owner = users[0]
            dm1 = users[1]
            dm2 = users[2]

            problem_db = ProblemDB.from_problem(
                problems[0],
                owner,
            )
            session.add(problem_db)
            session.commit()
            session.refresh(problem_db)

            group = Group(
                name="tingalinga",
                owner_id=owner.id,
                users=[dm1, dm2],
            )

            session.add(group)
            session.commit()
            session.refresh(group)

            group_session = GroupSessionDB(
                group_id=group.id,
                problem_id=problem_db.id,
                method="gnimbus",
                head_iteration_id=None,
            )

            session.add(group_session)
            session.commit()
            session.refresh(group_session)

            initial_iteration = GroupIteration(
                session_id=group_session.id,
                info_container=OptimizationPreference(
                    set_preferences={},
                ),
                notified={},
                state_id=None,
                parent_id=None,
            )

            session.add(initial_iteration)
            session.commit()
            session.refresh(initial_iteration)

            group_session.head_iteration_id = initial_iteration.id
            session.add(group_session)
            session.commit()
            session.refresh(group_session)

            print(
                f"Created group {group.id}, "
                f"group session {group_session.id}, "
                f"problem {problem_db.id}."
            )

    else:
        pass