from __future__ import annotations

from enum import Enum
import json
import os
from typing import Any, Mapping, NamedTuple
from urllib.request import Request, urlopen


class DecisionOutcome(str, Enum):
    STOP = "STOP"
    ESCALATE = "ESCALATE"
    PASS = "PASS"


class JevPrecheckResult(NamedTuple):
    outcome: DecisionOutcome
    score: float | None
    evidence: Mapping[str, object]
    error: str | None = None


def _escalate(error: str, evidence: Mapping[str, object] | None = None) -> JevPrecheckResult:
    safe_evidence = dict(evidence or {})
    safe_evidence.pop("authority_decision", None)
    safe_evidence["outcome"] = DecisionOutcome.ESCALATE.value
    safe_evidence["error"] = error
    return JevPrecheckResult(DecisionOutcome.ESCALATE, None, safe_evidence, error)


def _validate_thresholds(stop_at: float, pass_at: float) -> None:
    if not 0.0 <= stop_at < pass_at <= 1.0:
        raise ValueError("thresholds must satisfy 0 <= stop_at < pass_at <= 1")


def evaluate_before_heimel(
    state: object,
    instructions: str,
    *,
    criteria: Mapping[str, object] | None = None,
    stop_at: float = 0.2,
    pass_at: float = 0.8,
    base_url: str | None = None,
    timeout_seconds: float = 2.0,
    opener=urlopen,
) -> JevPrecheckResult:
    if not isinstance(instructions, str) or not instructions.strip():
        raise ValueError("instructions must be a non-empty string")
    _validate_thresholds(float(stop_at), float(pass_at))
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    service_url = (base_url or os.getenv("JUSTWORK_DECISION_URL", "")).strip().rstrip("/")
    if not service_url:
        return _escalate("JUSTWORK_DECISION_URL is not configured")

    payload: dict[str, Any] = {
        "state": state,
        "instructions": instructions.strip(),
        "stop_at": float(stop_at),
        "pass_at": float(pass_at),
        "timeout_seconds": float(timeout_seconds),
    }
    if criteria is not None:
        payload["criteria"] = dict(criteria)

    request = Request(
        f"{service_url}/decision/noul",
        data=json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )

    try:
        with opener(request, timeout=timeout_seconds) as response:
            parsed = json.loads(response.read().decode("utf-8"))
        if not isinstance(parsed, dict):
            return _escalate("invalid semantic gate response")

        if parsed.get("authority_decision") not in (None, ""):
            return _escalate(
                "semantic gate attempted authority decision",
                {
                    "provider": parsed.get("provider"),
                    "model": parsed.get("model"),
                },
            )

        raw_outcome = parsed.get("outcome")
        try:
            outcome = DecisionOutcome(raw_outcome)
        except (TypeError, ValueError):
            return _escalate(
                "unknown semantic gate outcome",
                {"provider": parsed.get("provider"), "model": parsed.get("model")},
            )

        score_raw = parsed.get("score")
        score: float | None
        if score_raw is None and outcome is DecisionOutcome.ESCALATE:
            score = None
        else:
            if isinstance(score_raw, bool) or not isinstance(score_raw, (int, float)):
                return _escalate(
                    "invalid semantic gate score",
                    {"provider": parsed.get("provider"), "model": parsed.get("model")},
                )
            score = float(score_raw)
            if not 0.0 <= score <= 1.0:
                return _escalate(
                    "invalid semantic gate score",
                    {"provider": parsed.get("provider"), "model": parsed.get("model")},
                )

        evidence = {
            "provider": parsed.get("provider"),
            "model": parsed.get("model"),
            "score": score,
            "outcome": outcome.value,
            "error": parsed.get("error"),
        }
        return JevPrecheckResult(outcome, score, evidence, parsed.get("error"))
    except Exception as exc:
        return _escalate(f"semantic gate unavailable: {type(exc).__name__}: {exc}")


def should_run_heimel(result: JevPrecheckResult) -> bool:
    return result.outcome is not DecisionOutcome.STOP
