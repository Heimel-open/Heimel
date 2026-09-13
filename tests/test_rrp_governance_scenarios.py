"""Governance scenario tests for RRP Evidence Pipeline v2."""

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
from vaig.rrp.risk_contract import get_risk_contract


def make_source(source_id, source_type):
    return EvidenceSource(
        source_id=source_id,
        source_type=source_type.value,
        provenance="test",
        raw_payload_digest=f"sha256:{source_id}",
        timestamp_acquired=datetime.now(timezone.utc).isoformat(),
        timestamp_submitted=datetime.now(timezone.utc).isoformat(),
    )


def make_condition(evidence_id, action_type, sources):
    contract = get_risk_contract(action_type)
    return EvidenceCondition(
        evidence_id=evidence_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        source_chain=sources,
        action_type=action_type,
        risk_contract_snapshot=contract,
        freshness_boundary_seconds=contract.get("freshness_seconds"),
        timestamp_validated=None,
        timestamp_expires=None,
        validation_status=ValidationStatus.SUBMITTED.value,
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


def test_stale_evidence_blocks_intent():
    cond = make_condition(
        "evc-stale-001",
        "LARGE_TRANSFER",
        [make_source("src-model", EvidenceSourceType.MODEL_OUTPUT)],
    )
    lifecycle = EvidenceValidationLifecycle(cond)
    lifecycle.transition(ValidationStatus.UNDER_VALIDATION, "validator", {})
    lifecycle.transition(ValidationStatus.STALE, "validator", {})

    with pytest.raises(ValueError, match="INTENT_BLOCKED"):
        IntentFactory.create(
            intent_id="int-stale-001",
            operator_id="op-test",
            evidence_condition=cond,
            action_type="LARGE_TRANSFER",
            action_parameters={},
            expected_outcome="blocked",
        )


def test_contested_evidence_blocks_intent():
    cond = make_condition(
        "evc-contested-001",
        "FLIGHT_CLEARANCE",
        [
            make_source("src-direct", EvidenceSourceType.DIRECT_OBSERVATION),
            make_source("src-human", EvidenceSourceType.HUMAN_REPORT),
        ],
    )
    lifecycle = EvidenceValidationLifecycle(cond)
    lifecycle.transition(ValidationStatus.UNDER_VALIDATION, "validator", {})
    lifecycle.transition(ValidationStatus.CONTESTED, "validator", {})

    with pytest.raises(ValueError, match="INTENT_BLOCKED"):
        IntentFactory.create(
            intent_id="int-contested-001",
            operator_id="op-test",
            evidence_condition=cond,
            action_type="FLIGHT_CLEARANCE",
            action_parameters={},
            expected_outcome="blocked",
        )


def test_override_allows_intent():
    IntentFactory.reset_domain("op-test")
    cond = make_condition(
        "evc-override-001",
        "FLIGHT_CLEARANCE",
        [
            make_source("src-direct", EvidenceSourceType.DIRECT_OBSERVATION),
            make_source("src-human", EvidenceSourceType.HUMAN_REPORT),
        ],
    )
    lifecycle = EvidenceValidationLifecycle(cond)
    lifecycle.transition(ValidationStatus.UNDER_VALIDATION, "validator", {})
    lifecycle.transition(ValidationStatus.CONTESTED, "validator", {})
    lifecycle.transition(ValidationStatus.OVERRIDDEN, "ATC-SUPERVISOR-L3", {})
    cond.validation_method = ValidationMethod.EXPERT_REVIEW.value
    cond.confidence_level = ConfidenceLevel.HIGH.value

    intent = IntentFactory.create(
        intent_id="int-override-001",
        operator_id="op-test",
        evidence_condition=cond,
        action_type="FLIGHT_CLEARANCE",
        action_parameters={},
        expected_outcome="allowed",
    )
    assert intent.intent_id == "int-override-001"


def test_insufficient_model_evidence_blocks_intent():
    cond = make_condition(
        "evc-insufficient-001",
        "LARGE_TRANSFER",
        [make_source("src-model", EvidenceSourceType.MODEL_OUTPUT)],
    )
    lifecycle = EvidenceValidationLifecycle(cond)
    lifecycle.transition(ValidationStatus.UNDER_VALIDATION, "validator", {})
    lifecycle.transition(ValidationStatus.INSUFFICIENT, "validator", {})
    cond.validation_method = ValidationMethod.AUTOMATED_CHECK.value
    cond.confidence_level = ConfidenceLevel.UNCERTAIN.value

    with pytest.raises(ValueError, match="INTENT_BLOCKED"):
        IntentFactory.create(
            intent_id="int-insufficient-001",
            operator_id="op-test",
            evidence_condition=cond,
            action_type="LARGE_TRANSFER",
            action_parameters={},
            expected_outcome="blocked",
        )
