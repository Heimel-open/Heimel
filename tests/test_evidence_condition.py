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


def make_source(source_id="src-1", source_type=EvidenceSourceType.SYSTEM_LOG):
    return EvidenceSource(
        source_id=source_id,
        source_type=source_type.value,
        provenance="test-provenance",
        raw_payload_digest="sha256:test",
        timestamp_acquired=datetime.now(timezone.utc).isoformat(),
        timestamp_submitted=datetime.now(timezone.utc).isoformat(),
    )


def make_condition(status=ValidationStatus.SUBMITTED, sources=None):
    return EvidenceCondition(
        evidence_id="evc-test-001",
        created_at=datetime.now(timezone.utc).isoformat(),
        source_chain=sources or [make_source()],
        freshness_boundary_seconds=3600,
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


def test_corroborated_evidence_can_be_validated_and_form_intent():
    condition = make_condition(
        sources=[
            make_source("src-1", EvidenceSourceType.SYSTEM_LOG),
            make_source("src-2", EvidenceSourceType.HUMAN_REPORT),
        ]
    )
    lifecycle = EvidenceValidationLifecycle(condition)

    lifecycle.transition(ValidationStatus.UNDER_VALIDATION, "validator", {})
    lifecycle.transition(
        ValidationStatus.VALIDATED,
        "validator",
        {"method": ValidationMethod.CORROBORATION.value},
    )

    intent = IntentFactory.create(
        intent_id="int-test-001",
        operator_id="op-test",
        evidence_condition=condition,
        action_type="TEST_ACTION",
        action_parameters={"scope": "bounded"},
        expected_outcome="safe bounded action",
    )

    assert condition.validation_status == "validated"
    assert intent.intent_id == "int-test-001"
    assert intent.intent_id in condition.bound_intents


def test_stale_evidence_blocks_intent_until_overridden():
    condition = make_condition(status=ValidationStatus.STALE)

    with pytest.raises(ValueError, match="INTENT_BLOCKED"):
        IntentFactory.create(
            intent_id="int-stale",
            operator_id="op-test",
            evidence_condition=condition,
            action_type="TEST_ACTION",
            action_parameters={},
            expected_outcome="blocked",
        )

    lifecycle = EvidenceValidationLifecycle(condition)
    lifecycle.transition(
        ValidationStatus.OVERRIDDEN,
        "authority",
        {"reason": "accepted with explicit evidence override"},
    )

    intent = IntentFactory.create(
        intent_id="int-overridden",
        operator_id="op-test",
        evidence_condition=condition,
        action_type="TEST_ACTION",
        action_parameters={},
        expected_outcome="allowed by override",
    )

    assert condition.validation_status == "overridden"
    assert intent.intent_id == "int-overridden"


def test_contested_evidence_blocks_intent():
    condition = make_condition(status=ValidationStatus.CONTESTED)

    with pytest.raises(ValueError, match="INTENT_BLOCKED"):
        IntentFactory.create(
            intent_id="int-contested",
            operator_id="op-test",
            evidence_condition=condition,
            action_type="TEST_ACTION",
            action_parameters={},
            expected_outcome="blocked",
        )
