from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .common import canonical_digest, utcnow
from .function import FunctionDefinition


class RegistryEntry(BaseModel):
    """One versioned Function in the Registry."""

    definition: FunctionDefinition
    function_hash: str

    model_config = ConfigDict(extra="forbid", frozen=True)


class RegistrySnapshot(BaseModel):
    """An immutable, hashed view of the registry at one point in time. Compiled
    execution is bound to a snapshot; later registry changes never affect it."""

    snapshot_id: str
    timestamp: datetime = Field(default_factory=utcnow)
    functions: dict[str, RegistryEntry]  # identity (id@version) -> entry
    graphs: dict[str, Any] = Field(default_factory=dict)  # workflow graph identity -> graph dump
    hash: str

    model_config = ConfigDict(extra="forbid", frozen=True)

    def resolve(self, function_id: str, version: str) -> FunctionDefinition | None:
        entry = self.functions.get(f"{function_id}@{version}")
        return entry.definition if entry else None

    def current_version(self, function_id: str) -> str | None:
        matches = [
            e.definition.version
            for e in self.functions.values()
            if e.definition.function_id == function_id and not e.definition.deprecated
        ]
        if not matches:
            return None
        return max(matches, key=_version_key)

    def entries_for(self, function_id: str) -> list[RegistryEntry]:
        return [e for e in self.functions.values() if e.definition.function_id == function_id]


def _version_key(version: str) -> tuple[int, int, int]:
    parts = version.split(".")
    def _part(p: str) -> int:
        digits = "".join(ch for ch in p if ch.isdigit())
        return int(digits or 0)

    return tuple(_part(p) for p in (parts + ["0", "0", "0"])[:3])  # type: ignore[return-value]


def compute_snapshot_hash(functions: dict[str, RegistryEntry]) -> str:
    return canonical_digest(
        {identity: {"def": e.definition.model_dump(mode="json"), "hash": e.function_hash} for identity, e in sorted(functions.items())}
    )
