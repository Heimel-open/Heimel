"""Governed Skill Manifest V1 and lifecycle invariants.

Build order: `nsolland/Index#637` (Governed Continual Skill Evolution).

Core principle:

    Capability evolution does not imply authority evolution.

A skill manifest describes capability and evidence ONLY. It carries NO
authority grant. The eight invariants are enforced here as deterministic
checks; REHT remains the sole authorization boundary.

Invariants:
1. skill_acquired != authority_granted
2. past_success != current_admissibility
3. skill_available != skill_permitted
4. skill_validated_at_t1 != skill_valid_at_t2
5. model_capability_change != mandate_change
6. skill_update -> re-evaluation required
7. skill_revoked -> execution denied
8. unknown provenance/version/missing evidence never resolves to ALLOW
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ValidationStatus(str, Enum):
    PENDING = "pending"
    VALIDATED = "validated"
    RESTRICTED = "restricted"
    REJECTED = "rejected"
    REVOKED = "revoked"


class RiskClass(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def content_hash(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class SkillManifestError(ValueError):
    pass


class UnknownProvenanceError(SkillManifestError):
    pass


class MissingEvidenceError(SkillManifestError):
    pass


@dataclass(frozen=True)
class SkillManifestV1:
    """Canonical governed skill manifest (capability + evidence only)."""

    skill_id: str
    version: str
    content_hash: str = ""
    origin: str = ""
    author_or_generator: str = ""
    model_id: str | None = None
    training_or_derivation_context: str = ""
    tool_requirements: Sequence[str] = field(default_factory=tuple)
    input_schema: str = ""
    output_schema: str = ""
    declared_scope: Sequence[str] = field(default_factory=tuple)
    known_exclusions: Sequence[str] = field(default_factory=tuple)
    risk_class: RiskClass = RiskClass.UNKNOWN
    evidence_refs: Sequence[str] = field(default_factory=tuple)
    validation_status: ValidationStatus = ValidationStatus.PENDING
    validated_at: datetime | None = None
    reviewer: str = ""
    revocation_state: str = "active"  # active | revoked
    supersedes: str | None = None

    def __post_init__(self) -> None:
        if not self.skill_id or not self.version:
            raise SkillManifestError("skill_id and version are required")
        if not self.content_hash:
            object.__setattr__(self, "content_hash", self.compute_content_hash())

    def compute_content_hash(self) -> str:
        payload = {
            "skill_id": self.skill_id,
            "version": self.version,
            "origin": self.origin,
            "author_or_generator": self.author_or_generator,
            "model_id": self.model_id,
            "declared_scope": list(self.declared_scope),
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
        }
        return content_hash(payload)

    # --- invariants -----------------------------------------------------
    def is_acquired(self) -> bool:
        return bool(self.skill_id and self.version)

    def has_known_provenance(self) -> bool:
        return bool(self.origin and self.author_or_generator)

    def has_sufficient_evidence(self) -> bool:
        return bool(self.evidence_refs) and bool(self.validated_at)

    def is_currently_validated(self, as_of: datetime | None = None) -> bool:
        """Invariant 4: validation at t1 is not validity at t2."""
        if self.validation_status != ValidationStatus.VALIDATED:
            return False
        return self.validated_at is not None

    def is_permitted(self) -> bool:
        """Invariant 7: revoked -> execution denied."""
        if self.revocation_state == "revoked":
            return False
        return self.validation_status not in (ValidationStatus.REJECTED, ValidationStatus.REVOKED)

    def admission_gate(self) -> tuple[bool, str]:
        """Invariant 8: unknown provenance/version/evidence never resolves to ALLOW.

        Returns (allowed, reason). This is advisory for SAGE/VAIG; REHT decides.
        """
        if not self.has_known_provenance():
            return False, "unknown provenance"
        if not self.has_sufficient_evidence():
            return False, "missing evidence"
        if not self.is_permitted():
            return False, "skill revoked or not permitted"
        return True, "advisory admit"


class SkillAdmissibilityEvaluator:
    """Advisory evaluation distinguishing capability from authority."""

    def evaluate(self, manifest: SkillManifestV1) -> dict[str, Any]:
        allowed, reason = manifest.admission_gate()
        return {
            "skill_id": manifest.skill_id,
            "version": manifest.version,
            "advisory_allowed": allowed,
            "reason": reason,
            "capability_evolved": manifest.is_acquired(),
            "authority_granted": False,  # never here
            "recommendation": "admit_for_testing" if allowed else "restrict_or_defer",
        }


__all__ = [
    "RiskClass",
    "SkillAdmissibilityEvaluator",
    "SkillManifestError",
    "SkillManifestV1",
    "ValidationStatus",
    "content_hash",
]
