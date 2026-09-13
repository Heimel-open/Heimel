"""Tests for EnvironmentIntegrityMonitor."""

from vaig.instruments.environment_integrity_monitor import EnvironmentIntegrityMonitor


class TestEnvironmentIntegrityMonitor:
    def test_clean_environment(self):
        """No integrity issues = 0.0."""
        inst = EnvironmentIntegrityMonitor()
        score = inst.score("test", "Alt fungerer som forventet.")
        assert score == 0.0, f"Expected 0.0, got {score}"

    def test_runtime_changed(self):
        """Runtime mismatch detected."""
        inst = EnvironmentIntegrityMonitor(expected_runtime="python3.11")
        score = inst.score("test", "respons", runtime="python3.12")
        assert score >= 0.4, f"Expected runtime issue, got {score}"

    def test_model_changed(self):
        """Model mismatch detected."""
        inst = EnvironmentIntegrityMonitor(expected_model="gpt-4")
        score = inst.score("test", "respons", model="claude-3")
        assert score >= 0.3, f"Expected model issue, got {score}"

    def test_env_change_language(self):
        """Language referring to environment changes."""
        inst = EnvironmentIntegrityMonitor()
        score = inst.score("test", "Vi byttet til ny modell og endret konfigurasjonen.")
        assert score >= 0.2, f"Expected env change signal, got {score}"

    def test_sandbox_changed(self):
        """Sandbox change language detected."""
        inst = EnvironmentIntegrityMonitor()
        score = inst.score("test", "Sandbox endret seg under kjøring.")
        assert score >= 0.4, f"Expected sandbox change signal, got {score}"

    def test_verification_failure(self):
        """Verification failure via kwargs."""
        inst = EnvironmentIntegrityMonitor()
        score = inst.score("test", "respons", verification_failed=True)
        assert score >= 0.5, f"Expected verification failure, got {score}"

    def test_errors_argument(self):
        """Errors argument increases score."""
        inst = EnvironmentIntegrityMonitor()
        score = inst.score("test", "respons", errors=3)
        assert score >= 0.3, f"Expected errors signal, got {score}"

    def test_empty_response(self):
        """Empty response = 0.0 (no issues detected)."""
        inst = EnvironmentIntegrityMonitor()
        score = inst.score("test", "")
        assert score == 0.0

    def test_score_range(self):
        """Score always in [0, 1]."""
        inst = EnvironmentIntegrityMonitor()
        inputs = [
            ("test", "", {}),
            ("test", "Alt normalt.", {}),
            ("test", "Ny konfig og ny modell installert.", {}),
            ("test", "respons", {"verification_failed": True, "errors": 5}),
        ]
        for prompt, response, kwargs in inputs:
            s = inst.score(prompt, response, **kwargs)
            assert 0.0 <= s <= 1.0, f"Score {s} out of range"
