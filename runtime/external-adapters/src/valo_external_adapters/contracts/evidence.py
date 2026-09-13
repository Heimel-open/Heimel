from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .common import EvidenceStatus, utcnow
from .time import TimeWindow


class Evidence(BaseModel):
    """Canonical evidence object. Evidence is NOT state: an asserted document
    never sets a fact by itself. It must flow RECEIVED -> UNVERIFIED -> ADMITTED
    -> derived state event -> WorldState."""

    evidence_id: str
    type: str  # e.g. "document", "certificate", "receipt", "observation"
    source: str
    issuer: str | None = None
    subject: str
    tenant_id: str
    captured_at: datetime = Field(default_factory=utcnow)
    validity: TimeWindow | None = None
    integrity_hash: str | None = None
    purpose: str | None = None
    classification: str | None = None
    status: EvidenceStatus = EvidenceStatus.RECEIVED
    content_ref: str | None = None
    hash: str | None = None
    admission_decision_ref: str | None = None
    admission_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    model_config = ConfigDict(extra="forbid", frozen=True)
