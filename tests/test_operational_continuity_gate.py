from datetime import datetime, timedelta, timezone
import hashlib

import pytest

from src.valo_platform.action_envelope.action_case_commit_bridge import (
    authorize_action_case_commit,
    verify_action_case_commit_binding,
)
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
    ContinuityClearanceState,
    ContinuityDecision,
    canonical_fingerprint_digest,
)
from src.valo_platform.decision_governance.models import ActionCaseStatus
from src.valo_platform.models.core_receipt import ExecutionDecision, Receipt

NOW = datetime(2026, 8, 1, 8, 0, tzinfo=timezone.utc)
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
        "tenant-1", attestation_signer=FixtureSigner(), now=lambda: NOW
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
        created_at=NOW,
        updated_at=NOW,
        submitted_at=NOW,
        evaluated_at=NOW,
        cleared_at=NOW,
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
        valid_from=NOW - timedelta(minutes=1),
        valid_until=NOW + timedelta(hours=1),
        idempotency_key="continuity-case-A",
        replay_nonce="continuity-nonce-A",
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
        evidence_ids=[],
    )


def continuity_decision(current=CURRENT, **updates):
    data = dict(
        continuity_decision_id="continuity-1",
        tenant_id="tenant-1",
        action_case_id="case-A",
        action_case_hash=CURRENT["state"],
        clearance_ref="clr-1",
        basis_snapshot_ref="basis-1",
        basis_snapshot_digest="sha256:basis",
        trigger_refs=("trigger-1",),
        impact_assessment_refs=("assessment-1",),
        racs_outcome=ActionDecision.ALLOW,
        clearance_state_after=ContinuityClearanceState.ACTIVE,
        requires_new_action_case=False,
        requires_new_clearance=False,
        reason_codes=("decision_basis_continuity_preserved",),
        evidence_refs=("evidence:continuity",),
        decider_ref="reht:continuity",
        decision_authority_ref="authority:reht",
        current_fingerprint_digest=canonical_fingerprint_digest(current),
        decided_at=NOW - timedelta(seconds=1),
        valid_until=NOW + timedelta(minutes=5),
    )
    data.update(updates)
    return ContinuityDecision(**data)


def authorize(*, current=CURRENT, decision=None, required=True, verified=True):
    c = chain()
    gate_result = gate()
    if decision is not None and verified:
        gate_result.details["continuity_verification"] = {
            "verified": True,
            "decision_ref": decision.continuity_decision_id,
            "decision_digest": decision.decision_digest,
        }
    binding = authorize_action_case_commit(
        c,
        action_case(),
        envelope(),
        clearance(),
        gate_result,
        receipt(),
        current_fingerprints=current,
        adapter="payments",
        target_system_ref="erp-1",
        continuity_required=required,
        continuity_decision=decision,
        continuity_checked_at=NOW if decision is not None else None,
    )
    return c, binding


def test_continuity_required_rejects_missing_decision():
    with pytest.raises(CommitChainError, match="CONTINUITY_DECISION_REQUIRED"):
        authorize(decision=None)


def test_continuity_requires_gateway_verification():
    with pytest.raises(CommitChainError, match="CONTINUITY_VERIFICATION_REQUIRED"):
        authorize(decision=continuity_decision(), verified=False)


def test_valid_continuity_is_bound_into_authorization_and_receipt():
    c, binding = authorize(decision=continuity_decision())
    authorization = c.authorizations[0]
    metadata = binding.receipt_snapshot["metadata"]
    assert binding.continuity_decision_ref == "continuity-1"
    assert "continuity-1" in authorization.revalidation_refs
    assert metadata["continuity_basis_snapshot_ref"] == "basis-1"
    assert metadata["clearance_state_at_commit"] == "active"
    assert verify_action_case_commit_binding(binding, authorization)


def test_cached_continuity_fingerprint_cannot_authorize_changed_dependency():
    current = {**CURRENT, "dependency": "sha256:new"}
    stale = continuity_decision(current=CURRENT)
    with pytest.raises(
        CommitChainError, match="CONTINUITY_CURRENT_FINGERPRINT_MISMATCH"
    ):
        authorize(current=current, decision=stale)


def test_non_executable_or_replacement_continuity_decision_is_rejected():
    defer = continuity_decision(
        racs_outcome=ActionDecision.DEFER,
        clearance_state_after=ContinuityClearanceState.DEFERRED,
        requires_new_clearance=True,
    )
    with pytest.raises(CommitChainError, match="NEW_CLEARANCE_REQUIRED"):
        authorize(decision=defer)


def test_continuity_binding_mismatch_is_rejected():
    wrong = continuity_decision(clearance_ref="other")
    with pytest.raises(CommitChainError, match="CONTINUITY_BINDING_MISMATCH"):
        authorize(decision=wrong)
