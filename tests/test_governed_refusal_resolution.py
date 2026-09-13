"""Tests for VAIG #95 Governed Refusal-to-Resolution orchestrator."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from vaig.governed_refusal_resolution import GovernedRefusalResolution, ResolutionStep
from vaig.rrp import AuthorityDecision, RefusalCategory, ResolutionState, SeverityLevel


def _g():
    return GovernedRefusalResolution(agent_id="vaig-agent")


def test_emit_refusal():
    g = _g()
    step = g.emit("ref-1", RefusalCategory.SAFETY_BOUNDARY, SeverityLevel.HIGH,
                  "VAIG-VOICE", "impersonation attempt", "no consent token",
                  ["rescope", "escalate", "halt"])
    assert step.ok is True
    assert step.data["refusal_id"] == "ref-1"
    assert g._lifecycle is not None


def test_enrich_inventory():
    g = _g()
    g.emit("ref-1", RefusalCategory.SAFETY_BOUNDARY, SeverityLevel.HIGH, "r", "i",
           "j", ["halt"])
    step = g.enrich(["speaker_consent_token"], ["legit simulation?"])
    assert step.ok is True
    assert step.data["missing_evidence"] == ["speaker_consent_token"]


def test_route_authority():
    g = _g()
    g.emit("ref-1", RefusalCategory.SAFETY_BOUNDARY, SeverityLevel.HIGH, "r", "i",
           "j", ["halt"])
    g.enrich([], [])
    step = g.route("boa-01", "Boundary Override Authority",
                   ["voice_synthesis"], "15m")
    assert step.ok is True
    assert step.data["authority_id"] == "boa-01"


def test_review_and_decide():
    g = _g()
    g.emit("ref-1", RefusalCategory.SAFETY_BOUNDARY, SeverityLevel.HIGH, "r", "i",
           "j", ["halt"])
    g.enrich([], [])
    g.route("boa-01", "BOA", ["voice"], "15m")
    g.review("boa-01")
    step = g.decide("boa-01", AuthorityDecision.REJECT, "no consent")
    assert step.ok is True
    assert step.data["decision"] == "REJECT"


def test_resolve_terminal():
    g = _g()
    g.emit("ref-1", RefusalCategory.SAFETY_BOUNDARY, SeverityLevel.HIGH, "r", "i",
           "j", ["halt"])
    g.enrich([], [])
    g.route("boa-01", "BOA", ["voice"], "15m")
    g.review("boa-01")
    g.decide("boa-01", AuthorityDecision.REJECT, "no consent")
    step = g.resolve("rrp_service", "closed")
    assert step.ok is True
    assert step.data["current_state"] == "resolved"


def test_full_refusal_resolution():
    g = _g()
    steps = g.run(
        refusal_id="ref-1", category=RefusalCategory.SAFETY_BOUNDARY,
        severity=SeverityLevel.HIGH, triggered_rule="VAIG-VOICE",
        input_summary="impersonation attempt", rationale="no consent token",
        permitted_actions=["rescope", "escalate", "halt"],
        missing_evidence=["speaker_consent_token"],
        unresolved=["legit simulation?"],
        authority_id="boa-01", authority_role="Boundary Override Authority",
        scope=["voice_synthesis"], decision_sla="15m",
        review_authority="boa-01", decision=AuthorityDecision.REJECT,
        decision_rationale="consent absent", resolve_service="rrp_service",
        resolve_note="refusal resolved by rejection")
    assert len(steps) == 6  # emit, enrich, route, review, decide, resolve
    assert steps[0].step == "emit"
    assert steps[-1].step == "resolve"
    assert steps[-1].data["current_state"] == "resolved"
    assert all(s.ok for s in steps)


def test_receipt_sink_called():
    sink = []
    g = GovernedRefusalResolution(receipt_sink=sink.append, agent_id="a")
    g.emit("ref-1", RefusalCategory.SAFETY_BOUNDARY, SeverityLevel.HIGH, "r", "i",
           "j", ["halt"])
    g.enrich([], [])
    g.route("boa-01", "BOA", ["voice"], "15m")
    # each state change emitted a receipt
    assert len(sink) >= 3


def test_trace_records_steps():
    g = _g()
    g.emit("ref-1", RefusalCategory.SAFETY_BOUNDARY, SeverityLevel.HIGH, "r", "i",
           "j", ["halt"])
    g.enrich([], [])
    trace = g.trace()
    assert len(trace) == 2
    assert all(isinstance(s, ResolutionStep) for s in trace)
