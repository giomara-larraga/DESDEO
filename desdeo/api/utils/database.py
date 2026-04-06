"""Utilities related to handling the database."""

from sqlmodel import Session, select

from desdeo.api.models import (
    BackgroundDatasetCreateRequest,
    BackgroundDatasetDB,
    ProblemDB,
    StateDB,
    UserSavedSolutionDB,
)


def user_save_solutions(
    state_db: StateDB,
    results: list,
    user_id: int,
    session: Session,
):
    """Save solutions to the user's archive and create new state in the database.

    Args:
        state_db: The state containing the solutions
        results: List of solutions to save
        user_id: ID of the user saving the solutions
        session: Database session
    """
    # Create archive entries for selected solutions
    for solution in results:
        archive_entry = UserSavedSolutionDB(
            name=solution.name if solution.name else None,
            objective_values=solution.objective_values,
            address_state=solution.address_state,
            state_id=state_db.id,
            address_result=solution.address_result,
            user_id=user_id,
            problem_id=state_db.problem_id,
            state=state_db,
        )
        session.add(archive_entry)
    # state is already set in UserSavedSolutionDB, so no need to add it explictly
    session.commit()


def create_background_dataset(
    request: BackgroundDatasetCreateRequest,
    session: Session,
) -> BackgroundDatasetDB:
    """Create and persist a background dataset entry."""
    problems = list(
        session.exec(
            select(ProblemDB).where(ProblemDB.id.in_(request.problem_ids))
        ).all()
    )

    if len(problems) != len(request.problem_ids):
        found_ids = {problem.id for problem in problems}
        missing_ids = [
            problem_id
            for problem_id in request.problem_ids
            if problem_id not in found_ids
        ]
        raise ValueError(f"Unknown problem ids: {missing_ids}")

    background_dataset = BackgroundDatasetDB(
        **request.model_dump(exclude={"problem_ids"}),
        problems=problems,
    )
    session.add(background_dataset)
    session.commit()
    session.refresh(background_dataset)
    return background_dataset


def list_background_datasets(
    problem_id: int,
    session: Session,
) -> list[BackgroundDatasetDB]:
    """Fetch background datasets for a problem."""
    statement = (
        select(BackgroundDatasetDB)
        .join(BackgroundDatasetDB.problems)
        .where(ProblemDB.id == problem_id)
    )

    datasets = list(session.exec(statement).all())
    deduplicated: dict[int, BackgroundDatasetDB] = {
        dataset.id: dataset for dataset in datasets
    }
    return list(deduplicated.values())
