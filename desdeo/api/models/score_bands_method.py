from typing import Literal

from sqlmodel import Field, SQLModel

from desdeo.tools.score_bands import (
    SCOREBandsConfig,
    SCOREBandsResult,
)

class SCOREBandsOptimizationOptions(SQLModel):
    optimize: bool = False
    algorithm: Literal["nsga3", "rvea"] = "nsga3"
    # Only number_of_vectors is currently supported by the router.
    algorithm_options: dict[str, int] = Field(default_factory=dict)

# The old name is retained for compatibility with existing imports.
OptimizationOptions = SCOREBandsOptimizationOptions

class SCOREBandsBandPreference(SQLModel):
    """Preference expressed by selecting an existing band's objective intervals."""

    preference_type: Literal["score_bands.band"] = "score_bands.band"
    cluster_id: int

class SCOREBandsSavedBand(SQLModel):
    """A reference to a saved band; source_state_id makes it stable across iterations."""

    source_state_id: int
    cluster_id: int
    name: str | None = None
    preferred_ranges: dict[str, tuple[float, float]] = Field(default_factory=dict)


class SCOREBandsMethodInitializeRequest(SQLModel):
    problem_id: int
    session_id: int | None = None
    parent_state_id: int | None = None  # kept for API consistency; ignored for a new root
    scorebands_options: SCOREBandsConfig = Field(default_factory=SCOREBandsConfig)
    optimization_options: SCOREBandsOptimizationOptions = Field(
        default_factory=SCOREBandsOptimizationOptions
    )

class SCOREBandsMethodIterationRequest(SQLModel):
    problem_id: int
    session_id: int | None = None
    parent_state_id: int | None = None
    preference: SCOREBandsBandPreference
    scorebands_options: SCOREBandsConfig | None = None  # None = inherit parent
    optimization_options: SCOREBandsOptimizationOptions = Field(
        default_factory=lambda: SCOREBandsOptimizationOptions(optimize=True)
    )

class SCOREBandsMethodSaveRequest(SQLModel):
    problem_id: int
    session_id: int | None = None
    parent_state_id: int | None = None
    preference: SCOREBandsBandPreference
    save: bool = True  # False removes a previously saved band
    source_state_id: int | None = None  # to remove a saved band from an older iteration
    name: str | None = None


class SCOREBandsMethodHistoryItem(SQLModel):
    state_id: int
    parent_state_id: int | None = None
    action: Literal["initialize", "iterate"]
    selected_cluster_id: int | None = None
    result: SCOREBandsResult


class SCOREBandsMethodResponse(SQLModel):
    """Common result for initialization, resuming, and optimization."""

    response_type: Literal["score_bands.initialize", "score_bands.iterate"] = "score_bands.initialize"
    state_id: int
    session_id: int | None = None  # GDM personal SCORE bands reuse this response without a session
    result: SCOREBandsResult
    saved_bands: list[SCOREBandsSavedBand] = Field(default_factory=list)
    history: list[SCOREBandsMethodHistoryItem] = Field(default_factory=list)


# Retain the original named type for GDM's existing personal SCORE Bands route.
class SCOREBandsMethodInitializeResponse(SCOREBandsMethodResponse):
    pass


class SCOREBandsMethodSaveResponse(SQLModel):
    response_type: Literal["score_bands.save"] = "score_bands.save"
    state_id: int
    session_id: int
    saved_bands: list[SCOREBandsSavedBand] = Field(default_factory=list)


class SCOREBandsMethodHistoryResponse(SQLModel):
    response_type: Literal["score_bands.history"] = "score_bands.history"
    session_id: int
    state_id: int | None = None
    saved_bands: list[SCOREBandsSavedBand] = Field(default_factory=list)
    history: list[SCOREBandsMethodHistoryItem] = Field(default_factory=list)
