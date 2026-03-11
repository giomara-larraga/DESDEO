# Utils to extract data from the database and create datasets with the experiment results
import warnings
from sqlmodel import Session, SQLModel, select
from desdeo.api.config import ServerConfig, SettingsConfig
from desdeo.api.models import ProblemDB, User, UserRole
from desdeo.api.db import engine
from sqlalchemy_utils import database_exists
from desdeo.api.models.generic_states import StateKind


from desdeo.api.models.generic_states import (
    StateDB,
    State,
    NIMBUSInitializationState,
    NIMBUSClassificationState,
    NIMBUSFinalState,
    NIMBUSSaveState,
    IntermediateSolutionState,
)


def ensure_database_exists():
    # For Postgres/MySQL: creates the database itself if missing.
    # For SQLite: not needed, but harmless.
    if not database_exists(engine.url):
        warnings.warn(
            f"Database does not exist at {engine.url}. Attempting to create it.",
            stacklevel=1,
        )
        return False
    return True


def fetch_problem_and_user(problem_id: int, session: Session) -> tuple[ProblemDB, User]:
    """Fetches the problem and user associated with a given problem ID.

    Args:
        problem_id (int): The ID of the problem to fetch.
        session (Session): The database session to use for fetching.

    Returns:
        tuple[ProblemDB, User]: A tuple containing the fetched ProblemDB and User objects.

    Raises:
        ValueError: If the problem with the given ID does not exist.
    """
    problem = session.get(ProblemDB, problem_id)
    if problem is None:
        raise ValueError(f"Problem with id {problem_id} does not exist.")

    user = session.get(User, problem.user_id)
    if user is None:
        raise ValueError(f"User with id {problem.user_id} does not exist.")

    return problem, user


def fetch_problems_from_state_table(session: Session) -> list[ProblemDB]:
    """Fetches all problems from the state table.

    Args:
        session (Session): The database session to use for fetching.
    Returns:
        list[ProblemDB]: A list of ProblemDB objects fetched from the state table.
    """
    statement = select(ProblemDB).join(StateDB, ProblemDB.id == StateDB.problem_id)
    problems = session.exec(statement).unique().all()
    return problems


# Fetch all states from a problem Id and return a list of states for that problem Id
def fetch_states_for_problem(problem_id: int, session: Session) -> list[StateDB]:
    """Fetches all states associated with a given problem ID.

    Args:
        problem_id (int): The ID of the problem to fetch states for.
        session (Session): The database session to use for fetching.

    Returns:
        list[StateDB]: A list of StateDB objects associated with the given problem ID.
    """
    statement = select(StateDB).where(StateDB.problem_id == problem_id)
    states = session.exec(statement).all()

    # From all the states, get the state_id and consult the state table to get the method and kind
    for state in states:
        statement = select(State).where(State.id == state.state_id)
        state_info = session.exec(statement).first()
        # Get the user info for the problem
        problem, user = fetch_problem_and_user(problem_id, session)

        # print(
        #    f"User: {user.username}, Problem ID: {problem.id}, State ID: {state.state_id}, Time stamp: {state.date_time}, Method: {state_info.method}, Kind: {state_info.kind}"
        # )

        # Depending on the kind, extract the relevant information from the nimbusinitializationstate, nimbusclassificationstate, nimbusintermediatestate, nimbusfinalstate tables and print it out
        if state_info.kind == StateKind.NIMBUS_INIT:
            print("NIMBUS Initialization State")
            # Consulte the nimbusinitializationstate table to get the relevant information
            statement = select(NIMBUSInitializationState).where(
                NIMBUSInitializationState.id == state.state_id
            )
            nimbus_init_state = session.exec(statement).first()

            print(
                f"Initialization State - Problem ID: {problem.id}, Time stamp: {state.date_time}, Method: {state_info.method}, Kind: {state_info.kind}, Initial Solution: {nimbus_init_state.solver_results}"
            )

    return states


if __name__ == "__main__":
    if not ensure_database_exists():
        print(
            "Database missing. Please run db_init_xnimbus.py to create and seed the database before running this script."
        )
    else:
        with Session(engine) as session:
            active_users = []
            problems = fetch_problems_from_state_table(session)

            for problem in problems:
                states = fetch_states_for_problem(problem.id, session)
