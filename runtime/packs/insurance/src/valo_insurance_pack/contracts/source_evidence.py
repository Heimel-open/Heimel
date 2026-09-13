from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..utils.crypto import iso_format, sha256_digest, utcnow


class ChangedSinceStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    UNCHANGED = "UNCHANGED"
    CHANGED = "CHANGED"


class RevocationVisibilityStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    SUSPENDED = "SUSPENDED"


class SourceAssuranceEvidenceV1(BaseModel):
    """Normalized evidence envelope from each load-bearing source.

    CRITICAL INVARIANT (P0): Absence of explicit observability is UNKNOWN by default.
    It is never presumed to be ACTIVE or UNCHANGED without proof.
    Supplied evidence_digest must strictly match computed digest at ingest.
    """

    source_id: str
    subject: str
    observed_at: datetime
    source_version: str | None = None
    valid_until: datetime | None = None
    changed_since_status: ChangedSinceStatus = ChangedSinceStatus.UNKNOWN
    revocation_visibility: RevocationVisibilityStatus = (
        RevocationVisibilityStatus.UNKNOWN
    )
    event_cursor: str | None = None
    version_cursor: str | None = None
    attestation_type: str = "GENERIC_ATTESTATION"
    evidence_digest: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)
    raw_payload: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def populate_and_validate(self) -> SourceAssuranceEvidenceV1:
        if not self.source_id or not self.source_id.strip():
            raise ValueError("source_id cannot be empty")
        if not self.subject or not self.subject.strip():
            raise ValueError("subject cannot be empty")
        if self.valid_until is not None and self.valid_until <= self.observed_at:
            raise ValueError("valid_until must be after observed_at")

        computed_digest = self.compute_digest()
        if self.evidence_digest is not None:
            if not self.evidence_digest.startswith("sha256:"):
                raise ValueError("evidence_digest must have sha256: prefix")
            if self.evidence_digest != computed_digest:
                raise ValueError(
                    f"evidence_digest mismatch: supplied '{self.evidence_digest}' "
                    f"does not match computed digest '{computed_digest}'"
                )
        else:
            object.__setattr__(self, "evidence_digest", computed_digest)
        return self

    def compute_digest(self) -> str:
        """Compute deterministic sha256 digest of core evidence contents."""
        core_data = {
            "source_id": self.source_id,
            "subject": self.subject,
            "observed_at": iso_format(self.observed_at),
            "source_version": self.source_version,
            "valid_until": iso_format(self.valid_until) if self.valid_until else None,
            "changed_since_status": self.changed_since_status.value,
            "revocation_visibility": self.revocation_visibility.value,
            "event_cursor": self.event_cursor,
            "version_cursor": self.version_cursor,
            "attestation_type": self.attestation_type,
            "provenance": self.provenance,
            "raw_payload": self.raw_payload,
        }
        return sha256_digest(core_data)

    def is_fresh(
        self, now: datetime | None = None, max_age_seconds: int | None = None
    ) -> bool:
        """Check if observation timestamp is within max age limit."""
        if max_age_seconds is None:
            return True
        now = now or utcnow()
        age = (now - self.observed_at).total_seconds()
        return 0 <= age <= max_age_seconds

    def is_active(self, now: datetime | None = None) -> bool:
        """Check if evidence is strictly active and within validity interval."""
        now = now or utcnow()
        if self.revocation_visibility != RevocationVisibilityStatus.ACTIVE:
            return False
        return not (self.valid_until is not None and now >= self.valid_until)

    def to_payload(self) -> dict[str, Any]:
        """Return canonical serializable dictionary."""
        return {
            "source_id": self.source_id,
            "subject": self.subject,
            "observed_at": iso_format(self.observed_at),
            "source_version": self.source_version,
            "valid_until": iso_format(self.valid_until) if self.valid_until else None,
            "changed_since_status": self.changed_since_status.value,
            "revocation_visibility": self.revocation_visibility.value,
            "event_cursor": self.event_cursor,
            "version_cursor": self.version_cursor,
            "attestation_type": self.attestation_type,
            "evidence_digest": self.evidence_digest or self.compute_digest(),
            "provenance": dict(self.provenance),
            "raw_payload": dict(self.raw_payload),
        }
