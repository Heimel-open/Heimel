from dataclasses import dataclass
from typing import Dict, List


@dataclass
class IntegritySignal:
    signal_id: str
    signal_type: str
    severity: str
    source: str
    metadata: Dict


@dataclass
class IntegrityResult:
    intact: bool
    reason: str
    signals: List[IntegritySignal]


class ContinuousIntegrityMonitor:
    """Detects changes that invalidate continued execution legitimacy."""

    CRITICAL_TYPES = {
        "policy_changed",
        "authority_revoked",
        "context_changed",
        "baro_escalation",
        "pert_deviation",
        "security_compromise",
    }

    def evaluate(self, signals: List[IntegritySignal]) -> IntegrityResult:
        critical = [s for s in signals if s.severity == "critical" or s.signal_type in self.CRITICAL_TYPES]
        if critical:
            return IntegrityResult(False, "continuous_integrity_failed", critical)
        return IntegrityResult(True, "continuous_integrity_intact", signals)
