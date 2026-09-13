from dataclasses import dataclass

from .levels import DistrustLevel, GateStatus


@dataclass
class ValidationResult:
    entry_id: str
    level: DistrustLevel
    combined_score: float
    scores: dict[str, float]
    worm_hash: str
    latency_ms: float

    @property
    def should_halt(self) -> bool:
        return self.level == DistrustLevel.HALT


@dataclass
class GateDecision:
    status: GateStatus
    combined_status: GateStatus
    coherence: float
    tav_regime: str | None
    metrics_logged: bool = True

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "combined_status": self.combined_status,
            "coherence": self.coherence,
            "tav_regime": self.tav_regime,
            "metrics_logged": self.metrics_logged,
        }
