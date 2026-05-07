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

    # If set, R-XIMO results are computed only for this target objective.
    # If None, results are computed for every objective.
    target_objective_symbol: str | None = Field(default=None)

    # The DM's exact current solution, in original objective scale, keyed
    # by output symbol. Threaded into `find_rival`'s case-1..9 selection
    # so it isn't driven by the KD-tree's nearest-neighbor estimate
    # (which can flip the sign of (ref - sol) per component at points
    # away from training data). SHAP's background is the multi-point
    # Pareto-front sample regardless of this field; the field is purely
    # for the case-selection step. When omitted the router falls back
    # to the KD-tree estimate.
    current_solution: dict[str, float] | None = Field(default=None)


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

    # R-XIMO Algorithm 1 results, keyed by target objective symbol. Each entry
    # carries the rival picked for that target plus the textual explanation
    # and suggestion. Populated when the explainer was driven through
    # `find_rival`; left as None when it was not (e.g. for backward-compat
    # callers that only want the SHAP matrix).
    rximo_results: dict[str, dict] | None = Field(sa_column=Column(JSON), default=None)
