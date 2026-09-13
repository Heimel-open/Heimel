"""
VACS capability extension tracking.

Recovered from VAIG Fidelity to prevent silent authority expansion during a
session. This module does not grant authority by itself; it records and caps
extension requests so the policy layer can deny, defer, or step up.
"""

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Set


DEFAULT_EXTENSION_CAP = 5


@dataclass(frozen=True)
class CapabilityExtensionEvent:
    event: str
    session_id: str
    extension_index: int
    capability: str
    scope_broadening: bool
    cap_limit: int
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event": self.event,
            "session_id": self.session_id,
            "extension_index": self.extension_index,
            "capability": self.capability,
            "scope_broadening": self.scope_broadening,
            "cap_limit": self.cap_limit,
            "timestamp": self.timestamp,
        }


class CapabilityExtensionCapExceeded(Exception):
    pass


class CapabilityExtensionTracker:
    """Tracks bounded capability extensions for one authority session."""

    def __init__(
        self,
        session_id: str,
        initial_capabilities: List[str],
        cap: int = DEFAULT_EXTENSION_CAP,
    ):
        if not session_id:
            raise ValueError("session_id is required")
        if cap < 0:
            raise ValueError("cap must be non-negative")

        self.session_id = session_id
        self.cap = cap
        self._initial: Set[str] = set(initial_capabilities)
        self._current: Set[str] = set(initial_capabilities)
        self._events: List[CapabilityExtensionEvent] = []

    def request_extension(self, capability: str) -> CapabilityExtensionEvent:
        if not capability:
            raise ValueError("capability is required")
        if len(self._events) >= self.cap:
            raise CapabilityExtensionCapExceeded(
                f"Session '{self.session_id}' reached capability extension cap ({self.cap})"
            )

        scope_broadening = not self._is_narrowing(capability)
        self._current.add(capability)

        event = CapabilityExtensionEvent(
            event="capability_extension",
            session_id=self.session_id,
            extension_index=len(self._events) + 1,
            capability=capability,
            scope_broadening=scope_broadening,
            cap_limit=self.cap,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        self._events.append(event)
        return event

    def has_capability(self, capability: str) -> bool:
        return capability in self._current

    def extension_count(self) -> int:
        return len(self._events)

    def remaining(self) -> int:
        return max(0, self.cap - len(self._events))

    def events(self) -> List[CapabilityExtensionEvent]:
        return list(self._events)

    def summary(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "cap": self.cap,
            "extensions_used": self.extension_count(),
            "remaining": self.remaining(),
            "scope_broadening_count": sum(1 for event in self._events if event.scope_broadening),
            "current_capabilities": sorted(self._current),
        }

    def _is_narrowing(self, capability: str) -> bool:
        if capability in self._current:
            return True

        candidate = capability.lower().replace(" ", "_")
        for existing in self._current:
            current = existing.lower().replace(" ", "_")
            if candidate.startswith(current + ":") or candidate.startswith(current + "/"):
                return True
            current_words = set(current.split("_"))
            candidate_words = set(candidate.split("_"))
            if current_words and current_words.issubset(candidate_words) and candidate_words != current_words:
                return True
        return False