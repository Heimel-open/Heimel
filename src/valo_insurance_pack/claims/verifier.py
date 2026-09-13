from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..contracts.claims_evidence_pack import ClaimsEvidencePackV1
from ..utils.crypto import utcnow


@dataclass(frozen=True)
class ClaimsVerificationReport:
    is_valid: bool
    pack_id: str
    policy_reference: str
    coverage_condition_ref: str
    verified_at: datetime
    errors: tuple[str, ...] = field(default_factory=tuple)
    checks_performed: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "pack_id": self.pack_id,
            "policy_reference": self.policy_reference,
            "coverage_condition_ref": self.coverage_condition_ref,
            "verified_at": self.verified_at.isoformat(),
            "errors": list(self.errors),
            "checks_performed": list(self.checks_performed),
        }


def verify_claims_evidence_pack(
    pack_data: ClaimsEvidencePackV1 | dict[str, Any] | str,
    *,
    strict: bool = True,
    now: datetime | None = None,
) -> ClaimsVerificationReport:
    """Verify an offline claims evidence pack without requiring worker chain-of-thought."""
    now = now or utcnow()
    checks: list[str] = [
        "schema_validation",
        "action_digest_integrity",
        "profile_digest_integrity",
        "evaluation_digest_integrity",
        "source_attestations_digest_integrity",
        "reht_clearance_digest_integrity",
        "racs_decision_digest_integrity",
        "receipt_digest_integrity",
        "veritas_outcome_digest_integrity",
        "policy_binding_cryptographic_chain",
        "cross_reference_consistency",
        "deterministic_evaluation_replay",
    ]

    try:
        if isinstance(pack_data, str):
            pack_dict = json.loads(pack_data)
            pack = ClaimsEvidencePackV1.model_validate(pack_dict)
        elif isinstance(pack_data, dict):
            pack = ClaimsEvidencePackV1.model_validate(pack_data)
        elif isinstance(pack_data, ClaimsEvidencePackV1):
            pack = pack_data
        else:
            return ClaimsVerificationReport(
                is_valid=False,
                pack_id="unknown",
                policy_reference="unknown",
                coverage_condition_ref="unknown",
                verified_at=now,
                errors=(f"unsupported pack data type: {type(pack_data)}",),
                checks_performed=tuple(checks),
            )

        is_valid, errors = pack.verify_integrity()
        return ClaimsVerificationReport(
            is_valid=is_valid,
            pack_id=pack.pack_id,
            policy_reference=pack.policy_reference,
            coverage_condition_ref=pack.coverage_condition_ref,
            verified_at=now,
            errors=tuple(errors),
            checks_performed=tuple(checks),
        )
    except Exception as e:
        return ClaimsVerificationReport(
            is_valid=False,
            pack_id=getattr(pack_data, "pack_id", "unknown")
            if hasattr(pack_data, "pack_id")
            else "unknown",
            policy_reference="unknown",
            coverage_condition_ref="unknown",
            verified_at=now,
            errors=(f"verification_exception: {e}",),
            checks_performed=tuple(checks),
        )
