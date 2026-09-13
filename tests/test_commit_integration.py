from datetime import datetime, timedelta, timezone
import hashlib

import pytest

from src.valo_platform.action_envelope.execution_gate import ExecutionGateResult
from src.valo_platform.action_envelope.models import (
    ActionDecision,
    ActionEnvelope,
    ActionType,
    ActorRole,
    ClearanceState,
    ConsequenceClass,
    GovernanceClearance,
    PurposeRecordRef,
)
from src.valo_platform.action_envelope.outcome_attestation import (
    CommitChainError,
    EvidenceBoundCommitChain,
)
from src.valo_platform.decision_governance.action_case import (
    ActionCaseLifecycleState,
    ActionCaseRecord,
)
from src.valo_platform.decision_governance.continuity import (
    ContinuityBasisSnapshot,
    ContinuityImpactAssessment,
    ContinuityMateriality,
)
from src.valo_platform.decision_governance.models import ActionCaseStatus
from src.valo_platform.models.core_receipt import ExecutionDecision, Receipt
from src.valo_platform.operational_continuity.commit_integration import (
    authorize_revalidated_action_case_commit,
    verify_revalidated_action_case_commit_binding,
)
from src.valo_platform.operational_continuity.observers import ObservationBinding
from src.valo_platform.operational_continuity.revalidation import (
    build_revalidation_request,
    evaluate_revalidation_request,
)
from src.valo_platform.operational_continuity.source_adapters import (
    ContinuitySourceBundle,
    ContinuitySourceDomain,
    ContinuitySourceObservation,
)
from src.valo_platform.operational_continuity.source_baselines import (
    ContinuitySourceBaseline,
    ContinuitySourceBaselineEntry,
)


NOW = datetime(2026, 8, 1, 14, 0, tzinfo=timezone.utc)
CURRENT = {
    "authority": "sha256:delegation",
    "policy": "sha256:policy",
    "context": "sha256:context",
    "state": "sha256:case-A",
    "evidence": "sha256:evidence",
}


class FixtureSigner:
    def sign(self, *, attester_id, attester_authority, payload_hash):
        return "fixture:" + hashlib.sha256(
            f"{attester_id}|{attester_authority}|{payload_hash}".encode()
        ).hexdigest()

    def verify(self, *, attester_id, attester_authority, payload_hash, signature):
        return signature == self.sign(
            attester_id=attester_id,
            attester_authority=attester_authority,
            payload_hash=payload_hash,
        )


def chain():
    return EvidenceBoundCommitChain(
        "tenant-1",
        attestation_signer=FixtureSigner(),
        now=lambda: NOW + timedelta(seconds=4),
    )


def action_case():
    return ActionCaseRecord(
        case_id="case-A",
        tenant_id="tenant-1",
        environment="test",
        record_version=3,
        case_hash=CURRENT["state"],
        decision_state=ActionCaseStatus.READY_FOR_REHT,
        lifecycle_state=ActionCaseLifecycleState.CLEARED,
        purpose_record_ref=PurposeRecordRef(
            purpose_id="purpose-1",
            version="1",
            record_ref="purpose:1",
            fingerprint="sha256:purpose",
            established_by="board",
            authority_ref="board:1",
        ),
        purpose_binding_ref="purpose-binding-1",
        mandate_ref="mandate:1",
        mandate_fingerprint="sha256:mandate",
        delegation_ref="delegation:1",
        delegation_fingerprint=CURRENT["authority"],
        policy_refs=("policy:1",),
        policy_fingerprint=CURRENT["policy"],
        evidence_refs=("evidence:case",),
        evidence_fingerprint=CURRENT["evidence"],
        context_refs=("context:1",),
        context_fingerprint=CURRENT["context"],
        action_class=ActionType.PROCESS_PAYMENT,
        consequence_class=ConsequenceClass.HIGH,
        clearance_ref="clr-1",
        created_at=NOW - timedelta(minutes=10),
        updated_at=NOW - timedelta(minutes=1),
        submitted_at=NOW - timedelta(minutes=9),
        evaluated_at=NOW - timedelta(minutes=8),
        cleared_at=NOW - timedelta(minutes=7),
    )


def envelope():
    return ActionEnvelope(
        action_id="case-A",
        action_type=ActionType.PROCESS_PAYMENT,
        actor_id="actor-1",
        actor_role=ActorRole.AUTOMATION,
        tenant_id="tenant-1",
        consequence_class=ConsequenceClass.HIGH,
    )


def clearance():
    return GovernanceClearance(
        clearance_id="clr-1",
        action_id="case-A",
        tenant_id="tenant-1",
        decision=ActionDecision.ALLOW,
        state=ClearanceState.ACTIVE,
        authority_fingerprint=CURRENT["authority"],
        policy_fingerprint=CURRENT["policy"],
        context_fingerprint=CURRENT["context"],
        state_fingerprint=CURRENT["state"],
        evidence_fingerprint=CURRENT["evidence"],
        evidence_refs=["evidence:clearance"],
        valid_from=NOW - timedelta(minutes=7),
        valid_until=NOW + timedelta(hours=1),
        idempotency_key="case-A-commit",
        replay_nonce="case-A-nonce",
    )


def gate():
    return ExecutionGateResult(
        allowed=True,
        commit_preclusive=False,
        clearance_id="clr-1",
        reason="CLEARANCE_VALID",
        details={
            "racs_verification": {
                "verified": True,
                "payload_digest": "sha256:signed-clearance",
            }
        },
    )


def receipt():
    return Receipt(
        request_id="request-1",
        decision=ExecutionDecision.ALLOW,
        actor_id="actor-1",
        actor_role="automation",
        evidence_ids=["evidence:existing"],
    )


def basis():
    return ContinuityBasisSnapshot(
        snapshot_id="basis-1",
        tenant_id="tenant-1",
        action_case_id="case-A",
        action_case_hash=CURRENT["state"],
        clearance_ref="clr-1",
        observed_at=NOW - timedelta(minutes=7),
        authority_fingerprint=CURRENT["authority"],
        policy_fingerprint=CURRENT["policy"],
        evidence_fingerprint=CURRENT["evidence"],
        context_fingerprint=CURRENT["context"],
        state_fingerprint=CURRENT["state"],
        purpose_binding_ref="purpose-binding-1",
        valid_until=NOW + timedelta(hours=1),
    )


def observation_binding():
    return ObservationBinding(
        tenant_id="tenant-1",
        action_case_id="case-A",
        action_case_hash=CURRENT["state"],
        clearance_ref="clr-1",
        observer_ref="observer:commit-boundary",
    )


def source_baseline():
    return ContinuitySourceBaseline(
        binding=observation_binding(),
        captured_at=NOW - timedelta(minutes=7),
        entries=(
            ContinuitySourceBaselineEntry(
                domain=ContinuitySourceDomain.POLICY,
                source_ref="source:policy",
                fingerprint="sha256:source-policy",
                evidence_refs=("evidence:policy",),
                captured_at=NOW - timedelta(minutes=7),
            ),
        ),
    )


def source_bundle():
    return ContinuitySourceBundle(
        binding=observation_binding(),
        observed_at=NOW,
        observations=(
            ContinuitySourceObservation(
                domain=ContinuitySourceDomain.POLICY,
                source_ref="source:policy",
                expected_fingerprint="sha256:source-policy",
                current_fingerprint="sha256:source-policy",
                observed_at=NOW,
                evidence_refs=("evidence:policy",),
                integrity_status="verified",
            ),
        ),
    )


def revalidation_chain():
    request = build_revalidation_request(
        request_id="revalidation-1",
        requester_ref="execution-gateway:1",
        basis=basis(),
        source_baseline=source_baseline(),
        source_bundle=source_bundle(),
        current_fingerprints=CURRENT,
        requested_at=NOW + timedelta(seconds=1),
    )
    assessment = ContinuityImpactAssessment(
        assessment_id="assessment-1",
        tenant_id="tenant-1",
        trigger_refs=tuple(trigger.trigger_id for trigger in request.triggers),
        action_case_id="case-A",
        action_case_hash=CURRENT["state"],
        clearance_ref="clr-1",
        materiality=ContinuityMateriality.NO_MATERIAL_CHANGE,
        impact_dimensions=("operational_continuity",),
        reason_codes=("all_sources_revalidated",),
        evidence_refs=(request.evidence_ref,),
        assessor_refs=("vaig:continuity",),
        confidence=1.0,
        assessed_at=NOW + timedelta(seconds=2),
    )
    result = evaluate_revalidation_request(
        request=request,
        assessment=assessment,
        clearance_state=ClearanceState.ACTIVE,
        now=NOW + timedelta(seconds=3),
        decider_ref="reht:continuity",
        decision_authority_ref="authority:reht",
    )
    return request, assessment, result


def authorize(**updates):
    request, assessment, result = revalidation_chain()
    request = updates.pop("revalidation_request", request)
    assessment = updates.pop("assessment", assessment)
    result = updates.pop("revalidation_result", result)
    current = updates.pop("current_fingerprints", CURRENT)
    c = updates.pop("chain", chain())
    binding = authorize_revalidated_action_case_commit(
        c,
        updates.pop("action_case", action_case()),
        updates.pop("envelope", envelope()),
        updates.pop("clearance", clearance()),
        updates.pop("gate_result", gate()),
        updates.pop("receipt", receipt()),
        current_fingerprints=current,
        adapter="payments",
        target_system_ref="erp-1",
        revalidation_request=request,
        assessment=assessment,
        revalidation_result=result,
        checked_at=NOW + timedelta(seconds=4),
        **updates,
    )
    return c, binding, request, assessment, result


def test_full_revalidation_chain_is_bound_into_commit_and_receipt():
    c, binding, request, assessment, result = authorize()
    authorization = c.authorizations[0]
    metadata = binding.commit_binding.receipt_snapshot["metadata"]

    assert binding.request_ref == request.evidence_ref
    assert binding.assessment_digest == assessment.assessment_digest
    assert binding.result_digest == result.result_digest
    assert metadata["continuity_revalidation_request_ref"] == request.evidence_ref
    assert metadata["continuity_revalidation_result_digest"] == result.result_digest
    assert binding.request_ref in authorization.revalidation_refs
    assert binding.assessment_ref in authorization.revalidation_refs
    assert binding.result_ref in authorization.revalidation_refs
    assert verify_revalidated_action_case_commit_binding(binding, authorization)


def test_receipt_or_wrapper_tamper_is_detected():
    c, binding, *_ = authorize()
    authorization = c.authorizations[0]
    snapshot = {
        **binding.commit_binding.receipt_snapshot,
        "metadata": {
            **binding.commit_binding.receipt_snapshot["metadata"],
            "continuity_revalidation_result_digest": "sha256:tampered",
        },
    }
    tampered_commit = binding.commit_binding.model_copy(
        update={"receipt_snapshot": snapshot}
    )
    tampered = binding.model_copy(update={"commit_binding": tampered_commit})
    assert not verify_revalidated_action_case_commit_binding(tampered, authorization)

    bad_hash = binding.model_copy(update={"content_hash": "sha256:bad"})
    assert not verify_revalidated_action_case_commit_binding(bad_hash, authorization)


def test_mismatched_request_or_assessment_is_rejected():
    request, assessment, result = revalidation_chain()
    foreign_request = request.model_copy(
        update={"request_digest": "sha256:other-request"}
    )
    assessment_for_foreign_request = assessment.model_copy(
        update={"evidence_refs": (foreign_request.evidence_ref,)}
    )
    with pytest.raises(CommitChainError, match="REQUEST_REF_MISMATCH"):
        authorize(
            revalidation_request=foreign_request,
            assessment=assessment_for_foreign_request,
            revalidation_result=result,
        )

    foreign_assessment = assessment.model_copy(
        update={"assessment_id": "other-assessment"}
    )
    with pytest.raises(CommitChainError, match="ASSESSMENT_REF_MISMATCH"):
        authorize(
            revalidation_request=request,
            assessment=foreign_assessment,
            revalidation_result=result,
        )

    invalid_vaig_assessment = assessment.model_copy(
        update={"evidence_refs": ("evidence:other",)}
    )
    with pytest.raises(CommitChainError, match="VAIG_ASSESSMENT_INVALID"):
        authorize(
            revalidation_request=request,
            assessment=invalid_vaig_assessment,
            revalidation_result=result,
        )


def test_current_state_mismatch_is_rejected_before_commit():
    with pytest.raises(CommitChainError, match="CURRENT_STATE_MISMATCH"):
        authorize(
            current_fingerprints={**CURRENT, "policy": "sha256:changed"}
        )


def test_result_from_future_is_rejected():
    request, assessment, result = revalidation_chain()
    future = result.model_copy(
        update={"completed_at": NOW + timedelta(seconds=10)}
    )
    with pytest.raises(CommitChainError, match="RESULT_FROM_FUTURE"):
        authorize(
            revalidation_request=request,
            assessment=assessment,
            revalidation_result=future,
        )
