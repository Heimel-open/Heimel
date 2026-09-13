"""
Tests for language inflation multiplier applied on top of rebilling.

Run: pytest tests/test_language_multiplier.py -v
"""
import pytest
from vaig.economy.token_meter import TokenMeter


class TestLanguageMultiplier:
    def test_language_multiplier_applied_on_top_of_rebilling(self):
        """
        Acceptance test: Norwegian/Danish 1.54x language factor applied on top
        of the 10.5x rebilling multiplier.
        """
        meter = TokenMeter(session_id="s-lang", language_inflation_factor=1.54)
        for _ in range(20):
            meter.record_turn(300)
        unique_tokens = 20 * 300
        expected = unique_tokens * 10.5 * 1.54
        assert meter.effective_tokens() == pytest.approx(expected, rel=1e-6)

    def test_no_inflation_matches_rebilling_only(self):
        meter = TokenMeter(session_id="s-no-inf")
        for _ in range(5):
            meter.record_turn(200)
        unique = 5 * 200
        assert meter.effective_tokens() == pytest.approx(unique * meter.rebilling_multiplier())

    def test_default_factor_is_one(self):
        meter = TokenMeter(session_id="s-default")
        assert meter.language_inflation_factor == 1.0

    def test_factor_above_one_increases_effective_tokens(self):
        base = TokenMeter(session_id="base")
        inflated = TokenMeter(session_id="inflated", language_inflation_factor=1.3)
        for m in [base, inflated]:
            for _ in range(5):
                m.record_turn(100)
        assert inflated.effective_tokens() > base.effective_tokens()

    def test_factors_compound_multiplicatively(self):
        m = TokenMeter(session_id="compound", language_inflation_factor=2.0)
        m.record_turn(100)
        m.record_turn(100)
        # rebilling = 1.5; unique = 200; effective = 200 * 1.5 * 2.0 = 600
        assert m.effective_tokens() == pytest.approx(600.0)
