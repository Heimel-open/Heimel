"""Tests for AdaptiveDistrustEngine."""

from vaig.instruments.adaptive_distrust_engine import AdaptiveDistrustEngine


class TestAdaptiveDistrustEngine:
    def test_clean_response(self):
        """No distrust signals = low score."""
        inst = AdaptiveDistrustEngine()
        score = inst.score("test", "Her er en pålitelig og nøyaktig analyse.")
        assert 0.0 <= score <= 0.3, f"Expected low, got {score}"

    def test_distrust_language(self):
        """Distrust signals detected = moderate score."""
        inst = AdaptiveDistrustEngine()
        score = inst.score("test", "Dette resultatet er inkonsekvent og motsigende.")
        assert score >= 0.2, f"Expected moderate, got {score}"

    def test_high_distrust(self):
        """Multiple distrust signals = high score."""
        inst = AdaptiveDistrustEngine()
        score = inst.score(
            "test",
            "Resultatet er upålitelig og inneholder hallusinasjoner. "
            "Det er inkonsekvent og villedende.",
        )
        assert score >= 0.4, f"Expected high, got {score}"

    def test_rising_trend(self):
        """Rising distrust history = trend signal."""
        inst = AdaptiveDistrustEngine(history=[0.1, 0.3, 0.5, 0.7])
        score = inst.score("test", "Uventet oppførsel.")
        assert score >= 0.2, f"Expected rising trend, got {score}"

    def test_history_via_kwargs(self):
        """History via kwargs overrides instance."""
        inst = AdaptiveDistrustEngine()
        score = inst.score("test", "respons", history=[0.3, 0.6, 0.9])
        assert score >= 0.05, f"Expected history signal, got {score}"

    def test_inconsistency_via_kwargs(self):
        """Inconsistency via kwargs increases score."""
        inst = AdaptiveDistrustEngine()
        score = inst.score("test", "respons", inconsistency=0.8)
        assert score >= 0.04, f"Expected inconsistency signal, got {score}"

    def test_empty_response(self):
        """Empty response = 0.0."""
        inst = AdaptiveDistrustEngine()
        score = inst.score("test", "")
        assert score == 0.0

    def test_score_range(self):
        """Score always in [0, 1]."""
        inst = AdaptiveDistrustEngine()
        inputs = [
            "Pålitelig og korrekt resultat.",
            "Uventet og inkonsekvent oppførsel.",
            "Hallusinasjon og villedende informasjon.",
            "",
        ]
        for r in inputs:
            s = inst.score("test", r)
            assert 0.0 <= s <= 1.0, f"Score {s} out of range for: {r}"
