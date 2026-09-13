"""Policy-driven aggregation for VAIG instrument results.

Aggregation preserves disagreement and fail states. It never grants authority;
it only produces a runtime evaluation signal for later REHT clearance.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

from vaig.instruments.result import InstrumentResult, InstrumentStatus


class AggregationMode(str, Enum):
    RISK_WEIGHTED_MAX = "RISK_WEIGHTED_MAX"
    HARD_VETO = "HARD_VETO"
    MINORITY_VETO = "MINORITY_VETO"
    CALIBRATED_FUSION = "CALIBRATED_FUSION"


@dataclass(frozen=True)
class AggregationPolicy:
    mode: AggregationMode = AggregationMode.RISK_WEIGHTED_MAX
    version: str = "risk-weighted-max-v1"
    slot_weights: Mapping[str, float] = field(default_factory=dict)
    hard_veto_slots: Tuple[str, ...] = ()
    independent_slots: Tuple[str, ...] = ()
    halt_threshold: float = 0.75
    veto_threshold: float = 0.75
    minority_veto_count: int = 2
    calibration_profile: Optional[str] = None

    def __post_init__(self) -> None:
        for name in ("halt_threshold", "veto_threshold"):
            value = float(getattr(self, name))
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")
        if self.minority_veto_count < 1:
            raise ValueError("minority_veto_count must be at least 1")
        for slot, weight in self.slot_weights.items():
            if not slot:
                raise ValueError("slot weight requires a non-empty slot name")
            if float(weight) < 0.0:
                raise ValueError("slot weights cannot be negative")


@dataclass(frozen=True)
class AggregationResult:
    mode: AggregationMode
    policy_version: str
    score: float
    contributing_slots: Tuple[str, ...] = ()
    vetoed_slots: Tuple[str, ...] = ()
    high_severity_slots: Tuple[str, ...] = ()
    unavailable_required_slots: Tuple[str, ...] = ()
    failed_slots: Tuple[str, ...] = ()
    abstained: bool = False
    abstention_reason: Optional[str] = None
    halt_requested: bool = False
    explanation: str = ""
    calibration_profile: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["mode"] = self.mode.value
        return payload


def _weighted_scores(
    measured: Mapping[str, float],
    weights: Mapping[str, float],
) -> Dict[str, float]:
    return {
        slot: min(1.0, max(0.0, score * float(weights.get(slot, 1.0))))
        for slot, score in measured.items()
    }


def aggregate_instrument_results(
    results: Mapping[str, InstrumentResult],
    policy: Optional[AggregationPolicy] = None,
    required_slots: Iterable[str] = (),
    failed_slots: Iterable[str] = (),
) -> AggregationResult:
    """Aggregate actual measurements under an explicit policy.

    Unavailable and failed results never become numeric zero-risk evidence.
    """

    selected = policy or AggregationPolicy()
    required = set(required_slots)
    failed = set(failed_slots)
    failed.update(
        slot for slot, result in results.items()
        if result.status is InstrumentStatus.ERROR
    )
    unavailable_required = tuple(sorted(
        slot for slot in required
        if slot not in results or results[slot].status is not InstrumentStatus.MEASURED
    ))

    measured = {
        slot: risk
        for slot, result in results.items()
        for risk in [result.risk_for_aggregation]
        if risk is not None
    }
    contributing = tuple(sorted(measured))
    weighted = _weighted_scores(measured, selected.slot_weights)
    fallback_score = max(weighted.values(), default=0.0)

    if failed:
        return AggregationResult(
            mode=selected.mode,
            policy_version=selected.version,
            score=fallback_score,
            contributing_slots=contributing,
            unavailable_required_slots=unavailable_required,
            failed_slots=tuple(sorted(failed)),
            abstained=True,
            abstention_reason="One or more instruments failed.",
            halt_requested=True,
            explanation="Aggregation abstained because an instrument failed.",
            calibration_profile=selected.calibration_profile,
        )

    if unavailable_required:
        return AggregationResult(
            mode=selected.mode,
            policy_version=selected.version,
            score=fallback_score,
            contributing_slots=contributing,
            unavailable_required_slots=unavailable_required,
            abstained=True,
            abstention_reason="Required measurements are unavailable.",
            halt_requested=True,
            explanation="Aggregation abstained because required measurements were unavailable.",
            calibration_profile=selected.calibration_profile,
        )

    if selected.mode is AggregationMode.CALIBRATED_FUSION:
        if not selected.calibration_profile:
            return AggregationResult(
                mode=selected.mode,
                policy_version=selected.version,
                score=fallback_score,
                contributing_slots=contributing,
                abstained=True,
                abstention_reason="CALIBRATED_FUSION requires a calibration profile.",
                halt_requested=True,
                explanation="Uncalibrated fusion is not admissible.",
            )
        missing_weights = tuple(sorted(set(measured).difference(selected.slot_weights)))
        if not selected.slot_weights or missing_weights:
            return AggregationResult(
                mode=selected.mode,
                policy_version=selected.version,
                score=fallback_score,
                contributing_slots=contributing,
                abstained=True,
                abstention_reason="CALIBRATED_FUSION requires explicit weights for every measured slot.",
                halt_requested=True,
                explanation="Fusion abstained because its calibrated weight contract was incomplete.",
                calibration_profile=selected.calibration_profile,
            )
        denominator = sum(float(selected.slot_weights[slot]) for slot in measured)
        if denominator <= 0.0:
            return AggregationResult(
                mode=selected.mode,
                policy_version=selected.version,
                score=0.0,
                contributing_slots=contributing,
                abstained=True,
                abstention_reason="CALIBRATED_FUSION weights sum to zero.",
                halt_requested=True,
                explanation="Fusion abstained because no calibrated contribution remained.",
                calibration_profile=selected.calibration_profile,
            )
        score = sum(
            measured[slot] * float(selected.slot_weights[slot])
            for slot in measured
        ) / denominator
        high = tuple(sorted(slot for slot, value in measured.items() if value >= selected.halt_threshold))
        halt = score >= selected.halt_threshold
        return AggregationResult(
            mode=selected.mode,
            policy_version=selected.version,
            score=round(score, 4),
            contributing_slots=contributing,
            high_severity_slots=high,
            halt_requested=halt,
            explanation="Applied calibrated weighted fusion under an explicit calibration profile.",
            calibration_profile=selected.calibration_profile,
        )

    score = fallback_score

    if selected.mode is AggregationMode.HARD_VETO:
        vetoed = tuple(sorted(
            slot for slot in selected.hard_veto_slots
            if weighted.get(slot, 0.0) >= selected.veto_threshold
        ))
        return AggregationResult(
            mode=selected.mode,
            policy_version=selected.version,
            score=round(score, 4),
            contributing_slots=contributing,
            vetoed_slots=vetoed,
            high_severity_slots=tuple(sorted(slot for slot, value in weighted.items() if value >= selected.halt_threshold)),
            halt_requested=bool(vetoed),
            explanation=(
                "A configured invariant slot crossed the veto threshold."
                if vetoed else "No configured invariant slot crossed the veto threshold."
            ),
        )

    if selected.mode is AggregationMode.MINORITY_VETO:
        high = tuple(sorted(
            slot for slot in selected.independent_slots
            if weighted.get(slot, 0.0) >= selected.veto_threshold
        ))
        vetoed = high if len(high) >= selected.minority_veto_count else ()
        return AggregationResult(
            mode=selected.mode,
            policy_version=selected.version,
            score=round(score, 4),
            contributing_slots=contributing,
            vetoed_slots=vetoed,
            high_severity_slots=high,
            halt_requested=bool(vetoed),
            explanation=(
                "Independent high-severity minority reached the veto count."
                if vetoed else "Independent high-severity minority remained below the veto count."
            ),
        )

    high = tuple(sorted(slot for slot, value in weighted.items() if value >= selected.halt_threshold))
    return AggregationResult(
        mode=AggregationMode.RISK_WEIGHTED_MAX,
        policy_version=selected.version,
        score=round(score, 4),
        contributing_slots=contributing,
        vetoed_slots=high,
        high_severity_slots=high,
        halt_requested=bool(high),
        explanation=(
            "Risk-weighted maximum crossed the halt threshold."
            if high else "Applied risk-weighted maximum without threshold breach."
        ),
    )
