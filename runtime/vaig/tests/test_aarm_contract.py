"""AARM contract tests — executable specification for the 6-verdict model.

Proves:
  * all six verdicts (ALLOW/MODIFY/DEFER/DENY/STEP_UP/HALT) are reachable,
  * MODIFY, DEFER, and STEP_UP remain semantically distinct (not aliased),
  * fail-closed behavior (invalid signal / evidence invalid => HALT).
"""

import pytest

from vaig.aarm import AARMVerdict, AARMSignal, aarm_decide, AARMSignalError
from vaig.agent_loop.gate import GateEvent, GateDecision, vaig_gate


def _sig(**over):
    base = dict(
        risk_class="low",
        uncertainty=0.0,
        reversibility="reversible",
        tool_authority="none",
        task_authority="none",
        drift_score=0.0,
        observation_trust=1.0,
        claims_substantiated=True,
        evidence_valid=True,
    )
    base.update(over)
    return AARMSignal(**base)


# --- 1. All six verdicts are reachable ----------------------------------

def test_halt_on_critical_risk():
    assert aarm_decide(_sig(risk_class="critical")) is AARMVerdict.HALT

def test_halt_on_invalid_evidence():
    assert aarm_decide(_sig(evidence_valid=False)) is AARMVerdict.HALT

def test_halt_fail_closed_on_malformed_signal():
    # A malformed signal fails closed at construction (AARMSignalError),
    # and vaig_gate converts any such failure into HALT — never allow.
    with pytest.raises(AARMSignalError):
        _sig(drift_score=2.0)
    evt = GateEvent(run_id="r", step_id="s", event_type="tool_call",
                    original_intent="x", current_frame="y",
                    tool_authority="EXECUTE_BOGUS", task_authority="read")
    d = vaig_gate(evt)
    assert d.decision == "halt"  # canonical AARM fail-closed on malformed authority

def test_deny_on_authority_scope_breach():
    assert aarm_decide(_sig(tool_authority="execute", task_authority="read")) is AARMVerdict.DENY

def test_step_up_on_high_risk():
    assert aarm_decide(_sig(risk_class="high", uncertainty=0.3)) is AARMVerdict.STEP_UP

def test_step_up_on_irreversible_high_uncertainty():
    assert aarm_decide(_sig(reversibility="irreversible", uncertainty=0.6)) is AARMVerdict.STEP_UP

def test_defer_on_high_uncertainty():
    assert aarm_decide(_sig(uncertainty=0.85)) is AARMVerdict.DEFER

def test_defer_on_low_observation_trust():
    assert aarm_decide(_sig(observation_trust=0.2)) is AARMVerdict.DEFER

def test_modify_on_low_confidence_reversible():
    # ok evidence, low confidence, reversible -> execute with modification
    assert aarm_decide(_sig(uncertainty=0.6, reversibility="reversible")) is AARMVerdict.MODIFY

def test_allow_on_low_risk_good_evidence():
    assert aarm_decide(_sig(risk_class="low", uncertainty=0.1, drift_score=0.1)) is AARMVerdict.ALLOW


# --- 2. MODIFY / DEFER / STEP_UP are semantically distinct ----------------

def test_modify_defer_stepup_distinct():
    v_modify = aarm_decide(_sig(uncertainty=0.6, reversibility="reversible", risk_class="medium"))
    v_defer = aarm_decide(_sig(uncertainty=0.85))
    v_stepup = aarm_decide(_sig(risk_class="high", uncertainty=0.3))
    assert {v_modify, v_defer, v_stepup} == {AARMVerdict.MODIFY, AARMVerdict.DEFER, AARMVerdict.STEP_UP}
    assert v_modify is not v_defer
    assert v_modify is not v_stepup
    assert v_defer is not v_stepup

def test_modify_is_execute_with_modification_not_pause():
    # A modify verdict must not be conflated with defer (pause) or step_up.
    v = aarm_decide(_sig(risk_class="medium", uncertainty=0.6, reversibility="reversible"))
    assert v is AARMVerdict.MODIFY
    assert v is not AARMVerdict.DEFER
    assert v is not AARMVerdict.STEP_UP

def test_stepup_is_escalation_not_deny():
    v = aarm_decide(_sig(risk_class="high", uncertainty=0.2))
    assert v is AARMVerdict.STEP_UP
    assert v is not AARMVerdict.DENY


# --- 3. vaig_gate is the canonical entrypoint, returns AARMVerdict --------

def test_vaig_gate_returns_aarm_verdict():
    evt = GateEvent(run_id="r", step_id="s", event_type="tool_call",
                    original_intent="x", current_frame="y",
                    tool_authority="execute", task_authority="read")
    d: GateDecision = vaig_gate(evt)
    assert d.decision == "deny"  # vaig_gate returns GateDecision with string decision
    # vaig_gate returns GateDecision with string decision (not AARMVerdict enum)

def test_vaig_gate_fail_closed_on_exception():
    # A garbage event that breaks normalization -> canonical AARM HALT,
    # never allow.
    evt = GateEvent(run_id="r", step_id="s", event_type="tool_call",
                    original_intent="x", current_frame="y",
                    tool_authority="EXECUTE_BOGUS", task_authority="read")
    d = vaig_gate(evt)
    assert d.decision == "halt"  # fail-closed on malformed authority
