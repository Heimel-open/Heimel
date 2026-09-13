from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from valo_platform.action_envelope.models import (
    ActionConstraint,
    ActionDecision,
    ClearanceState,
    ConsequenceClass,
    GovernanceClearance,
    Reversibility,
)
from valo_platform.public_procurement import (
    AuthorityBinding,
    CommitActionType,
    EvidenceReference,
    RequestedExternalCommit,
    RiskLevel,
    build_procurement_action_case,
)
from valo_platform.public_procurement.clearance_profiles import (
    AssessmentDisposition,
    ProcurementProfileId,
    default_clearance_profiles,
)
from valo_platform.public_procurement.runtime import (
    PROCUREMENT_COMMIT_DIGEST_CONSTRAINT,
    ProcurementClearanceRequest,
    ProcurementIntegrityState,
    ProcurementRuntimeError,
    bind_procurement_receipt_refs,
    bind_reht_clearance,
    build_racs_bound_procurement_commit,
    evaluate_procurement_continuous_integrity,
    prepare_procurement_clearance_request,
)


NOW = datetime(2026, 7, 29, 19, 30, tzinfo=timezone.utc)
DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
DIGEST_C = "sha256:" + "c" * 64


def evidence(evidence_id: str, evidence_type: str, *, expires_in_minutes: int = 60):
    return EvidenceReference(
        evidence_id=evidence_id,
        evidence_type=evidence_type,
        source_ref=f"source:{evidence_id}",
        content_digest=DIGEST_A,
        issued_at=NOW - timedelta(days=1),
        expires_at=NOW + timedelta(minutes=expires_in_minutes),
    )


def authority() -> AuthorityBinding:
    return AuthorityBinding(
        principal_id="principal:procurement-director",
        mandate_ref="mandate:procurement:2026",
        delegation_ref="delegation:procurement:5m",
        authority_version="5",
        valid_at=NOW,
        evidence_refs=("authority-attestation:5",),
    )


def payment_case(
    *,
    risk_level: RiskLevel = RiskLevel.HIGH,
    evidence_types: tuple[str, ...] = (
        "invoice",
        "delivery_attestation",
        "bank_account_verification",
    ),
    current_state_digest: str = DIGEST_B,
):
    return build_procurement_action_case(
        case_id="case:payment:1",
        action_ref="payment:invoice:INV-1",
        purpose="Pay verified invoice under the public contract",
        principal_id=authority().principal_id,
        mandate_ref=authority().mandate_ref,
        authority=authority(),
        procedure_ref="procedure:1",
        contract_ref="contract:1",
        operator_ref="operator:1",
        policy_version="procurement-policy:2026.7",
        criteria_versions=(),
        evidence_refs=tuple(
            evidence(f"evidence:{index}", evidence_type)
            for index, evidence_type in enumerate(evidence_types, start=1)
        ),
        current_state_digest=current_state_digest,
        risk_level=risk_level,
        reversible=False,
        consequence="Transfer NOK 2 500 000 to the supplier bank account",
        requested_commit=RequestedExternalCommit(
            action_type=CommitActionType.EXECUTE_PAYMENT,
            target_system="erp:buyer-1",
            resource_ref="invoice:INV-1",
            payload_digest=DIGEST_C,
            idempotency_key="payment:INV-1:v1",
            reversible=False,
            consequence="Execute supplier payment",
        ),
        created_at=NOW,
    )


def request(*, case=None, observed_at=NOW):
    return prepare_procurement_clearance_request(
        tenant_id="tenant:buyer-1",
        environment_id="production",
        action_case=case or payment_case(),
        profile=default_clearance_profiles()[ProcurementProfileId.PAYMENT],
        observed_at=observed_at,
    )


def clearance(
    clearance_request,
    *,
    decision: ActionDecision = ActionDecision.ALLOW,
    state: ClearanceState = ClearanceState.ACTIVE,
    commit_digest: str | None = None,
    valid_from=NOW - timedelta(minutes=1),
    valid_until=NOW + timedelta(minutes=30),
):
    return GovernanceClearance(
        clearance_id="reht-clearance:payment:1",
        action_id=clearance_request.case_id,
        tenant_id=clearance_request.tenant_id,
        decision=decision,
        state=state,
        authority_refs=list(clearance_request.authority_refs),
        policy_refs=list(clearance_request.policy_refs),
        evidence_refs=list(clearance_request.evidence_refs),
        authority_fingerprint=clearance_request.authority_fingerprint,
        policy_fingerprint=clearance_request.policy_fingerprint,
        context_fingerprint=clearance_request.context_fingerprint,
        state_fingerprint=clearance_request.request_digest,
        evidence_fingerprint=clearance_request.evidence_fingerprint,
        consequence_class=clearance_request.consequence_class,
        reversibility=clearance_request.reversibility,
        constraints=[
            ActionConstraint(
                constraint_id="constraint:commit-digest",
                constraint_type=PROCUREMENT_COMMIT_DIGEST_CONSTRAINT,
                value=commit_digest or clearance_request.commit_digest,
                reason="Bind clearance to the exact requested external commit",
            )
        ],
        issued_at=NOW,
        valid_from=valid_from,
        valid_until=valid_until,
        idempotency_key=clearance_request.idempotency_key,
        receipt_ref="receipt:clearance:1",
    )


def test_request_binds_tenant_profile_consequence_and_exact_commit() -> None:
    prepared = request(case=payment_case(risk_level=RiskLevel.CRITICAL))

    assert prepared.assessment.disposition is AssessmentDisposition.READY_FOR_REHT
    assert prepared.tenant_id == "tenant:buyer-1"
    assert prepared.profile_id is ProcurementProfileId.PAYMENT
    assert prepared.consequence_class is ConsequenceClass.C4_CRITICAL
    assert prepared.reversibility is Reversibility.IRREVERSIBLE
    assert prepared.commit_payload_digest == DIGEST_C
    assert prepared.grants_authority is False


def test_request_digest_rejects_tampering() -> None:
    payload = request().model_dump(mode="json")
    payload["target_system"] = "attacker-system"

    with pytest.raises(ValidationError, match="request_digest"):
        ProcurementClearanceRequest(**payload)


def test_exact_external_clearance_becomes_executable_binding() -> None:
    prepared = request()
    binding = bind_reht_clearance(
        request=prepared,
        clearance=clearance(prepared),
        observed_at=NOW,
    )

    assert binding.executable is True
    assert binding.decision is ActionDecision.ALLOW
    assert binding.clearance_receipt_ref == "receipt:clearance:1"
    assert binding.grants_authority is False


def test_wrong_commit_digest_constraint_fails_closed() -> None:
    prepared = request()

    with pytest.raises(ProcurementRuntimeError, match="COMMIT_DIGEST_MISMATCH"):
        bind_reht_clearance(
            request=prepared,
            clearance=clearance(prepared, commit_digest=DIGEST_A),
            observed_at=NOW,
        )


def test_cross_tenant_clearance_is_rejected() -> None:
    prepared = request()
    foreign = clearance(prepared).model_copy(update={"tenant_id": "tenant:other"})

    with pytest.raises(ProcurementRuntimeError, match="TENANT_MISMATCH"):
        bind_reht_clearance(request=prepared, clearance=foreign, observed_at=NOW)


def test_permissive_clearance_cannot_override_missing_evidence() -> None:
    incomplete = request(case=payment_case(evidence_types=("invoice",)))
    assert incomplete.assessment.disposition is AssessmentDisposition.GATHER_EVIDENCE

    with pytest.raises(ProcurementRuntimeError, match="PERMISSIVE_CLEARANCE"):
        bind_reht_clearance(
            request=incomplete,
            clearance=clearance(incomplete, decision=ActionDecision.ALLOW),
            observed_at=NOW,
        )


def test_non_permissive_clearance_binds_but_cannot_reach_racs() -> None:
    prepared = request()
    binding = bind_reht_clearance(
        request=prepared,
        clearance=clearance(prepared, decision=ActionDecision.STEP_UP),
        observed_at=NOW,
    )
    event = evaluate_procurement_continuous_integrity(
        binding=binding,
        current_action_case=payment_case(),
        profile=default_clearance_profiles()[ProcurementProfileId.PAYMENT],
        observed_at=NOW,
    )

    assert binding.executable is False
    with pytest.raises(ProcurementRuntimeError, match="NOT_EXECUTABLE"):
        build_racs_bound_procurement_commit(
            binding=binding,
            integrity_event=event,
            observed_at=NOW,
        )


def test_current_integrity_event_allows_exact_racs_bound_commit() -> None:
    prepared = request()
    binding = bind_reht_clearance(
        request=prepared,
        clearance=clearance(prepared),
        observed_at=NOW,
    )
    event = evaluate_procurement_continuous_integrity(
        binding=binding,
        current_action_case=payment_case(),
        profile=default_clearance_profiles()[ProcurementProfileId.PAYMENT],
        observed_at=NOW + timedelta(minutes=1),
    )
    commit = build_racs_bound_procurement_commit(
        binding=binding,
        integrity_event=event,
        observed_at=NOW + timedelta(minutes=1),
    )

    assert event.state is ProcurementIntegrityState.CURRENT
    assert commit.commit_digest == prepared.commit_digest
    assert commit.payload_digest == prepared.commit_payload_digest
    assert commit.executed is False
    assert commit.grants_authority is False


def test_bank_change_requires_revalidation_and_blocks_commit() -> None:
    prepared = request()
    binding = bind_reht_clearance(
        request=prepared,
        clearance=clearance(prepared),
        observed_at=NOW,
    )
    event = evaluate_procurement_continuous_integrity(
        binding=binding,
        current_action_case=payment_case(current_state_digest=DIGEST_A),
        profile=default_clearance_profiles()[ProcurementProfileId.PAYMENT],
        observed_at=NOW + timedelta(minutes=1),
        changed_fields=("bank_details",),
    )

    assert event.state is ProcurementIntegrityState.REVALIDATION_REQUIRED
    assert event.revalidation_required is True
    assert "MATERIAL_CHANGE_TRIGGERED" in event.reasons
    with pytest.raises(ProcurementRuntimeError, match="INTEGRITY_EVENT_REQUEST_MISMATCH"):
        build_racs_bound_procurement_commit(
            binding=binding,
            integrity_event=event,
            observed_at=NOW + timedelta(minutes=1),
        )


def test_expired_clearance_is_rejected_before_binding() -> None:
    prepared = request()

    with pytest.raises(ProcurementRuntimeError, match="VALIDITY_WINDOW"):
        bind_reht_clearance(
            request=prepared,
            clearance=clearance(
                prepared,
                valid_from=NOW - timedelta(hours=2),
                valid_until=NOW - timedelta(hours=1),
            ),
            observed_at=NOW,
        )


def test_receipt_binding_only_references_canonical_receipts() -> None:
    prepared = request()
    binding = bind_reht_clearance(
        request=prepared,
        clearance=clearance(prepared),
        observed_at=NOW,
    )
    receipts = bind_procurement_receipt_refs(
        binding=binding,
        execution_receipt_ref="receipt:execution:1",
        outcome_receipt_ref="receipt:outcome:1",
    )

    assert receipts.clearance_receipt_ref == "receipt:clearance:1"
    assert receipts.execution_receipt_ref == "receipt:execution:1"
    assert receipts.outcome_receipt_ref == "receipt:outcome:1"
    assert receipts.grants_authority is False
