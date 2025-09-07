"""Models specific to the RXIMO explainer."""

from sqlmodel import JSON, Column, Field, SQLModel

from .generic import SolutionInfo
from .preference import ReferencePoint
from .generic_states import SolutionReferenceResponse


class RXIMOExplainRequest(SQLModel):
    """Model of the request to the RXIMO explainer."""

    problem_id: int
    session_id: int | None = Field(default=None)
    parent_state_id: int | None = Field(default=None)
    preference: ReferencePoint = Field(Column(JSON))


class RXIMOExplainResponse(SQLModel):
    """The response from the RXIMO explain endpoint."""

    shap_values: dict = Field(
        sa_column=Column(JSON),
        description="The SHAP values for the explained solution.",
    )
    base_values: dict = Field(
        sa_column=Column(JSON),
        description="The baseline values for the explained solution.",
    )
    explained_data: dict = Field(
        sa_column=Column(JSON),
        description="The input data that was explained.",
    )
