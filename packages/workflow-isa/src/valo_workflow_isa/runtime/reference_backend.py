from __future__ import annotations

from typing import Any

from ..ports.runtime_backend import RuntimeBackend


class ReferenceBackend(RuntimeBackend):
    """In-memory durable backend. Makes execution deterministic and resumable
    within a process; a Temporal backend can satisfy the same contract later."""

    def __init__(self) -> None:
        self._instances: dict[str, dict[str, Any]] = {}
        self._events: dict[str, list[dict[str, Any]]] = {}

    def save_instance(self, instance: dict[str, Any]) -> None:
        self._instances[instance["instance_id"]] = instance

    def load_instance(self, instance_id: str) -> dict[str, Any] | None:
        return self._instances.get(instance_id)

    def append_event(self, event: dict[str, Any]) -> None:
        self._events.setdefault(event["workflow_instance_id"], []).append(event)

    def events_for(self, instance_id: str) -> list[dict[str, Any]]:
        return list(self._events.get(instance_id, []))
