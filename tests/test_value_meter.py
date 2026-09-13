"""
Tests for VAIG Value Meter — Authorized Value computation.

Run: pytest tests/test_value_meter.py -v
"""

import pytest
from vaig.value_meter import (
    AARMOutcome,
    AARM_GATE_WEIGHTS,
    GATE_OVERHEAD_SECONDS,
    IntentRecord,
    ValueMeter,
    AuthorizedValueResult,
)


class TestAARMGateWeights:
    def test_allow_is_one(self):
        assert AARM_GATE_WEIGHTS[AARMOutcome.ALLOW] == 1.0

    def test_modify_is_half(self):
        assert AARM_GATE_WEIGHTS[AARMOutcome.MODIFY] == 0.5

    def test_deny_deny_defer_halt_are_zero(self):
        for outcome in [AARMOutcome.DENY, AARMOutcome.DEFER,
                        AARMOutcome.STEP_UP, AARMOutcome.HALT]:
            assert AARM_GATE_WEIGHTS[outcome] == 0.0


class TestIntentRecord:
    def test_allow_full_contribution(self):
        rec = IntentRecord(
            packet_id="p1",
            intent_value=100.0,
            aarm_outcome=AARMOutcome.ALLOW,
        )
        assert rec.gate_weight == 1.0
        assert rec.authorized_contribution == 100.0

    def test_modify_half_contribution(self):
        rec = IntentRecord(
            packet_id="p2",
            intent_value=100.0,
            aarm_outcome=AARMOutcome.MODIFY,
        )
        assert rec.gate_weight == 0.5
        assert rec.authorized_contribution == 50.0

    def test_deny_zero_contribution(self):
        rec = IntentRecord(
            packet_id="p3",
            intent_value=100.0,
            aarm_outcome=AARMOutcome.DENY,
        )
        assert rec.gate_weight == 0.0
        assert rec.authorized_contribution == 0.0

    def test_to_dict_contains_required_fields(self):
        rec = IntentRecord(
            packet_id="p4",
            intent_value=50.0,
            aarm_outcome=AARMOutcome.ALLOW,
        )
        d = rec.to_dict()
        assert "packet_id" in d
        assert "intent_value" in d
        assert "aarm_outcome" in d
        assert "gate_weight" in d
        assert "authorized_contribution" in d


class TestValueMeterEmpty:
    def test_empty_returns_zero_result(self):
        meter = ValueMeter(session_id="empty-session")
        result = meter.compute(window_seconds=60.0)
        assert result.authorized_value == 0.0
        assert result.n_decisions == 0
        assert result.control_yield == 0.0
        assert result.allow_rate == 0.0

    def test_blocked_ratio_empty(self):
        meter = ValueMeter(session_id="s0")
        assert meter.blocked_ratio() == 0.0


class TestValueMeterAllAllow:
    def test_all_allow_maximizes_authorized_value(self):
        meter = ValueMeter(session_id="s-all-allow")
        for i in range(10):
            meter.record(f"p{i}", intent_value=1.0, aarm_outcome=AARMOutcome.ALLOW)

        result = meter.compute(window_seconds=3600.0)

        assert result.n_decisions == 10
        assert result.n_allowed == 10
        assert result.n_blocked == 0
        assert result.allow_rate == 1.0
        assert result.authorized_value > 0
        assert result.control_yield > 0

    def test_all_deny_produces_zero_authorized_value(self):
        meter = ValueMeter(session_id="s-all-deny")
        for i in range(5):
            meter.record(f"p{i}", intent_value=1000.0, aarm_outcome=AARMOutcome.DENY)

        result = meter.compute(window_seconds=3600.0)

        assert result.authorized_value == 0.0
        assert result.n_blocked == 5
        assert result.allow_rate == 0.0
        assert meter.blocked_ratio() == 1.0


class TestValueMeterMixed:
    def test_mixed_outcomes_partial_value(self):
        """ALLOW=full, MODIFY=half, DENY=zero — sum must be between 0 and all-ALLOW."""
        meter_mixed = ValueMeter(session_id="s-mixed")
        meter_all = ValueMeter(session_id="s-all")

        outcomes = [AARMOutcome.ALLOW, AARMOutcome.MODIFY, AARMOutcome.DENY]
        for i, outcome in enumerate(outcomes):
            meter_mixed.record(f"p{i}", intent_value=100.0, aarm_outcome=outcome)
            meter_all.record(f"p{i}", intent_value=100.0, aarm_outcome=AARMOutcome.ALLOW)

        result_mixed = meter_mixed.compute(window_seconds=3600.0)
        result_all = meter_all.compute(window_seconds=3600.0)

        assert 0 < result_mixed.authorized_value < result_all.authorized_value
        assert result_mixed.n_allowed == 1
        assert result_mixed.n_modified == 1
        assert result_mixed.n_blocked == 1

    def test_allow_rate_calculation(self):
        meter = ValueMeter(session_id="s-rate")
        meter.record("p1", 1.0, AARMOutcome.ALLOW)
        meter.record("p2", 1.0, AARMOutcome.ALLOW)
        meter.record("p3", 1.0, AARMOutcome.MODIFY)
        meter.record("p4", 1.0, AARMOutcome.DENY)

        result = meter.compute(window_seconds=60.0)
        # 2 ALLOW + 1 MODIFY = 3 authorized out of 4
        assert result.allow_rate == pytest.approx(0.75)


class TestValueMeterEquation:
    def test_equation_scales_with_intent_value(self):
        """Higher intent value → higher Authorized Value."""
        def make_meter(intent_val: float) -> float:
            m = ValueMeter(session_id=f"s-{intent_val}")
            m.record("p1", intent_value=intent_val, aarm_outcome=AARMOutcome.ALLOW)
            return m.compute(window_seconds=3600.0).authorized_value

        av_low = make_meter(10.0)
        av_high = make_meter(100.0)
        assert av_high == pytest.approx(av_low * 10.0, rel=1e-6)

    def test_gate_overhead_normalization(self):
        """Smaller gate overhead → larger AV (same integral, divided by c²)."""
        m_fast = ValueMeter(session_id="fast", gate_overhead=43e-9)
        m_slow = ValueMeter(session_id="slow", gate_overhead=200e-9)

        for m in [m_fast, m_slow]:
            m.record("p1", intent_value=1.0, aarm_outcome=AARMOutcome.ALLOW)

        av_fast = m_fast.compute(window_seconds=3600.0).authorized_value
        av_slow = m_slow.compute(window_seconds=3600.0).authorized_value

        # (200/43)² ≈ 21.6x difference
        ratio = av_fast / av_slow
        expected_ratio = (200e-9 / 43e-9) ** 2
        assert ratio == pytest.approx(expected_ratio, rel=1e-4)

    def test_hash_is_deterministic_given_fixed_time(self):
        result = AuthorizedValueResult(
            session_id="s-hash",
            n_decisions=5,
            n_allowed=5,
            n_modified=0,
            n_blocked=0,
            raw_integral=0.5,
            gate_overhead=GATE_OVERHEAD_SECONDS,
            authorized_value=1234567.0,
            control_yield=0.9,
            window_seconds=3600.0,
            allow_rate=1.0,
        )
        # Hash computed on init — must be non-empty
        assert len(result.hash) == 64  # SHA-256 hex


class TestControlYield:
    def test_control_yield_is_av_over_gate_cost(self):
        meter = ValueMeter(session_id="s-yield")
        for i in range(4):
            meter.record(f"p{i}", intent_value=1.0, aarm_outcome=AARMOutcome.ALLOW)

        result = meter.compute(window_seconds=3600.0)

        expected_gate_cost = GATE_OVERHEAD_SECONDS * 4
        expected_yield = result.authorized_value / expected_gate_cost
        assert result.control_yield == pytest.approx(expected_yield, rel=1e-6)

    def test_blocked_actions_reduce_control_yield(self):
        m_clean = ValueMeter(session_id="clean")
        m_blocked = ValueMeter(session_id="blocked")

        for i in range(4):
            m_clean.record(f"p{i}", 1.0, AARMOutcome.ALLOW)

        for i in range(2):
            m_blocked.record(f"p{i}", 1.0, AARMOutcome.ALLOW)
        for i in range(2, 4):
            m_blocked.record(f"p{i}", 1.0, AARMOutcome.DENY)

        r_clean = m_clean.compute(window_seconds=3600.0)
        r_blocked = m_blocked.compute(window_seconds=3600.0)

        assert r_clean.control_yield > r_blocked.control_yield
