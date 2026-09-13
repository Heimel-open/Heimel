from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .common import utcnow


class TimeWindow(BaseModel):
    """A validity window. `valid_until` must be later than `valid_from`."""

    valid_from: datetime
    valid_until: datetime

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def check_window(self) -> TimeWindow:
        if self.valid_until <= self.valid_from:
            raise ValueError("valid_until must be later than valid_from")
        return self

    def is_active_at(self, moment: datetime | None = None) -> bool:
        moment = moment or utcnow()
        return self.valid_from <= moment < self.valid_until


class Timestamps(BaseModel):
    """Explicit kernel time.

    Distinguishes when we learned something (observed_at / recorded_at) from
    when it actually applied (effective_at / valid_from / valid_until).
    """

    observed_at: datetime = Field(default_factory=utcnow)
    recorded_at: datetime = Field(default_factory=utcnow)
    effective_at: datetime = Field(default_factory=utcnow)
    valid_from: datetime = Field(default_factory=utcnow)
    valid_until: datetime | None = None
    superseded_at: datetime | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def check_order(self) -> Timestamps:
        if self.effective_at < self.valid_from:
            raise ValueError("effective_at must not precede valid_from")
        if self.recorded_at < self.observed_at:
            raise ValueError("recorded_at must not precede observed_at")
        if self.valid_until is not None and self.valid_until <= self.valid_from:
            raise ValueError("valid_until must be later than valid_from")
        if self.superseded_at is not None and self.superseded_at <= self.recorded_at:
            raise ValueError("superseded_at must be later than recorded_at")
        return self


def is_backdated(observed_at: datetime, recorded_at: datetime) -> bool:
    """A correction-style event may backdate effective/valid windows, but an
    append of a freshly-observed fact must not appear before its observation."""
    return recorded_at < observed_at
