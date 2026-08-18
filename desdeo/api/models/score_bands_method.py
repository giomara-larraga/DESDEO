from typing import Literal

from pydantic import BaseModel, Field

from desdeo.tools.score_bands import (
    SCOREBandsConfig,
    SCOREBandsResult,
)


class OptimizationOptions(BaseModel):
    """Options to indicate if SCORE bands will perform optimization or not."""
    
    optimize: bool = Field(
        default=False,
        description=(
            "Indicates if SCORE bands will perform optimization or not."
        ),
    )
    algorithm: Literal["nsga3", "rvea"] | None = Field(
        default=None,
        description=(
            "The optimization algorithm to use. If not provided, the default "
            "algorithm will be used."
        ),
    )
    #Here we can add more optimization options as needed, such as population size, number of generations, etc.
    algorithm_options: dict | None = Field(
        default=None,
        description=(
            "Additional options for the optimization algorithm. This can be "
            "used to specify parameters such as population size, number of "
            "generations, etc."
        ),
    )

class SCOREBandsMethodInitializeRequest(BaseModel):
    """Calculate and persist SCORE Bands for a discrete problem."""
    problem_id: int
    session_id: int | None = None
    parent_state_id: int | None = None
    scorebands_options: SCOREBandsConfig = Field(
        default_factory=SCOREBandsConfig
    )
    optimization_options: OptimizationOptions = Field(
        default_factory=OptimizationOptions,
        description=(
            "Options to indicate if SCORE bands will perform optimization or not."
        ),
    )

class SCOREBandsMethodInitializeResponse(BaseModel):
    """Persisted SCORE Bands result."""

    state_id: int
    result: SCOREBandsResult


class SCOREBandsMethodIterationRequest(BaseModel):
    """Calculate and persist SCORE Bands for a discrete problem."""

    problem_id: int
    session_id: int | None = None
    parent_state_id: int | None = None
    optimization_options: OptimizationOptions = Field(
        default_factory=OptimizationOptions,
        description=(
            "Options to indicate if SCORE bands will perform optimization or not."
        ),
    )
    relevant_solutions: list[int] = Field(
        default=[],
        description=(
            "A list of solution IDs that belong to a band selected by the DM. "
            "If optimization is enabled, the ranges for each objective in the selected band will be used to constrain the optimization problem."
            "If optimization is not enabled, the relevant solutions will be used to calculate the next set of SCORE bands."
        ),
    )
    scorebands_options: SCOREBandsConfig = Field(
        default_factory=SCOREBandsConfig
    )

