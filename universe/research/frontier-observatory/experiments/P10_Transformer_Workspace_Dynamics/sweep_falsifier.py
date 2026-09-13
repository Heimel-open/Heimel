from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean
from typing import Iterable, Mapping, Sequence

PHASES = (
    "BROAD_SCAN",
    "TARGET_LOCK",
    "DISCONFIRMING_SWEEP",
    "UNCERTAINTY_MAP",
    "CANDIDATE_SET",
)

CONSISTENT = "CONSISTENT"
FALSIFIED = "FALSIFIED"
INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass(frozen=True)
class SweepObservation:
    phase: str
    workspace: Mapping[str, float]
    trace_id: str = "trace"
    targets: frozenset[str] = frozenset()
    disconfirming: frozenset[str] = frozenset()
    tau: float | None = None

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "SweepObservation":
        return cls(
            phase=str(payload["phase"]),
            workspace={str(k): float(v) for k, v in dict(payload["workspace"]).items()},
            trace_id=str(payload.get("trace_id", "trace")),
            targets=frozenset(str(x) for x in payload.get("targets", [])),
            disconfirming=frozenset(str(x) for x in payload.get("disconfirming", [])),
            tau=None if payload.get("tau") is None else float(payload["tau"]),
        )


@dataclass(frozen=True)
class WorkspaceMetrics:
    phase: str
    trace_id: str
    previous_phase: str | None
    support_size: int
    concentration: float
    entropy: float
    target_mass: float
    disconfirming_mass: float
    turnover: float | None
    tau: float | None


@dataclass(frozen=True)
class CriterionResult:
    criterion: str
    status: str
    observed: float | None
    threshold: str
    explanation: str


def _validate_workspace(workspace: Mapping[str, float], max_capacity: int) -> None:
    if max_capacity < 2:
        raise ValueError("max_capacity must be >= 2")
    active = 0
    for concept, weight in workspace.items():
        if not isinstance(concept, str) or not concept:
            raise ValueError("workspace concept names must be non-empty strings")
        if not math.isfinite(weight) or weight < 0:
            raise ValueError("workspace weights must be finite and non-negative")
        if weight > 0:
            active += 1
    if active > max_capacity:
        raise ValueError(
            f"workspace support {active} exceeds configured capacity {max_capacity}"
        )


def _validate_thresholds(
    *,
    min_target_gain: float,
    min_concentration_gain: float,
    min_counter_gain: float,
    min_disconfirming_turnover: float,
    max_candidate_turnover: float,
    min_candidate_tau_fraction: float,
) -> None:
    nonnegative = {
        "min_target_gain": min_target_gain,
        "min_concentration_gain": min_concentration_gain,
        "min_counter_gain": min_counter_gain,
        "min_disconfirming_turnover": min_disconfirming_turnover,
    }
    for name, value in nonnegative.items():
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"{name} must be finite and non-negative")
    if not math.isfinite(max_candidate_turnover) or not 0 <= max_candidate_turnover <= 1:
        raise ValueError("max_candidate_turnover must be inside [0, 1]")
    if not math.isfinite(min_candidate_tau_fraction) or not 0 <= min_candidate_tau_fraction <= 1:
        raise ValueError("min_candidate_tau_fraction must be inside [0, 1]")


def normalize_workspace(
    workspace: Mapping[str, float], max_capacity: int = 25
) -> dict[str, float]:
    _validate_workspace(workspace, max_capacity)
    total = sum(workspace.values())
    if total <= 0:
        return {}
    return {k: v / total for k, v in workspace.items() if v > 0}


def concentration(workspace: Mapping[str, float], max_capacity: int = 25) -> float:
    p = normalize_workspace(workspace, max_capacity)
    return sum(value * value for value in p.values())


def normalized_entropy(
    workspace: Mapping[str, float], max_capacity: int = 25
) -> float:
    p = normalize_workspace(workspace, max_capacity)
    if not p:
        return 0.0
    entropy = -sum(value * math.log(value) for value in p.values())
    return entropy / math.log(max_capacity)


def concept_mass(
    workspace: Mapping[str, float],
    concepts: Iterable[str],
    max_capacity: int = 25,
) -> float:
    p = normalize_workspace(workspace, max_capacity)
    return sum(p.get(concept, 0.0) for concept in concepts)


def workspace_turnover(
    previous: Mapping[str, float],
    current: Mapping[str, float],
    max_capacity: int = 25,
) -> float:
    p = normalize_workspace(previous, max_capacity)
    q = normalize_workspace(current, max_capacity)
    keys = set(p) | set(q)
    return 0.5 * sum(abs(p.get(key, 0.0) - q.get(key, 0.0)) for key in keys)


def measure_trace(
    observations: Sequence[SweepObservation], max_capacity: int = 25
) -> list[WorkspaceMetrics]:
    metrics: list[WorkspaceMetrics] = []
    previous_workspace: dict[str, Mapping[str, float]] = {}
    previous_phase: dict[str, str] = {}

    for observation in observations:
        if observation.phase not in PHASES:
            raise ValueError(f"unknown phase: {observation.phase}")
        if not observation.trace_id:
            raise ValueError("trace_id must be non-empty")
        _validate_workspace(observation.workspace, max_capacity)
        if observation.tau is not None and not math.isfinite(observation.tau):
            raise ValueError("tau must be finite when supplied")

        normalized = normalize_workspace(observation.workspace, max_capacity)
        prior_workspace = previous_workspace.get(observation.trace_id)
        prior_phase = previous_phase.get(observation.trace_id)
        metrics.append(
            WorkspaceMetrics(
                phase=observation.phase,
                trace_id=observation.trace_id,
                previous_phase=prior_phase,
                support_size=len(normalized),
                concentration=sum(v * v for v in normalized.values()),
                entropy=normalized_entropy(observation.workspace, max_capacity),
                target_mass=sum(normalized.get(x, 0.0) for x in observation.targets),
                disconfirming_mass=sum(
                    normalized.get(x, 0.0) for x in observation.disconfirming
                ),
                turnover=(
                    None
                    if prior_workspace is None
                    else workspace_turnover(
                        prior_workspace, observation.workspace, max_capacity
                    )
                ),
                tau=observation.tau,
            )
        )
        previous_workspace[observation.trace_id] = observation.workspace
        previous_phase[observation.trace_id] = observation.phase

    return metrics


def _trace_means(
    metrics: Sequence[WorkspaceMetrics],
    phase: str,
    field: str,
    *,
    previous_phase: str | None = None,
) -> dict[str, float]:
    buckets: dict[str, list[float]] = {}
    for metric in metrics:
        if metric.phase != phase:
            continue
        if previous_phase is not None and metric.previous_phase != previous_phase:
            continue
        value = getattr(metric, field)
        if value is None:
            continue
        buckets.setdefault(metric.trace_id, []).append(float(value))
    return {trace_id: fmean(values) for trace_id, values in buckets.items()}


def _paired_gain_criterion(
    criterion: str,
    lhs: Mapping[str, float],
    rhs: Mapping[str, float],
    minimum_gain: float,
    explanation: str,
) -> CriterionResult:
    shared_trace_ids = sorted(set(lhs) & set(rhs))
    if not shared_trace_ids:
        return CriterionResult(
            criterion,
            INSUFFICIENT_EVIDENCE,
            None,
            f">= {minimum_gain:.3f}",
            explanation,
        )
    paired_gains = [lhs[trace_id] - rhs[trace_id] for trace_id in shared_trace_ids]
    observed = fmean(paired_gains)
    return CriterionResult(
        criterion,
        CONSISTENT if observed >= minimum_gain else FALSIFIED,
        observed,
        f">= {minimum_gain:.3f}",
        explanation,
    )


def evaluate_hypothesis(
    observations: Sequence[SweepObservation],
    *,
    max_capacity: int = 25,
    min_target_gain: float = 0.10,
    min_concentration_gain: float = 0.05,
    min_counter_gain: float = 0.10,
    min_disconfirming_turnover: float = 0.20,
    max_candidate_turnover: float = 0.10,
    min_candidate_tau_fraction: float = 1.0,
    goldilocks: tuple[float, float] | None = None,
) -> list[CriterionResult]:
    _validate_thresholds(
        min_target_gain=min_target_gain,
        min_concentration_gain=min_concentration_gain,
        min_counter_gain=min_counter_gain,
        min_disconfirming_turnover=min_disconfirming_turnover,
        max_candidate_turnover=max_candidate_turnover,
        min_candidate_tau_fraction=min_candidate_tau_fraction,
    )
    metrics = measure_trace(observations, max_capacity=max_capacity)

    broad_target = _trace_means(metrics, "BROAD_SCAN", "target_mass")
    locked_target = _trace_means(metrics, "TARGET_LOCK", "target_mass")
    broad_concentration = _trace_means(metrics, "BROAD_SCAN", "concentration")
    locked_concentration = _trace_means(metrics, "TARGET_LOCK", "concentration")
    locked_counter = _trace_means(metrics, "TARGET_LOCK", "disconfirming_mass")
    counter_counter = _trace_means(
        metrics, "DISCONFIRMING_SWEEP", "disconfirming_mass"
    )
    counter_turnover = _trace_means(metrics, "DISCONFIRMING_SWEEP", "turnover")

    results = [
        _paired_gain_criterion(
            "JFS-1 target alignment",
            locked_target,
            broad_target,
            min_target_gain,
            "TARGET_LOCK should increase probability mass on declared target concepts within the same trace.",
        ),
        _paired_gain_criterion(
            "JFS-2 workspace concentration",
            locked_concentration,
            broad_concentration,
            min_concentration_gain,
            "TARGET_LOCK should concentrate the sparse workspace relative to BROAD_SCAN within the same trace.",
        ),
        _paired_gain_criterion(
            "JFS-3 disconfirming recruitment",
            counter_counter,
            locked_counter,
            min_counter_gain,
            "DISCONFIRMING_SWEEP should recruit declared counterevidence concepts relative to TARGET_LOCK within the same trace.",
        ),
    ]

    if not counter_turnover:
        results.append(
            CriterionResult(
                "JFS-4 disconfirming reorganization",
                INSUFFICIENT_EVIDENCE,
                None,
                f">= {min_disconfirming_turnover:.3f}",
                "A disconfirming sweep should measurably reorganize workspace contents.",
            )
        )
    else:
        observed = fmean(counter_turnover.values())
        results.append(
            CriterionResult(
                "JFS-4 disconfirming reorganization",
                CONSISTENT if observed >= min_disconfirming_turnover else FALSIFIED,
                observed,
                f">= {min_disconfirming_turnover:.3f}",
                "A disconfirming sweep should measurably reorganize workspace contents; each trace contributes equal weight.",
            )
        )

    candidate_metrics = [m for m in metrics if m.phase == "CANDIDATE_SET"]
    stable_turnover = _trace_means(
        metrics,
        "CANDIDATE_SET",
        "turnover",
        previous_phase="CANDIDATE_SET",
    )
    if not stable_turnover:
        results.append(
            CriterionResult(
                "JFS-5 operational fixed point",
                INSUFFICIENT_EVIDENCE,
                None,
                f"<= {max_candidate_turnover:.3f}",
                "Repeated CANDIDATE_SET readouts should stabilize in workspace coordinates.",
            )
        )
    else:
        observed = fmean(stable_turnover.values())
        results.append(
            CriterionResult(
                "JFS-5 operational fixed point",
                CONSISTENT if observed <= max_candidate_turnover else FALSIFIED,
                observed,
                f"<= {max_candidate_turnover:.3f}",
                "Repeated CANDIDATE_SET readouts should stabilize in workspace coordinates; each trace contributes equal weight.",
            )
        )

    if goldilocks is None:
        results.append(
            CriterionResult(
                "JFS-6 P10 spectral coupling",
                INSUFFICIENT_EVIDENCE,
                None,
                "candidate tau inside configured G",
                "The P10 tau coupling is evaluated only when a Goldilocks band is supplied.",
            )
        )
    else:
        low, high = goldilocks
        if not (math.isfinite(low) and math.isfinite(high) and low < high):
            raise ValueError("goldilocks must be a finite (low, high) interval")
        if not candidate_metrics or any(metric.tau is None for metric in candidate_metrics):
            results.append(
                CriterionResult(
                    "JFS-6 P10 spectral coupling",
                    INSUFFICIENT_EVIDENCE,
                    None,
                    f">= {min_candidate_tau_fraction:.3f} candidate tau inside [{low:.6g}, {high:.6g}]",
                    "Every candidate-set observation needs tau to test the paired P10 coupling without silently dropping missing measurements.",
                )
            )
        else:
            tau_inside_by_trace: dict[str, list[float]] = {}
            for metric in candidate_metrics:
                assert metric.tau is not None
                tau_inside_by_trace.setdefault(metric.trace_id, []).append(
                    1.0 if low <= metric.tau <= high else 0.0
                )
            trace_fractions = [
                fmean(values) for values in tau_inside_by_trace.values()
            ]
            fraction_inside = fmean(trace_fractions)
            results.append(
                CriterionResult(
                    "JFS-6 P10 spectral coupling",
                    CONSISTENT
                    if fraction_inside >= min_candidate_tau_fraction
                    else FALSIFIED,
                    fraction_inside,
                    f">= {min_candidate_tau_fraction:.3f} candidate tau inside configured G",
                    "Workspace stabilization and spectral state remain distinct; tau coverage is complete and each trace contributes equal weight.",
                )
            )

    return results


def overall_status(results: Sequence[CriterionResult]) -> str:
    if any(result.status == FALSIFIED for result in results):
        return "FALSIFIED_BY_TRACE"
    if any(result.status == INSUFFICIENT_EVIDENCE for result in results):
        return INSUFFICIENT_EVIDENCE
    return "NOT_FALSIFIED_BY_TRACE"


def load_jsonl(path: str | Path) -> list[SweepObservation]:
    observations: list[SweepObservation] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
                observations.append(SweepObservation.from_dict(payload))
            except Exception as exc:
                raise ValueError(f"invalid JSONL line {line_number}: {exc}") from exc
    return observations


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Falsification harness for the J-space / Framleis adaptive sweep hypothesis."
    )
    parser.add_argument("trace", help="JSONL trace with phase/workspace observations")
    parser.add_argument("--capacity", type=int, default=25)
    parser.add_argument("--min-target-gain", type=float, default=0.10)
    parser.add_argument("--min-concentration-gain", type=float, default=0.05)
    parser.add_argument("--min-counter-gain", type=float, default=0.10)
    parser.add_argument("--min-disconfirming-turnover", type=float, default=0.20)
    parser.add_argument("--max-candidate-turnover", type=float, default=0.10)
    parser.add_argument("--min-candidate-tau-fraction", type=float, default=1.0)
    parser.add_argument("--goldilocks-low", type=float)
    parser.add_argument("--goldilocks-high", type=float)
    args = parser.parse_args()

    band = None
    if args.goldilocks_low is not None or args.goldilocks_high is not None:
        if args.goldilocks_low is None or args.goldilocks_high is None:
            parser.error("both --goldilocks-low and --goldilocks-high are required")
        band = (args.goldilocks_low, args.goldilocks_high)

    observations = load_jsonl(args.trace)
    results = evaluate_hypothesis(
        observations,
        max_capacity=args.capacity,
        min_target_gain=args.min_target_gain,
        min_concentration_gain=args.min_concentration_gain,
        min_counter_gain=args.min_counter_gain,
        min_disconfirming_turnover=args.min_disconfirming_turnover,
        max_candidate_turnover=args.max_candidate_turnover,
        min_candidate_tau_fraction=args.min_candidate_tau_fraction,
        goldilocks=band,
    )
    payload = {
        "status": overall_status(results),
        "criteria": [
            {
                "criterion": result.criterion,
                "status": result.status,
                "observed": result.observed,
                "threshold": result.threshold,
                "explanation": result.explanation,
            }
            for result in results
        ],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 1 if payload["status"] == "FALSIFIED_BY_TRACE" else 0


if __name__ == "__main__":
    raise SystemExit(main())
