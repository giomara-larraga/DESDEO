"""Database models for explainer caching."""

from datetime import datetime
from sqlmodel import Field, SQLModel, Column, LargeBinary, JSON
from typing import Optional


class ExplainerCacheDB(SQLModel, table=True):
    """Database model for caching explainer data using problem_id as key."""

    __tablename__ = "explainer_cache"

    # Primary key - use the existing problem_id
    problem_id: int = Field(primary_key=True, foreign_key="problem.id")

    # User who created the cache (for access control)
    user_id: int = Field(foreign_key="user.id", index=True)

    # Problem structure info (for validation)
    variable_symbols: list[str] = Field(sa_column=Column(JSON))
    objective_symbols: list[str] = Field(sa_column=Column(JSON))
    n_samples: int = Field(default=200)

    # Cached data (stored as compressed bytes)
    problem_data: bytes = Field(sa_column=Column(LargeBinary))

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed: datetime = Field(default_factory=datetime.utcnow)
    access_count: int = Field(default=0)

    # Optional: store additional info about the evaluation method used
    evaluation_method: str = Field(
        default="unknown"
    )  # "actual_evaluation" or "synthetic_fallback"
    evaluation_error: Optional[str] = Field(default=None)
