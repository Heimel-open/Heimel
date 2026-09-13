"""
VACS recovery manager.

Recovered from VAIG Fidelity as rollback and escalation policy. Recovery maps to
existing ACS/VACS primitives and does not introduce new decision primitives.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

try:
    from .checkpoint import CheckpointManager
except ImportError:
    from checkpoint import CheckpointManager


class RecoveryLevel(Enum):
    ARGUMENT = "ARGUMENT"
    API = "API"
    SEGMENT = "SEGMENT"
    FULL = "FULL"
    ESCALATE = "ESCALATE"


RECOVERY_DECISION_MAP = {
    RecoveryLevel.ARGUMENT: "MODIFY",
    RecoveryLevel.API: "DEFER",
    RecoveryLevel.SEGMENT: "STEP_UP",
    RecoveryLevel.FULL: "STEP_UP",
    RecoveryLevel.ESCALATE: "HALT",
}


@dataclass(frozen=True)
class RecoveryAction:
    level: RecoveryLevel
    decision: str
    reason: str
    checkpoint_id: Optional[str] = None
    retry_count: int = 0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, object]:
        return {
            "level": self.level.value,
            "decision": self.decision,
            "reason": self.reason,
            "checkpoint_id": self.checkpoint_id,
            "retry_count": self.retry_count,
            "timestamp": self.timestamp,
        }


class RecoveryManager:
    CONSECUTIVE_LIMIT = 3

    def __init__(self, checkpoint_manager: CheckpointManager, max_retries: Optional[Dict[RecoveryLevel, int]] = None):
        self.checkpoint_manager = checkpoint_manager
        self.max_retries = max_retries or {
            RecoveryLevel.ARGUMENT: 3,
            RecoveryLevel.API: 2,
            RecoveryLevel.SEGMENT: 1,
            RecoveryLevel.FULL: 0,
            RecoveryLevel.ESCALATE: 0,
        }
        self.retry_counts: Dict[RecoveryLevel, int] = {level: 0 for level in RecoveryLevel}
        self.action_log: List[RecoveryAction] = []
        self.consecutive_failures = 0

    def recover(self, failure_kind: str, reason: str = "gate denied proposed transition") -> Tuple[RecoveryLevel, str, Optional[str]]:
        level = self._classify_failure(failure_kind)
        level = self._apply_retry_limits(level)

        if level == RecoveryLevel.ESCALATE:
            action = self._record(level, reason, None)
            self.consecutive_failures = 0
            return action.level, action.decision, action.checkpoint_id

        self.retry_counts[level] += 1
        self.consecutive_failures += 1

        checkpoint_id = self._rollback_target(level)
        action = self._record(level, reason, checkpoint_id)

        if self.consecutive_failures >= self.CONSECUTIVE_LIMIT:
            esc = self._record(RecoveryLevel.ESCALATE, "consecutive failure limit reached", checkpoint_id)
            self.consecutive_failures = 0
            return esc.level, esc.decision, esc.checkpoint_id

        return action.level, action.decision, action.checkpoint_id

    def reset_retry_counts(self) -> None:
        self.retry_counts = {level: 0 for level in RecoveryLevel}
        self.consecutive_failures = 0

    def get_recovery_stats(self) -> Dict[str, object]:
        return {
            "total_actions": len(self.action_log),
            "consecutive_failures": self.consecutive_failures,
            "escalations": sum(1 for action in self.action_log if action.level == RecoveryLevel.ESCALATE),
            "retry_counts": {level.value: count for level, count in self.retry_counts.items()},
        }

    def _classify_failure(self, failure_kind: str) -> RecoveryLevel:
        normalized = (failure_kind or "").lower()
        if normalized in {"argument", "argument_error", "field", "single_change"}:
            return RecoveryLevel.ARGUMENT
        if normalized in {"api", "api_error", "tool", "schema"}:
            return RecoveryLevel.API
        if normalized in {"segment", "multi_step", "partial"}:
            return RecoveryLevel.SEGMENT
        if normalized in {"full", "restart"}:
            return RecoveryLevel.FULL
        return RecoveryLevel.ESCALATE

    def _apply_retry_limits(self, level: RecoveryLevel) -> RecoveryLevel:
        chain = [
            RecoveryLevel.ARGUMENT,
            RecoveryLevel.API,
            RecoveryLevel.SEGMENT,
            RecoveryLevel.FULL,
            RecoveryLevel.ESCALATE,
        ]
        index = chain.index(level)
        while index < len(chain):
            candidate = chain[index]
            if self.retry_counts[candidate] < self.max_retries.get(candidate, 0):
                return candidate
            index += 1
        return RecoveryLevel.ESCALATE

    def _rollback_target(self, level: RecoveryLevel) -> Optional[str]:
        checkpoints = self.checkpoint_manager.store.list_checkpoints(self.checkpoint_manager.container_id)
        if not checkpoints:
            return None
        checkpoint_id = checkpoints[0] if level == RecoveryLevel.FULL else checkpoints[-1]
        self.checkpoint_manager.rollback(checkpoint_id)
        return checkpoint_id

    def _record(self, level: RecoveryLevel, reason: str, checkpoint_id: Optional[str]) -> RecoveryAction:
        action = RecoveryAction(
            level=level,
            decision=RECOVERY_DECISION_MAP[level],
            reason=reason,
            checkpoint_id=checkpoint_id,
            retry_count=self.retry_counts[level],
        )
        self.action_log.append(action)
        return action