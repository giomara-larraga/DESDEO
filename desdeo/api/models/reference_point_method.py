"""Models specific to the reference point method."""

from sqlmodel import JSON, Column, Field, SQLModel

from .preference import ReferencePoint


class RPMSolveRequest(SQLModel):
    """Model of the request to the reference point method."""

    problem_id: int
    session_id: int | None = Field(default=None)
    parent_state_id: int | None = Field(default=None)

    scalarization_options: dict[str, float | str | bool] | None = Field(
        sa_column=Column(JSON), default=None
    )
    solver: str | None = Field(default=None)
    solver_options: dict[str, float | str | bool] | None = Field(
        sa_column=Column(JSON), default=None
    )
    preference: ReferencePoint = Field(Column(JSON))


class RPMExplainRequest(SQLModel):
    """Model of the request to generate explanations for the reference point method."""

    problem_id: int
    state_id: int  # The state containing the solutions to explain
    solution_index: int = Field(
        default=0, description="Index of the solution to explain"
    )
    explanation_options: dict[str, float | str | bool] | None = Field(
        sa_column=Column(JSON), default=None
    )


class RPMExplanationResponse(SQLModel):
    """Model of the response containing explanations."""

    state_id: int
    solution_index: int
    explanations: dict = Field(sa_column=Column(JSON))
    variable_importance: dict[str, float] = Field(sa_column=Column(JSON))
    success: bool
    message: str
