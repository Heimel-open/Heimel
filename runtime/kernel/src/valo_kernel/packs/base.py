from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ..contracts.common import EntityType, RelationType
from ..contracts.events import CanonicalEvent, EventType
from ..world.state import WorldState

_NAMESPACE_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")
Reducer = Callable[[WorldState, CanonicalEvent], WorldState]


@dataclass(frozen=True)
class WorldPack:
    """A bounded domain extension.

    Packs may declare only namespaced types. The Kernel validates registration
    before applying an event and preserves every core invariant around the pack
    reducer. A pack cannot replace a core type or reducer.
    """

    name: str
    namespace: str
    entity_types: frozenset[str] = field(default_factory=frozenset)
    relationship_types: frozenset[str] = field(default_factory=frozenset)
    constraints: tuple[Any, ...] = field(default_factory=tuple)
    event_types: frozenset[str] = field(default_factory=frozenset)
    reducers: dict[str, Reducer] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("pack name is required")
        if not _NAMESPACE_PATTERN.fullmatch(self.namespace):
            raise ValueError("pack namespace must be lowercase and stable")

        prefix = f"{self.namespace}:"
        declarations = {
            "entity_type": self.entity_types,
            "relationship_type": self.relationship_types,
            "event_type": self.event_types,
        }
        for label, values in declarations.items():
            for value in values:
                if not value.startswith(prefix):
                    raise ValueError(
                        f"{label} {value!r} must use namespace {prefix!r}"
                    )

        core_entity_types = {item.value for item in EntityType}
        core_relationship_types = {item.value for item in RelationType}
        core_event_types = {item.value for item in EventType}
        if core_entity_types & set(self.entity_types):
            raise ValueError("pack cannot redefine a core entity type")
        if core_relationship_types & set(self.relationship_types):
            raise ValueError("pack cannot redefine a core relationship type")
        if core_event_types & set(self.event_types):
            raise ValueError("pack cannot redefine a core event type")

        reducer_types = set(self.reducers)
        if reducer_types != set(self.event_types):
            raise ValueError(
                "every pack event type requires exactly one deterministic reducer"
            )

    def register(self, engine_reducers: dict[EventType | str, Reducer]) -> None:
        for event_name, reducer in self.reducers.items():
            if event_name in engine_reducers:
                raise ValueError(f"event reducer collision: {event_name}")
            engine_reducers[event_name] = reducer
