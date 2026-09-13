"""Tests for vaig.rrp.racs_adapter against observed contracts."""

import pytest

from vaig.rrp.core import AuthorityDecision, RefusalCategory, SeverityLevel
from vaig.rrp.evidence import (
    ConfidenceLevel,
    EvidenceCondition,
    EvidenceSource,
    ValidationStatus,
)
from vaig.rrp.intent import Intent
from vaig.rrp.racs_adapter import build_governance_result, map_authority_decision_to_racs


def _make_evidence_condition(validation_status="validated", confidence=None):
    return EvidenceCondition(
        evidence_id="ev-1",
        created_at="2026-07-31T00:00:00+00:00",
        source_chain=[
            EvidenceSource(
                source_id="src-1",
                source_type="system_log",
                provenance="test",
                raw_payload_digest="0x0",
                timestamp_acquired="2026-07-31T00:00:00+00:00",
                timestamp_submitted="2026-07-31T00:00:00+00:00",
            )
        ],
        freshness_boundary_seconds=3600,
        timestamp_validated="2026-07-31T00:00:00+00:00",
        timestamp_expires="2026-07-31T01:00:00+00:00",
        validation_status=validation_status,
        validator="test",
        validation_method="direct_verification",
        validation_reasoning="ok",
        confidence_level=str(confidence) if confidence is not None else "",
        confidence_reasoning="ok",
        contested_by=None,
        contest_reasoning=None,
        bound_intents=[],
        action_type="STATUS_CHECK",
    )


def _make_refusal_event():
    return type(
        "RefusalEvent",
        (),
        {
            "refusal_id": "ref-1",
            "category": RefusalCategory.POLICY_VIOLATION,
            "triggered_rule": "RULE-1",
        },
    )


def test_map_authority_decision_to_racs_all_mappings():
    mapping = {
        AuthorityDecision.APPROVE: "ALLOW",
        AuthorityDecision.RESCOPE: "MODIFY",
        AuthorityDecision.REJECT: "DENY",
        AuthorityDecision.ESCALATE: "STEP_UP",
        AuthorityDecision.TERMINATE: "HALT",
    }
    for authority, expected in mapping.items():
        assert map_authority_decision_to_racs(authority) == expected


def test_map_authority_decision_none_is_deny():
    assert map_authority_decision_to_racs(None) == "DENY"


def test_map_authority_decision_unknown_is_deny():
    # Use the observed fallback path: a subclass-like enum value not in map.
    class FakeAuthorityDecision(str):
        value = "UNKNOWN"

    fake = FakeAuthorityDecision("UNKNOWN")
    # Function accepts AuthorityDecision | None; fake Duck-types like str enum.
    # We bypass static type checking to test runtime behavior of the unknown branch.
    assert map_authority_decision_to_racs(fake) == "DENY"  # type: ignore[arg-type]


def test_build_governance_result_none_inputs():
    result = build_governance_result(None)
    assert result.decision == "DENY"
    assert result.source_authority_decision is None
    assert result.evidence_condition_id is None
    assert result.refusal_id is None


def test_build_governance_result_missing_evidence():
    result = build_governance_result(
        AuthorityDecision.APPROVE,
        tenant_id="tenant-1",
        request_digest="digest-1",
    )
    assert result.decision == "ALLOW"
    assert result.tenant_id == "tenant-1"
    assert result.request_digest == "digest-1"
    assert result.evidence_condition_id is None


def test_build_governance_result_preserves_metadata():
    evidence = _make_evidence_condition()
    refusal = _make_refusal_event()
    intent = Intent(
        intent_id="intent-1",
        created_at="2026-07-31T00:00:00+00:00",
        operator_id="op-1",
        evidence_id="ev-1",
        evidence_condition_snapshot={"validation_status": "validated"},
        action_type="MEDICAL_INTERVENTION",
        action_parameters={},
        expected_outcome="ok",
        source_domain="medical",
        target_domain="medical",
        cross_domain=False,
        authorization_status="PENDING",
        authorization_authority=None,
        authorization_timestamp=None,
        authorization_reasoning=None,
    )
    result = build_governance_result(
        AuthorityDecision.ESCALATE,
        refusal_event=refusal,
        evidence_condition=evidence,
        confidence_level=ConfidenceLevel.HIGH,
        severity_level=SeverityLevel.CRITICAL,
        intent=intent,
        tenant_id="tenant-1",
        request_digest="digest-1",
    )
    assert result.decision == "STEP_UP"
    assert result.source_authority_decision == "ESCALATE"
    assert result.evidence_condition_id == "ev-1"
    assert result.confidence_level == ConfidenceLevel.HIGH.value
    assert result.intent_action_type == "MEDICAL_INTERVENTION"
    assert result.refusal_id == "ref-1"
    assert "SEVERITY_CRITICAL" in result.reasons
    assert "CONFIDENCE_HIGH" in result.reasons
    assert "EVIDENCE_STATUS_VALIDATED" in result.reasons
    assert "REFUSAL_CATEGORY_POLICY_VIOLATION" in result.reasons
    assert "INTENT_ACTION_MEDICAL_INTERVENTION" in result.reasons
