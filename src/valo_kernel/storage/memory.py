from __future__ import annotations

from ..contracts.events import CanonicalEvent
from ..world.state import WorldState
from .base import AppendOnlyStore


class MemoryStore(AppendOnlyStore):
    """In-memory append-only store for the first kernel implementation.

    Idempotency is owned here, alongside the append-only event history, so a
    duplicate idempotency_key is rejected even by a fresh engine over the same
    store."""

    def __init__(self) -> None:
        self._events: list[CanonicalEvent] = []
        self._state: WorldState | None = None
        self._idempotency: dict[str, CanonicalEvent] = {}

    def append_event(self, event: CanonicalEvent, state: WorldState) -> None:
        if event.idempotency_key is not None:
            if event.idempotency_key in self._idempotency:
                raise ValueError(
                    f"idempotency_key {event.idempotency_key} was already applied"
                )
            self._idempotency[event.idempotency_key] = event
        self._events.append(event)
        self._state = state

    def events(self) -> list[CanonicalEvent]:
        return list(self._events)

    def last_event(self) -> CanonicalEvent | None:
        return self._events[-1] if self._events else None

    def state(self) -> WorldState | None:
        return self._state

    def has_idempotency_key(self, key: str) -> bool:
        return key in self._idempotency
