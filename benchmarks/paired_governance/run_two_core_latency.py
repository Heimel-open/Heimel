from __future__ import annotations

import copy
import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import median
from time import perf_counter_ns
from typing import Any

from tests.two_core_harness import (
    CAPABILITY,
    PURPOSE,
    TARGET,
    TwoCoreRuntime,
    _authority_event,
    base_engine,
)
from valo_reht import RealReht

NOW = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)

# --------------------------------------------------------------------------
# Frozen scenario family definitions (mirrors benchmarks/paired_governance).
# --------------------------------------------------------------------------

BASE_AUTH = {
    "authority_id": "auth-bench-1",
    "principal": "agent-1",
    "capability": "DO_EFFECT",
    "scope": ["target-1"],
    "constraints": {"purpose_id": "PURPOSE_A", "limit": "LOW"},
    "validity": {"valid_from": "2026-01-01T00:00:00+00:00", "valid_until": "2030-01-01T00:00:00+00:00"},
    "status": "ACTIVE",
}

BASE_CTX = {
    "actor": "agent-1",
    "identity": "id-agent-1",
    "time": {"now": "2026-08-19T09:30:00+00:00"},
    "authority": [BASE_AUTH],
}

BASE_ACTION = {
    "capability": "DO_EFFECT",
    "target": "target-1",
    "action_type": "DO_EFFECT",
    "purpose_id": "PURPOSE_A",
}


def _case(scenario_id: str) -> tuple[dict[str, Any], dict[str, Any], str]:
    ctx = copy.deepcopy(BASE_CTX)
    action = copy.deepcopy(BASE_ACTION)
    oracle = "ALLOW"
    if scenario_id == "PG-002":
        ctx["authority"][0]["validity"]["valid_until"] = "2026-08-19T09:00:00+00:00"
        oracle = "DENY"
    elif scenario_id == "PG-003":
        ctx["authority"][0]["status"] = "REVOKED"
        oracle = "DENY"
    elif scenario_id == "PG-004":
        action["target"] = "target-2"
        oracle = "DENY"
    elif scenario_id == "PG-005":
        action["purpose_id"] = "PURPOSE_B"
        oracle = "DENY"
    elif scenario_id == "PG-006":
        action["constraints"] = {"limit": "HIGH"}
        oracle = "DENY"
    elif scenario_id == "PG-007":
        ctx["time"] = {}
        oracle = "DENY"
    elif scenario_id == "PG-008":
        action["capability"] = "UNAUTHORIZED_EFFECT_FROM_TOOL_OUTPUT"
        oracle = "DENY"
    elif scenario_id == "PG-009":
        action["capability"] = "WRITE_GOVERNED_MEMORY"
        action["target"] = "future-policy-state"
        oracle = "DENY"
    elif scenario_id in {"PG-010", "PG-011", "PG-012"}:
        oracle = "DENY"
    elif scenario_id == "PG-013":
        ctx["identity"] = None
        oracle = "DENY"
    elif scenario_id == "PG-014":
        action["step_up"] = {
            "required": True,
            "reason": "material ambiguity requires authorized human or higher-trust decision",
        }
        oracle = "STEP_UP"
    elif scenario_id == "PG-015":
        oracle = "ALLOW"
    return ctx, action, oracle


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _stats(values: list[float]) -> dict[str, float]:
    return {
        "p50_ms": median(values) if values else 0.0,
        "p95_ms": _percentile(values, 0.95),
        "p99_ms": _percentile(values, 0.99),
        "max_ms": max(values, default=0.0),
    }


def _measure(fn: Callable[[], Any], iterations: int) -> list[float]:
    values: list[float] = []
    for _ in range(iterations):
        started = perf_counter_ns()
        fn()
        values.append((perf_counter_ns() - started) / 1_000_000)
    return values


def run(iterations: int = 200) -> dict[str, Any]:
    scenario_ids = [f"PG-{i:03d}" for i in range(1, 16)]
    reht = RealReht()

    # A. REHT-only over the frozen scenario families (the old REHT baseline
    #    was measured this way: one authorize call per frozen case).
    def reht_only_step() -> None:
        for sid in scenario_ids:
            ctx, action, _ = _case(sid)
            reht.authorize(ctx, action)

    reht_only = _measure(reht_only_step, iterations)
    per_call_reht = [value / len(scenario_ids) for value in reht_only]

    # B. TWO-CORE end-to-end over the frozen families: fresh Kernel context ->
    #    RealReht -> mechanical effect -> outcome evidence -> Kernel admission.
    def two_core_step() -> None:
        for sid in scenario_ids:
            action: dict[str, Any] = {
                "action_id": f"action:{sid}",
                "capability": CAPABILITY,
                "target": TARGET,
                "action_type": CAPABILITY,
                "purpose_id": PURPOSE,
            }
            engine = base_engine(now=NOW)
            if sid == "PG-002":
                engine = base_engine(now=NOW, authority=False)
                engine.append(
                    _authority_event(
                        now=NOW - timedelta(minutes=2),
                        valid_until=NOW - timedelta(seconds=1),
                    )
                )
            if sid == "PG-004":
                action["target"] = "target-2"
            if sid == "PG-005":
                action["purpose_id"] = "PURPOSE_B"
            if sid == "PG-006":
                action["constraints"] = {"limit": "HIGH"}
            if sid == "PG-009":
                action["capability"] = "WRITE_GOVERNED_MEMORY"
                action["target"] = "future-policy-state"
            if sid == "PG-014":
                action["step_up"] = {"required": True, "reason": "gate"}
            runtime = TwoCoreRuntime(engine)
            runtime.commit(
                scenario_id=sid,
                action_contract=action,
                now=NOW,
                effect_fn=lambda arguments: {"ok": True},
                nonce=f"nonce:{sid}",
            )

    two_core = _measure(two_core_step, iterations)
    per_scenario_two_core = [value / len(scenario_ids) for value in two_core]

    return {
        "method": (
            "perf_counter_ns; p50/p95/p99 via sorted linear interpolation; "
            "REHT-only and TWO-CORE are per frozen scenario"
        ),
        "iterations_per_path": iterations,
        "scenario_count": len(scenario_ids),
        "reht_only_per_call_ms": _stats(per_call_reht),
        "two_core_per_scenario_ms": _stats(per_scenario_two_core),
        "old_reht_baseline_ms": {"p50": "0.049-0.063", "p95": "0.124"},
        "old_full_chain_baseline_ms": {"p50": "2.1-2.2", "p95": "3.8-4.1"},
        "comparability": (
            "old baselines were measured on GitHub Actions (ubuntu-latest) against a "
            "previous valo-kernel and a lighter REHT artifact path; local numbers are "
            "NOT DIRECTLY COMPARABLE to the CI baselines. Reported for local relative "
            "comparison only; see docs/evidence report for a same-machine old-vs-new run."
        ),
    }


def main() -> None:
    payload = run()
    output = Path("benchmarks/paired_governance/latest_two_core_latency.json")
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()