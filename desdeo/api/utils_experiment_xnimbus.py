# Utils to extract data from the database and create datasets with the experiment results
import warnings
import json
import csv
from pathlib import Path
from typing import Any
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


def _to_serializable(value: Any) -> Any:
    """Converts SQLModel/Pydantic-like objects into plain serializable values."""
    if value is None:
        return None

    if isinstance(value, list):
        return [_to_serializable(item) for item in value]

    if isinstance(value, tuple):
        return tuple(_to_serializable(item) for item in value)

    if isinstance(value, dict):
        return {key: _to_serializable(val) for key, val in value.items()}

    if hasattr(value, "model_dump"):
        return _to_serializable(value.model_dump())

    return value


def _extract_phase_data(phase: str, state_id: int, session: Session) -> dict[str, Any]:
    """Retrieves phase-specific fields for a given state id."""
    if phase == "initialize":
        state = session.exec(
            select(NIMBUSInitializationState).where(NIMBUSInitializationState.id == state_id)
        ).first()
        if state is None:
            return {}

        return {
            "solver_results": _to_serializable(state.solver_results),
        }

    if phase == "solve_candidates":
        state = session.exec(
            select(NIMBUSClassificationState).where(NIMBUSClassificationState.id == state_id)
        ).first()
        if state is None:
            return {}

        return {
            "preferences": _to_serializable(state.preferences),
            "current_objectives": _to_serializable(state.current_objectives),
            "num_desired": _to_serializable(state.num_desired),
            "previous_preferences": _to_serializable(state.previous_preferences),
            "solver_results": _to_serializable(state.solver_results),
            "filtered_lagrange_multipliers": _to_serializable(state.filtered_lagrange_multipliers),
            "tradeoffs_matrix": _to_serializable(state.tradeoffs_matrix),
        }

    if phase == "final":
        state = session.exec(
            select(NIMBUSFinalState).where(NIMBUSFinalState.id == state_id)
        ).first()
        if state is None:
            return {}

        return {
            "solver_results": _to_serializable(state.solver_results),
            "solution_result_index": _to_serializable(state.solution_result_index),
        }

    if phase in {"intermediate", "solve_intermediate"}:
        state = session.exec(
            select(IntermediateSolutionState).where(IntermediateSolutionState.id == state_id)
        ).first()
        if state is None:
            return {}

        return {
            "num_desired": _to_serializable(state.num_desired),
            "context": _to_serializable(state.context),
            "reference_solution_1": _to_serializable(state.reference_solution_1),
            "reference_solution_2": _to_serializable(state.reference_solution_2),
            "solver_results": _to_serializable(state.solver_results),
        }

    return {}


def fetch_users_problems_states_grouped_by_method(session: Session) -> list[dict[str, Any]]:
    """Fetches user -> problem -> state data, grouped by method, with phase-specific payloads.

    Returned structure per user:
        {
            "user_id": int,
            "username": str,
            "experiment_group": int | None,
            "preferred_method": str | None,
            "problems": [
                {
                    "problem_id": int,
                    "stateDB": [{"state_id": int | None, "date_time": str | None}],
                    "states_grouped_by_method": {
                        "<method>": [
                            {
                                "state_id": int,
                                "date_time": str | None,
                                "method": str,
                                "phase": str,
                                "kind": str,
                                "phase_data": {...}
                            }
                        ]
                    }
                }
            ]
        }
    """
    users = session.exec(select(User).order_by(User.id)).all()
    all_data: list[dict[str, Any]] = []

    for user in users:
        user_entry: dict[str, Any] = {
            "user_id": user.id,
            "username": user.username,
            "experiment_group": user.experiment_group,
            "preferred_method": user.preferred_method,
            "problems": [],
        }

        problems = session.exec(
            select(ProblemDB).where(ProblemDB.user_id == user.id).order_by(ProblemDB.id)
        ).all()

        for problem in problems:
            statedb_rows = session.exec(
                select(StateDB).where(StateDB.problem_id == problem.id).order_by(StateDB.id)
            ).all()

            if not statedb_rows:
                continue

            problem_entry: dict[str, Any] = {
                "problem_id": problem.id,
                "stateDB": [
                    {
                        "state_id": state_row.state_id,
                        "date_time": state_row.date_time,
                    }
                    for state_row in statedb_rows
                ],
                "states_grouped_by_method": {},
            }

            for state_row in statedb_rows:
                if state_row.state_id is None:
                    continue

                base_state = session.exec(
                    select(State).where(State.id == state_row.state_id)
                ).first()

                if base_state is None:
                    continue

                method = base_state.method
                phase_data = _extract_phase_data(base_state.phase, state_row.state_id, session)

                state_entry = {
                    "state_id": state_row.state_id,
                    "date_time": state_row.date_time,
                    "method": base_state.method,
                    "phase": base_state.phase,
                    "kind": base_state.kind.value,
                    "phase_data": phase_data,
                }

                if method not in problem_entry["states_grouped_by_method"]:
                    problem_entry["states_grouped_by_method"][method] = []

                problem_entry["states_grouped_by_method"][method].append(state_entry)

            user_entry["problems"].append(problem_entry)

        if user_entry["problems"]:
            all_data.append(user_entry)

    return all_data


def _flatten_states_for_csv(dataset: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flattens nested user/problem/state data into per-state rows for CSV export."""
    rows: list[dict[str, Any]] = []

    for user in dataset:
        for problem in user.get("problems", []):
            grouped_states = problem.get("states_grouped_by_method", {})
            for method, method_states in grouped_states.items():
                for state in method_states:
                    rows.append(
                        {
                            "user_id": user.get("user_id"),
                            "username": user.get("username"),
                            "experiment_group": user.get("experiment_group"),
                            "preferred_method": user.get("preferred_method"),
                            "problem_id": problem.get("problem_id"),
                            "state_id": state.get("state_id"),
                            "date_time": state.get("date_time"),
                            "method": method,
                            "phase": state.get("phase"),
                            "kind": state.get("kind"),
                            "phase_data": json.dumps(state.get("phase_data", {}), ensure_ascii=False),
                        }
                    )

    return rows


def export_users_problems_states_data(
    dataset: list[dict[str, Any]],
    output_dir: str | Path = "datasets",
    base_filename: str = "xnimbus_experiment_user_problem_states",
) -> dict[str, str]:
    """Exports nested experiment dataset to JSON and flattened CSV files.

    Args:
        dataset: Output from `fetch_users_problems_states_grouped_by_method`.
        output_dir: Target directory for generated files.
        base_filename: Base filename without extension.

    Returns:
        dict[str, str]: Paths for generated `json` and `csv` files.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    json_path = output_path / f"{base_filename}.json"
    csv_path = output_path / f"{base_filename}.csv"

    with json_path.open("w", encoding="utf-8") as json_file:
        json.dump(dataset, json_file, indent=2, ensure_ascii=False)

    csv_rows = _flatten_states_for_csv(dataset)
    csv_headers = [
        "user_id",
        "username",
        "experiment_group",
        "preferred_method",
        "problem_id",
        "state_id",
        "date_time",
        "method",
        "phase",
        "kind",
        "phase_data",
    ]

    with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=csv_headers)
        writer.writeheader()
        writer.writerows(csv_rows)

    return {
        "json": str(json_path),
        "csv": str(csv_path),
    }


def _group_label(experiment_group: Any) -> str:
    """Builds a filesystem-safe label for experiment group values."""
    if experiment_group is None:
        return "group_unassigned"

    return f"group_{experiment_group}"


def export_users_problems_states_by_experiment_group(
    dataset: list[dict[str, Any]],
    output_dir: str | Path = "datasets",
    base_filename: str = "xnimbus_experiment_user_problem_states",
) -> dict[str, dict[str, str]]:
    """Exports separate JSON/CSV files for each experiment group.

    Returns:
        dict[str, dict[str, str]]: Mapping from group label to exported file paths.
    """
    grouped_dataset: dict[str, list[dict[str, Any]]] = {}

    for user_entry in dataset:
        label = _group_label(user_entry.get("experiment_group"))
        grouped_dataset.setdefault(label, []).append(user_entry)

    group_output_dir = Path(output_dir) / "experiment_groups"
    group_output_dir.mkdir(parents=True, exist_ok=True)

    export_map: dict[str, dict[str, str]] = {}

    for label, group_data in grouped_dataset.items():
        export_map[label] = export_users_problems_states_data(
            dataset=group_data,
            output_dir=group_output_dir,
            base_filename=f"{base_filename}_{label}",
        )

    return export_map


if __name__ == "__main__":
    if not ensure_database_exists():
        print(
            "Database missing. Please run db_init_xnimbus.py to create and seed the database before running this script."
        )
    else:
        with Session(engine) as session:
            dataset = fetch_users_problems_states_grouped_by_method(session)
            export_paths = export_users_problems_states_data(dataset)
            grouped_export_paths = export_users_problems_states_by_experiment_group(dataset)

            print("Export complete:")
            print(f"- JSON: {export_paths['json']}")
            print(f"- CSV: {export_paths['csv']}")
            print("Per experiment group exports:")

            for group_label, paths in grouped_export_paths.items():
                print(f"- {group_label} JSON: {paths['json']}")
                print(f"- {group_label} CSV: {paths['csv']}")
