"""This module initializes the database."""

import warnings

import numpy as np
from sqlalchemy_utils import database_exists
from sqlmodel import Session, SQLModel

from desdeo.api.config import ServerConfig, SettingsConfig
from desdeo.api.db import engine
from desdeo.api.models import (
    BackgroundDatasetCreateRequest,
    ProblemDB,
    User,
    UserRole,
)
from desdeo.api.routers.user_authentication import get_password_hash
from desdeo.api.utils.database import create_background_dataset
from desdeo.mcdm.reference_point_method import rpm_solve_solutions
from desdeo.problem import Problem, get_ideal_dict, get_nadir_dict
from desdeo.problem.testproblems import dtlz2, river_pollution_problem, simple_knapsack

problems = [river_pollution_problem()]

BACKGROUND_DATA_METHOD = "reference_point_method"
BACKGROUND_DATA_NUM_SAMPLES = 200
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
) -> BackgroundDatasetCreateRequest:
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

    return BackgroundDatasetCreateRequest(
        name=f"Initial background data for {problem_db.name}",
        kind=method,
        num_samples=num_samples,
        preference_values=preference_values,
        objective_values=objective_values,
        problem_ids=[problem_db.id],
    )


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
            user_analyst = User(
                username=ServerConfig.test_user_analyst_name,
                password_hash=get_password_hash(
                    ServerConfig.test_user_analyst_password
                ),
                role=UserRole.analyst,
                group="test",
            )
            session.add(user_analyst)
            session.commit()
            session.refresh(user_analyst)

            rng = np.random.default_rng(seed=42)

            for problem in problems:
                problem_db = ProblemDB.from_problem(problem, user_analyst)
                session.add(problem_db)
                session.commit()
                session.refresh(problem_db)

                bg_request = _build_background_dataset_request(
                    problem=problem,
                    problem_db=problem_db,
                    rng=rng,
                    method=BACKGROUND_DATA_METHOD,
                    num_samples=BACKGROUND_DATA_NUM_SAMPLES,
                )
                create_background_dataset(bg_request, session)

        """

        db.add(user_analyst)
        db.commit()
        db.refresh(user_analyst)

        # add first test DM user
        user_dm1 = db_models.User(
            username=ServerDebugConfig.test_user_dm1_name,
            password_hash=get_password_hash(ServerDebugConfig.test_user_dm1_password),
            role=UserRole.DM,
            privileges=[],
            user_group="",
        )
        db.add(user_dm1)
        db.commit()
        db.refresh(user_dm1)

        # add second test DM user
        user_dm2 = db_models.User(
            username=ServerDebugConfig.test_user_dm2_name,
            password_hash=get_password_hash(ServerDebugConfig.test_user_dm2_password),
            role=UserRole.DM,
            privileges=[],
            user_group="",
        )
        db.add(user_dm2)
        db.commit()
        db.refresh(user_dm2)

        db.close()
        """

    else:
        # deployment stuff
        pass
