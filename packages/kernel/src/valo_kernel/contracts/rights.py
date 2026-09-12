from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .common import utcnow
from .time import TimeWindow


class Right(BaseModel):
    """Canonical right: access right, right to payment, right to service,
    right to representation, right to appeal."""

    right_id: str
    holder: str
    right_type: str  # e.g. "ACCESS", "PAYMENT", "SERVICE", "REPRESENTATION", "APPEAL"
    object: str
    scope: list[str] = Field(default_factory=list)
    basis: str
    validity: TimeWindow
    conditions: list[str] = Field(default_factory=list)
    status: str = "ACTIVE"  # ACTIVE | REVOKED | EXPIRED | FULFILLED

    model_config = ConfigDict(extra="forbid", frozen=True)

    def is_active(self, moment: datetime | None = None) -> bool:
        moment = moment or utcnow()
        return self.status == "ACTIVE" and self.validity.is_active_at(moment)

