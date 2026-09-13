"""Signed, replayable evaluation report for VAIG -> REHT handoff.

P0.9 of the VAIG rebuild (nsolland/VAIG#133): VAIG must emit one bounded,
hash-chained report that REHT can replay and reject when it is stale,
mismatched, uncalibrated or incomplete. The report never grants execution
authority; it only records what VAIG actually measured and what it refused to
assert.

Design rules (consistent with vaig/aggregation.py and vaig/evidence_intake.py):

* A missing, failed or uncalibrated measurement is recorded as a *status*,
  never coerced to a numeric 0.0 risk.
* The report is deterministic: the same evaluation produces the same digest,
  so REHT can replay it and detect tampering or silent regeneration.
* ``execution_authority`` is always False. ``requires_reht_clearance`` is
  always True. VAIG only produces runtime signals; clearance is REHT's call.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from vaig.instruments.result import InstrumentResult, InstrumentStatus
from vaig.orchestrator import OrchestratorResult
from vaig.epistemic_underdetermination import UnderdeterminationAssessment
from vaig.analytic_tradecraft import AnalyticTradecraftAssessment

if TYPE_CHECKING:
    from vaig.calibration import CalibrationProfile


class ReportDisposition(str, Enum):
    """Outcome REHT should apply to a replayed report."""

    ADMISSIBLE = "ADMISSIBLE"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class InstrumentSlotReport:
    """One slot's recorded measurement state — never a silent 0.0."""

    slot: str
    status: str
    risk: Optional[float]
    implementation: str = ""
    version: str = "unversioned"
    calibration_profile: Optional[str] = None
    calibration_metrics: Optional[CalibrationProfile] = None
    failure_reason: Optional[str] = None
    self_judging: bool = False

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["risk"] = self.risk
        if self.calibration_metrics is not None:
            payload["calibration_metrics"] = self.calibration_metrics.as_dict()
        return payload


def _slot_to_dict(slot: Any) -> Dict[str, Any]:
    return slot.to_dict() if hasattr(slot, "to_dict") else dict(slot)


@dataclass(frozen=True)
class EvaluationReport:
    """Hash-bound, replayable record of one VAIG evaluation.

    REHT replays the canonical payload and compares the recomputed digest to
    ``report_digest``. If they differ the report was tampered with or silently
    regenerated. If ``rejection_reasons`` is non-empty the report is not
    admissible for clearance regardless of digest integrity.
    """

    report_id: str
    generated_at: datetime
    schema_version: str
    evaluation_id: str
    distrust_level: str
    combined_score: float
    should_halt: bool
    requires_human_review: bool
    evidence_state: str
    evidence_blocked: bool
    execution_authority: bool
    requires_reht_clearance: bool
    slots: Tuple[InstrumentSlotReport, ...]
    required_unmeasured: Tuple[str, ...]
    instrument_errors: Tuple[Tuple[str, str], ...]
    aggregation_mode: Optional[str]
    aggregation_abstained: bool
    aggregation_abstention_reason: Optional[str]
    veto_reasons: Tuple[str, ...]
    rejection_reasons: Tuple[str, ...]
    worm_hash: Optional[str]
    report_digest: str
    underdetermination: Optional[Dict[str, Any]] = None
    tradecraft: Optional[Dict[str, Any]] = None

    @property
    def admissible(self) -> bool:
        return not self.rejection_reasons

    @property
    def disposition(self) -> ReportDisposition:
        return (
            ReportDisposition.REJECTED
            if self.rejection_reasons
            else ReportDisposition.ADMISSIBLE
        )

    def to_dict(self) -> Dict[str, Any]:
        generated_at = (
            self.generated_at.isoformat()
            if isinstance(self.generated_at, datetime)
            else self.generated_at
        )
        payload: Dict[str, Any] = {
            "report_id": self.report_id,
            "generated_at": generated_at,
            "schema_version": self.schema_version,
            "evaluation_id": self.evaluation_id,
            "distrust_level": self.distrust_level,
            "combined_score": self.combined_score,
            "should_halt": self.should_halt,
            "requires_human_review": self.requires_human_review,
            "evidence_state": self.evidence_state,
            "evidence_blocked": self.evidence_blocked,
            "execution_authority": self.execution_authority,
            "requires_reht_clearance": self.requires_reht_clearance,
            "slots": [_slot_to_dict(s) for s in self.slots],
            "required_unmeasured": list(self.required_unmeasured),
            "instrument_errors": [list(p) for p in self.instrument_errors],
            "aggregation_mode": self.aggregation_mode,
            "aggregation_abstained": self.aggregation_abstained,
            "aggregation_abstention_reason": self.aggregation_abstention_reason,
            "veto_reasons": list(self.veto_reasons),
            "rejection_reasons": list(self.rejection_reasons),
            "worm_hash": self.worm_hash,
            "report_digest": self.report_digest,
            "underdetermination": self.underdetermination,
            "tradecraft": self.tradecraft,
        }
        return payload

    def canonical_payload(self) -> Dict[str, Any]:
        """Deterministic, hashable view excluding the digest itself.

        ``generated_at`` is intentionally excluded: the digest binds the
        evaluation content, not the wall-clock moment the report was emitted,
        so the same evaluation always yields the same digest.
        """

        return {
            "report_id": self.report_id,
            "schema_version": self.schema_version,
            "evaluation_id": self.evaluation_id,
            "distrust_level": self.distrust_level,
            "combined_score": self.combined_score,
            "should_halt": self.should_halt,
            "requires_human_review": self.requires_human_review,
            "evidence_state": self.evidence_state,
            "evidence_blocked": self.evidence_blocked,
            "execution_authority": self.execution_authority,
            "requires_reht_clearance": self.requires_reht_clearance,
            "slots": [_slot_to_dict(s) for s in self.slots],
            "required_unmeasured": sorted(self.required_unmeasured),
            "instrument_errors": sorted(
                [list(p) for p in self.instrument_errors]
            ),
            "aggregation_mode": self.aggregation_mode,
            "aggregation_abstained": self.aggregation_abstained,
            "aggregation_abstention_reason": self.aggregation_abstention_reason,
            "veto_reasons": sorted(self.veto_reasons),
            "rejection_reasons": sorted(self.rejection_reasons),
            "worm_hash": self.worm_hash,
            "underdetermination": self.underdetermination,
            "tradecraft": self.tradecraft,
        }

    def verify(self) -> Tuple[bool, List[str]]:
        """Replay check REHT can run.

        Returns (intact, problems). ``intact`` is False if the digest does not
        match the canonical payload (tampering / silent regeneration). When
        ``intact`` is True but ``rejection_reasons`` is non-empty, the report is
        internally consistent yet not admissible for clearance.
        """

        problems: List[str] = []
        expected = _digest_payload(self.canonical_payload())
        tampered = expected != self.report_digest
        if tampered:
            problems.append(
                "report_digest mismatch: report was altered or silently regenerated"
            )
        if self.execution_authority is not False:
            problems.append("report claims execution authority (must be False)")
        if self.requires_reht_clearance is not True:
            problems.append("report does not require REHT clearance")
        if self.rejection_reasons:
            problems.append(
                "report is not admissible: " + "; ".join(self.rejection_reasons)
            )
        # `intact` reflects tamper-integrity only (digest + authority fields),
        # NOT admissibility. A report can be internally consistent yet rejected
        # (rejection_reasons non-empty) — that is still intact, just not
        # admissible for clearance (see the `admissible` property).
        intact = (
            not tampered
            and self.execution_authority is False
            and self.requires_reht_clearance is True
        )
        return (intact, problems)


_SCHEMA_VERSION = "evaluation-report-v1"


def _digest_payload(payload: Dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _slot_reports(
    instrument_results: Dict[str, InstrumentResult],
) -> List[InstrumentSlotReport]:
    reports: List[InstrumentSlotReport] = []
    for slot in sorted(instrument_results):
        result = instrument_results[slot]
        risk = result.risk_for_aggregation
        reports.append(
            InstrumentSlotReport(
                slot=slot,
                status=result.status.value,
                risk=risk,
                implementation=result.implementation,
                version=result.version,
                calibration_profile=result.calibration_profile,
                calibration_metrics=result.calibration_metrics,
                failure_reason=result.failure_reason,
                self_judging=result.self_judging,
            )
        )
    return reports


def build_evaluation_report(
    result: OrchestratorResult,
    *,
    report_id: Optional[str] = None,
    now: Optional[datetime] = None,
) -> EvaluationReport:
    """Construct a replayable EvaluationReport from an OrchestratorResult.

    Never grants authority; records what was measured and what was refused.
    """

    current_time = now or datetime.now(timezone.utc)
    validation = result.validation
    aggregation = validation.aggregation

    slots = _slot_reports(validation.instrument_results)

    required_unmeasured = tuple(sorted(validation.required_unmeasured))
    instrument_errors = tuple(
        sorted((slot, err) for slot, err in validation.instrument_errors.items())
    )

    rejection_reasons: List[str] = []
    if result.should_halt:
        rejection_reasons.append("evaluation halted")
    if result.evidence_intake is not None and result.evidence_intake.blocks_consequential_action:
        rejection_reasons.append(
            "evidence intake blocked: "
            + (
                "; ".join(result.evidence_intake.blocking_reasons)
                or result.evidence_intake.state.value
            )
        )
    if aggregation is not None and aggregation.abstained:
        rejection_reasons.append(
            "aggregation abstained: " + (aggregation.abstention_reason or "unknown")
        )
    if required_unmeasured:
        rejection_reasons.append(
            "required slots unmeasured: " + ", ".join(required_unmeasured)
        )
    if instrument_errors:
        rejection_reasons.append(
            "instrument errors: " + ", ".join(slot for slot, _ in instrument_errors)
        )
    # P0.6 (partial): an instrument that requires calibration but has no bound
    # profile yields an uncalibrated measurement. That must not pass clearance
    # silently — REHT must see it and refuse. Fail-closed.
    uncalibrated_slots = tuple(
        slot
        for slot, res in validation.instrument_results.items()
        if res.status == InstrumentStatus.UNCALIBRATED
    )
    if uncalibrated_slots:
        rejection_reasons.append(
            "uncalibrated instruments: " + ", ".join(sorted(uncalibrated_slots))
        )

    evidence_state = (
        result.evidence_intake.state.value
        if result.evidence_intake is not None
        else "NOT_EVALUATED"
    )

    underdetermination = (
        dict(result.underdetermination.to_dict())
        if result.underdetermination is not None
        else None
    )
    tradecraft = (
        dict(result.tradecraft.to_dict())
        if result.tradecraft is not None
        else None
    )

    report = EvaluationReport(
        report_id=report_id or validation.entry_id,
        generated_at=current_time,
        schema_version=_SCHEMA_VERSION,
        evaluation_id=validation.entry_id,
        distrust_level=validation.level.value,
        combined_score=validation.combined_score,
        should_halt=result.should_halt,
        requires_human_review=result.requires_human_review,
        evidence_state=evidence_state,
        evidence_blocked=bool(
            result.evidence_intake
            and result.evidence_intake.blocks_consequential_action
        ),
        execution_authority=False,
        requires_reht_clearance=True,
        slots=tuple(slots),
        required_unmeasured=required_unmeasured,
        instrument_errors=instrument_errors,
        aggregation_mode=aggregation.mode.value if aggregation is not None else None,
        aggregation_abstained=bool(aggregation and aggregation.abstained),
        aggregation_abstention_reason=(
            aggregation.abstention_reason if aggregation is not None else None
        ),
        veto_reasons=tuple(sorted(validation.veto_reasons)),
        rejection_reasons=tuple(sorted(set(rejection_reasons))),
        worm_hash=validation.worm_hash,
        report_digest="",
        underdetermination=underdetermination,
        tradecraft=tradecraft,
    )

    digest = _digest_payload(report.canonical_payload())
    return EvaluationReport(
        report_id=report.report_id,
        generated_at=report.generated_at,
        schema_version=report.schema_version,
        evaluation_id=report.evaluation_id,
        distrust_level=report.distrust_level,
        combined_score=report.combined_score,
        should_halt=report.should_halt,
        requires_human_review=report.requires_human_review,
        evidence_state=report.evidence_state,
        evidence_blocked=report.evidence_blocked,
        execution_authority=report.execution_authority,
        requires_reht_clearance=report.requires_reht_clearance,
        slots=report.slots,
        required_unmeasured=report.required_unmeasured,
        instrument_errors=report.instrument_errors,
        aggregation_mode=report.aggregation_mode,
        aggregation_abstained=report.aggregation_abstained,
        aggregation_abstention_reason=report.aggregation_abstention_reason,
        veto_reasons=report.veto_reasons,
        rejection_reasons=report.rejection_reasons,
        worm_hash=report.worm_hash,
        report_digest=digest,
        underdetermination=report.underdetermination,
        tradecraft=report.tradecraft,
    )


def _to_evaluation_report(self: OrchestratorResult, **kwargs: Any) -> EvaluationReport:
    """OrchestratorResult.to_evaluation_report() — REHT-handoff helper."""

    return build_evaluation_report(self, **kwargs)


OrchestratorResult.to_evaluation_report = _to_evaluation_report  # type: ignore[attr-defined]
