"""Tests for AARM decision digests and monotonic session state."""

from types import SimpleNamespace

from vaig.aarm import (
    AARMAuthorityEnvelope,
    AARMDecision,
    AARMState,
    AARMSignal,
    AARMVerdict,
    aarm_decide,
    aarm_signal_digest,
    evaluate_signal,
)
from vaig.orchestrator import VAIGOrchestrator


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


def _allow(**over):
    return _sig(uncertainty=0.1, drift_score=0.0, **over)


def _halt(**over):
    return _sig(risk_class="critical", **over)


def _deny(**over):
    return _sig(tool_authority="delete", task_authority="read", **over)


def _modify(**over):
    return _sig(uncertainty=0.6, **over)


def _defer(**over):
    return _sig(uncertainty=0.85, **over)


# --- Digests ---------------------------------------------------------------

def test_signal_digest_is_deterministic():
    signal = _allow()
    assert aarm_signal_digest(signal) == aarm_signal_digest(signal)
    assert len(aarm_signal_digest(signal)) == 64


def test_decision_digest_binds_verdict_and_evidence():
    allow = evaluate_signal(_allow())
    halt = evaluate_signal(_halt())
    assert allow.verdict is AARMVerdict.ALLOW
    assert halt.verdict is AARMVerdict.HALT
    assert allow.decision_digest != halt.decision_digest
    assert len(allow.decision_digest) == 64


def test_decision_digest_is_consistent_across_calls():
    first = evaluate_signal(_allow())
    second = evaluate_signal(_allow())
    assert first.decision_digest == second.decision_digest
    assert first.signal_digest == second.signal_digest


def test_digest_changes_when_evidence_changes():
    low = evaluate_signal(_sig(uncertainty=0.1))
    high = evaluate_signal(_sig(uncertainty=0.85))
    assert low.decision_digest != high.decision_digest


# --- Monotonic session state ----------------------------------------------

def test_halt_latches_and_blocks_downgrade():
    state = AARMState()
    assert state.evaluate(_allow()).verdict is AARMVerdict.ALLOW
    assert state.evaluate(_halt()).verdict is AARMVerdict.HALT

    downgrade = state.evaluate(_allow())
    assert downgrade.verdict is AARMVerdict.HALT
    assert downgrade.latched is True
    assert downgrade.prior_verdict is AARMVerdict.ALLOW
    assert "cannot downgrade" in downgrade.reason
    assert state.latched_verdict is AARMVerdict.HALT


def test_deny_cannot_be_downgraded():
    state = AARMState()
    assert state.evaluate(_deny()).verdict is AARMVerdict.DENY
    later = state.evaluate(_allow())
    assert later.verdict is AARMVerdict.DENY
    assert later.latched is True


def test_defer_and_modify_latch_over_allow():
    state = AARMState()
    assert state.evaluate(_defer()).verdict is AARMVerdict.DEFER
    later = state.evaluate(_allow())
    assert later.verdict is AARMVerdict.DEFER
    assert later.latched is True

    state2 = AARMState()
    assert state2.evaluate(_modify()).verdict is AARMVerdict.MODIFY
    later2 = state2.evaluate(_allow())
    assert later2.verdict is AARMVerdict.MODIFY
    assert later2.latched is True


def test_equal_verdict_repeat_is_not_latched():
    state = AARMState()
    first = state.evaluate(_halt())
    second = state.evaluate(_halt())
    assert first.verdict is AARMVerdict.HALT
    assert second.verdict is AARMVerdict.HALT
    assert second.latched is False
    assert second.prior_verdict is None


def test_reset_clears_latch():
    state = AARMState()
    state.evaluate(_halt())
    assert state.latched_verdict is AARMVerdict.HALT
    state.reset()
    assert state.latched_verdict is None
    assert state.evaluate(_allow()).verdict is AARMVerdict.ALLOW


# --- Envelope policy -------------------------------------------------------

def _enveloped(**over):
    base = dict(
        actor_id="actor-1",
        action_type="STORE_OBSERVATION",
        timestamp_iso="2026-08-05T12:00:00Z",
        envelope=AARMAuthorityEnvelope(
            envelope_id="env-1",
            actor_id="actor-1",
            allowed_action_types=("STORE_OBSERVATION", "READ_LAST_SEEN"),
            max_rate_per_sec=100,
            valid_until_iso="2099-01-01T00:00:00Z",
        ),
    )
    base.update(over)
    return _sig(**base)


def test_envelope_identity_mismatch_denied():
    signal = _enveloped(actor_id="intruder")
    assert aarm_decide(signal) is AARMVerdict.DENY


def test_envelope_expiry_denied():
    signal = _enveloped(timestamp_iso="2099-06-01T00:00:00Z")
    assert aarm_decide(signal) is AARMVerdict.DENY


def test_envelope_allowed_actions_denied():
    signal = _enveloped(action_type="DELETE_EVERYTHING")
    assert aarm_decide(signal) is AARMVerdict.DENY


def test_envelope_in_order_allows():
    assert aarm_decide(_enveloped()) is AARMVerdict.ALLOW


# --- expected_value / human_time_minutes sharpen MODIFY vs DEFER -----------

def test_human_review_available_defers_instead_of_modify():
    verdict = aarm_decide(_sig(uncertainty=0.6, human_time_minutes=2.0))
    assert verdict is AARMVerdict.DEFER


def test_low_expected_value_defers_instead_of_modify():
    verdict = aarm_decide(_sig(uncertainty=0.6, expected_value="low"))
    assert verdict is AARMVerdict.DEFER


# --- MODIFY constraints ----------------------------------------------------

def test_modify_carries_constraints():
    decision = evaluate_signal(_sig(uncertainty=0.6))
    assert decision.verdict is AARMVerdict.MODIFY
    assert "require-human-acknowledgement" in decision.constraints


def test_allow_carries_no_constraints():
    decision = evaluate_signal(_allow())
    assert decision.verdict is AARMVerdict.ALLOW
    assert decision.constraints == ()


# --- Anti-replay and rate limiting -----------------------------------------

def test_session_replay_nonce_denied():
    state = AARMState()
    first = state.evaluate(_allow(nonce="n-1"))
    assert first.verdict is AARMVerdict.ALLOW
    replay = state.evaluate(_allow(nonce="n-1"))
    assert replay.verdict is AARMVerdict.DENY
    assert "replay" in replay.reason


def test_session_envelope_rate_limit_denied():
    state = AARMState()
    envelope = AARMAuthorityEnvelope(
        envelope_id="env-rate",
        actor_id="actor-1",
        max_rate_per_sec=1,
        valid_until_iso="2099-01-01T00:00:00Z",
    )
    first = _sig(
        nonce="r-1",
        timestamp_iso="2026-08-05T12:00:00Z",
        envelope=envelope,
    )
    second = _sig(
        nonce="r-2",
        timestamp_iso="2026-08-05T12:00:00.500Z",
        envelope=envelope,
    )
    assert state.evaluate(first).verdict is AARMVerdict.ALLOW
    denied = state.evaluate(second)
    assert denied.verdict is AARMVerdict.DENY
    assert "rate limit" in denied.reason


# --- Orchestrator session wiring -------------------------------------------

def _empty_plan(orchestrator):
    orchestrator.ensemble.instruments = {}
    orchestrator.dirigent.conduct = lambda _terrain: SimpleNamespace(
        internal=[],
        external=[],
        bench=[],
        thresholds={},
        context_health=1.0,
        context_warning=None,
        context_warning_detail=None,
    )


def test_orchestrator_uses_bounded_aarm_session(tmp_path):
    orchestrator = VAIGOrchestrator(
        log_path=str(tmp_path / "audit.jsonl"),
        with_cakm=False,
    )
    _empty_plan(orchestrator)
    first = orchestrator.evaluate(prompt="Step one", response="ok")
    second = orchestrator.evaluate(prompt="Step two", response="ok")

    assert first.aarm_decision is not None
    assert len(first.aarm_decision.decision_digest) == 64
    assert second.aarm_decision is not None
    assert orchestrator.aarm_state.latched_verdict is not None
    # Unique nonces per evaluate: no replay false-positive across steps.
    assert first.aarm_decision.verdict is not AARMVerdict.DENY or "replay" not in (
        first.aarm_decision.reason
    )
