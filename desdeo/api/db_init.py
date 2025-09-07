"""This module initializes the database."""

import warnings

from sqlalchemy_utils import database_exists
from sqlmodel import Session, SQLModel

from desdeo.api.config import ServerDebugConfig, SettingsConfig
from desdeo.api.db import engine
from desdeo.api.models import ProblemDB, User, UserRole, ReferenceData
from desdeo.api.routers.user_authentication import get_password_hash
from desdeo.problem.testproblems import dtlz2, river_pollution_problem, simple_knapsack
from typing import List, Dict, Optional
from desdeo.problem import Problem
from desdeo.tools import payoff_table_method

from desdeo.mcdm.reference_point_method import rpm_solve_solutions

from desdeo.problem import (
    Problem,
    numpy_array_to_objective_dict,
    objective_dict_to_numpy_array,
)

problems = [dtlz2(10, 3), river_pollution_problem()]
import numpy as np


def sample_input_space(ideal, nadir, n_samples: int = 20) -> np.ndarray:
    ideal = np.array(list(ideal.values()))
    nadir = np.array(list(nadir.values()))
    """Generate random samples from the input space between ideal and nadir points."""
    dims = len(ideal)
    # Generate uniform random samples between 0 and 1
    samples = np.random.random((n_samples, dims))
    # Scale and translate the samples to fit between ideal and nadir
    ranges = nadir - ideal
    samples = ideal + (samples * ranges)
    return samples


def init_reference_points(
    db: Session, problem_id: int, problem: Problem, n_samples: int = 100
) -> None:
    """
    Initialize reference points by randomly sampling the input space and evaluating
    the problem at those points.

    Args:
        db: Database session
        problem_id: ID of the problem
        problem: The actual problem instance
        n_samples: Number of random samples to generate
    """
    # Get ideal and nadir points from the problem
    ideal, nadir = payoff_table_method(problem)
    problem = problem.update_ideal_and_nadir(new_ideal=ideal, new_nadir=nadir)

    # Generate random samples in the input space
    reference_points = sample_input_space(ideal, nadir, n_samples)

    # Evaluate each reference point
    for ref_point in reference_points:
        dict_reference_point = numpy_array_to_objective_dict(problem, ref_point)

        # Solve the achievement scalarizing function problem
        results = rpm_solve_solutions(problem, reference_point=dict_reference_point)

        solution = results[0]  # Take the first solution

        solution_objective_vector = objective_dict_to_numpy_array(
            problem, solution.optimal_objectives
        )
        reference_point_vector = objective_dict_to_numpy_array(
            problem, dict_reference_point
        )

        reference_data = ReferenceData(
            problem_id=problem_id,
            reference_values=reference_point_vector.tolist(),
            objective_values=solution_objective_vector.tolist(),
        )

        db.add(reference_data)

    db.commit()


if __name__ == "__main__":
    if SettingsConfig.debug:
        # debug stuff

        print("Creating database tables.")
        if not database_exists(engine.url):
            SQLModel.metadata.create_all(engine)
        else:
            warnings.warn("Database already exists. Clearing it.", stacklevel=1)
            # Drop all tables
            SQLModel.metadata.drop_all(bind=engine)
            SQLModel.metadata.create_all(engine)
        print("Database tables created.")

        with Session(engine) as session:
            user_analyst = User(
                username=ServerDebugConfig.test_user_analyst_name,
                password_hash=get_password_hash(
                    ServerDebugConfig.test_user_analyst_password
                ),
                role=UserRole.analyst,
                group="test",
            )
            session.add(user_analyst)
            session.commit()
            session.refresh(user_analyst)

            for problem in problems:
                problem_db = ProblemDB.from_problem(problem, user_analyst)
                session.add(problem_db)
                session.commit()
                session.refresh(problem_db)

                # Initialize reference points with random sampling
                init_reference_points(
                    session,
                    problem_db.id,
                    problem,
                    n_samples=100,  # Adjust based on your needs
                )

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
