from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from urllib.error import URLError


SCRIPT = Path(__file__).parents[1] / "scripts" / "jev_precheck.py"
spec = importlib.util.spec_from_file_location("jev_precheck", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Response:
    def __init__(self, payload: dict[str, object]):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def _body(outcome: str, **extra: object) -> dict[str, object]:
    result: dict[str, object] = {
        "outcome": outcome,
        "score": 0.5,
        "provider": "typesafe",
        "model": "jev-1.13.0",
        "error": None,
        "authority_decision": None,
    }
    result.update(extra)
    return result


def test_stop_is_the_only_outcome_that_skips_heimel():
    result = module.JevPrecheckResult(module.DecisionOutcome.STOP, 0.03, {})
    assert module.should_run_heimel(result) is False
    for outcome in (module.DecisionOutcome.PASS, module.DecisionOutcome.ESCALATE):
        result = module.JevPrecheckResult(outcome, 0.5, {})
        assert module.should_run_heimel(result) is True


def test_pass_never_becomes_authority():
    def opener(request, timeout):
        return Response(_body("PASS", score=0.94))

    result = module.evaluate_before_heimel(
        {"intent": "send email"},
        "Does this need the Heimel consequence path?",
        base_url="https://justwork.internal/",
        opener=opener,
    )
    assert result.outcome is module.DecisionOutcome.PASS
    assert result.score == 0.94
    assert "authority_decision" not in result.evidence
    assert module.should_run_heimel(result) is True


def test_stop_targets_shared_justwork_endpoint_without_typesafe_secret():
    captured = {}

    def opener(request, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.get_header("Authorization")
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return Response(_body("STOP", score=0.04))

    result = module.evaluate_before_heimel(
        {"intent": "summarize locally"},
        "Does this require a consequence-bearing Heimel path?",
        criteria={"true": "A consequential action may follow", "false": "No consequential action can follow"},
        stop_at=0.2,
        pass_at=0.8,
        base_url="https://justwork.internal/",
        opener=opener,
    )
    assert result.outcome is module.DecisionOutcome.STOP
    assert captured["url"] == "https://justwork.internal/decision/noul"
    assert captured["authorization"] is None
    assert captured["body"]["stop_at"] == 0.2
    assert captured["body"]["pass_at"] == 0.8


def test_missing_service_and_transport_failure_escalate(monkeypatch):
    monkeypatch.delenv("JUSTWORK_DECISION_URL", raising=False)
    missing = module.evaluate_before_heimel("state", "question")
    assert missing.outcome is module.DecisionOutcome.ESCALATE
    assert module.should_run_heimel(missing) is True

    def broken(request, timeout):
        raise URLError("down")

    failed = module.evaluate_before_heimel(
        "state", "question", base_url="https://justwork.internal", opener=broken
    )
    assert failed.outcome is module.DecisionOutcome.ESCALATE
    assert module.should_run_heimel(failed) is True


def test_unknown_or_malformed_response_escalates():
    unknown = module.evaluate_before_heimel(
        "state",
        "question",
        base_url="https://justwork.internal",
        opener=lambda request, timeout: Response(_body("ALLOW")),
    )
    assert unknown.outcome is module.DecisionOutcome.ESCALATE

    malformed = module.evaluate_before_heimel(
        "state",
        "question",
        base_url="https://justwork.internal",
        opener=lambda request, timeout: Response({"outcome": "PASS", "score": "bad"}),
    )
    assert malformed.outcome is module.DecisionOutcome.ESCALATE


def test_semantic_gate_cannot_mint_authority():
    result = module.evaluate_before_heimel(
        "state",
        "question",
        base_url="https://justwork.internal",
        opener=lambda request, timeout: Response(_body("PASS", authority_decision="ALLOW", score=0.99)),
    )
    assert result.outcome is module.DecisionOutcome.ESCALATE
    assert result.error == "semantic gate attempted authority decision"
    assert "authority_decision" not in result.evidence
    assert module.should_run_heimel(result) is True


def test_thresholds_and_instructions_are_validated():
    for stop_at, pass_at in ((0.8, 0.2), (-0.1, 0.8), (0.2, 1.1)):
        try:
            module.evaluate_before_heimel("state", "question", stop_at=stop_at, pass_at=pass_at)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid thresholds must be rejected")

    try:
        module.evaluate_before_heimel("state", "  ")
    except ValueError:
        pass
    else:
        raise AssertionError("empty instructions must be rejected")
