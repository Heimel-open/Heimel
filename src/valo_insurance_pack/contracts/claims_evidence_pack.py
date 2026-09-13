from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..utils.crypto import iso_format, sha256_digest, utcnow
from .assurance_profile import AssuranceProfileV1
from .evaluation import CommitAssuranceEvaluationV1
from .policy_binding import PolicyBindingV1
from .source_evidence import SourceAssuranceEvidenceV1


class ClaimsEvidencePackV1(BaseModel):
    """Claim-relevant evidence bundle for deterministic offline claim verification.

    Verifiable purely through cryptographic hashes and deterministic replay,
    without requiring access to worker chain-of-thought or proprietary runtime weights.
    """

    pack_id: str = Field(default_factory=lambda: f"claim-pack-{uuid4()}")
    policy_reference: str
    coverage_condition_ref: str
    exact_action: dict[str, Any]
    action_digest: str
    active_assurance_profile: AssuranceProfileV1
    profile_digest: str
    source_attestations: list[SourceAssuranceEvidenceV1]
    commit_time_evaluation: CommitAssuranceEvaluationV1
    evaluation_digest: str
    reht_clearance: dict[str, Any]
    reht_clearance_digest: str
    racs_decision: dict[str, Any]
    racs_decision_digest: str
    effect_receipt: dict[str, Any]
    receipt_digest: str
    veritas_verification: dict[str, Any]
    veritas_outcome_digest: str
    policy_binding: PolicyBindingV1
    integrity_hashes: dict[str, str] = Field(default_factory=dict)
    replay_inputs: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=utcnow)
    pack_digest: str | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def populate_hashes(self) -> ClaimsEvidencePackV1:
        # Build integrity hashes dictionary
        computed_integrity = {
            "action_digest": self.action_digest,
            "profile_digest": self.profile_digest,
            "evaluation_digest": self.evaluation_digest,
            "reht_clearance_digest": self.reht_clearance_digest,
            "racs_decision_digest": self.racs_decision_digest,
            "receipt_digest": self.receipt_digest,
            "veritas_outcome_digest": self.veritas_outcome_digest,
            "binding_hash": self.policy_binding.binding_hash
            or self.policy_binding.compute_hash(),
        }
        for i, ev in enumerate(self.source_attestations):
            computed_integrity[f"evidence_{ev.source_id}"] = (
                ev.evidence_digest or ev.compute_digest()
            )

        if not self.integrity_hashes:
            object.__setattr__(self, "integrity_hashes", computed_integrity)

        computed_pack = self.compute_pack_digest()
        if self.pack_digest is None:
            object.__setattr__(self, "pack_digest", computed_pack)
        return self

    def compute_pack_digest(self) -> str:
        """Deterministic sha256 digest of the entire evidence pack."""
        payload = {
            "pack_id": self.pack_id,
            "policy_reference": self.policy_reference,
            "coverage_condition_ref": self.coverage_condition_ref,
            "action_digest": self.action_digest,
            "profile_digest": self.profile_digest,
            "evaluation_digest": self.evaluation_digest,
            "reht_clearance_digest": self.reht_clearance_digest,
            "racs_decision_digest": self.racs_decision_digest,
            "receipt_digest": self.receipt_digest,
            "veritas_outcome_digest": self.veritas_outcome_digest,
            "binding_hash": self.policy_binding.binding_hash
            or self.policy_binding.compute_hash(),
            "generated_at": iso_format(self.generated_at),
        }
        return sha256_digest(payload)

    def verify_integrity(self) -> tuple[bool, list[str]]:
        """Verify cryptographic integrity and cross-references of all bundle components.

        Returns (is_valid, list_of_errors).
        """
        errors: list[str] = []

        # 1. Action digest
        computed_action_digest = sha256_digest(self.exact_action)
        if self.action_digest != computed_action_digest:
            errors.append(
                f"action_digest_mismatch: declared {self.action_digest} != computed {computed_action_digest}"
            )

        # 2. Profile digest
        if self.profile_digest != self.active_assurance_profile.digest:
            errors.append(
                f"profile_digest_mismatch: declared {self.profile_digest} != computed {self.active_assurance_profile.digest}"
            )

        # 3. Evaluation digest
        computed_eval_digest = self.commit_time_evaluation.compute_digest()
        if self.evaluation_digest != computed_eval_digest:
            errors.append(
                f"evaluation_digest_mismatch: declared {self.evaluation_digest} != computed {computed_eval_digest}"
            )

        # 4. Source attestations digests
        for ev in self.source_attestations:
            ev_computed = ev.compute_digest()
            if ev.evidence_digest and ev.evidence_digest != ev_computed:
                errors.append(
                    f"source_evidence_mismatch for {ev.source_id}: {ev.evidence_digest} != {ev_computed}"
                )

        # 5. REHT clearance digest
        clearance_computed = sha256_digest(self.reht_clearance)
        if self.reht_clearance_digest != clearance_computed:
            errors.append(
                f"reht_clearance_digest_mismatch: declared {self.reht_clearance_digest} != computed {clearance_computed}"
            )

        # 6. RACS decision digest
        racs_computed = sha256_digest(self.racs_decision)
        if self.racs_decision_digest != racs_computed:
            errors.append(
                f"racs_decision_digest_mismatch: declared {self.racs_decision_digest} != computed {racs_computed}"
            )

        # 7. Effect receipt digest
        receipt_computed = sha256_digest(self.effect_receipt)
        if self.receipt_digest != receipt_computed:
            errors.append(
                f"receipt_digest_mismatch: declared {self.receipt_digest} != computed {receipt_computed}"
            )

        # 8. Veritas verification outcome digest
        veritas_computed = sha256_digest(self.veritas_verification)
        if self.veritas_outcome_digest != veritas_computed:
            errors.append(
                f"veritas_outcome_digest_mismatch: declared {self.veritas_outcome_digest} != computed {veritas_computed}"
            )

        # 9. Policy binding verification
        binding_computed = self.policy_binding.compute_hash()
        if self.policy_binding.binding_hash != binding_computed:
            errors.append(
                f"policy_binding_hash_mismatch: declared {self.policy_binding.binding_hash} != computed {binding_computed}"
            )

        # 10. Cross-reference consistency
        if self.policy_binding.action_digest != self.action_digest:
            errors.append("policy_binding action_digest cross-reference mismatch")
        if self.policy_binding.profile_digest != self.profile_digest:
            errors.append("policy_binding profile_digest cross-reference mismatch")
        if self.policy_binding.reht_clearance_digest != self.reht_clearance_digest:
            errors.append(
                "policy_binding reht_clearance_digest cross-reference mismatch"
            )
        if self.policy_binding.racs_decision_digest != self.racs_decision_digest:
            errors.append(
                "policy_binding racs_decision_digest cross-reference mismatch"
            )
        if self.policy_binding.execution_receipt_digest != self.receipt_digest:
            errors.append(
                "policy_binding execution_receipt_digest cross-reference mismatch"
            )
        if self.policy_binding.veritas_outcome_digest != self.veritas_outcome_digest:
            errors.append(
                "policy_binding veritas_outcome_digest cross-reference mismatch"
            )

        # 11. Replay verification
        if self.replay_inputs:
            from ..evaluation.evaluator import evaluate_commit_assurance

            replayed_eval = evaluate_commit_assurance(
                profile=self.active_assurance_profile,
                action=self.exact_action,
                source_evidences=self.source_attestations,
                reht_clearance_ref=self.commit_time_evaluation.reht_clearance_ref,
                racs_decision_ref=self.commit_time_evaluation.racs_decision_ref,
                now=self.commit_time_evaluation.evaluated_at,
                evaluation_id=self.commit_time_evaluation.evaluation_id,
            )
            if replayed_eval.compute_digest() != computed_eval_digest:
                errors.append(
                    "deterministic_replay_mismatch: replayed evaluation produces different digest"
                )
            if (
                replayed_eval.assurance_result
                != self.commit_time_evaluation.assurance_result
            ):
                errors.append(
                    "deterministic_replay_mismatch: replayed assurance result differs"
                )

        # 12. Top-level pack digest (the bundle seal: pack_id, policy_reference,
        # generated_at and every component digest)
        computed_pack_digest = self.compute_pack_digest()
        if self.pack_digest is not None and self.pack_digest != computed_pack_digest:
            errors.append(
                f"pack_digest_mismatch: declared {self.pack_digest} != computed {computed_pack_digest}"
            )

        # 13. Integrity hashes consistency (informational seal must match recomputation)
        expected_integrity = {
            "action_digest": self.action_digest,
            "profile_digest": self.profile_digest,
            "evaluation_digest": self.evaluation_digest,
            "reht_clearance_digest": self.reht_clearance_digest,
            "racs_decision_digest": self.racs_decision_digest,
            "receipt_digest": self.receipt_digest,
            "veritas_outcome_digest": self.veritas_outcome_digest,
            "binding_hash": self.policy_binding.binding_hash
            or self.policy_binding.compute_hash(),
        }
        for i, ev in enumerate(self.source_attestations):
            expected_integrity[f"evidence_{ev.source_id}"] = (
                ev.evidence_digest or ev.compute_digest()
            )
        if self.integrity_hashes and self.integrity_hashes != expected_integrity:
            errors.append("integrity_hashes_mismatch: declared hashes differ from recomputation")

        return (len(errors) == 0, errors)

    def to_json(self) -> str:
        """Export as formatted JSON string."""
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True)
