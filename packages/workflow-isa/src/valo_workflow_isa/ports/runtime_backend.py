from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class RuntimeBackend(ABC):
    """Durable runtime contract. A Temporal backend can satisfy the same
    contract later; the first implementation is an in-memory reference backend
    that makes the runtime deterministic and resumable."""

    @abstractmethod
    def save_instance(self, instance: dict[str, Any]) -> None: ...

    @abstractmethod
    def load_instance(self, instance_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def append_event(self, event: dict[str, Any]) -> None: ...

    @abstractmethod
    def events_for(self, instance_id: str) -> list[dict[str, Any]]: ...
