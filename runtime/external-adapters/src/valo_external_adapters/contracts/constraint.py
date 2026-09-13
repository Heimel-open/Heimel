from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from .time import TimeWindow


class Constraint(BaseModel):
    """Generic constraint. Examples: worker must have credential X; amount
    <= 100000; data must remain in EU; service only available in region Y."""

    constraint_id: str
    constraint_type: str  # e.g. "CREDENTIAL_REQUIRED", "LIMIT", "REGION", "DATA_LOCALITY"
    subject: str
    predicate: str
    basis: str | None = None
    severity: str = "REQUIRED"  # REQUIRED | ADVISORY
    validity: TimeWindow

    model_config = ConfigDict(extra="forbid", frozen=True)
