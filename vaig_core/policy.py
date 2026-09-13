import os
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class PolicyConfig:
    halt_threshold: float = 0.75
    degrade_threshold: float = 0.55
    warn_threshold: float = 0.35
    monitor_threshold: float = 0.15
    coherence_threshold: Optional[float] = None
    tav_crystalline: float = 0.0001
    tav_fluid: float = 0.15
    tav_gaseous: float = 0.35

    @property
    def distrust_thresholds(self) -> Dict[str, float]:
        return {
            "HALT": self.halt_threshold,
            "DEGRADE": self.degrade_threshold,
            "WARN": self.warn_threshold,
            "MONITOR": self.monitor_threshold,
        }


def load_policy() -> PolicyConfig:
    c0_raw = os.environ.get("VALO_COHERENCE_THRESHOLD")
    return PolicyConfig(coherence_threshold=float(c0_raw) if c0_raw else None)


default_policy = PolicyConfig()
