"""External instrument failures must fail closed, never measure zero risk."""

from types import SimpleNamespace

from vaig.aarm import AARMVerdict
from vaig.ensemble import DistrustLevel
from vaig.orchestrator import VAIGOrchestrator


class FailingExt:
    name = "scanner"

    def is_available(self) -> bool:
        return True

    def score(self, prompt, response):
        raise RuntimeError("scanner unavailable")


class InvalidExt:
    name = "bogus"

    def is_available(self) -> bool:
        return True

    def score(self, prompt, response):
        return 2.0


class PassingExt:
    name = "calm"

    def is_available(self) -> bool:
        return True

    def score(self, prompt, response):
        return 0.1


def _configure_plan(orchestrator, external):
    orchestrator.ensemble.instruments = {}
    orchestrator.dirigent.conduct = lambda _terrain: SimpleNamespace(
        internal=[],
        external=external,
        bench=[],
        thresholds={},
        context_health=1.0,
        context_warning=None,
        context_warning_detail=None,
    )


def _make(external_instruments, external, tmp_path):
    orchestrator = VAIGOrchestrator(
        log_path=str(tmp_path / "audit.jsonl"),
        with_cakm=False,
        external_instruments=external_instruments,
    )
    _configure_plan(orchestrator, external)
    return orchestrator


def test_configured_external_failure_fails_closed(tmp_path):
    orchestrator = _make([FailingExt()], ["scanner"], tmp_path)
    result = orchestrator.evaluate("Check risk", "Scanning now.")
    assert "ext_scanner" in result.external_errors
    assert result.external_errors["ext_scanner"] == "RuntimeError"
    assert result.validation.level is DistrustLevel.HALT
    assert result.should_halt is True
    assert result.aarm_verdict is not AARMVerdict.ALLOW


def test_invalid_external_score_fails_closed(tmp_path):
    orchestrator = _make([InvalidExt()], ["bogus"], tmp_path)
    result = orchestrator.evaluate("Check risk", "Scanning now.")
    assert "ext_bogus" in result.external_errors
    assert result.should_halt is True


def test_healthy_external_is_measured_and_does_not_halt(tmp_path):
    orchestrator = _make([PassingExt()], ["calm"], tmp_path)
    result = orchestrator.evaluate("Check risk", "All calm.")
    assert result.external_errors == {}
    assert "ext_calm" in result.validation.scores
    assert result.validation.scores["ext_calm"] == 0.1
    assert result.validation.level is DistrustLevel.TRUSTED
    assert result.should_halt is False


def test_unconfigured_planned_external_is_silently_skipped(tmp_path):
    orchestrator = _make([], ["not-registered"], tmp_path)
    result = orchestrator.evaluate("Check risk", "Scanning now.")
    assert result.external_errors == {}
    assert "ext_not-registered" not in result.validation.scores
    assert result.should_halt is False
