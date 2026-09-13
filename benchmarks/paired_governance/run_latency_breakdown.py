from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from statistics import median
from time import perf_counter_ns
from typing import Any

from benchmarks.paired_governance import run_end_to_end as base
from benchmarks.paired_governance import run_end_to_end_fixed as fixed


LAYERS = ("kernel", "reht", "racs", "gateway", "veritas")
_current_scenario: str | None = None
_timings_ns: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
_call_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))


def _record(layer: str, elapsed_ns: int) -> None:
    if _current_scenario is None:
        return
    _timings_ns[_current_scenario][layer] += elapsed_ns
    _call_counts[_current_scenario][layer] += 1


def _timed_function(layer: str, fn: Callable[..., Any]) -> Callable[..., Any]:
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        started = perf_counter_ns()
        try:
            return fn(*args, **kwargs)
        finally:
            _record(layer, perf_counter_ns() - started)

    return wrapped


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
        "max_ms": max(values, default=0.0),
    }


def _install_instrumentation() -> Callable[[base.Scenario], dict[str, Any]]:
    global _current_scenario

    base._engine_for = fixed._engine_for
    base._kernel_context = fixed._kernel_context

    original_engine_for = base._engine_for
    original_kernel_context = base._kernel_context
    original_racs = base._racs_and_clearance
    original_reht = base.RealReht
    original_gateway = base.valo_gateway.ValoGateway
    original_veritas = base.veritas.VeritasChainService
    original_governed = base._governed_record

    base._engine_for = _timed_function("kernel", original_engine_for)
    base._kernel_context = _timed_function("kernel", original_kernel_context)
    base._racs_and_clearance = _timed_function("racs", original_racs)

    class TimedReht(original_reht):
        def authorize(self, *args: Any, **kwargs: Any) -> Any:
            started = perf_counter_ns()
            try:
                return super().authorize(*args, **kwargs)
            finally:
                _record("reht", perf_counter_ns() - started)

    class TimedGateway(original_gateway):
        def execute(self, *args: Any, **kwargs: Any) -> Any:
            started = perf_counter_ns()
            try:
                return super().execute(*args, **kwargs)
            finally:
                _record("gateway", perf_counter_ns() - started)

    class TimedVeritas(original_veritas):
        def store_boundary_negative_evidence(self, *args: Any, **kwargs: Any) -> Any:
            started = perf_counter_ns()
            try:
                return super().store_boundary_negative_evidence(*args, **kwargs)
            finally:
                _record("veritas", perf_counter_ns() - started)

        def store_gateway_execution_observation(self, *args: Any, **kwargs: Any) -> Any:
            started = perf_counter_ns()
            try:
                return super().store_gateway_execution_observation(*args, **kwargs)
            finally:
                _record("veritas", perf_counter_ns() - started)

        def verify_chain(self, *args: Any, **kwargs: Any) -> Any:
            started = perf_counter_ns()
            try:
                return super().verify_chain(*args, **kwargs)
            finally:
                _record("veritas", perf_counter_ns() - started)

    base.RealReht = TimedReht
    base.valo_gateway.ValoGateway = TimedGateway
    base.veritas.VeritasChainService = TimedVeritas

    def governed(scenario: base.Scenario) -> dict[str, Any]:
        global _current_scenario
        _current_scenario = scenario.scenario_id
        try:
            return original_governed(scenario)
        finally:
            _current_scenario = None

    base._governed_record = governed
    return governed


def run() -> dict[str, Any]:
    _install_instrumentation()
    payload = base.run()
    governed_records = {
        row["scenario_id"]: row
        for row in payload["records"]
        if row["condition"] == "REHT"
    }

    per_scenario: list[dict[str, Any]] = []
    for scenario_id, record in sorted(governed_records.items()):
        layer_ms = {
            layer: _timings_ns[scenario_id].get(layer, 0) / 1_000_000
            for layer in LAYERS
        }
        measured_layers_ms = sum(layer_ms.values())
        total_ms = float(record["decision_latency_ms"])
        per_scenario.append(
            {
                "scenario_id": scenario_id,
                "decision": record["decision"],
                "enforcement_layer": record["enforcement_layer"],
                "total_end_to_end_ms": total_ms,
                "layers_ms": layer_ms,
                "layer_call_counts": {
                    layer: _call_counts[scenario_id].get(layer, 0) for layer in LAYERS
                },
                "unattributed_harness_ms": max(0.0, total_ms - measured_layers_ms),
            }
        )

    summary: dict[str, dict[str, Any]] = {}
    for layer in LAYERS:
        all_values = [row["layers_ms"][layer] for row in per_scenario]
        executed_values = [
            row["layers_ms"][layer]
            for row in per_scenario
            if row["layer_call_counts"][layer] > 0
        ]
        summary[layer] = {
            "all_scenarios_contribution": _stats(all_values),
            "when_executed": {
                "scenario_count": len(executed_values),
                **_stats(executed_values),
            },
        }

    total_values = [row["total_end_to_end_ms"] for row in per_scenario]
    unattributed_values = [row["unattributed_harness_ms"] for row in per_scenario]
    return {
        "chain": "Kernel -> REHT -> RACS -> Gateway/effect -> Veritas",
        "scenario_count": len(per_scenario),
        "layer_latency": summary,
        "total_end_to_end": _stats(total_values),
        "unattributed_harness": {
            "p50_ms": median(unattributed_values),
            "p95_ms": _percentile(unattributed_values, 0.95),
        },
        "governed_failures": payload["governed_failures"],
        "per_scenario": per_scenario,
    }


def main() -> None:
    payload = run()
    output = Path("benchmarks/paired_governance/latest_latency_breakdown.json")
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {key: value for key, value in payload.items() if key != "per_scenario"},
            indent=2,
            sort_keys=True,
        )
    )
    if payload["governed_failures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
