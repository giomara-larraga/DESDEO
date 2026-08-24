"""Shared fixtures for GDM session tests."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

# Import all table models before create_all().
# This ensures their metadata is registered.
from desdeo.api.models import ProblemDB, User  # noqa: F401
from desdeo.api.models.gdm.gdm_aggregate import (  # noqa: F401
    Group,
    GroupIteration,
    GroupSessionDB,
)
from desdeo.api.models.gdm.group_user_link import GroupUserLink  # noqa: F401
from desdeo.api.models.generic_states import StateDB  # noqa: F401

from desdeo.api.app import app
from desdeo.api.db import get_session

import pytest
from sqlmodel import Session

from desdeo.api.models import ProblemDB, User
from desdeo.problem.testproblems import river_pollution_problem_discrete
from desdeo.tools.generics import SolverResults

@pytest.fixture
def problem_factory():
    def _create_problem(
        session: Session,
        owner: User,
    ) -> ProblemDB:
        problem = ProblemDB.from_problem(
            river_pollution_problem_discrete(),
            user=owner,
        )

        session.add(problem)
        session.commit()
        session.refresh(problem)

        return problem

    return _create_problem

@pytest.fixture
def engine():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    SQLModel.metadata.create_all(test_engine)

    try:
        yield test_engine
    finally:
        SQLModel.metadata.drop_all(test_engine)


@pytest.fixture
def db_session(engine) -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(engine) -> Generator[TestClient, None, None]:
    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()

@pytest.fixture
def solver_result_factory():
    def _create() -> SolverResults:
        field_names = SolverResults.model_fields

        values = {}

        if "optimal_variables" in field_names:
            values["optimal_variables"] = {"x1": 1.0}

        if "optimal_objectives" in field_names:
            values["optimal_objectives"] = {"f1": 2.0}

        if "constraint_values" in field_names:
            values["constraint_values"] = {}

        if "success" in field_names:
            values["success"] = True

        if "message" in field_names:
            values["message"] = "test result"

        return SolverResults(**values)

    return _create