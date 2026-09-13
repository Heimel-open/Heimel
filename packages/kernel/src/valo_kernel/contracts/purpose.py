from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .time import TimeWindow


class Purpose(BaseModel):
    """Purpose is first-class: access to data is not enough, execution must
    also be within a legitimate purpose."""

    purpose_id: str
    purpose_type: str  # e.g. "provision", "inspection", "payment", "audit"
    scope: list[str] = Field(default_factory=list)
    basis: str
    permitted_data: list[str] = Field(default_factory=list)
    permitted_actions: list[str] = Field(default_factory=list)
    validity: TimeWindow

    model_config = ConfigDict(extra="forbid", frozen=True)

