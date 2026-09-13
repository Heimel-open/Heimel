"""
Tests for the AI Economy Gate — context budget and loop stop decisions.

Run: pytest tests/test_cost_value_gate.py -v
"""
import pytest
from vaig.economy.context_budget import ContextBudget
from vaig.economy.decision import EconomyGate, EconomyOutcome, EconomyRequest
from vaig.economy.receipt import make_receipt


class TestContextOverBudget:
    def test_over_budget_low_risk_returns_compress(self):
        """Acceptance test: context over budget → compress (low risk)."""
        gate = EconomyGate(budget=ContextBudget(max_tokens=50_000))
        req = EconomyRequest(session_id="s1", current_tokens=60_000, risk_level=0.1)
        decision = gate.decide(req)
        assert decision.outcome == EconomyOutcome.COMPRESS

    def test_over_budget_high_risk_returns_retrieve(self):
        """Acceptance test: context over budget → retrieve (high risk)."""
        gate = EconomyGate(budget=ContextBudget(max_tokens=50_000))
        req = EconomyRequest(session_id="s2", current_tokens=60_000, risk_level=0.7)
        decision = gate.decide(req)
        assert decision.outcome == EconomyOutcome.RETRIEVE

    def test_over_budget_never_returns_allow(self):
        """Acceptance test: context over budget never returns allow."""
        gate = EconomyGate(budget=ContextBudget(max_tokens=50_000))
        req = EconomyRequest(session_id="s3", current_tokens=75_000)
        decision = gate.decide(req)
        assert decision.outcome != EconomyOutcome.ALLOW

    def test_within_budget_returns_allow(self):
        gate = EconomyGate(budget=ContextBudget(max_tokens=100_000))
        req = EconomyRequest(session_id="s4", current_tokens=20_000)
        decision = gate.decide(req)
        assert decision.outcome == EconomyOutcome.ALLOW

    def test_exactly_at_budget_is_not_over(self):
        gate = EconomyGate(budget=ContextBudget(max_tokens=50_000))
        req = EconomyRequest(session_id="s5", current_tokens=50_000)
        decision = gate.decide(req)
        assert decision.outcome == EconomyOutcome.ALLOW


class TestLoopStop:
    def test_rising_cost_no_uncertainty_reduction_returns_stop(self):
        """Acceptance test: rising cost + no uncertainty reduction → stop."""
        gate = EconomyGate()
        req = EconomyRequest(
            session_id="s6",
            current_tokens=10_000,
            cost_trend=0.1,
            uncertainty=0.7,
            prev_uncertainty=0.7,
        )
        decision = gate.decide(req)
        assert decision.outcome == EconomyOutcome.STOP

    def test_rising_cost_with_uncertainty_improvement_allows(self):
        """Uncertainty is falling → loop still has value → allow."""
        gate = EconomyGate()
        req = EconomyRequest(
            session_id="s7",
            current_tokens=10_000,
            cost_trend=0.1,
            uncertainty=0.4,
            prev_uncertainty=0.7,
        )
        decision = gate.decide(req)
        assert decision.outcome == EconomyOutcome.ALLOW

    def test_first_step_no_prev_uncertainty_not_stopped(self):
        """First step has prev_uncertainty=0 → stop condition does not trigger."""
        gate = EconomyGate()
        req = EconomyRequest(
            session_id="s8",
            current_tokens=5_000,
            cost_trend=0.5,
            uncertainty=0.9,
            prev_uncertainty=0.0,
        )
        decision = gate.decide(req)
        assert decision.outcome != EconomyOutcome.STOP

    def test_zero_cost_trend_not_stopped(self):
        gate = EconomyGate()
        req = EconomyRequest(
            session_id="s9",
            current_tokens=5_000,
            cost_trend=0.0,
            uncertainty=0.8,
            prev_uncertainty=0.8,
        )
        decision = gate.decide(req)
        assert decision.outcome != EconomyOutcome.STOP


class TestHumanApproval:
    def test_cost_exceeds_threshold_requires_human(self):
        gate = EconomyGate()
        req = EconomyRequest(
            session_id="s10",
            current_tokens=5_000,
            estimated_cost=150.0,
            human_cost_threshold=100.0,
        )
        decision = gate.decide(req)
        assert decision.outcome == EconomyOutcome.REQUIRE_HUMAN

    def test_cost_below_threshold_allows(self):
        gate = EconomyGate()
        req = EconomyRequest(
            session_id="s11",
            current_tokens=5_000,
            estimated_cost=80.0,
            human_cost_threshold=100.0,
        )
        decision = gate.decide(req)
        assert decision.outcome == EconomyOutcome.ALLOW


class TestReceipt:
    def test_receipt_has_sha256_hash(self):
        gate = EconomyGate()
        req = EconomyRequest(session_id="s12", current_tokens=1_000)
        decision = gate.decide(req)
        receipt = make_receipt(decision, session_id="s12")
        assert len(receipt.hash) == 64

    def test_receipt_to_dict_contains_required_fields(self):
        gate = EconomyGate()
        req = EconomyRequest(session_id="s13", current_tokens=1_000)
        decision = gate.decide(req)
        receipt = make_receipt(decision, session_id="s13")
        d = receipt.to_dict()
        for key in ("session_id", "outcome", "model_tier", "token_cost", "reasoning", "timestamp", "hash"):
            assert key in d
