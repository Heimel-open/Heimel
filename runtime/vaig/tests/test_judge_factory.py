"""Judge factory, multiverse simulation and candidate-model evaluation."""

import pytest

from vaig.judge import (
    HTTPJudgeProvider,
    JudgeFactory,
    JudgeModelEvaluator,
    JudgeMultiverse,
    JudgeSpec,
    LabeledCase,
    VerdictMapProvider,
)
from vaig.judge.providers import DeterministicJudgeProvider


def _spec(provider="ollama", model="judge-7b", temp=0.0, provenance="private"):
    return JudgeSpec(
        provider=provider,
        model_id=model,
        model_version="v1",
        temperature=temp,
        provenance=provenance,
    )


def test_spec_config_hash_is_deterministic_and_sampling_aware():
    a = _spec(temp=0.0)
    b = _spec(temp=0.0)
    c = _spec(temp=1.0)
    assert a.config_hash == b.config_hash
    assert a.config_hash != c.config_hash
    assert a.stable_id == b.stable_id == "ollama:judge-7b:v1"


def test_spec_rejects_bad_sampling():
    with pytest.raises(ValueError):
        _spec(temp=3.0)
    with pytest.raises(ValueError):
        JudgeSpec(provider="x", model_id="m", model_version="1", provenance="unknown")


def test_factory_builds_deterministic_judge():
    provider = VerdictMapProvider({"ollama:judge-7b:v1": "SUPPORTED"})
    factory = JudgeFactory(provider)
    judge = factory.build(_spec())
    assert judge("any prompt") == "SUPPORTED"


def test_multiverse_unanimous_does_not_abstain():
    factory = JudgeFactory(
        DeterministicJudgeProvider(lambda prompt, spec: "SUPPORTED")
    )
    m = JudgeMultiverse(factory)
    report = m.run(
        [_spec(temp=0.0), _spec(temp=1.0)],
        run_case=lambda judge_fn, prompt, response: (0.3, "ALLOW"),
    )
    assert report.n_runs == 2
    assert report.unanimous is True
    assert report.abstain is False


def _temp_based_verdict(judge_fn, prompt, response):
    """Simulate sampling variance: temperature flips the judge's verdict."""
    verdict = judge_fn(prompt)
    if verdict == "ALLOW":
        return 0.2, "ALLOW"
    return 0.9, "HALT"


def test_multiverse_abstains_on_spread():
    factory = JudgeFactory(
        DeterministicJudgeProvider(
            lambda prompt, spec: "ALLOW" if spec.temperature < 0.5 else "HALT"
        )
    )
    m = JudgeMultiverse(factory, max_spread=0.1)
    report = m.run(
        [_spec(temp=0.0), _spec(temp=1.0)],
        run_case=_temp_based_verdict,
        prompt="case",
    )
    assert report.abstain is True
    assert "spread" in report.reason


def test_multiverse_abstains_on_verdict_split():
    factory = JudgeFactory(
        DeterministicJudgeProvider(
            lambda prompt, spec: "ALLOW" if spec.temperature < 0.5 else "HALT"
        )
    )
    m = JudgeMultiverse(factory, max_spread=0.9)
    report = m.run(
        [_spec(temp=0.0), _spec(temp=1.0)],
        run_case=_temp_based_verdict,
        prompt="case",
    )
    assert report.abstain is True
    assert "not unanimous" in report.reason


def test_evaluator_promotes_good_candidate():
    factory = JudgeFactory(DeterministicJudgeProvider(lambda p, s: "ok"))
    cases = [
        LabeledCase(prompt=f"attack-{i}", response="r", label=1) for i in range(20)
    ] + [
        LabeledCase(prompt=f"benign-{i}", response="r", label=0) for i in range(20)
    ]

    def run_case(judge_fn, prompt, response):
        return (0.9, "HALT") if "attack" in prompt else (0.1, "ALLOW")

    evaluator = JudgeModelEvaluator(factory, run_case=run_case, min_samples=20)
    result = evaluator.evaluate(
        _spec(provenance="self-trained"), cases, incumbent_auc=0.55
    )
    assert result.samples == 40
    assert result.recommendation == "promote"
    assert result.auc is not None and result.auc >= 0.6


def test_evaluator_requires_min_samples():
    factory = JudgeFactory(DeterministicJudgeProvider(lambda p, s: "ok"))
    cases = [LabeledCase(prompt="p", response="r", label=1) for _ in range(5)]
    evaluator = JudgeModelEvaluator(
        factory, run_case=lambda judge_fn, p, r: (0.9, "HALT"), min_samples=20
    )
    result = evaluator.evaluate(_spec(provenance="private"), cases)
    assert result.recommendation == "needs-more-data"


def test_evaluator_rejects_worse_than_incumbent():
    factory = JudgeFactory(DeterministicJudgeProvider(lambda p, s: "ok"))
    cases = [LabeledCase(prompt="p", response="r", label=1) for _ in range(20)]
    evaluator = JudgeModelEvaluator(
        factory, run_case=lambda judge_fn, p, r: (0.9, "HALT"), min_samples=20
    )
    result = evaluator.evaluate(_spec(), cases, incumbent_auc=0.99)
    assert result.recommendation == "reject"


def test_http_provider_sends_openai_chat_and_parses(monkeypatch):
    import requests

    captured = {}

    class FakeResp:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "HALT"}}]}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return FakeResp()

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    spec = _spec()
    provider = HTTPJudgeProvider()
    assert provider.complete("judge this", spec) == "HALT"
    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["json"]["model"] == "judge-7b"
    assert captured["json"]["temperature"] == 0.0
    assert "Authorization" not in captured["headers"]
