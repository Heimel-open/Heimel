"""Blindspot guard for model-backed measurements (VAIG).

Adopts the BARO guard pattern: model measurements must declare confidence and
must agree before they are allowed to drive a verdict as if they were measured
certainty. Guarded results are downgraded to ``UNCALIBRATED`` so the ensemble's
existing fail-closed aggregation excludes them — never a silent 0.0.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from typing import Dict, List, Tuple

from vaig.instruments.result import InstrumentResult, InstrumentStatus

DEFAULT_ABSTAIN_CONFIDENCE = 0.3
DEFAULT_DISAGREEMENT_THRESHOLD = 0.35


@dataclass
class GuardReport:
    """Outcome of one blindspot guard pass over instrument results."""

    abstained_slots: Dict[str, str] = field(default_factory=dict)
    low_agreement: bool = False
    agreement_detail: str = ""
    signal_trust: str = "FULL"

    @property
    def abstained(self) -> bool:
        return bool(self.abstained_slots)


class BlindspotGuard:
    """Fail-closed guard over model-backed instrument measurements."""

    def __init__(
        self,
        abstain_confidence: float = DEFAULT_ABSTAIN_CONFIDENCE,
        disagreement_threshold: float = DEFAULT_DISAGREEMENT_THRESHOLD,
    ) -> None:
        if not 0.0 <= abstain_confidence <= 1.0:
            raise ValueError("abstain_confidence must be in [0, 1]")
        if not 0.0 <= disagreement_threshold <= 1.0:
            raise ValueError("disagreement_threshold must be in [0, 1]")
        self.abstain_confidence = abstain_confidence
        self.disagreement_threshold = disagreement_threshold

    def guard_results(
        self,
        results: Dict[str, InstrumentResult],
    ) -> Tuple[Dict[str, InstrumentResult], GuardReport]:
        """Return a guarded copy of ``results`` plus the guard report.

        Measured self-judged results without a declared confidence, and any
        measured result whose declared confidence is below the abstain
        threshold, are downgraded to ``UNCALIBRATED`` (fail-closed).
        """
        guarded: Dict[str, InstrumentResult] = {}
        report = GuardReport()

        measured = []
        for slot, res in results.items():
            if res.status is not InstrumentStatus.MEASURED:
                guarded[slot] = res
                continue

            reason = self._abstain_reason(res)
            if reason is not None:
                report.abstained_slots[slot] = reason
                guarded[slot] = InstrumentResult(
                    slot=slot,
                    status=InstrumentStatus.UNCALIBRATED,
                    implementation=res.implementation,
                    version=res.version,
                    required_inputs=res.required_inputs,
                    supplied_inputs=res.supplied_inputs,
                    evidence_refs=res.evidence_refs,
                    failure_reason=reason,
                    self_judging=res.self_judging,
                )
                continue

            guarded[slot] = res
            measured.append((slot, res))

        report.low_agreement, report.agreement_detail = self._check_agreement(
            measured
        )
        if report.low_agreement:
            report.signal_trust = "REDUCED"
        elif report.abstained:
            report.signal_trust = "PARTIAL"

        return guarded, report

    def _abstain_reason(self, res: InstrumentResult) -> str | None:
        if res.self_judging:
            # Mandatory independent judge: a measurement produced by the same
            # model that made the output can never drive the verdict, even with
            # a declared confidence. Only a genuinely separate judge_fn counts.
            return "self_judged_without_independent_judge"
        if res.confidence is not None and res.confidence < self.abstain_confidence:
            return "below_confidence_threshold"
        return None

    def _check_agreement(
        self,
        measured: List[Tuple[str, InstrumentResult]],
    ) -> Tuple[bool, str]:
        """Flag low agreement between measured slots that both declare confidence."""
        declared: List[Tuple[str, float]] = []
        for slot, res in measured:
            if res.confidence is None:
                continue
            risk = res.calibrated_risk
            if risk is None:
                risk = res.raw_score
            if risk is not None:
                declared.append((slot, risk))
        if len(declared) < 2:
            return False, ""
        worst_pair = max(
            combinations(declared, 2),
            key=lambda pair: abs(pair[0][1] - pair[1][1]),
        )
        worst = abs(worst_pair[0][1] - worst_pair[1][1])
        if worst < self.disagreement_threshold:
            return False, ""
        return True, (
            f"max disagreement {worst:.2f} between "
            f"{worst_pair[0][0]}={worst_pair[0][1]:.2f} and "
            f"{worst_pair[1][0]}={worst_pair[1][1]:.2f}"
        )
