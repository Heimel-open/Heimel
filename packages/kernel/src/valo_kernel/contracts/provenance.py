from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .common import VerificationStatus, utcnow


class Provenance(BaseModel):
    """Canonical provenance: every significant state fact can answer where it
    came from."""

    source_type: str  # e.g. "system", "human", "model", "external"
    source_id: str
    source_system: str
    issuer: str | None = None
    observed_at: datetime = Field(default_factory=utcnow)
    evidence_refs: list[str] = Field(default_factory=list)
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    confidence_if_inferred: float | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)

