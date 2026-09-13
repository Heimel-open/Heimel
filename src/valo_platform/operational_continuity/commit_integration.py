"""Bind the full continuity revalidation chain into commit authorization.

This wrapper verifies request -> VAIG assessment -> REHT decision, then calls the
canonical Action Case commit bridge. It adds exact refs and digests to the
existing receipt and authorization chain without creating a second commit path.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Mapping, Optional, Sequence

from pydantic import BaseModel, ConfigDict, model_validator

from src.valo_platform.action_envelope.action_case_commit_bridge import (
    ActionCaseCommitBinding,
    authorize_action_case_commit,
    verify_action_case_commit_binding,
)
from src.valo_platform.action_envelope.execution_gate import ExecutionGateResult
from src.valo_platform.action_envelope.models import (
    ActionEnvelope,
    GovernanceClearance,
)
from src.valo_platform.action_envelope.outcome_attestation import (
    CommitAuthorizationRecord,
    CommitChainError,
    EvidenceBoundCommitChain,
)
from src.valo_platform.decision_governance.action_case import ActionCaseRecord
from src.valo_platform.decision_governance.continuity import (
    ContinuityContractError,
    ContinuityImpactAssessment,
    canonical_digest,
    canonical_fingerprint_digest,
)
from src.valo_platform.models.core_receipt import Receipt

from .revalidation import (
    ContinuityRevalidationRequest,
    ContinuityRevalidationResult,
    validate_vaig_assessment,
)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise CommitChainError("CONTINUITY_REVALIDATION_TIME_MUST_BE_AWARE")
    return value.astimezone(timezone.utc)


def _assessment_ref(assessment: ContinuityImpactAssessment) -> str:
    return (
        f"continuity-assessment:{assessment.assessment_id}:"
        f"{assessment.assessment_digest}"
    )


def _result_ref(result: ContinuityRevalidationResult) -> str:
    return f"continuity-revalidation-result:{result.result_digest}"


def _proof_payload(
    *,
    request: ContinuityRevalidationRequest,
    assessment: ContinuityImpactAssessment,
    result: ContinuityRevalidationResult,
) -> dict[str, str]:
    return {
        "request_ref": request.evidence_ref,
        "request_digest": request.request_digest,
        "assessment_ref": _assessment_ref(assessment),
        "assessment_digest": assessment.assessment_digest,
        "result_ref": _result_ref(result),
        "result_digest": result.result_digest,
        "decision_ref": result.decision.continuity_decision_id,
        "decision_digest": result.decision.decision_digest,
    }


class RevalidatedActionCaseCommitBinding(BaseModel):
    """Exact commit binding extended with the complete revalidation proof."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    commit_binding: ActionCaseCommitBinding
    request_ref: str
    request_digest: str
    assessment_ref: str
    assessment_digest: str
    result_ref: str
    result_digest: str
    proof_digest: str
    content_hash: str = ""

    @model_validator(mode="after")
    def _validate_binding(self) -> "RevalidatedActionCaseCommitBinding":
        expected = canonical_digest(
            self.model_dump(mode="json", exclude={"content_hash"})
        )
        if self.content_hash and self.content_hash != expected:
            raise ContinuityContractError(
                "revalidated commit content_hash does not match binding"
            )
        if not self.content_hash:
            object.__setattr__(self, "content_hash", expected)
        return self


def _validate_full_revalidation_chain(
    *,
    action_case: ActionCaseRecord,
    clearance: GovernanceClearance,
    current_fingerprints: Mapping[str, Optional[str]],
    request: ContinuityRevalidationRequest,
    assessment: ContinuityImpactAssessment,
    result: ContinuityRevalidationResult,
    checked_at: datetime,
) -> None:
    checked_at = _as_utc(checked_at)
    try:
        validate_vaig_assessment(request, assessment)
    except ContinuityContractError as exc:
        raise CommitChainError("CONTINUITY_VAIG_ASSESSMENT_INVALID") from exc

    expected_binding = (
        action_case.tenant_id,
        action_case.case_id,
        action_case.case_hash,
        clearance.clearance_id,
    )
    request_binding = (
        request.basis.tenant_id,
        request.basis.action_case_id,
        request.basis.action_case_hash,
        request.basis.clearance_ref,
    )
    if request_binding != expected_binding:
        raise CommitChainError("CONTINUITY_REVALIDATION_BINDING_MISMATCH")

    if result.request_ref != request.evidence_ref:
        raise CommitChainError("CONTINUITY_REVALIDATION_REQUEST_REF_MISMATCH")
    if result.request_digest != request.request_digest:
        raise CommitChainError("CONTINUITY_REVALIDATION_REQUEST_DIGEST_MISMATCH")
    if result.assessment_ref != assessment.assessment_id:
        raise CommitChainError("CONTINUITY_REVALIDATION_ASSESSMENT_REF_MISMATCH")
    if result.assessment_digest != assessment.assessment_digest:
        raise CommitChainError("CONTINUITY_REVALIDATION_ASSESSMENT_DIGEST_MISMATCH")
    if result.decision.action_case_id != action_case.case_id:
        raise CommitChainError("CONTINUITY_REVALIDATION_DECISION_CASE_MISMATCH")
    if result.decision.action_case_hash != action_case.case_hash:
        raise CommitChainError("CONTINUITY_REVALIDATION_DECISION_HASH_MISMATCH")
    if result.decision.clearance_ref != clearance.clearance_id:
        raise CommitChainError("CONTINUITY_REVALIDATION_DECISION_CLEARANCE_MISMATCH")
    if result.completed_at < assessment.assessed_at:
        raise CommitChainError("CONTINUITY_REVALIDATION_RESULT_PREDATES_ASSESSMENT")
    if result.completed_at > checked_at:
        raise CommitChainError("CONTINUITY_REVALIDATION_RESULT_FROM_FUTURE")

    if (
        canonical_fingerprint_digest(current_fingerprints)
        != request.current_fingerprints.fingerprint_digest
    ):
        raise CommitChainError("CONTINUITY_REVALIDATION_CURRENT_STATE_MISMATCH")
    if result.decision.current_fingerprint_digest != (
        request.current_fingerprints.fingerprint_digest
    ):
        raise CommitChainError("CONTINUITY_REVALIDATION_DECISION_STATE_MISMATCH")


def authorize_revalidated_action_case_commit(
    chain: EvidenceBoundCommitChain,
    action_case: ActionCaseRecord,
    envelope: ActionEnvelope,
    clearance: GovernanceClearance,
    gate_result: ExecutionGateResult,
    receipt: Receipt,
    *,
    current_fingerprints: Mapping[str, Optional[str]],
    adapter: str,
    target_system_ref: str,
    revalidation_request: ContinuityRevalidationRequest,
    assessment: ContinuityImpactAssessment,
    revalidation_result: ContinuityRevalidationResult,
    checked_at: datetime,
    mode: str = "enforce",
    consume: bool = True,
    checkpoint_refs: Sequence[str] = (),
    revalidation_refs: Sequence[str] = (),
) -> RevalidatedActionCaseCommitBinding:
    """Authorize through the canonical bridge after verifying the full chain."""

    checked_at = _as_utc(checked_at)
    _validate_full_revalidation_chain(
        action_case=action_case,
        clearance=clearance,
        current_fingerprints=current_fingerprints,
        request=revalidation_request,
        assessment=assessment,
        result=revalidation_result,
        checked_at=checked_at,
    )

    proof_payload = _proof_payload(
        request=revalidation_request,
        assessment=assessment,
        result=revalidation_result,
    )
    proof_digest = canonical_digest(proof_payload)

    bound_gate = replace(
        gate_result,
        details={
            **gate_result.details,
            "continuity_verification": {
                "verified": True,
                **proof_payload,
                "proof_digest": proof_digest,
            },
        },
    )

    request_ref = revalidation_request.evidence_ref
    assessment_ref = _assessment_ref(assessment)
    result_ref = _result_ref(revalidation_result)
    evidence_refs = {
        request_ref,
        assessment_ref,
        result_ref,
        *revalidation_request.evidence_refs,
        *assessment.evidence_refs,
        *revalidation_result.decision.evidence_refs,
    }

    bound_receipt = receipt.model_copy(deep=True)
    bound_receipt.evidence_ids = sorted(
        set(bound_receipt.evidence_ids) | evidence_refs
    )
    bound_receipt.evidence_count = len(bound_receipt.evidence_ids)
    bound_receipt.metadata = {
        **bound_receipt.metadata,
        "continuity_revalidation_request_ref": request_ref,
        "continuity_revalidation_request_digest": (
            revalidation_request.request_digest
        ),
        "continuity_revalidation_assessment_ref": assessment_ref,
        "continuity_revalidation_assessment_digest": assessment.assessment_digest,
        "continuity_revalidation_result_ref": result_ref,
        "continuity_revalidation_result_digest": revalidation_result.result_digest,
        "continuity_revalidation_proof_digest": proof_digest,
    }

    effective_revalidation_refs = {
        *revalidation_refs,
        request_ref,
        assessment_ref,
        result_ref,
        revalidation_result.decision.continuity_decision_id,
    }
    commit_binding = authorize_action_case_commit(
        chain,
        action_case,
        envelope,
        clearance,
        bound_gate,
        bound_receipt,
        current_fingerprints=current_fingerprints,
        adapter=adapter,
        target_system_ref=target_system_ref,
        mode=mode,
        consume=consume,
        checkpoint_refs=checkpoint_refs,
        revalidation_refs=tuple(sorted(effective_revalidation_refs)),
        continuity_required=True,
        continuity_decision=revalidation_result.decision,
        continuity_checked_at=checked_at,
    )

    return RevalidatedActionCaseCommitBinding(
        commit_binding=commit_binding,
        request_ref=request_ref,
        request_digest=revalidation_request.request_digest,
        assessment_ref=assessment_ref,
        assessment_digest=assessment.assessment_digest,
        result_ref=result_ref,
        result_digest=revalidation_result.result_digest,
        proof_digest=proof_digest,
    )


def verify_revalidated_action_case_commit_binding(
    binding: RevalidatedActionCaseCommitBinding,
    authorization: CommitAuthorizationRecord,
) -> bool:
    """Verify the canonical commit plus all request/assessment/result bindings."""

    if not verify_action_case_commit_binding(
        binding.commit_binding,
        authorization,
    ):
        return False

    metadata = binding.commit_binding.receipt_snapshot.get("metadata") or {}
    expected_metadata = {
        "continuity_revalidation_request_ref": binding.request_ref,
        "continuity_revalidation_request_digest": binding.request_digest,
        "continuity_revalidation_assessment_ref": binding.assessment_ref,
        "continuity_revalidation_assessment_digest": binding.assessment_digest,
        "continuity_revalidation_result_ref": binding.result_ref,
        "continuity_revalidation_result_digest": binding.result_digest,
        "continuity_revalidation_proof_digest": binding.proof_digest,
    }
    for key, expected in expected_metadata.items():
        if metadata.get(key) != expected:
            return False

    required_refs = {
        binding.request_ref,
        binding.assessment_ref,
        binding.result_ref,
        binding.commit_binding.continuity_decision_ref,
    }
    if None in required_refs:
        return False
    if not required_refs.issubset(set(authorization.revalidation_refs)):
        return False
    if not {
        binding.request_ref,
        binding.assessment_ref,
        binding.result_ref,
    }.issubset(set(binding.commit_binding.receipt_snapshot.get("evidence_ids") or [])):
        return False

    expected_content_hash = canonical_digest(
        binding.model_dump(mode="json", exclude={"content_hash"})
    )
    return expected_content_hash == binding.content_hash


__all__ = [
    "RevalidatedActionCaseCommitBinding",
    "authorize_revalidated_action_case_commit",
    "verify_revalidated_action_case_commit_binding",
]
