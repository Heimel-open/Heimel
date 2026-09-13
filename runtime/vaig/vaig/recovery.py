"""RecoveryManager — L5.5, structured escalation after L4 HALT."""

from enum import Enum
from typing import List


class RecoveryAction(Enum):
    RETRY      = "RETRY"
    FALLBACK   = "FALLBACK"
    SANDBOX    = "SANDBOX"
    ISOLATE    = "ISOLATE"
    HUMAN_STOP = "HUMAN_STOP"


_ESCALATION_PATH = [
    RecoveryAction.RETRY,
    RecoveryAction.FALLBACK,
    RecoveryAction.SANDBOX,
    RecoveryAction.ISOLATE,
    RecoveryAction.HUMAN_STOP,
]


class RecoveryManager:
    """
    L5.5 — Structured escalation after L4 HALT.

    Wraps VAIGOrchestrator output and decides next action.

    Usage:
        rm = RecoveryManager()
        action = rm.handle(orchestrator_result, attempt=0)
        if action == RecoveryAction.RETRY:
            # retry the request
            ...
    """

    def handle(self, result, attempt: int = 0, cakm_l4_count: int = 0) -> RecoveryAction:
        """
        Decide next recovery action.

        result: OrchestratorResult or any object with .level (DistrustLevel)
        attempt: how many recovery attempts have been made (0 = first failure)
        cakm_l4_count: number of L4 events in current session (from CAKM)
        """
        from vaig.ensemble import DistrustLevel

        if getattr(result, "level", None) != DistrustLevel.HALT:
            return RecoveryAction.RETRY

        if cakm_l4_count >= 3:
            return RecoveryAction.ISOLATE

        idx = min(attempt, len(_ESCALATION_PATH) - 1)
        return _ESCALATION_PATH[idx]

    def escalation_path(self, result) -> List[RecoveryAction]:
        """Return the full escalation path for this result."""
        from vaig.ensemble import DistrustLevel
        if getattr(result, "level", None) != DistrustLevel.HALT:
            return [RecoveryAction.RETRY]
        return list(_ESCALATION_PATH)

    def should_escalate(self, result) -> bool:
        """True if this result warrants escalation beyond simple retry."""
        from vaig.ensemble import DistrustLevel
        return getattr(result, "level", None) == DistrustLevel.HALT
