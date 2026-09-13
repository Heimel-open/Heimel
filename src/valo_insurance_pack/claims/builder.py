from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import uuid4

from ..contracts.assurance_profile import AssuranceProfileV1
from ..contracts.claims_evidence_pack import ClaimsEvidencePackV1
from ..contracts.evaluation import CommitAssuranceEvaluationV1
from ..contracts.policy_binding import PolicyBindingV1
from ..contracts.source_evidence import SourceAssuranceEvidenceV1
from ..utils.crypto import sha256_digest, utcnow


def _to_clean_dict(obj: Any) -> dict[str, Any]:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if hasattr(obj, "to_payload"):
        return obj.to_payload()
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if isinstance(obj, dict):
        return dict(obj)
    raise ValueError(
        f"cannot bind non-serializable object into claims evidence: {type(obj).__name__}"
    )


class ClaimsEvidencePackBuilder:
    """Builder for assembling tamper-evident ClaimsEvidencePackV1 bundles."""

    def __init__(
        self,
        *,
        policy_reference: str,
        coverage_condition_ref: str,
        active_assurance_profile: AssuranceProfileV1,
    ) -> None:
        self.policy_reference = policy_reference
        self.coverage_condition_ref = coverage_condition_ref
        self.profile = active_assurance_profile
        self.source_attestations: list[SourceAssuranceEvidenceV1] = []
        self._action: dict[str, Any] | None = None
        self._evaluation: CommitAssuranceEvaluationV1 | None = None
        self._reht_clearance: dict[str, Any] | None = None
        self._racs_decision: dict[str, Any] | None = None
        self._effect_receipt: dict[str, Any] | None = None
        self._veritas_verification: dict[str, Any] | None = None

    def add_source_evidence(
        self, evidence: SourceAssuranceEvidenceV1
    ) -> ClaimsEvidencePackBuilder:
        self.source_attestations.append(evidence)
        return self

    def set_source_evidences(
        self, evidences: Sequence[SourceAssuranceEvidenceV1]
    ) -> ClaimsEvidencePackBuilder:
        self.source_attestations = list(evidences)
        return self

    def set_action(self, action: Any) -> ClaimsEvidencePackBuilder:
        self._action = _to_clean_dict(action)
        return self

    def set_evaluation(
        self, evaluation: CommitAssuranceEvaluationV1
    ) -> ClaimsEvidencePackBuilder:
        self._evaluation = evaluation
        return self

    def set_reht_clearance(self, clearance: Any) -> ClaimsEvidencePackBuilder:
        self._reht_clearance = _to_clean_dict(clearance)
        return self

    def set_racs_decision(self, decision: Any) -> ClaimsEvidencePackBuilder:
        self._racs_decision = _to_clean_dict(decision)
        return self

    def set_effect_receipt(self, receipt: Any) -> ClaimsEvidencePackBuilder:
        self._effect_receipt = _to_clean_dict(receipt)
        return self

    def set_veritas_verification(self, verification: Any) -> ClaimsEvidencePackBuilder:
        self._veritas_verification = _to_clean_dict(verification)
        return self

    def build(
        self,
        *,
        pack_id: str | None = None,
        now: datetime | None = None,
    ) -> ClaimsEvidencePackV1:
        now = now or utcnow()
        if self._action is None:
            raise ValueError("action must be set before building claims pack")
        if self._evaluation is None:
            raise ValueError(
                "commit_time_evaluation must be set before building claims pack"
            )
        if self._reht_clearance is None:
            raise ValueError("reht_clearance must be set before building claims pack")
        if self._racs_decision is None:
            raise ValueError("racs_decision must be set before building claims pack")
        if self._effect_receipt is None:
            raise ValueError("effect_receipt must be set before building claims pack")
        if self._veritas_verification is None:
            raise ValueError(
                "veritas_verification must be set before building claims pack"
            )

        action_digest = sha256_digest(self._action)
        profile_digest = self.profile.digest
        eval_digest = self._evaluation.compute_digest()
        clearance_digest = sha256_digest(self._reht_clearance)
        racs_digest = sha256_digest(self._racs_decision)
        receipt_digest = sha256_digest(self._effect_receipt)
        veritas_digest = sha256_digest(self._veritas_verification)

        clearance_ref = (
            self._reht_clearance.get("clearance_id")
            or self._reht_clearance.get("reht_ref")
            or "clr-default"
        )
        racs_ref = (
            self._racs_decision.get("decision_id")
            or self._racs_decision.get("action_type")
            or "racs-default"
        )
        receipt_ref = (
            self._effect_receipt.get("execution_id")
            or self._effect_receipt.get("permit_id")
            or "rec-default"
        )
        veritas_ref = (
            self._veritas_verification.get("package_id")
            or self._veritas_verification.get("observation_digest")
            or self._veritas_verification.get("execution_id")
            or "ver-default"
        )

        policy_binding = PolicyBindingV1(
            policy_condition_ref=self.coverage_condition_ref,
            profile_version_ref=f"{self.profile.profile_id}:{self.profile.profile_version}",
            profile_digest=profile_digest,
            action_digest=action_digest,
            reht_clearance_ref=str(clearance_ref),
            reht_clearance_digest=clearance_digest,
            racs_decision_ref=str(racs_ref),
            racs_decision_digest=racs_digest,
            execution_receipt_ref=str(receipt_ref),
            execution_receipt_digest=receipt_digest,
            veritas_outcome_ref=str(veritas_ref),
            veritas_outcome_digest=veritas_digest,
            bound_at=now,
        )

        replay_inputs = {
            "profile": self.profile.to_payload(),
            "action": self._action,
            "source_evidences": [ev.to_payload() for ev in self.source_attestations],
            "reht_clearance_ref": self._evaluation.reht_clearance_ref,
            "racs_decision_ref": self._evaluation.racs_decision_ref,
            "evaluated_at": self._evaluation.evaluated_at.isoformat(),
        }

        pack = ClaimsEvidencePackV1(
            pack_id=pack_id or f"claim-pack-{uuid4()}",
            policy_reference=self.policy_reference,
            coverage_condition_ref=self.coverage_condition_ref,
            exact_action=self._action,
            action_digest=action_digest,
            active_assurance_profile=self.profile,
            profile_digest=profile_digest,
            source_attestations=self.source_attestations,
            commit_time_evaluation=self._evaluation,
            evaluation_digest=eval_digest,
            reht_clearance=self._reht_clearance,
            reht_clearance_digest=clearance_digest,
            racs_decision=self._racs_decision,
            racs_decision_digest=racs_digest,
            effect_receipt=self._effect_receipt,
            receipt_digest=receipt_digest,
            veritas_verification=self._veritas_verification,
            veritas_outcome_digest=veritas_digest,
            policy_binding=policy_binding,
            replay_inputs=replay_inputs,
            generated_at=now,
        )

        is_valid, errors = pack.verify_integrity()
        if not is_valid:
            raise ValueError(
                f"Assembled ClaimsEvidencePack failed integrity verification: {errors}"
            )

        return pack
