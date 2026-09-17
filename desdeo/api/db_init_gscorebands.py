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
from desdeo.problem.testproblems import dmitry_forest_problem_disc

problems = [dmitry_forest_problem_disc()]

predefined_experiment = False
predefined_names = ["jpajamas", "kmiettinen", "bsaini", "glarraga"]


if not predefined_experiment:
    num_analysts = 1
    num_dms = 2
    usernames_analyst = [f"analyst{i + 1}" for i in range(num_analysts)]
    usernames_dm = [f"dm{i + 1}" for i in range(num_dms)]
else:
    num_analysts = 1
    num_dms = len(predefined_names) - num_analysts
    usernames_analyst = predefined_names[:num_analysts]
    usernames_dm = predefined_names[num_analysts : num_analysts + num_dms]


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
                    password_hash=get_password_hash("desdeo123"),
                    role=UserRole.analyst,
                    group="test",
                )
                session.add(analyst)
                users.append(analyst)

            for username in usernames_dm:
                dm = User(
                    username=username,
                    password_hash=get_password_hash("desdeo123"),
                    role=UserRole.dm,
                    group="test",
                )
                session.add(dm)
                users.append(dm)

            session.commit()

            for user in users:
                session.refresh(user)

            # so far the group can have only one owner, so we will use the first user as the owner and the rest as dms
            owner = users[0]
            dms = users[1:]

            problem_db = ProblemDB.from_problem(
                problems[0],
                owner,
            )
            session.add(problem_db)
            session.commit()
            session.refresh(problem_db)

            group = Group(
                name="powerpuff girls",
                owner_id=owner.id,
                users=dms,
            )

            session.add(group)
            session.commit()
            session.refresh(group)

            group_session = GroupSessionDB(
                group_id=group.id,
                problem_id=problem_db.id,
                method="gdm-score-bands",
                head_iteration_id=None,
            )

            session.add(group_session)
            session.commit()
            session.refresh(group_session)

            print(
                f"Created SCORE Bands group session "
                f"{group_session.id} for group {group.id}"
            )

            # Create a csv with usernames and passwords for the users
            with open("users.csv", "w") as f:
                f.write("username,password\n")
                for user in users:
                    f.write(f"{user.username},desdeo123\n")

            print("Created users.csv with usernames and passwords.")

    else:
        pass
