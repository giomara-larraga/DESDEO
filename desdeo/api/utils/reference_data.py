"""Utility functions for handling reference data."""

import polars as pl
from sqlalchemy.orm import Session
from sqlmodel import select

from desdeo.api.db_models import ReferenceData


def get_reference_data_as_dataframe(session: Session, problem_id: int) -> pl.DataFrame:
    """Get reference data for a problem as a Polars DataFrame.

    Args:
        session: The database session
        problem_id: ID of the problem to get reference data for

    Returns:
        pl.DataFrame: DataFrame containing reference points and their objective values

    Raises:
        ValueError: If no reference data is found for the problem
    """
    # Query reference data for the problem
    reference_data_query = select(ReferenceData).where(
        ReferenceData.problem_id == problem_id
    )
    reference_data = session.exec(reference_data_query).all()

    if not reference_data:
        raise ValueError(f"No reference data found for problem {problem_id}")

    # Convert reference data to rows for DataFrame
    data_rows = []
    for ref in reference_data:
        # Convert to dictionaries if they're not already
        ref_values = (
            ref.reference_values
            if isinstance(ref.reference_values, dict)
            else {f"z_{i+1}": v for i, v in enumerate(ref.reference_values)}
        )
        obj_values = (
            ref.objective_values
            if isinstance(ref.objective_values, dict)
            else {f"f_{i+1}": v for i, v in enumerate(ref.objective_values)}
        )

        row = {
            **ref_values,  # Reference point values
            **obj_values,  # Corresponding objective values
        }
        data_rows.append(row)

    # Create DataFrame from the collected data
    return pl.DataFrame(data_rows)


def get_reference_point_symbols(n_elements: int) -> tuple[list[str], list[str]]:
    """Get standardized symbols for reference points and objectives.

    Args:
        n_elements: Number of elements (same for both reference points and objectives)

    Returns:
        tuple: (reference_point_symbols, objective_symbols) where
               reference points are named z_1, z_2, ... z_n and
               objectives are named f_1, f_2, ... f_n
    """
    # Create standardized symbol names
    reference_symbols = [f"z_{i+1}" for i in range(n_elements)]
    objective_symbols = [f"f_{i+1}" for i in range(n_elements)]

    return reference_symbols, objective_symbols
