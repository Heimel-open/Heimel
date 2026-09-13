import pytest
from datetime import datetime, timezone

from vaig.rrp import (
    AuthorityAssignment,
    AuthorityDecision,
    RefusalCategory,
    RefusalEvent,
    RefusalLifecycle,
    ResolutionState,
    SeverityLevel,
    UncertaintyInventory,
)


def make_refusal() -> RefusalEvent:
    return RefusalEvent(
        refusal_id="ref-2026-0001",
        timestamp=datetime.now(timezone.utc).isoformat(),
        category=RefusalCategory.SAFETY_BOUNDARY,
        severity=SeverityLevel.HIGH,
        triggered_rule="VAIG-SAFETY-VOICE-IMPERSONATION",
        operator_id="operator-17",
        session_id="session-8831",
        input_summary="Request attempted to generate synthetic voice resembling enrolled executive speaker.",
        rationale="Voice similarity exceeded threshold and no consent token was present.",
        permitted_actions=["rescope", "escalate", "halt"],
        model_state_digest="sha256:abc123",
    )


def make_inventory(refusal_id: str) -> UncertaintyInventory:
    return UncertaintyInventory(
        refusal_id=refusal_id,
        unresolved_questions=["Is this a legitimate training simulation?"],
        missing_evidence=["speaker_consent_token"],
        ambiguity_sources=["operator_intent"],
        confidence_notes="Voice match score exceeded 0.92 threshold.",
        context_integrity_status="clean_context_no_prompt_injection_detected",
        risk_if_ignored="Unauthorized synthetic impersonation risk.",
    )


def make_assignment(refusal_id: str) -> AuthorityAssignment:
    return AuthorityAssignment(
        refusal_id=refusal_id,
        authority_role="Boundary Override Authority",
        authority_id="boa-safety-01",
        scope_of_authority=["voice_synthesis", "executive_identity", "training_simulation"],
        decision_latency_sla="15m",
        permitted_decisions=[
            AuthorityDecision.APPROVE,
            AuthorityDecision.RESCOPE,
            AuthorityDecision.REJECT,
            AuthorityDecision.TERMINATE,
        ],
        assignment_rationale="High-severity safety refusal requires BOA safety review.",
    )


def test_complete_refusal_lifecycle_rejects_and_resolves():
    lifecycle = RefusalLifecycle(make_refusal())

    lifecycle.enrich(make_inventory(lifecycle.refusal_event.refusal_id))
    lifecycle.route(make_assignment(lifecycle.refusal_event.refusal_id))
    lifecycle.start_review("boa-safety-01")
    lifecycle.decide(
        "boa-safety-01",
        AuthorityDecision.REJECT,
        "Consent token absent; request cannot continue.",
    )
    lifecycle.resolve("rrp_lifecycle_service", "Refusal resolved by rejection and audit closure.")

    exported = lifecycle.export()

    assert lifecycle.state is ResolutionState.RESOLVED
    assert exported["current_state"] == "resolved"
    assert exported["refusal_event"]["category"] == "safety_boundary"
    assert exported["uncertainty_inventory"]["missing_evidence"] == ["speaker_consent_token"]
    assert exported["authority_assignment"]["authority_id"] == "boa-safety-01"


def test_accountability_thread_appends_each_state_change():
    lifecycle = RefusalLifecycle(make_refusal())
    initial_count = len(lifecycle.accountability_thread.entries)

    lifecycle.enrich(make_inventory(lifecycle.refusal_event.refusal_id))
    lifecycle.route(make_assignment(lifecycle.refusal_event.refusal_id))
    lifecycle.start_review("boa-safety-01")

    assert initial_count == 1
    assert len(lifecycle.accountability_thread.entries) == 4
    assert [entry.linked_state for entry in lifecycle.accountability_thread.entries] == [
        ResolutionState.EMITTED,
        ResolutionState.ENRICHED,
        ResolutionState.ROUTED,
        ResolutionState.UNDER_REVIEW,
    ]


def test_invalid_transition_is_rejected():
    lifecycle = RefusalLifecycle(make_refusal())

    with pytest.raises(ValueError):
        lifecycle.start_review("boa-safety-01")


def test_terminal_resolved_state_rejects_further_transition():
    lifecycle = RefusalLifecycle(make_refusal())
    lifecycle.enrich(make_inventory(lifecycle.refusal_event.refusal_id))
    lifecycle.resolve("rrp_lifecycle_service", "Advisory refusal resolved without authority review.")

    with pytest.raises(ValueError):
        lifecycle.route(make_assignment(lifecycle.refusal_event.refusal_id))
