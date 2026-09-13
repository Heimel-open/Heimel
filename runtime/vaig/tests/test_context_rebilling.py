"""
Tests for context rebilling multiplier.

Run: pytest tests/test_context_rebilling.py -v
"""
import pytest
from vaig.economy.token_meter import TokenMeter


class TestRebillingMultiplier:
    def test_twenty_turns_300_tokens_is_10_5x(self):
        """Core acceptance test: 20 × 300 tokens → 10.5x rebilling multiplier."""
        meter = TokenMeter(session_id="s1")
        for _ in range(20):
            meter.record_turn(300)
        assert meter.rebilling_multiplier() == pytest.approx(10.5)

    def test_single_turn_is_1x(self):
        meter = TokenMeter(session_id="s2")
        meter.record_turn(500)
        assert meter.rebilling_multiplier() == pytest.approx(1.0)

    def test_two_equal_turns_is_1_5x(self):
        # Turn 1: 100 billed; Turn 2: 200 billed; total=300; unique=200; ratio=1.5
        meter = TokenMeter(session_id="s3")
        meter.record_turn(100)
        meter.record_turn(100)
        assert meter.rebilling_multiplier() == pytest.approx(1.5)

    def test_empty_meter_returns_zero(self):
        meter = TokenMeter(session_id="s4")
        assert meter.rebilling_multiplier() == 0.0

    def test_multiplier_increases_with_more_turns(self):
        m5 = TokenMeter(session_id="m5")
        m10 = TokenMeter(session_id="m10")
        for _ in range(5):
            m5.record_turn(100)
        for _ in range(10):
            m10.record_turn(100)
        assert m10.rebilling_multiplier() > m5.rebilling_multiplier()

    def test_formula_matches_n_plus_one_over_two(self):
        """For equal-length turns, multiplier == (n+1)/2."""
        for n in [1, 5, 10, 20, 50]:
            meter = TokenMeter(session_id=f"n{n}")
            for _ in range(n):
                meter.record_turn(100)
            assert meter.rebilling_multiplier() == pytest.approx((n + 1) / 2, rel=1e-9)

    def test_unequal_turns_computed_correctly(self):
        # Turn 1: 100; Turn 2: 200; Turn 3: 300
        # cumulative: 100, 300, 600 → total_billed=1000; unique=600
        # multiplier = 1000/600 ≈ 1.6667
        meter = TokenMeter(session_id="unequal")
        meter.record_turn(100)
        meter.record_turn(200)
        meter.record_turn(300)
        assert meter.rebilling_multiplier() == pytest.approx(1000 / 600, rel=1e-6)
