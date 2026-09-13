from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..utils.crypto import iso_format, sha256_digest, utcnow


class AssuranceResult(str, Enum):
    SATISFIED = "SATISFIED"
    UNMET = "UNMET"
    STEP_UP_REQUIRED = "STEP_UP_REQUIRED"
    DEFERRED = "DEFERRED"
    HALTED = "HALTED"


class CommitAssuranceEvaluationV1(BaseModel):
    """Deterministic commit-time evaluation of evidence against an AssuranceProfile.

    CRITICAL INVARIANT: The insurance layer can NEVER override REHT or RACS.
    It does not grant execution authority.
    """

    evaluation_id: str = Field(default_factory=lambda: f"eval-{uuid4()}")
    action_ref: str
    profile_ref: str
    evidence_refs: list[str] = Field(default_factory=list)
    evidence_digests: dict[str, str] = Field(default_factory=dict)
    assurance_result: AssuranceResult
    unmet_requirements: list[str] = Field(default_factory=list)
    evaluated_at: datetime = Field(default_factory=utcnow)
    reht_clearance_ref: str | None = None
    racs_decision_ref: str | None = None
    consequence_class: str = "STANDARD"
    evaluation_digest: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_and_digest(self) -> CommitAssuranceEvaluationV1:
        if not self.action_ref or not self.action_ref.strip():
            raise ValueError("action_ref is required")
        if not self.profile_ref or not self.profile_ref.strip():
            raise ValueError("profile_ref is required")

        computed = self.compute_digest()
        if self.evaluation_digest is None:
            object.__setattr__(self, "evaluation_digest", computed)
        return self

    def compute_digest(self) -> str:
        """Deterministic sha256 digest of the evaluation."""
        payload = {
            "action_ref": self.action_ref,
            "profile_ref": self.profile_ref,
            "evidence_refs": sorted(self.evidence_refs),
            "evidence_digests": dict(sorted(self.evidence_digests.items())),
            "assurance_result": self.assurance_result.value,
            "unmet_requirements": sorted(self.unmet_requirements),
            "evaluated_at": iso_format(self.evaluated_at),
            "reht_clearance_ref": self.reht_clearance_ref,
            "racs_decision_ref": self.racs_decision_ref,
            "consequence_class": self.consequence_class,
        }
        return sha256_digest(payload)

    @property
    def is_satisfied(self) -> bool:
        """Return True only if all assurance profile requirements are met."""
        return (
            self.assurance_result == AssuranceResult.SATISFIED
            and len(self.unmet_requirements) == 0
        )

    def to_payload(self) -> dict[str, Any]:
        """Return canonical serializable dictionary."""
        return {
            "evaluation_id": self.evaluation_id,
            "action_ref": self.action_ref,
            "profile_ref": self.profile_ref,
            "evidence_refs": list(self.evidence_refs),
            "evidence_digests": dict(self.evidence_digests),
            "assurance_result": self.assurance_result.value,
            "unmet_requirements": list(self.unmet_requirements),
            "evaluated_at": iso_format(self.evaluated_at),
            "reht_clearance_ref": self.reht_clearance_ref,
            "racs_decision_ref": self.racs_decision_ref,
            "consequence_class": self.consequence_class,
            "evaluation_digest": self.evaluation_digest or self.compute_digest(),
            "metadata": dict(self.metadata),
        }
