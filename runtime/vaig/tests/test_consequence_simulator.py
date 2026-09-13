"""Tests for ConsequenceSimulator."""

from vaig.instruments.consequence_simulator import ConsequenceSimulator


class TestConsequenceSimulator:
    def test_clean_response(self):
        """No consequence signals = low score."""
        inst = ConsequenceSimulator()
        score = inst.score("test", "Here is a simple analysis of the data.")
        assert 0.0 <= score <= 0.2, f"Expected low, got {score}"

    def test_moderate_consequence(self):
        """Moderate consequence language = moderate score."""
        inst = ConsequenceSimulator()
        score = inst.score("test", "This may cause damage to the system.")
        assert score >= 0.1, f"Expected moderate, got {score}"

    def test_critical_consequence(self):
        """Critical consequence language = high score."""
        inst = ConsequenceSimulator()
        score = inst.score(
            "test",
            "This could lead to a security breakdown and severe financial loss.",
        )
        assert score >= 0.2, f"Expected high, got {score}"

    def test_cascade_effect(self):
        """Cascade/chain reaction signals = score."""
        inst = ConsequenceSimulator()
        score = inst.score("test", "This will trigger a cascade of errors with domino effect.")
        assert score >= 0.2, f"Expected cascade signal, got {score}"

    def test_mitigation_lowers_score(self):
        """Mitigation language reduces score."""
        inst = ConsequenceSimulator()
        score_risk = inst.score("test", "This causes data loss and system crash.")
        score_safe = inst.score(
            "test",
            "This causes data loss and system crash, but it is reversed and mitigated.",
        )
        assert score_safe <= score_risk, f"Mitigation should lower: risk={score_risk}, safe={score_safe}"

    def test_multiple_signals(self):
        """Multiple consequence types = higher score."""
        inst = ConsequenceSimulator()
        score = inst.score(
            "test",
            "This is a catastrophic security breach with data loss that triggers a chain reaction. "
            "This leads to financial collapse and permanent damage.",
        )
        assert score >= 0.4, f"Expected high for multiple, got {score}"

    def test_empty_response(self):
        """Empty response = 0.0."""
        inst = ConsequenceSimulator()
        score = inst.score("test", "")
        assert score == 0.0

    def test_score_range(self):
        """Score always in [0, 1]."""
        inst = ConsequenceSimulator()
        inputs = [
            "Regular response without consequences.",
            "This may cause delays and loss.",
            "Security breach and data loss with cascade effect.",
            "No damage, everything reversible.",
            "",
        ]
        for r in inputs:
            s = inst.score("test", r)
            assert 0.0 <= s <= 1.0, f"Score {s} out of range for: {r}"
