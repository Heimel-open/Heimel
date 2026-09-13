"""Lifecycle and RiskContract tests for RRP Evidence Pipeline v2."""

from datetime import datetime, timezone

import pytest

from vaig.rrp.evidence import (
    ConfidenceLevel,
    EvidenceCondition,
    EvidenceSource,
    EvidenceSourceType,
    EvidenceValidationLifecycle,
    ValidationMethod,
    ValidationStatus,
)
from vaig.rrp.intent import IntentFactory
from vaig.rrp.risk_contract import get_risk_contract, is_domain_isolated, RiskDomain


def make_source(source_id="src", source_type=EvidenceSourceType.SYSTEM_LOG):
    return EvidenceSource(
        source_id=source_id,
        source_type=source_type.value,
        provenance="test",
        raw_payload_digest=f"sha256:{source_id}",
        timestamp_acquired=datetime.now(timezone.utc).isoformat(),
        timestamp_submitted=datetime.now(timezone.utc).isoformat(),
    )


def make_condition(status=ValidationStatus.SUBMITTED, action_type="LARGE_TRANSFER", sources=None):
    contract = get_risk_contract(action_type)
    return EvidenceCondition(
        evidence_id="evc-test-001",
        created_at=datetime.now(timezone.utc).isoformat(),
        source_chain=sources if sources is not None else [],
        action_type=action_type,
        risk_contract_snapshot=contract,
        freshness_boundary_seconds=contract.get("freshness_seconds"),
        timestamp_validated=None,
        timestamp_expires=None,
        validation_status=status.value,
        validator="",
        validation_method=ValidationMethod.UNVALIDATED.value,
        validation_reasoning="",
        confidence_level=ConfidenceLevel.UNKNOWN.value,
        confidence_reasoning="",
        contested_by=None,
        contest_reasoning=None,
        bound_intents=[],
        override_authority=None,
        override_reasoning=None,
        override_timestamp=None,
        validation_history=[],
    )


def test_contract_is_hardcoded_copy():
    contract = get_risk_contract("LARGE_TRANSFER")
    assert contract["tier"] == "critical"
    assert contract["requires_corroboration"] is True
    contract["tier"] = "low"
    assert get_risk_contract("LARGE_TRANSFER")["tier"] == "critical"


def test_unknown_contract_defaults_to_elevated():
    contract = get_risk_contract("UNKNOWN_ACTION")
    assert contract["tier"] == "elevated"
    assert contract["requires_evidence"] is True


def test_critical_contracts_require_evidence():
    for action in ["LARGE_TRANSFER", "FLIGHT_CLEARANCE", "MEDICAL_INTERVENTION"]:
        assert get_risk_contract(action)["requires_evidence"] is True


def test_domain_isolation_pairs():
    assert is_domain_isolated(RiskDomain.FINANCIAL, RiskDomain.MEDICAL) is True
    assert is_domain_isolated(RiskDomain.AVIATION, RiskDomain.FINANCIAL) is True
    assert is_domain_isolated(RiskDomain.GENERAL, RiskDomain.GENERAL) is False


def test_cross_domain_intent_blocked():
    IntentFactory.reset_domain("op-test")
    cond = make_condition(
        ValidationStatus.SUBMITTED,
        sources=[
            make_source("src-a", EvidenceSourceType.EXTERNAL_FEED),
            make_source("src-b", EvidenceSourceType.HUMAN_REPORT),
        ],
    )
    lifecycle = EvidenceValidationLifecycle(cond)
    lifecycle.validate_against_contract()

    with pytest.raises(ValueError, match="ISOLATED"):
        IntentFactory.create(
            intent_id="int-cross-001",
            operator_id="op-test",
            evidence_condition=cond,
            action_type="LARGE_TRANSFER",
            action_parameters={},
            expected_outcome="blocked",
            source_domain="financial",
            target_domain="medical",
        )


def test_corroboration_enforced_by_contract():
    cond = make_condition(sources=[make_source("src-single", EvidenceSourceType.MODEL_OUTPUT)])
    lifecycle = EvidenceValidationLifecycle(cond)
    lifecycle.validate_against_contract()

    assert cond.validation_status == ValidationStatus.INSUFFICIENT.value
    assert "corroboration" in cond.validation_reasoning.lower()


def test_low_risk_no_evidence_required():
    cond = make_condition(action_type="STATUS_CHECK", sources=[make_source()])
    lifecycle = EvidenceValidationLifecycle(cond)
    lifecycle.validate_against_contract()

    assert cond.validation_status == ValidationStatus.VALIDATED.value
    assert cond.validation_method == ValidationMethod.CONTRACT_ENFORCED.value


@pytest.mark.parametrize(
    "status",
    [ValidationStatus.INSUFFICIENT, ValidationStatus.CONTRACT_BLOCKED],
)
def test_intent_blocked_on_non_admissible(status):
    cond = make_condition(status)
    with pytest.raises(ValueError, match="INTENT_BLOCKED"):
        IntentFactory.create(
            intent_id=f"int-{status.value}",
            operator_id="op-test",
            evidence_condition=cond,
            action_type="LARGE_TRANSFER",
            action_parameters={},
            expected_outcome="blocked",
        )


def test_intent_allowed_on_validated():
    IntentFactory.reset_domain("op-test")
    cond = make_condition(ValidationStatus.VALIDATED)
    intent = IntentFactory.create(
        intent_id="int-val-001",
        operator_id="op-test",
        evidence_condition=cond,
        action_type="LARGE_TRANSFER",
        action_parameters={},
        expected_outcome="allowed",
    )
    assert intent.intent_id == "int-val-001"
