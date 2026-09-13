import os
from dataclasses import dataclass


@dataclass
class PolicyConfig:
    halt_threshold: float = 0.75
    degrade_threshold: float = 0.55
    warn_threshold: float = 0.35
    monitor_threshold: float = 0.15
    coherence_threshold: float | None = None
    tav_crystalline: float = 0.0001
    tav_fluid: float = 0.15
    tav_gaseous: float = 0.35

    @property
    def distrust_thresholds(self) -> dict[str, float]:
        return {
            "HALT": self.halt_threshold,
            "DEGRADE": self.degrade_threshold,
            "WARN": self.warn_threshold,
            "MONITOR": self.monitor_threshold,
        }


def load_policy() -> PolicyConfig:
    raw = os.environ.get("VALO_COHERENCE_THRESHOLD")
    return PolicyConfig(coherence_threshold=float(raw) if raw else None)


default_policy = PolicyConfig()
