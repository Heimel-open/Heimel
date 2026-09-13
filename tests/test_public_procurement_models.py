from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from valo_platform.public_procurement import (
    AuthorityBinding,
    AwardDecision,
    AwardRecommendation,
    AwardStatus,
    CommitActionType,
    ContractModification,
    EvaluationResult,
    EvidenceReference,
    ModificationKind,
    Money,
    MoneyDelta,
    PaymentAction,
    PaymentActionKind,
    RequestedExternalCommit,
    RiskLevel,
    build_procurement_action_case,
    public_procurement_schema_bundle,
)
from valo_platform.public_procurement.models import CriterionScore, ProcurementActionCase


NOW = datetime(2026, 7, 29, 16, 0, tzinfo=timezone.utc)
DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
DIGEST_C = "sha256:" + "c" * 64


def evidence() -> EvidenceReference:
    return EvidenceReference(
        evidence_id="evidence:eligibility:1",
        evidence_type="eligibility_attestation",
        source_ref="registry:operator:987654321",
        content_digest=DIGEST_A,
        issued_at=NOW,
        expires_at=NOW + timedelta(days=30),
    )


def authority() -> AuthorityBinding:
    return AuthorityBinding(
        principal_id="principal:procurement-director",
        mandate_ref="mandate:procurement:2026",
        delegation_ref="delegation:award:5000000",
        authority_version="7",
        valid_at=NOW,
        evidence_refs=("evidence:delegation:7",),
    )


def requested_commit(action_type: CommitActionType = CommitActionType.COMMIT_AWARD) -> RequestedExternalCommit:
    return RequestedExternalCommit(
        action_type=action_type,
        target_system="eprocurement:no:buyer-1",
        resource_ref="procedure:2026-001",
        payload_digest=DIGEST_B,
        idempotency_key=f"commit:procedure:2026-001:{action_type.value}:v1",
        reversible=False,
        consequence="Create a legally consequential procurement state change",
    )


def action_case() -> ProcurementActionCase:
    return build_procurement_action_case(
        case_id="case:procurement:award:1",
        action_ref="award:procedure:2026-001",
        purpose="Award the contract to the best admissible tender",
        principal_id="principal:procurement-director",
        mandate_ref="mandate:procurement:2026",
        authority=authority(),
        procedure_ref="procedure:2026-001",
        contract_ref=None,
        operator_ref="operator:987654321",
        policy_version="procurement-policy:2026.7",
        criteria_versions=("criteria:2026-001:v3",),
        evidence_refs=(evidence(),),
        current_state_digest=DIGEST_C,
        risk_level=RiskLevel.HIGH,
        reversible=False,
        consequence="Commit the award and create a contract entitlement",
        requested_commit=requested_commit(),
        created_at=NOW,
    )


def test_action_case_is_canonically_digest_bound() -> None:
    case = action_case()

    assert case.case_digest.startswith("sha256:")
    assert case.authority.principal_id == case.principal_id
    assert case.authority.mandate_ref == case.mandate_ref
    assert case.grants_authority is False


def test_tampered_action_case_digest_is_rejected() -> None:
    payload = action_case().model_dump(mode="json")
    payload["consequence"] = "Different external consequence"

    with pytest.raises(ValidationError, match="case_digest"):
        ProcurementActionCase(**payload)


def test_unknown_fields_are_rejected() -> None:
    payload = evidence().model_dump(mode="json")
    payload["approved_by_ai"] = True

    with pytest.raises(ValidationError):
        EvidenceReference(**payload)


def test_evaluation_and_recommendation_cannot_grant_authority() -> None:
    with pytest.raises(ValidationError, match="cannot grant procurement authority"):
        EvaluationResult(
            evaluation_id="evaluation:1",
            tender_ref="tender:1",
            criterion_scores=(
                CriterionScore(
                    criterion_ref="criterion:quality",
                    raw_score=Decimal("90"),
                    weighted_score=Decimal("45"),
                ),
            ),
            total_score=Decimal("90"),
            evaluator_refs=("human:evaluator:1",),
            judge_version="sage-judge:4",
            ambiguity_score=Decimal("0.1"),
            evaluated_at=NOW,
            grants_authority=True,
        )

    with pytest.raises(ValidationError, match="cannot grant authority"):
        AwardRecommendation(
            recommendation_id="recommendation:1",
            procedure_ref="procedure:2026-001",
            recommended_tender_ref="tender:1",
            evaluation_refs=("evaluation:1",),
            reason="Highest admissible quality-adjusted score",
            created_at=NOW,
            grants_authority=True,
        )


def test_award_decision_requires_award_commit_binding() -> None:
    with pytest.raises(ValidationError, match="commit_award"):
        AwardDecision(
            award_decision_id="award:1",
            procedure_ref="procedure:2026-001",
            winning_tender_ref="tender:1",
            status=AwardStatus.CLEARED,
            authority=authority(),
            clearance_ref="reht-clearance:award:1",
            policy_version="procurement-policy:2026.7",
            decided_at=NOW,
            requested_commit=requested_commit(CommitActionType.EXECUTE_PAYMENT),
        )


def test_contract_modification_supports_value_reduction() -> None:
    modification = ContractModification(
        modification_id="modification:1",
        contract_ref="contract:1",
        kind=ModificationKind.VALUE,
        requested_at=NOW,
        value_delta=MoneyDelta(amount=Decimal("-125000"), currency="NOK"),
        rationale="Reduce scope and total contract exposure",
        evidence_refs=(evidence(),),
        authority=authority(),
        clearance_ref="reht-clearance:modification:1",
        requested_commit=requested_commit(CommitActionType.MODIFY_CONTRACT),
    )

    assert modification.value_delta is not None
    assert modification.value_delta.amount == Decimal("-125000")


def test_payment_action_commit_type_must_match_action() -> None:
    with pytest.raises(ValidationError, match="hold_payment"):
        PaymentAction(
            payment_action_id="payment-action:1",
            invoice_ref="invoice:1",
            action_kind=PaymentActionKind.HOLD,
            amount=Money(amount=Decimal("250000"), currency="NOK"),
            bank_account_ref="bank-account:operator:1:v2",
            authority=authority(),
            clearance_ref="reht-clearance:payment:1",
            requested_commit=requested_commit(CommitActionType.EXECUTE_PAYMENT),
        )

    held = PaymentAction(
        payment_action_id="payment-action:1",
        invoice_ref="invoice:1",
        action_kind=PaymentActionKind.HOLD,
        amount=Money(amount=Decimal("250000"), currency="NOK"),
        bank_account_ref="bank-account:operator:1:v2",
        authority=authority(),
        clearance_ref="reht-clearance:payment:1",
        requested_commit=requested_commit(CommitActionType.HOLD_PAYMENT),
    )

    assert held.requested_commit.action_type is CommitActionType.HOLD_PAYMENT


def test_expired_before_issue_is_rejected() -> None:
    with pytest.raises(ValidationError, match="expires_at"):
        EvidenceReference(
            evidence_id="evidence:bad",
            evidence_type="eligibility_attestation",
            source_ref="registry:operator:987654321",
            content_digest=DIGEST_A,
            issued_at=NOW,
            expires_at=NOW - timedelta(seconds=1),
        )


def test_schema_bundle_is_versioned_and_complete() -> None:
    bundle = public_procurement_schema_bundle()

    assert bundle["schema_version"] == "0.1.0"
    assert "ProcurementActionCase" in bundle["models"]
    assert "AwardDecision" in bundle["models"]
    assert "MoneyDelta" in bundle["models"]
    assert bundle["models"]["ProcurementActionCase"]["additionalProperties"] is False
