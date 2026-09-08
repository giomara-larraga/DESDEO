"""Production database initialisation script.

Run once as a Kubernetes Job after the first deployment (or after a full
database wipe). It is intentionally idempotent: running it multiple times
against the same database is safe.

What it does
------------
1. Creates all SQLModel tables if they do not already exist.
   (Uses create_all which is a no-op for tables that are present.)
2. Seeds an initial analyst user whose credentials come from env vars.
   If the user already exists the step is skipped.

Environment variables required
-------------------------------
DATABASE_URL          PostgreSQL DSN, e.g.
                      postgresql://desdeo:<pw>@desdeo-postgres:5432/desdeo
DESDEO_ADMIN_USERNAME Username for the seeded analyst account.
DESDEO_ADMIN_PASSWORD Password for the seeded analyst account.

Optional
--------
DESDEO_ADMIN_GROUP    Group name for the seeded user (default: "admin").
"""

import os
import sys

from sqlmodel import Session, SQLModel, select

# Import the engine after DATABASE_URL is in the environment so the config
# module picks it up correctly.
from desdeo.api.db import engine
from desdeo.api.models import User, UserRole
from desdeo.api.models.problem import ProblemDB
from desdeo.api.routers.user_authentication import get_password_hash
from desdeo.problem.testproblems import dmitry_forest_problem_disc
from desdeo.api.models.gdm.gdm_aggregate import (
    Group,
    GroupSessionDB,
)

problems = [dmitry_forest_problem_disc()]

num_analysts = 1
num_dms = 2

usernames_analyst = [f"analyst{i + 1}" for i in range(num_analysts)]
usernames_dm = [f"dm{i + 1}" for i in range(num_dms)]


def create_tables() -> None:
    print(
        "[db-init] Creating database tables (create_all is a no-op for existing tables)..."
    )
    SQLModel.metadata.create_all(engine)
    print("[db-init] Tables ready.")


def seed_admin_user() -> None:
    # in this context, the admin will be the moderator
    username = os.environ.get("DESDEO_ADMIN_USERNAME")
    password = os.environ.get("DESDEO_ADMIN_PASSWORD")
    group = os.environ.get("DESDEO_ADMIN_GROUP", "admin")
    password_dm = "gdmdesdeo"  # default password for DMs

    if not username or not password:
        print(
            "[db-init] WARNING: DESDEO_ADMIN_USERNAME or DESDEO_ADMIN_PASSWORD not set — skipping user seed."
        )
        return

    with Session(engine) as session:
        users: list[User] = []
        existing = session.exec(select(User).where(User.username == username)).first()

        if existing:
            print(f"[db-init] User '{username}' already exists — skipping.")
            return

        user = User(
            username=username,
            password_hash=get_password_hash(password),
            role=UserRole.analyst,
            group=group,
        )
        session.add(user)
        users.append(user)
        print(f"[db-init] Created user '{username}' (role=analyst, group={group}).")

        for username in usernames_dm:
            dm = User(
                username=username,
                password_hash=get_password_hash(password_dm),
                role=UserRole.dm,
                group=group,
            )
            session.add(dm)
            users.append(dm)
            print(f"[db-init] Created user '{username}' (role=dm, group={group}).")

        session.commit()

        for user in users:
            session.refresh(user)

        problem_db = ProblemDB.from_problem(
            problems[0],
            users[0],
        )
        session.add(problem_db)
        session.commit()
        session.refresh(problem_db)

        dms = users[1 : num_analysts + num_dms + 1]

        group = Group(
            name="forest_group",
            owner_id=users[0].id,
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
            f"[db-init] Created SCORE Bands group session "
            f"{group_session.id} for group {group.id}"
        )


def main() -> None:
    database_url = "postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    if not database_url:
        print("[db-init] ERROR: DATABASE_URL is not set.", file=sys.stderr)
        sys.exit(1)

    print(
        f"[db-init] Using database: {database_url.split('@')[-1]}"
    )  # hide credentials
    create_tables()
    seed_admin_user()
    print("[db-init] Done.")


if __name__ == "__main__":
    main()
