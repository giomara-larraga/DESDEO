from pydantic import BaseModel, Field

from desdeo.tools.score_bands import (
    SCOREBandsConfig,
    SCOREBandsResult,
)


class SCOREBandsMethodRequest(BaseModel):
    """Calculate and persist SCORE Bands for a discrete problem."""

    problem_id: int
    session_id: int | None = None
    parent_state_id: int | None = None

    options: SCOREBandsConfig = Field(
        default_factory=SCOREBandsConfig
    )


class SCOREBandsMethodResponse(BaseModel):
    """Persisted SCORE Bands result."""

    state_id: int
    result: SCOREBandsResult