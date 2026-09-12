from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .common import VerificationStatus, utcnow


class IdentityClaim(BaseModel):
    """An identifier for an entity. Entities are separate from identities; a
    single entity may carry many claims. No free-form text identity may be used
    as execution identity."""

    identity_id: str
    entity_id: str
    tenant_id: str
    claim_type: str  # e.g. "internal_id", "national_id", "employee_id", "external_id"
    value: str
    issuer: str | None = None
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    verification_ref: str | None = None
    issued_at: datetime = Field(default_factory=utcnow)
    valid_until: datetime | None = None
    revoked_at: datetime | None = None
    evidence_refs: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def check_validity(self) -> IdentityClaim:
        if self.valid_until is not None and self.valid_until <= self.issued_at:
            raise ValueError("valid_until must be later than issued_at")
        return self

    def is_active(self, moment: datetime | None = None) -> bool:
        moment = moment or utcnow()
        if self.revoked_at is not None and self.revoked_at <= moment:
            return False
        if self.valid_until is not None and moment >= self.valid_until:
            return False
        return self.verification_status == VerificationStatus.VERIFIED

