from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .common import TruthStatus, utcnow
from .provenance import Provenance


class Fact(BaseModel):
    """A state fact with an explicit truth status. Facts are never binary
    true/false. Only CONFIRMED may be used for high-risk execution."""

    fact_id: str
    subject: str  # entity_id
    predicate: str  # e.g. "certified", "account_number", "status"
    object: str
    tenant_id: str
    truth_status: TruthStatus = TruthStatus.UNKNOWN
    model: str | None = None
    model_version: str | None = None
    confidence: float | None = None
    source_context: str | None = None
    effective_from: datetime = Field(default_factory=utcnow)
    effective_until: datetime | None = None
    version: int = 1
    provenance: Provenance
    evidence_refs: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid", frozen=True)

    def is_active(self, moment: datetime | None = None) -> bool:
        moment = moment or utcnow()
        if self.truth_status in (TruthStatus.REVOKED, TruthStatus.STALE, TruthStatus.UNKNOWN):
            return False
        return self.effective_from <= moment and (
            self.effective_until is None or moment < self.effective_until
        )

