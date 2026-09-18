"""Evidence admissibility as a conditional pre-authorization capability.

This module may decide whether a decision basis is evidentially admissible.
It never grants execution authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Optional


class EvidenceRequirement(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    REQUIRED = "REQUIRED"


class EvidenceAdmissibilityDecision(str, Enum):
    ADMIT = "ADMIT"
    REFUSE = "REFUSE"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True)
class EvidenceRecord:
    source_ref: str
    content_hash: str
    read_ref: str
    derivation_hash: str
    evaluator_id: str
    evaluator_version: str
    sufficiency: str

    @property
    def derivation_receipt(self) -> str:
        body = {
            "source_ref": self.source_ref,
            "content_hash": self.content_hash,
            "read_ref": self.read_ref,
            "derivation_hash": self.derivation_hash,
            "evaluator_id": self.evaluator_id,
            "evaluator_version": self.evaluator_version,
            "sufficiency": self.sufficiency,
        }
        raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class EvidenceAdmissibilityResult:
    decision: EvidenceAdmissibilityDecision
    derivation_receipt: Optional[str]
    reason: str


def evaluate_evidence(
    requirement: EvidenceRequirement,
    evidence: Optional[EvidenceRecord],
) -> EvidenceAdmissibilityResult:
    if requirement is EvidenceRequirement.NOT_REQUIRED:
        return EvidenceAdmissibilityResult(
            decision=EvidenceAdmissibilityDecision.ADMIT,
            derivation_receipt=None,
            reason="evidence_not_required",
        )

    if evidence is None:
        return EvidenceAdmissibilityResult(
            decision=EvidenceAdmissibilityDecision.INSUFFICIENT,
            derivation_receipt=None,
            reason="required_evidence_missing",
        )

    material_fields = (
        evidence.source_ref,
        evidence.content_hash,
        evidence.read_ref,
        evidence.derivation_hash,
        evidence.evaluator_id,
        evidence.evaluator_version,
    )
    if any(not isinstance(value, str) or not value.strip() for value in material_fields):
        return EvidenceAdmissibilityResult(
            decision=EvidenceAdmissibilityDecision.REFUSE,
            derivation_receipt=None,
            reason="material_evidence_binding_missing",
        )

    if not evidence.content_hash.startswith("sha256:") or not evidence.derivation_hash.startswith("sha256:"):
        return EvidenceAdmissibilityResult(
            decision=EvidenceAdmissibilityDecision.REFUSE,
            derivation_receipt=None,
            reason="unsupported_evidence_digest",
        )

    if evidence.sufficiency != "SUFFICIENT":
        return EvidenceAdmissibilityResult(
            decision=EvidenceAdmissibilityDecision.INSUFFICIENT,
            derivation_receipt=evidence.derivation_receipt,
            reason="evidence_insufficient",
        )

    return EvidenceAdmissibilityResult(
        decision=EvidenceAdmissibilityDecision.ADMIT,
        derivation_receipt=evidence.derivation_receipt,
        reason="evidence_admissible",
    )
