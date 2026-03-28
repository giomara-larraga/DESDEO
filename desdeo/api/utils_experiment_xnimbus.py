# Utils to extract data from the database and create datasets with the experiment results
import warnings
import json
import csv
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
from sqlmodel import Session, select
from desdeo.api.models import ProblemDB, User
from desdeo.api.db import engine
from sqlalchemy_utils import database_exists
from desdeo.api.models.generic_states import StateKind


from desdeo.api.models.generic_states import (
    StateDB,
    State,
    NIMBUSInitializationState,
    NIMBUSClassificationState,
    NIMBUSFinalState,
    IntermediateSolutionState,
)


EXPERIMENT_METHODS = ("nimbus", "xnimbus")


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
            select(NIMBUSInitializationState).where(
                NIMBUSInitializationState.id == state_id
            )
        ).first()
        if state is None:
            return {}

        return {
            "solver_results": _to_serializable(state.solver_results),
        }

    if phase == "solve_candidates":
        state = session.exec(
            select(NIMBUSClassificationState).where(
                NIMBUSClassificationState.id == state_id
            )
        ).first()
        if state is None:
            return {}

        return {
            "preferences": _to_serializable(state.preferences),
            "current_objectives": _to_serializable(state.current_objectives),
            "num_desired": _to_serializable(state.num_desired),
            "previous_preferences": _to_serializable(state.previous_preferences),
            "solver_results": _to_serializable(state.solver_results),
            "filtered_lagrange_multipliers": _to_serializable(
                state.filtered_lagrange_multipliers
            ),
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
            select(IntermediateSolutionState).where(
                IntermediateSolutionState.id == state_id
            )
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


def fetch_users_problems_states_grouped_by_method(
    session: Session, include_phase_data: bool = True
) -> list[dict[str, Any]]:
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
                select(StateDB)
                .where(StateDB.problem_id == problem.id)
                .order_by(StateDB.id)
            ).all()

            if not statedb_rows:
                continue

            problem_entry: dict[str, Any] = {
                "problem_id": problem.id,
                "objective_name_map": {
                    objective.symbol: objective.name
                    for objective in (problem.objectives or [])
                    if objective.symbol and objective.name
                },
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
                phase_data = (
                    _extract_phase_data(base_state.phase, state_row.state_id, session)
                    if include_phase_data
                    else {}
                )

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


def _parse_date_time(value: str | None) -> datetime | None:
    """Parse stored ISO timestamps, returning None for missing or invalid values."""
    if value is None:
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _get_time_window(
    states: list[dict[str, Any]],
) -> tuple[str | None, str | None, float | None]:
    """Return first timestamp, last timestamp, and elapsed seconds for a state collection."""
    stamped_states = [
        (state.get("date_time"), _parse_date_time(state.get("date_time")))
        for state in states
    ]
    stamped_states = [
        (raw, parsed) for raw, parsed in stamped_states if parsed is not None
    ]

    if not stamped_states:
        return None, None, None

    stamped_states.sort(key=lambda item: item[1])
    first_raw, first_parsed = stamped_states[0]
    last_raw, last_parsed = stamped_states[-1]

    return first_raw, last_raw, max((last_parsed - first_parsed).total_seconds(), 0.0)


def _normalize_preferred_method(method: str | None) -> str:
    """Normalize preferred method labels for grouping and display."""
    if method is None:
        return "unspecified"

    normalized = method.strip().lower()
    return normalized or "unspecified"


def _build_method_summary(
    method: str,
    states: list[dict[str, Any]],
    include_action_details: bool = False,
) -> dict[str, Any]:
    """Summarize the actions taken within a single method."""
    sorted_states = sorted(
        states,
        key=lambda state: (
            _parse_date_time(state.get("date_time")) or datetime.min,
            state.get("state_id") or 0,
        ),
    )
    phase_counts = Counter(state.get("phase", "unknown") for state in sorted_states)
    first_action_at, last_action_at, duration_seconds = _get_time_window(sorted_states)

    return {
        "method": method,
        "total_actions": len(sorted_states),
        "problem_ids": sorted(
            {
                state.get("problem_id")
                for state in sorted_states
                if state.get("problem_id") is not None
            }
        ),
        "phase_counts": dict(sorted(phase_counts.items())),
        "first_action_at": first_action_at,
        "last_action_at": last_action_at,
        "duration_seconds": duration_seconds,
        "actions": [
            {
                "state_id": state.get("state_id"),
                "problem_id": state.get("problem_id"),
                "date_time": state.get("date_time"),
                "phase": state.get("phase"),
                "kind": state.get("kind"),
                "phase_data": (
                    state.get("phase_data", {}) if include_action_details else {}
                ),
            }
            for state in sorted_states
        ],
    }


def _build_user_summary(
    user_entry: dict[str, Any],
    include_action_details: bool = False,
) -> dict[str, Any]:
    """Build a per-user summary with method drill-down information."""
    method_states: dict[str, list[dict[str, Any]]] = {
        method: [] for method in EXPERIMENT_METHODS
    }
    all_states: list[dict[str, Any]] = []
    problem_objective_names: dict[str, dict[str, str]] = {}

    for problem in user_entry.get("problems", []):
        problem_id = problem.get("problem_id")
        if problem_id is not None:
            problem_objective_names[str(problem_id)] = problem.get(
                "objective_name_map", {}
            )
        grouped_states = problem.get("states_grouped_by_method", {})

        for method, states in grouped_states.items():
            method_states.setdefault(method, [])

            for state in states:
                state_with_problem = {
                    "problem_id": problem_id,
                    "state_id": state.get("state_id"),
                    "date_time": state.get("date_time"),
                    "phase": state.get("phase"),
                    "kind": state.get("kind"),
                    "phase_data": state.get("phase_data", {}),
                }
                method_states[method].append(state_with_problem)
                all_states.append(state_with_problem)

    first_action_at, last_action_at, duration_seconds = _get_time_window(all_states)

    methods = {
        method: _build_method_summary(
            method,
            method_states.get(method, []),
            include_action_details=include_action_details,
        )
        for method in sorted(method_states)
    }

    return {
        "user_id": user_entry.get("user_id"),
        "username": user_entry.get("username"),
        "preferred_method": _normalize_preferred_method(
            user_entry.get("preferred_method")
        ),
        "problem_objective_names": problem_objective_names,
        "problem_count": len(user_entry.get("problems", [])),
        "total_actions": len(all_states),
        "first_action_at": first_action_at,
        "last_action_at": last_action_at,
        "duration_seconds": duration_seconds,
        "methods": methods,
    }


def build_experiment_group_summaries(
    session: Session,
    include_action_details: bool = False,
) -> list[dict[str, Any]]:
    """Aggregate per-group summaries for analyst-facing experiment dashboards."""
    dataset = fetch_users_problems_states_grouped_by_method(
        session, include_phase_data=include_action_details
    )
    grouped: dict[int | None, list[dict[str, Any]]] = {}

    for user_entry in dataset:
        grouped.setdefault(user_entry.get("experiment_group"), []).append(user_entry)

    group_summaries: list[dict[str, Any]] = []

    for experiment_group, group_users in sorted(
        grouped.items(), key=lambda item: (-1 if item[0] is None else item[0])
    ):
        user_summaries = sorted(
            [
                _build_user_summary(
                    user_entry,
                    include_action_details=include_action_details,
                )
                for user_entry in group_users
            ],
            key=lambda user: user["username"].lower(),
        )
        preferred_method_counts = Counter(
            user_summary["preferred_method"] for user_summary in user_summaries
        )
        durations = [
            user_summary["duration_seconds"]
            for user_summary in user_summaries
            if user_summary["duration_seconds"] is not None
        ]

        group_summaries.append(
            {
                "experiment_group": experiment_group,
                "group_label": (
                    "Unassigned"
                    if experiment_group is None
                    else f"Group {experiment_group}"
                ),
                "user_count": len(user_summaries),
                "preferred_method_counts": dict(
                    sorted(preferred_method_counts.items())
                ),
                "average_duration_seconds": (
                    sum(durations) / len(durations) if durations else None
                ),
                "users": user_summaries,
            }
        )

    return group_summaries


def build_group_user_summary(
    session: Session,
    experiment_group: int | None,
    user_id: int,
    include_action_details: bool = False,
) -> dict[str, Any] | None:
    """Fetch a single user summary within an experiment group."""
    if include_action_details:
        dataset = fetch_users_problems_states_grouped_by_method(
            session, include_phase_data=True
        )
        for user_entry in dataset:
            if user_entry.get("experiment_group") != experiment_group:
                continue

            if user_entry.get("user_id") == user_id:
                return _build_user_summary(user_entry, include_action_details=True)

        return None

    for group_summary in build_experiment_group_summaries(session):
        if group_summary.get("experiment_group") != experiment_group:
            continue

        for user_summary in group_summary.get("users", []):
            if user_summary.get("user_id") == user_id:
                return user_summary

        return None

    return None


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
                            "phase_data": json.dumps(
                                state.get("phase_data", {}), ensure_ascii=False
                            ),
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
            grouped_export_paths = export_users_problems_states_by_experiment_group(
                dataset
            )

            print("Export complete:")
            print(f"- JSON: {export_paths['json']}")
            print(f"- CSV: {export_paths['csv']}")
            print("Per experiment group exports:")

            for group_label, paths in grouped_export_paths.items():
                print(f"- {group_label} JSON: {paths['json']}")
                print(f"- {group_label} CSV: {paths['csv']}")
