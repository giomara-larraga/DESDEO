"""This module initializes the database."""

import warnings

import numpy as np
from sqlalchemy_utils import database_exists
from sqlmodel import Session, SQLModel

from desdeo.api.config import SettingsConfig
from desdeo.api.db import engine
from desdeo.api.models import (
    ProblemDB,
    User,
    UserRole,
    
)
from desdeo.api.models.gdm.gdm_aggregate import (
    Group,
    GroupSessionDB,
    GroupIteration,
)
from desdeo.api.routers.user_authentication import get_password_hash
from desdeo.problem.testproblems import river_pollution_problem_discrete
from desdeo.api.models.gdm.gnimbus import OptimizationPreference


problems = [river_pollution_problem_discrete(five_objective_variant=False)]

num_analysts = 1
num_dms = 2

usernames_analyst = [f"analyst{i + 1}" for i in range(num_analysts)]
usernames_dm = [f"dm{i + 1}" for i in range(num_dms)]

user_owner = User(
    id="1",
    username=usernames_analyst[0],
    password_hash=get_password_hash("12345"),
    role=UserRole.analyst,
    group="test",
)

id_user = 1
if __name__ == "__main__":
    if SettingsConfig.debug:
        # debug stuff

        print("Creating database tables.")
        if not database_exists(engine.url):
            SQLModel.metadata.create_all(engine)
        else:
            warnings.warn("Database already exists. Clearing it.", stacklevel=1)
            # Drop all tables
            SQLModel.metadata.reflect(bind=engine)
            SQLModel.metadata.drop_all(bind=engine)
            SQLModel.metadata.create_all(engine)
        print("Database tables created.")

        with Session(engine) as session:
            for user in usernames_analyst:
                user_analyst = User(
                    id=str(id_user),
                    username=user,
                    password_hash=get_password_hash(
                        "12345"
                    ),
                    role=UserRole.analyst,
                    group="test",
                    group_ids=[1],
                )
                session.add(user_analyst)
                session.commit()
                session.refresh(user_analyst)
                id_user += 1

            for user in usernames_dm:
                user_dm = User(
                    id=str(id_user),
                    username=user,
                    password_hash=get_password_hash(
                        "12345"
                    ),
                    role=UserRole.dm,
                    group="test",
                    group_ids=[1],
                )
                session.add(user_dm)
                session.commit()
                session.refresh(user_dm)
                id_user += 1

            rng = np.random.default_rng(seed=42)

            for problem in problems:
                #Add the problem to the analyst1
                problem_db = ProblemDB.from_problem(problem, user_owner)
                session.add(problem_db)
                session.commit()
                session.refresh(problem_db)


            owner = session.get(User, 1)
            dm1 = session.get(User, 2)
            dm2 = session.get(User, 3)

            # Create a group for GDM testing
            group_name = "tingalinga"
            group = Group(
                name=group_name,
                owner_id=owner.id,
                user_ids=[dm1.id, dm2.id],
                problem_id=problem_db.id,
            )

            group.model_rebuild()
            
            
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

            # Optional: only if you want pre-initialized GNIMBUS session.
            # Otherwise let /gnimbus/initialize create the first iterations.
            initial_iteration = GroupIteration(
                session_id=group_session.id,
                info_container=OptimizationPreference(set_preferences={}),
                notified={},
                state_id=None,
                parent_id=None,
            )
            session.add(initial_iteration)
            session.commit()
            session.refresh(initial_iteration)

            group_session.head_iteration_id = initial_iteration.id
            session.add(group_session)


            session.close()

    else:
        # deployment stuff
        pass
