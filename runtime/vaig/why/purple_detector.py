"""
Purple Detector — Governance/system trust event detection.

Purple is a meta-status that overlays any normal UI state.
It activates on governance events (certificate expiry, attestation failure,
2-person auth, policy changes) — never on normal action-risk levels.

This is a skeleton. Out-of-band monitoring hooks are deferred to PR #9.
"""

from dataclasses import dataclass, field
from typing import List


# Events that trigger PURPLE status
PURPLE_EVENT_TYPES = [
    "certificate_expiry",
    "attestation_failure",
    "two_person_auth_triggered",
    "policy_change_in_flight",
    "operator_override_active",
    "recovery_mode",
]


@dataclass
class PurpleEvent:
    """A single governance/system trust event."""
    event_type: str
    description: str
    timestamp: float = field(default_factory=lambda: __import__("time").time())

    def is_valid_type(self) -> bool:
        return self.event_type in PURPLE_EVENT_TYPES


class PurpleDetector:
    """
    Detect governance/system trust events that activate PURPLE overlay.

    Out-of-band from the normal inference path. Monitors system health,
    not inference quality.
    """

    def __init__(self):
        self._active_events: List[PurpleEvent] = []

    def check(self) -> bool:
        """
        Return True if any PURPLE-class event is currently active.

        In the skeleton, this reads from the manual event list.
        In production (PR #9), this will query system health hooks.
        """
        return len(self._active_events) > 0

    @property
    def active_events(self) -> List[str]:
        """List descriptions of currently active purple events."""
        return [e.description for e in self._active_events]

    @property
    def active_event_types(self) -> List[str]:
        """List event types of currently active purple events."""
        return [e.event_type for e in self._active_events]

    def add_event(self, event_type: str, description: str) -> None:
        """
        Manually add a purple event. For testing and skeleton use.

        Args:
            event_type: Must be in PURPLE_EVENT_TYPES
            description: Human-readable description

        Raises:
            ValueError: If event_type is not a valid purple event type
        """
        if event_type not in PURPLE_EVENT_TYPES:
            raise ValueError(
                f"Invalid purple event type: {event_type}. "
                f"Valid types: {PURPLE_EVENT_TYPES}"
            )
        self._active_events.append(PurpleEvent(event_type, description))

    def clear_event(self, event_type: str) -> bool:
        """Remove all events of a given type. Returns True if any were removed."""
        original = len(self._active_events)
        self._active_events = [e for e in self._active_events if e.event_type != event_type]
        return len(self._active_events) < original

    def clear_all(self) -> None:
        """Remove all active events."""
        self._active_events.clear()

    def is_purple_event_type(self, event_type: str) -> bool:
        """Check if an event type is a valid purple-class event."""
        return event_type in PURPLE_EVENT_TYPES
