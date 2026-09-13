"""Judge multiverse as the default orchestration path (fail-closed)."""

from types import SimpleNamespace


from vaig.aarm import AARMVerdict
from vaig.judge import DeterministicJudgeProvider, JudgeFactory, JudgeSpec
from vaig.orchestrator import VAIGOrchestrator


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


def _specs(model):
    return [
        JudgeSpec(provider="test", model_id=model, model_version="v1", temperature=0.0),
        JudgeSpec(provider="test", model_id=model, model_version="v1", temperature=1.0),
    ]


def test_multiverse_default_unanimous_uses_first_result(tmp_path):
    factory = JudgeFactory(
        DeterministicJudgeProvider(lambda prompt, spec: "ok")
    )
    orch = VAIGOrchestrator(
        log_path=str(tmp_path / "a.jsonl"),
        regression_path=str(tmp_path / "r.jsonl"),
        with_cakm=False,
        judge_specs=_specs("judge-a"),
        judge_factory=factory,
    )
    _empty_plan(orch)
    result = orch.evaluate(prompt="p", response="r")
    assert result.multiverse_report is not None
    assert result.multiverse_report.n_runs == 2
    assert result.multiverse_abstained is False
    assert result.aarm_verdict in set(AARMVerdict)


def test_multiverse_default_abstains_on_disagreement(tmp_path):
    factory = JudgeFactory(
        DeterministicJudgeProvider(lambda prompt, spec: "ok")
    )
    orch = VAIGOrchestrator(
        log_path=str(tmp_path / "a.jsonl"),
        regression_path=str(tmp_path / "r.jsonl"),
        with_cakm=False,
        judge_specs=_specs("judge-b"),
        judge_factory=factory,
    )
    _empty_plan(orch)

    calls = {"n": 0}

    def divergent_single(prompt, response, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            score, verdict = 0.1, AARMVerdict.ALLOW
        else:
            score, verdict = 0.9, AARMVerdict.HALT
        validation = SimpleNamespace(combined_score=score)
        return SimpleNamespace(
            validation=validation,
            aarm_verdict=verdict,
            aarm_decision=None,
            multiverse_report=None,
            multiverse_abstained=False,
        )

    orch._evaluate_single = divergent_single  # type: ignore[method-assign]
    result = orch.evaluate(prompt="p", response="r")
    assert result.multiverse_report is not None
    assert result.multiverse_report.abstain is True
    assert result.multiverse_abstained is True
    assert result.aarm_verdict is AARMVerdict.HALT


def test_multiverse_single_spec_falls_back_to_single_path(tmp_path):
    factory = JudgeFactory(
        DeterministicJudgeProvider(lambda prompt, spec: "ok")
    )
    orch = VAIGOrchestrator(
        log_path=str(tmp_path / "a.jsonl"),
        regression_path=str(tmp_path / "r.jsonl"),
        with_cakm=False,
        judge_specs=_specs("judge-c")[:1],
        judge_factory=factory,
    )
    _empty_plan(orch)
    result = orch.evaluate(prompt="p", response="r")
    assert result.multiverse_report is None
    assert result.aarm_verdict in set(AARMVerdict)


def test_advanced_kwargs_forward_through_multiverse(tmp_path):
    factory = JudgeFactory(
        DeterministicJudgeProvider(lambda prompt, spec: "ok")
    )
    orch = VAIGOrchestrator(
        log_path=str(tmp_path / "a.jsonl"),
        regression_path=str(tmp_path / "r.jsonl"),
        with_cakm=False,
        judge_specs=_specs("judge-d"),
        judge_factory=factory,
    )
    _empty_plan(orch)
    result = orch.evaluate(
        prompt="p",
        response="r",
        session_id="session-xyz",
        iteration_count=3,
    )
    assert result.multiverse_report is not None
