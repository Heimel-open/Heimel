"""Tests for GoalDriftDetector."""

from vaig.instruments.goal_drift_detector import GoalDriftDetector


class TestGoalDriftDetector:
    def test_aligned_response(self):
        """Response stays close to mandate = low score."""
        inst = GoalDriftDetector()
        score = inst.score(
            "Analyser kundedata for Cegal-pilot",
            "Her er analysen av kundedata for Cegal-pilot.",
        )
        assert 0.0 <= score <= 0.4, f"Expected low drift, got {score}"

    def test_drifted_response(self):
        """Response diverges from mandate = high score."""
        inst = GoalDriftDetector(mandate="Analyser kundedata")
        score = inst.score(
            "Analyser kundedata",
            "Jeg tror egentlig vi heller bør endre strategi til å bygge et spill.",
        )
        assert score >= 0.4, f"Expected high drift, got {score}"

    def test_explicit_mandate(self):
        """Explicit mandate overrides prompt."""
        inst = GoalDriftDetector(mandate="Beregn ROI for markedsføring")
        score = inst.score(
            "Gjør noe annet",
            "Her er den nye strategien for produktutvikling.",
        )
        assert 0.0 <= score <= 1.0

    def test_empty_response(self):
        """Empty response = 0.0."""
        inst = GoalDriftDetector()
        score = inst.score("Mandat", "")
        assert score == 0.0

    def test_divergence_language(self):
        """Explicit divergence signals drive score up."""
        inst = GoalDriftDetector(mandate="Følg original plan")
        score = inst.score(
            "Følg original plan",
            "Jeg har tenkt — jeg tror egentlig vi bør endre strategi og heller gå en annen vei.",
        )
        assert score >= 0.5, f"Expected clear drift, got {score}"

    def test_score_range(self):
        """Score always in [0, 1]."""
        inst = GoalDriftDetector()
        inputs = [
            ("Mandat A", "Svar til mandat A."),
            ("Mandat B", "Helt annet svar med ny strategi."),
            ("Mandat C", ""),
            ("", "Response without mandate"),
        ]
        for prompt, response in inputs:
            s = inst.score(prompt, response)
            assert 0.0 <= s <= 1.0, f"Score {s} out of range for ({prompt}, {response})"
