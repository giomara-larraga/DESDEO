"""Models specific to the RXIMO explainer interface."""

from typing import Literal

from sqlmodel import JSON, Column, Field, SQLModel

from .preference import ReferencePoint


class RXIMOExplainRequest(SQLModel):
    """Request model for SHAP explanations in the RXIMO method."""

    problem_id: int
    session_id: int | None = Field(default=None)
    parent_state_id: int | None = Field(default=None)

    preference: ReferencePoint = Field(Column(JSON))
    background_dataset_id: int | None = Field(default=None)


class RXIMOExplainResponse(SQLModel):
    """Response model for SHAP explanations in the RXIMO method."""

    response_type: Literal["rximo.explain"] = "rximo.explain"

    problem_id: int
    background_dataset_id: int
    input_symbols: list[str]
    output_symbols: list[str]
    reference_point: dict[str, float]
    explained_objective_values: dict[str, float]
    base_values: dict[str, float]
    shap_values: dict[str, dict[str, float]]
