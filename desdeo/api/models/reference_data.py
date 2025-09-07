"""Defines reference data models."""

from typing import TYPE_CHECKING, List
from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy import JSON

if TYPE_CHECKING:
    from .problem import ProblemDB


class ReferenceDataBase(SQLModel):
    """Base reference data object."""

    reference_values: List[float] = Field(sa_type=JSON)
    objective_values: List[float] = Field(sa_type=JSON)


class ReferenceData(ReferenceDataBase, table=True):
    """The table model of reference data stored in the database."""

    __tablename__ = "reference_data"  # Explicitly set table name

    id: int | None = Field(primary_key=True, default=None)
    problem_id: int = Field(
        foreign_key="problemdb.id"
    )  # Update to match the actual table name

    # Back populates
    problem: "ProblemDB" = Relationship(back_populates="reference_data")


class ReferenceDataRead(ReferenceDataBase):
    """The object to handle public reference data information."""

    id: int
    problem_id: int
