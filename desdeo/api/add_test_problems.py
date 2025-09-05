"""Script to add test problems to an existing database."""

from sqlmodel import Session, select

from desdeo.api.config import ServerDebugConfig
from desdeo.api.db import engine
from desdeo.api.models import ProblemDB, User
from desdeo.problem.testproblems import dtlz2, river_pollution_problem, simple_knapsack


def add_test_problems(username: str = ServerDebugConfig.test_user_analyst_name):
    """Add test problems to the database for a specific user.

    Args:
        username: The username to associate the problems with.
                 Defaults to test analyst user.
    """
    problems = [dtlz2(10, 3), simple_knapsack(), river_pollution_problem()]

    with Session(engine) as session:
        # Find the user
        user = session.exec(select(User).where(User.username == username)).first()

        if not user:
            print(f"User {username} not found in the database.")
            return

        # Check which problems already exist
        for problem in problems:
            existing_problem = session.exec(
                select(ProblemDB).where(
                    ProblemDB.user_id == user.id, ProblemDB.name == problem.name
                )
            ).first()

            if existing_problem:
                print(f"Problem '{problem.name}' already exists for user {username}")
                continue

            # Add new problem
            problem_db = ProblemDB.from_problem(problem, user)
            session.add(problem_db)
            print(f"Added problem '{problem.name}' for user {username}")

        session.commit()


if __name__ == "__main__":
    add_test_problems()
    print("Done!")
