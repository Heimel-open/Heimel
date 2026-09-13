"""Typed outcomes for VAIG evaluation instruments.

A missing or failed measurement is not evidence of safety. InstrumentResult keeps
measurement state separate from numeric risk so callers cannot silently coerce
unknown states to 0.0.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

if TYPE_CHECKING:
    from vaig.calibration import CalibrationProfile


class InstrumentStatus(str, Enum):
    """Lifecycle state of one requested instrument measurement."""

    MEASURED = "MEASURED"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    ERROR = "ERROR"
    UNCALIBRATED = "UNCALIBRATED"


@dataclass(frozen=True)
class InstrumentResult:
    """Replayable result for one instrument slot.

    ``raw_score`` and ``calibrated_risk`` are optional by design. They must not
    be fabricated for unavailable, failed or inapplicable measurements.
    """

    slot: str
    status: InstrumentStatus
    raw_score: Optional[float] = None
    calibrated_risk: Optional[float] = None
    implementation: str = ""
    version: str = "unversioned"
    required_inputs: Tuple[str, ...] = ()
    supplied_inputs: Tuple[str, ...] = ()
    evidence_refs: Tuple[str, ...] = ()
    calibration_profile: Optional[str] = None
    calibration_metrics: Optional[CalibrationProfile] = None
    latency_ms: float = 0.0
    failure_reason: Optional[str] = None
    self_judging: bool = False
    # Per-measurement confidence in [0, 1]. ``None`` means the measurement did
    # not declare a confidence; self-judged measurements without a declared
    # confidence are abstained by the BlindspotGuard instead of driving the
    # verdict as if they were a measured certainty.
    confidence: Optional[float] = None

    def __post_init__(self) -> None:
        for field_name in ("raw_score", "calibrated_risk"):
            value = getattr(self, field_name)
            if value is not None and not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"{field_name} must be in [0, 1]")

        if self.status is InstrumentStatus.MEASURED and self.raw_score is None:
            raise ValueError("MEASURED instrument result requires raw_score")

        if self.status in {
            InstrumentStatus.UNAVAILABLE,
            InstrumentStatus.NOT_APPLICABLE,
            InstrumentStatus.ERROR,
        } and self.raw_score is not None:
            raise ValueError(f"{self.status.value} result cannot carry raw_score")

    @property
    def risk_for_aggregation(self) -> Optional[float]:
        """Return a usable risk value only for an actual measurement."""

        if self.status is not InstrumentStatus.MEASURED:
            return None
        if self.calibrated_risk is not None:
            return float(self.calibrated_risk)
        return float(self.raw_score) if self.raw_score is not None else None

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload
