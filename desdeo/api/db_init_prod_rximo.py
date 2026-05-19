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
3. Seeds predefined admin users.
4. Seeds the default RXIMO problem and a background dataset, mirroring the
    information created by `db_init.py` in debug mode.

Environment variables required
-------------------------------
DESDEO_ADMIN_USERNAME Username for the seeded analyst account.
DESDEO_ADMIN_PASSWORD Password for the seeded analyst account.

Optional
--------
DESDEO_ADMIN_GROUP                Group name for seeded users (default: "admin").
DESDEO_PREDEFINED_ADMIN_PASSWORD  Password for predefined admins. If omitted,
                                  DESDEO_ADMIN_PASSWORD is reused.
"""

import os

import numpy as np

from sqlmodel import Session, SQLModel, select

from desdeo.api.db import engine
from desdeo.api.models import BackgroundDatasetDB, ProblemDB, User, UserRole
from desdeo.api.routers.user_authentication import get_password_hash
from desdeo.api.utils.database import create_background_dataset
from desdeo.mcdm.reference_point_method import rpm_solve_solutions
from desdeo.problem import Problem, get_ideal_dict, get_nadir_dict
from desdeo.problem.testproblems import river_pollution_problem

PREDEFINED_ADMINS = ["glarraga", "gmisitano", "kmiettinen", "kmatkovic"]

problems = [river_pollution_problem(five_objective_variant=False)]

BACKGROUND_DATA_METHOD = "reference_point_method"
BACKGROUND_DATA_NUM_SAMPLES = 300
SUPPORTED_BACKGROUND_DATA_METHODS = {
    "reference_point_method",
    "random_reference_points",
}


def _coerce_scalar(value):
    """Convert solver outputs to plain Python scalars for JSON storage."""
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.reshape(-1)[0].item()
    if isinstance(value, list):
        return value[0]
    return value


def _objective_sampling_bounds(problem: Problem) -> dict[str, tuple[float, float]]:
    """Return usable objective-space sampling bounds for a problem."""
    ideals = get_ideal_dict(problem)
    nadirs = get_nadir_dict(problem)
    bounds: dict[str, tuple[float, float]] = {}

    for obj in problem.objectives:
        lower = ideals.get(obj.symbol)
        upper = nadirs.get(obj.symbol)
        if lower is None or upper is None or lower >= upper:
            lower, upper = 0.0, 1.0
        bounds[obj.symbol] = (float(lower), float(upper))

    return bounds


def _uniform_reference_points(
    problem: Problem,
    num_samples: int,
    rng: np.random.Generator,
) -> list[dict[str, float]]:
    """Create reference points with uniform marginals over each ideal-nadir range."""
    bounds = _objective_sampling_bounds(problem)
    objective_symbols = [obj.symbol for obj in problem.objectives]

    per_objective_values = {
        symbol: np.linspace(bounds[symbol][0], bounds[symbol][1], num_samples)
        for symbol in objective_symbols
    }

    # Shuffle each objective's evenly spaced values to avoid sampling only the diagonal.
    for symbol in objective_symbols:
        per_objective_values[symbol] = rng.permutation(per_objective_values[symbol])

    return [
        {
            symbol: float(per_objective_values[symbol][sample_index])
            for symbol in objective_symbols
        }
        for sample_index in range(num_samples)
    ]


def _build_background_dataset_request(
    problem: Problem,
    problem_db: ProblemDB,
    rng: np.random.Generator,
    method: str,
    num_samples: int,
):
    """Generate a background dataset request with a selectable generation method."""
    if method not in SUPPORTED_BACKGROUND_DATA_METHODS:
        supported_methods = ", ".join(sorted(SUPPORTED_BACKGROUND_DATA_METHODS))
        raise ValueError(
            f"Unsupported background data method '{method}'. Supported methods: {supported_methods}."
        )

    preference_values = {f"z_{obj.symbol}": [] for obj in problem.objectives}
    objective_values = {obj.symbol: [] for obj in problem.objectives}
    reference_points = _uniform_reference_points(problem, num_samples, rng)

    if method == "reference_point_method":
        for reference_point in reference_points:
            results = rpm_solve_solutions(problem, reference_point)

            for result in results:
                for obj in problem.objectives:
                    preference_values[f"z_{obj.symbol}"].append(
                        reference_point[obj.symbol]
                    )
                    objective_values[obj.symbol].append(
                        float(_coerce_scalar(result.optimal_objectives[obj.symbol]))
                    )

                if len(next(iter(objective_values.values()))) >= num_samples:
                    break

            if len(next(iter(objective_values.values()))) >= num_samples:
                break

    if method == "random_reference_points":
        for reference_point in reference_points:
            for obj in problem.objectives:
                preference_values[f"z_{obj.symbol}"].append(reference_point[obj.symbol])
                objective_values[obj.symbol].append(reference_point[obj.symbol])

    from desdeo.api.models import BackgroundDatasetCreateRequest

    return BackgroundDatasetCreateRequest(
        name=f"Initial background data for {problem_db.name}",
        kind=method,
        num_samples=num_samples,
        preference_values=preference_values,
        objective_values=objective_values,
        problem_ids=[problem_db.id],
    )


def create_tables() -> None:
    print("[db-init] Creating database tables (create_all is a no-op for existing tables)...")
    SQLModel.metadata.create_all(engine)
    print("[db-init] Tables ready.")


def _get_or_create_user(
    session: Session,
    username: str,
    password: str,
    role: UserRole,
    group: str,
) -> tuple[User, bool]:
    existing = session.exec(select(User).where(User.username == username)).first()
    if existing:
        return existing, False

    user = User(
        username=username,
        password_hash=get_password_hash(password),
        role=role,
        group=group,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    print(f"[db-init] Created user '{username}' (role={role.value}, group={group}).")
    return user, True


def seed_bootstrap_analyst(session: Session) -> User | None:
    username = os.environ.get("DESDEO_ADMIN_USERNAME")
    password = os.environ.get("DESDEO_ADMIN_PASSWORD")
    group = os.environ.get("DESDEO_ADMIN_GROUP", "admin")

    if not username or not password:
        print(
            "[db-init] WARNING: DESDEO_ADMIN_USERNAME or DESDEO_ADMIN_PASSWORD not set - skipping analyst seed."
        )
        return None

    user, created = _get_or_create_user(
        session=session,
        username=username,
        password=password,
        role=UserRole.analyst,
        group=group,
    )

    if user.role != UserRole.analyst:
        print(
            f"[db-init] WARNING: Existing user '{username}' has role '{user.role.value}', expected 'analyst'."
        )
    elif not created:
        print(f"[db-init] User '{username}' already exists - using as analyst owner.")

    return user


def seed_predefined_admins(session: Session) -> None:
    admin_password = os.environ.get("DESDEO_PREDEFINED_ADMIN_PASSWORD") or os.environ.get(
        "DESDEO_ADMIN_PASSWORD"
    )
    group = os.environ.get("DESDEO_ADMIN_GROUP", "admin")

    created_or_existing_admins: list[User] = []

    if not admin_password:
        print(
            "[db-init] WARNING: DESDEO_PREDEFINED_ADMIN_PASSWORD (or DESDEO_ADMIN_PASSWORD fallback) not set - skipping predefined admin seed."
        )
        return created_or_existing_admins

    for username in PREDEFINED_ADMINS:
        existing = session.exec(select(User).where(User.username == username)).first()
        if existing:
            print(f"[db-init] User '{username}' already exists - skipping.")
            created_or_existing_admins.append(existing)
            continue

        user, _ = _get_or_create_user(
            session=session,
            username=username,
            password=admin_password,
            role=UserRole.admin,
            group=group,
        )
        created_or_existing_admins.append(user)

    return created_or_existing_admins


def seed_problems_and_background_data(session: Session, owners: list[User]) -> None:
    if not owners:
        print("[db-init] WARNING: No users available - skipping problem and background-data seed.")
        return

    for owner in owners:
        rng = np.random.default_rng(seed=42)

        for problem in problems:
            existing_problem = session.exec(
                select(ProblemDB).where(
                    ProblemDB.user_id == owner.id,
                    ProblemDB.name == problem.name,
                )
            ).first()

            if existing_problem:
                problem_db = existing_problem
                print(f"[db-init] Problem '{problem_db.name}' already exists for user '{owner.username}' - skipping.")
            else:
                problem_db = ProblemDB.from_problem(problem, owner)
                session.add(problem_db)
                session.commit()
                session.refresh(problem_db)
                print(f"[db-init] Created problem '{problem_db.name}' for user '{owner.username}'.")

            expected_dataset_name = f"Initial background data for {problem_db.name}"
            existing_dataset = session.exec(
                select(BackgroundDatasetDB)
                .join(BackgroundDatasetDB.problems)
                .where(
                    BackgroundDatasetDB.name == expected_dataset_name,
                    BackgroundDatasetDB.kind == BACKGROUND_DATA_METHOD,
                    ProblemDB.id == problem_db.id,
                )
            ).first()

            if existing_dataset:
                print(
                    f"[db-init] Background dataset '{expected_dataset_name}' already exists for problem '{problem_db.name}' - skipping."
                )
                continue

            bg_request = _build_background_dataset_request(
                problem=problem,
                problem_db=problem_db,
                rng=rng,
                method=BACKGROUND_DATA_METHOD,
                num_samples=BACKGROUND_DATA_NUM_SAMPLES,
            )
            create_background_dataset(bg_request, session)
            print(
                f"[db-init] Created background dataset '{expected_dataset_name}' for problem '{problem_db.name}'."
            )


def main() -> None:
    print(f"[db-init] Using database: {engine.url.render_as_string(hide_password=True)}")
    create_tables()
    with Session(engine) as session:
        users_for_problem_seed: list[User] = []

        owner = seed_bootstrap_analyst(session)
        if owner is not None:
            users_for_problem_seed.append(owner)

        users_for_problem_seed.extend(seed_predefined_admins(session))

        # Keep a stable order but avoid duplicate users if names overlap.
        deduplicated_users = list({user.id: user for user in users_for_problem_seed}.values())
        seed_problems_and_background_data(session, deduplicated_users)
    print("[db-init] Done.")


if __name__ == "__main__":
    main()
