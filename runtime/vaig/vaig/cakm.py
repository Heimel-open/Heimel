"""CAKM — L7, Cross-Agent Knowledge Monitor. Session-level distrust pattern detection."""

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class AlertLevel(Enum):
    GREEN  = "GREEN"   # Normal
    YELLOW = "YELLOW"  # ≥2 L3 (DEGRADE) in session
    ORANGE = "ORANGE"  # ≥1 L4 (HALT) or ≥3 L3
    RED    = "RED"     # L4 persists after recovery, or ORANGE sustained


@dataclass
class _SessionState:
    l3_count: int = 0
    l4_count: int = 0
    first_l4_ts: Optional[float] = None
    orange_since: Optional[float] = None
    alert: AlertLevel = AlertLevel.GREEN
    events: List[dict] = field(default_factory=list)


class CAKM:
    """
    L7 — Cross-Agent Knowledge Monitor.

    Tracks distrust levels across a session and escalates alert level
    when patterns of elevated risk emerge.

    Usage:
        cakm = CAKM()
        alert = cakm.observe("session-abc", orchestrator_result)
        if alert in (AlertLevel.ORANGE, AlertLevel.RED):
            council.submit(orchestrator_result, prompt, response)
    """

    def __init__(self, orange_sustained_secs: float = 300.0):
        self._sessions: Dict[str, _SessionState] = {}
        self._lock = threading.Lock()
        self._orange_sustained = orange_sustained_secs

    def observe(self, session_id: str, result) -> AlertLevel:
        """
        Record a result for a session and return updated alert level.
        result: OrchestratorResult or any object with .level (DistrustLevel)
        """
        from vaig.ensemble import DistrustLevel

        with self._lock:
            state = self._sessions.setdefault(session_id, _SessionState())
            level = getattr(result, "level", None)
            if level is None and hasattr(result, "validation"):
                level = result.validation.level

            state.events.append({"ts": time.time(), "level": level.value if level else "?"})

            if level == DistrustLevel.HALT:
                state.l4_count += 1
                if state.first_l4_ts is None:
                    state.first_l4_ts = time.time()
            elif level == DistrustLevel.DEGRADE:
                state.l3_count += 1

            state.alert = self._compute(state)
            return state.alert

    def _compute(self, state: _SessionState) -> AlertLevel:
        now = time.time()
        if state.l4_count >= 2:
            return AlertLevel.RED
        if state.orange_since and (now - state.orange_since) >= self._orange_sustained:
            return AlertLevel.RED
        if state.l4_count >= 1 or state.l3_count >= 3:
            if state.orange_since is None:
                state.orange_since = now
            return AlertLevel.ORANGE
        if state.l3_count >= 2:
            return AlertLevel.YELLOW
        return AlertLevel.GREEN

    def status(self, session_id: str) -> AlertLevel:
        with self._lock:
            state = self._sessions.get(session_id)
        return state.alert if state else AlertLevel.GREEN

    def reset(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    def sessions_at_risk(self) -> List[str]:
        """Return session IDs at ORANGE or RED."""
        with self._lock:
            return [
                sid for sid, s in self._sessions.items()
                if s.alert in (AlertLevel.ORANGE, AlertLevel.RED)
            ]

    def summary(self) -> Dict[str, int]:
        """Count of sessions per alert level."""
        with self._lock:
            counts: Dict[str, int] = {lvl.value: 0 for lvl in AlertLevel}
            for s in self._sessions.values():
                counts[s.alert.value] += 1
            return counts
