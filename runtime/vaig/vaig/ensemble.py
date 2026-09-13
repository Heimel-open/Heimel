"""VAIGEnsemble — L1-4, de åtte blinde menn."""

import hashlib
import math
import time
import uuid
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from vaig.aggregation import (
    AggregationMode,
    AggregationPolicy,
    AggregationResult,
    aggregate_instrument_results,
)
from vaig.guard import BlindspotGuard, GuardReport
from vaig.instruments.eval import ContinuousEvaluator
from vaig.instruments.registry import build_optimal_ensemble, SLOT_ORDER
from vaig.instruments.result import InstrumentResult, InstrumentStatus
from vaig.model_signals import ModelSignalBundle
from vaig.signal_source import SignalSource
from vaig.trajectory import Trajectory
from vaig.worm import WORMLog


class DistrustLevel(Enum):
    TRUSTED = "L0"
    MONITOR = "L1"
    WARN = "L2"
    DEGRADE = "L3"
    HALT = "L4"


@dataclass
class ValidationResult:
    entry_id: str
    level: DistrustLevel
    combined_score: float
    scores: Dict[str, float]
    worm_hash: str
    latency_ms: float
    instrument_errors: Dict[str, str] = field(default_factory=dict)
    instrument_results: Dict[str, InstrumentResult] = field(default_factory=dict)
    required_unmeasured: Tuple[str, ...] = ()
    aggregation: Optional[AggregationResult] = None
    veto_reasons: Tuple[str, ...] = ()
    guard_report: Optional[GuardReport] = None

    @property
    def should_halt(self) -> bool:
        return self.level == DistrustLevel.HALT

    def __str__(self) -> str:
        lines = [
            f"combined_score: {self.combined_score:.4f}",
            f"distrust_level: {self.level.value} — {self.level.name}",
            "instruments:",
        ]
        for slot, result in self.instrument_results.items():
            if result.status is InstrumentStatus.MEASURED:
                lines.append(f"  {slot}: {result.raw_score:.2f} ({result.status.value})")
            else:
                lines.append(f"  slot: — ({result.status.value})")
        if self.instrument_errors:
            lines.append("instrument_errors:")
            for slot, error in self.instrument_errors.items():
                lines.append(f"  {slot}: {error}")
        if self.required_unmeasured:
            lines.append("required_unmeasured: " + ", ".join(self.required_unmeasured))
        if self.aggregation is not None:
            lines.append(
                f"aggregation: {self.aggregation.mode.value} "
                f"({self.aggregation.policy_version})"
            )
            if self.aggregation.vetoed_slots:
                lines.append("vetoed_slots: " + ", ".join(self.aggregation.vetoed_slots))
            if self.aggregation.abstained:
                lines.append(f"abstained: {self.aggregation.abstention_reason}")
        if self.veto_reasons:
            lines.append("veto_reasons: " + "; ".join(self.veto_reasons))
        lines.append(f"worm_hash: sha256:{self.worm_hash[:8]}...")
        return "\n".join(lines)


_THRESHOLDS_DEFAULT = {
    "HALT": 0.75, "DEGRADE": 0.55, "WARN": 0.35, "MONITOR": 0.15,
}


def _score_to_level(
    score: float,
    l4_auto: bool,
    thresholds: Optional[Dict[str, float]] = None,
) -> DistrustLevel:
    t = thresholds or _THRESHOLDS_DEFAULT
    use_custom_thresholds = thresholds is not None
    if (l4_auto or use_custom_thresholds) and score >= t.get("HALT", 0.75):
        return DistrustLevel.HALT
    if score >= t.get("DEGRADE", 0.55):
        return DistrustLevel.DEGRADE
    if score >= t.get("WARN", 0.35):
        return DistrustLevel.WARN
    if score >= t.get("MONITOR", 0.15):
        return DistrustLevel.MONITOR
    return DistrustLevel.TRUSTED


def _implementation_name(instrument: object) -> str:
    cls = instrument.__class__
    return f"{cls.__module__}.{cls.__name__}"


def _input_is_supplied(value: object) -> bool:
    if value is None:
        return False
    try:
        return len(value) > 0
    except TypeError:
        return True


def _calibration_profile(instrument: object) -> Optional[str]:
    getter = getattr(instrument, "calibration_profile_id", None)
    return getter() if callable(getter) else None


def _is_calibrated(instrument: object, requires_calibration: bool) -> bool:
    if not requires_calibration:
        return True
    checker = getattr(instrument, "is_calibrated", None)
    return bool(checker()) if callable(checker) else False


class VAIGEnsemble:
    """
    L1-4 — de åtte blinde menn.

    Runs typed instruments over exact native inputs, applies policy-driven
    aggregation, and returns a DistrustLevel. Missing input and missing
    calibration are explicit states, never measured zero risk.
    """

    def __init__(
        self,
        log_path: str = "vaig_audit.jsonl",
        l4_auto_trigger: bool = False,
        generate_fn: Optional[Callable[[str], str]] = None,
        judge_fn: Optional[Callable[[str], str]] = None,
        aggregation_policy: Optional[AggregationPolicy] = None,
        signal_source: Optional[SignalSource] = None,
    ):
        self.instruments = build_optimal_ensemble()
        self.worm = WORMLog(log_path)
        self.l4_auto = l4_auto_trigger
        self.generate_fn = generate_fn
        self.judge_fn = judge_fn
        self.aggregation_policy = aggregation_policy or AggregationPolicy()
        self.signal_source = signal_source
        self.blindspot_guard = BlindspotGuard()
        self.evaluator = ContinuousEvaluator(self.worm.path)

    def evaluate(
        self,
        prompt: str,
        response: str,
        generate_fn: Optional[Callable[[str], str]] = None,
        active_slots: Optional[Set[str]] = None,
        extra_scores: Optional[Dict[str, float]] = None,
        context: Optional[Dict] = None,
        thresholds: Optional[Dict[str, float]] = None,
        instrument_inputs: Optional[Dict[str, Dict]] = None,
        required_slots: Optional[Set[str]] = None,
        aggregation_policy: Optional[AggregationPolicy] = None,
        model_signals: Optional[ModelSignalBundle] = None,
        judge_fn: Optional[Callable[[str], str]] = None,
        signal_source: Optional[SignalSource] = None,
        trajectory: Optional["Trajectory"] = None,
    ) -> ValidationResult:
        """
        instrument_inputs remains a direct compatibility path.
        model_signals is the preferred hash-bound provider/local-model input.
        """
        t0 = time.perf_counter()
        gfn = generate_fn or self.generate_fn
        jfn = judge_fn or self.judge_fn
        ssrc = signal_source or self.signal_source
        signal_failure: Optional[Tuple[str, str]] = None
        bundle: Optional[ModelSignalBundle] = None
        if ssrc is not None:
            try:
                bundle = ssrc.fetch(prompt, response)
            except Exception as exc:  # fail closed, never silent 0.0
                signal_failure = (getattr(ssrc, "id", "signal-source"), str(exc))
        scores: Dict[str, float] = {}
        instrument_errors: Dict[str, str] = {}
        instrument_results: Dict[str, InstrumentResult] = {}
        required = set(required_slots or set())

        supplied_by_slot: Dict[str, Dict] = {}
        signal_refs: Dict[str, Tuple[str, ...]] = {}
        if bundle is not None:
            supplied_by_slot.update(bundle.instrument_inputs())
            signal_refs.update(bundle.evidence_refs())
            src_id = getattr(ssrc, "id", "")
            if src_id:
                for slot in bundle.instrument_inputs():
                    signal_refs[slot] = signal_refs.get(slot, ()) + (src_id,)
        if model_signals is not None:
            supplied_by_slot.update(model_signals.instrument_inputs())
            signal_refs.update(model_signals.evidence_refs())
        for slot, values in (instrument_inputs or {}).items():
            supplied_by_slot.setdefault(slot, {}).update(values)
            signal_refs.pop(slot, None)

        requested = set(SLOT_ORDER) if active_slots is None else set(active_slots)
        requested.update(required)
        slots_to_run = [slot for slot in SLOT_ORDER if slot in requested]
        slots_to_run.extend(sorted(requested.difference(SLOT_ORDER)))

        for slot in slots_to_run:
            instrument = self.instruments.get(slot)
            requires_judge = bool(getattr(instrument, "requires_judge_fn", False))
            instrument_self_judging = (
                bool(getattr(instrument, "self_judging", False)) if instrument else False
            )
            # P0.5 (full): if an independent judge_fn is injected, this slot is
            # no longer self-judging even if the instrument declares itself so.
            judged_independently = bool(requires_judge and jfn is not None)
            self_judging = instrument_self_judging and not judged_independently
            supplied_inputs = ["prompt", "response"]
            if gfn is not None:
                supplied_inputs.append("generate_fn")
            if jfn is not None:
                supplied_inputs.append("judge_fn")
            supplied_inputs.extend(sorted(supplied_by_slot.get(slot, {}).keys()))

            if instrument is None:
                instrument_results[slot] = InstrumentResult(
                    slot=slot,
                    status=InstrumentStatus.UNAVAILABLE,
                    supplied_inputs=tuple(supplied_inputs),
                    failure_reason="No available implementation for requested slot.",
                    self_judging=self_judging,
                )
                continue

            implementation = _implementation_name(instrument)
            version = str(getattr(instrument, "version", "unversioned"))
            requires_generate = bool(getattr(instrument, "requires_generate_fn", False))
            required_native = tuple(getattr(instrument, "required_native_inputs", ()))
            requires_calibration = bool(getattr(instrument, "requires_calibration", False))
            requires_trajectory = bool(getattr(instrument, "requires_trajectory", False))
            # P0.5 (full): when an independent judge_fn is supplied for a
            # judge-requiring instrument, generate_fn is no longer required
            # (the judge plays the judge role). Otherwise generate_fn stays
            # required for self-judging instruments.
            judge_supplied = bool(requires_judge and jfn is not None)
            generate_required = requires_generate and not judge_supplied
            required_inputs = (
                (("generate_fn",) if generate_required else ())
                + (("judge_fn",) if requires_judge else ())
                + required_native
                + (("calibration_profile",) if requires_calibration else ())
            )
            if requires_trajectory:
                required_inputs = required_inputs + ("trajectory",)
            calibration_profile = _calibration_profile(instrument)
            if calibration_profile:
                supplied_inputs.append("calibration_profile")
            if requires_trajectory and trajectory is not None:
                supplied_inputs.append("trajectory")
            if requires_trajectory and trajectory is None:
                instrument_results[slot] = InstrumentResult(
                    slot=slot,
                    status=InstrumentStatus.UNAVAILABLE,
                    implementation=implementation,
                    version=version,
                    required_inputs=required_inputs,
                    supplied_inputs=tuple(supplied_inputs),
                    failure_reason="Required input 'trajectory' was not supplied.",
                    self_judging=self_judging,
                )
                continue

            # P0.5 (full): a judge-requiring instrument with no judge source
            # fails closed. Prefer an injected judge_fn (independent); fall back
            # to generate_fn only as a self-judge (flagged via self_judging).
            if requires_judge and jfn is None and gfn is None:
                instrument_results[slot] = InstrumentResult(
                    slot=slot,
                    status=InstrumentStatus.UNCALIBRATED,
                    implementation=implementation,
                    version=version,
                    required_inputs=required_inputs,
                    supplied_inputs=tuple(supplied_inputs),
                    evidence_refs=signal_refs.get(slot, ()),
                    calibration_profile=calibration_profile,
                    failure_reason="Required judge_fn (or generate_fn) was not supplied.",
                    self_judging=False,
                )
                continue

            if not _is_calibrated(instrument, requires_calibration):
                instrument_results[slot] = InstrumentResult(
                    slot=slot,
                    status=InstrumentStatus.UNCALIBRATED,
                    implementation=implementation,
                    version=version,
                    required_inputs=required_inputs,
                    supplied_inputs=tuple(supplied_inputs),
                    evidence_refs=signal_refs.get(slot, ()),
                    failure_reason="Versioned calibration artifact is not bound.",
                    self_judging=self_judging,
                )
                continue

            if generate_required and gfn is None:
                instrument_results[slot] = InstrumentResult(
                    slot=slot,
                    status=InstrumentStatus.UNAVAILABLE,
                    implementation=implementation,
                    version=version,
                    required_inputs=required_inputs,
                    supplied_inputs=tuple(supplied_inputs),
                    evidence_refs=signal_refs.get(slot, ()),
                    calibration_profile=calibration_profile,
                    failure_reason="Required generate_fn was not supplied.",
                    self_judging=self_judging,
                )
                continue

            missing_native = tuple(
                name for name in required_native
                if not _input_is_supplied(supplied_by_slot.get(slot, {}).get(name))
            )
            if missing_native:
                if signal_failure is not None:
                    src_id, src_err = signal_failure
                    reason = (
                        f"Signal source '{src_id}' unavailable "
                        f"({src_err}); required native inputs not supplied: "
                        + ", ".join(missing_native)
                    )
                elif ssrc is None:
                    reason = (
                        "SignalSource not supplied; required native inputs "
                        "were not supplied: " + ", ".join(missing_native)
                    )
                else:
                    reason = (
                        "Required native inputs were not supplied: "
                        + ", ".join(missing_native)
                    )
                instrument_results[slot] = InstrumentResult(
                    slot=slot,
                    status=InstrumentStatus.UNAVAILABLE,
                    implementation=implementation,
                    version=version,
                    required_inputs=required_inputs,
                    supplied_inputs=tuple(supplied_inputs),
                    evidence_refs=signal_refs.get(slot, ()),
                    calibration_profile=calibration_profile,
                    failure_reason=reason,
                    self_judging=self_judging,
                )
                continue

            instrument_started = time.perf_counter()
            try:
                kwargs: Dict[str, Any] = {"prompt": prompt, "response": response}
                if requires_judge and jfn is not None:
                    # P0.5 (full): independent judge takes precedence.
                    kwargs["judge_fn"] = jfn
                elif requires_generate:
                    kwargs["generate_fn"] = gfn
                if requires_trajectory and trajectory is not None:
                    kwargs["trajectory"] = trajectory
                kwargs.update(supplied_by_slot.get(slot, {}))

                raw_score = float(instrument.score(**kwargs))
                if not math.isfinite(raw_score) or not 0.0 <= raw_score <= 1.0:
                    raise ValueError("instrument score must be finite and in [0, 1]")

                rounded = round(raw_score, 4)
                scores[slot] = rounded
                instrument_results[slot] = InstrumentResult(
                    slot=slot,
                    status=InstrumentStatus.MEASURED,
                    raw_score=rounded,
                    implementation=implementation,
                    version=version,
                    required_inputs=required_inputs,
                    supplied_inputs=tuple(supplied_inputs),
                    evidence_refs=signal_refs.get(slot, ()),
                    calibration_profile=calibration_profile,
                    latency_ms=round((time.perf_counter() - instrument_started) * 1000, 3),
                    self_judging=self_judging,
                )
            except Exception as exc:
                instrument_errors[slot] = exc.__class__.__name__
                scores[slot] = 1.0
                instrument_results[slot] = InstrumentResult(
                    slot=slot,
                    status=InstrumentStatus.ERROR,
                    implementation=implementation,
                    version=version,
                    required_inputs=required_inputs,
                    supplied_inputs=tuple(supplied_inputs),
                    evidence_refs=signal_refs.get(slot, ()),
                    calibration_profile=calibration_profile,
                    latency_ms=round((time.perf_counter() - instrument_started) * 1000, 3),
                    failure_reason=exc.__class__.__name__,
                    self_judging=self_judging,
                )

        for slot, value in (extra_scores or {}).items():
            self_judging = False  # external adapters are not self-judging this model
            try:
                raw_score = float(value)
                if not math.isfinite(raw_score) or not 0.0 <= raw_score <= 1.0:
                    raise ValueError("external score must be finite and in [0, 1]")
                rounded = round(raw_score, 4)
                scores[slot] = rounded
                instrument_results[slot] = InstrumentResult(
                    slot=slot,
                    status=InstrumentStatus.MEASURED,
                    raw_score=rounded,
                    implementation="external_adapter",
                    supplied_inputs=("external_score",),
                    self_judging=self_judging,
                )
            except Exception as exc:
                instrument_errors[slot] = exc.__class__.__name__
                scores[slot] = 1.0
                instrument_results[slot] = InstrumentResult(
                    slot=slot,
                    status=InstrumentStatus.ERROR,
                    implementation="external_adapter",
                    supplied_inputs=("external_score",),
                    failure_reason=exc.__class__.__name__,
                    self_judging=self_judging,
                )

        # P0.2 integration: compute veto_reasons from aggregation result
        veto_reasons: List[str] = []

        # Blindspot guard: self-judged model measurements without declared
        # confidence, and low-confidence measurements, abstain (fail-closed)
        # before they can drive the aggregate; low agreement across measured
        # model slots reduces signal trust.
        instrument_results, guard_report = self.blindspot_guard.guard_results(
            instrument_results
        )

        # Calibration feedback: once enough labeled outcomes exist, the
        # AUC-based calibrated weights override the policy's slot weights so
        # instruments that measurably discriminate risk carry the decision and
        # instruments worse than chance are disabled.
        effective_policy = aggregation_policy or self.aggregation_policy
        calibrated = self.evaluator.calibrated_weights(min_samples=10)
        if calibrated:
            effective_policy = replace(
                effective_policy,
                slot_weights={**effective_policy.slot_weights, **calibrated},
                calibration_profile="auc-calibrated",
            )

        # Use main's policy-driven aggregation
        aggregation = aggregate_instrument_results(
            instrument_results,
            policy=effective_policy,
            required_slots=required,
            failed_slots=instrument_errors,
        )
        combined = aggregation.score
        level = _score_to_level(combined, self.l4_auto, thresholds)
        if aggregation.halt_requested or aggregation.abstained:
            level = DistrustLevel.HALT

        # Compute veto reasons compatible with P0.2 semantics
        if aggregation.vetoed_slots:
            label = {
                AggregationMode.HARD_VETO: "invariant-veto",
                AggregationMode.MINORITY_VETO: "minority-veto",
                AggregationMode.RISK_WEIGHTED_MAX: "high-severity",
                AggregationMode.CALIBRATED_FUSION: "high-severity",
            }.get(aggregation.mode, "veto")
            for slot in aggregation.vetoed_slots:
                veto_reasons.append(f"{label}: {slot}")
        if aggregation.abstained:
            veto_reasons.append(f"abstained: {aggregation.abstention_reason}")
        if aggregation.halt_requested and not veto_reasons:
            veto_reasons.append("halt_requested")

        required_unmeasured = tuple(sorted(
            slot
            for slot in required
            if slot not in instrument_results
            or instrument_results[slot].status is not InstrumentStatus.MEASURED
        ))
        if instrument_errors or required_unmeasured:
            level = DistrustLevel.HALT

        entry_id = str(uuid.uuid4())[:8]
        latency = (time.perf_counter() - t0) * 1000

        worm_payload = {
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "combined": combined,
            "level": level.value,
            "scores": scores,
            "instrument_scores": scores,
            "instrument_results": {
                slot: result.to_dict() for slot, result in instrument_results.items()
            },
            "aggregation": aggregation.to_dict(),
        }
        if instrument_errors:
            worm_payload["instrument_errors"] = instrument_errors
        if required_unmeasured:
            worm_payload["required_unmeasured"] = list(required_unmeasured)
        if veto_reasons:
            worm_payload["veto_reasons"] = veto_reasons
        if context:
            worm_payload.update(context)
        if model_signals is not None:
            worm_payload["model_signal_binding"] = model_signals.audit_metadata()

        worm_hash = self.worm.append(entry_id, worm_payload)

        return ValidationResult(
            entry_id=entry_id,
            level=level,
            combined_score=round(combined, 4),
            scores=scores,
            worm_hash=worm_hash,
            latency_ms=round(latency, 1),
            instrument_errors=instrument_errors,
            instrument_results=instrument_results,
            required_unmeasured=required_unmeasured,
            aggregation=aggregation,
            veto_reasons=tuple(veto_reasons),
            guard_report=guard_report,
        )
