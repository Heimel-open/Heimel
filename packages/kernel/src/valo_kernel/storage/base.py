from __future__ import annotations

from abc import ABC, abstractmethod

from ..contracts.events import CanonicalEvent
from ..world.state import WorldState


class AppendOnlyStore(ABC):
    """Storage-agnostic append-only interface. The first implementation is
    in-memory; a PostgreSQL store can satisfy the same contract later.

    The store owns idempotency: a duplicate idempotency_key must be rejected
    even by a freshly constructed engine against the same store."""

    @abstractmethod
    def append_event(self, event: CanonicalEvent, state: WorldState) -> None: ...

    @abstractmethod
    def events(self) -> list[CanonicalEvent]: ...

    @abstractmethod
    def last_event(self) -> CanonicalEvent | None: ...

    @abstractmethod
    def state(self) -> WorldState | None: ...

    @abstractmethod
    def has_idempotency_key(self, key: str) -> bool: ...

