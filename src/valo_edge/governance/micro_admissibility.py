"""Embedded micro-admissibility — fail-closed signal fusion, stdlib-only.

On-device equivalent of ``reht_admissibility_engine``. Fuses observer signals
into ONE governed verdict with the same priority semantics:

    DENY > DEFER > ADMIT_WITH_CONDITIONS > ADMIT

Fails closed on any exception or absent evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple


class AdmissibilityVerdict(str, Enum):
    ADMIT = "ADMIT"
    ADMIT_WITH_CONDITIONS = "ADMIT_WITH_CONDITIONS"
    DEFER = "DEFER"
    DENY = "DENY"


class SignalDisposition(str, Enum):
    BLOCK = "block"
    ESCALATE = "escalate"
    CAUTION = "caution"
    OK = "ok"


@dataclass(frozen=True)
class MicroSignal:
    """One observed signal feeding the fusion."""
    source: str
    disposition: SignalDisposition
    confidence: float = 1.0
    severity: str = "low"
    detail: str = ""


@dataclass
class MicroAdmissibilityDecision:
    verdict: AdmissibilityVerdict
    governance_confidence: float
    reasons: List[str] = field(default_factory=list)
    conditions: List[str] = field(default_factory=list)
    blocking_sources: List[str] = field(default_factory=list)


_BLOCK_SEVERITIES = {"critical"}


class MicroAdmissibilityEngine:
    """Fail-closed local admissibility fusion."""

    def decide(
        self,
        *,
        signals: List[MicroSignal],
        risk_tier: str = "L1",
        has_human_delegate: bool = True,
    ) -> MicroAdmissibilityDecision:
        try:
            return self._decide(signals=signals, risk_tier=risk_tier,
                                has_human_delegate=has_human_delegate)
        except Exception:  # pragma: no cover - defensive fail-closed
            return MicroAdmissibilityDecision(
                verdict=AdmissibilityVerdict.DENY,
                governance_confidence=0.0,
                reasons=["fusion_error"],
                blocking_sources=["engine"],
            )

    def _decide(
        self,
        *,
        signals: List[MicroSignal],
        risk_tier: str,
        has_human_delegate: bool,
    ) -> MicroAdmissibilityDecision:
        reasons: List[str] = []
        conditions: List[str] = []
        blocking: List[str] = []

        if not has_human_delegate and risk_tier in ("L2", "L3", "high", "irreversible"):
            blocking.append("authority")
            reasons.append("no human delegate accountable for high-risk action")

        confidences: List[float] = []
        for s in signals:
            confidences.append(max(0.0, min(1.0, s.confidence)))
            if s.disposition == SignalDisposition.BLOCK or s.severity in _BLOCK_SEVERITIES:
                blocking.append(s.source)
                reasons.append(f"blocking signal from {s.source}: {s.detail}")
            elif s.disposition == SignalDisposition.ESCALATE:
                reasons.append(f"escalate from {s.source}: {s.detail}")
            elif s.disposition == SignalDisposition.CAUTION:
                conditions.append(f"monitor {s.source}: {s.detail}")

        if blocking:
            verdict = AdmissibilityVerdict.DENY
        elif any(s.disposition == SignalDisposition.ESCALATE for s in signals):
            verdict = AdmissibilityVerdict.DEFER
        elif conditions:
            verdict = AdmissibilityVerdict.ADMIT_WITH_CONDITIONS
        else:
            verdict = AdmissibilityVerdict.ADMIT

        if not confidences:
            return MicroAdmissibilityDecision(
                verdict=AdmissibilityVerdict.DENY,
                governance_confidence=0.0,
                reasons=["no observer evidence supplied"],
                blocking_sources=["evidence"],
            )

        gov_conf = min(confidences)
        if verdict == AdmissibilityVerdict.DENY:
            gov_conf = 0.0
        elif conditions:
            gov_conf = round(gov_conf * 0.85, 4)

        return MicroAdmissibilityDecision(
            verdict=verdict,
            governance_confidence=gov_conf,
            reasons=reasons,
            conditions=conditions,
            blocking_sources=blocking,
        )
