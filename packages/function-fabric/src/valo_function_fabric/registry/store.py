from __future__ import annotations

from typing import Any
from uuid import uuid4

from ..contracts.common import FunctionStatus, canonical_digest
from ..contracts.function import FunctionDefinition
from ..contracts.graph import FunctionGraph
from ..contracts.registry import RegistryEntry, RegistrySnapshot


class RegistryError(ValueError):
    """Unknown function, version, or illegal registry mutation."""


class FunctionRegistry:
    """Canonical, versioned, snapshotable Function Registry. Registry mutation
    is a separate governed change-management path; it is never self-modifying
    during execution."""

    def __init__(self) -> None:
        self._functions: dict[str, RegistryEntry] = {}
        self._graphs: dict[str, Any] = {}  # graph identity -> WorkflowGraph
        self._source_graphs: dict[str, FunctionGraph] = {}

    def register(
        self,
        definition: FunctionDefinition,
        graph: Any,
        source_graph: FunctionGraph | None = None,
    ) -> str:
        identity = definition.identity
        if identity in self._functions:
            raise RegistryError(f"function already registered: {identity}")
        function_hash = canonical_digest(definition.model_dump(mode="json"))
        self._functions[identity] = RegistryEntry(definition=definition, function_hash=function_hash)
        self._graphs[definition.workflow_ref] = graph
        if source_graph is not None:
            self._source_graphs[definition.workflow_ref] = source_graph
        return identity

    def resolve(self, function_id: str, version: str | None = None) -> FunctionDefinition:
        if version is None:
            snapshot = self.snapshot()
            version = snapshot.current_version(function_id)
            if version is None:
                raise RegistryError(f"no active version of {function_id}")
        entry = self._functions.get(f"{function_id}@{version}")
        if entry is None:
            raise RegistryError(f"unknown function {function_id}@{version}")
        return entry.definition

    def get(self, identity: str) -> FunctionDefinition:
        entry = self._functions.get(identity)
        if entry is None:
            raise RegistryError(f"unknown function identity: {identity}")
        return entry.definition

    def graph_for(self, definition: FunctionDefinition) -> Any:
        return self._graphs[definition.workflow_ref]

    def source_graph_for(self, definition: FunctionDefinition) -> FunctionGraph | None:
        return self._source_graphs.get(f"{definition.workflow_ref}@{definition.version}")

    def list_versions(self, function_id: str) -> list[str]:
        return sorted(
            (e.definition.version for e in self._functions.values() if e.definition.function_id == function_id),
            key=_version_key,
        )

    def dependents(self, function_id: str) -> list[str]:
        """Blast radius: functions whose source FunctionGraph references this
        function."""
        result = set()
        for graph in self._source_graphs.values():
            for call in graph.nodes:
                if call.function_ref.function_id == function_id:
                    result.add(graph.graph_id)
        return sorted(result)

    def dependencies(self, function_id: str) -> list[str]:
        """Functions referenced by this function's source FunctionGraph."""
        for entry in self._functions.values():
            if entry.definition.function_id != function_id:
                continue
            graph = self._source_graphs.get(entry.definition.workflow_ref)
            if graph is None:
                return []
            return sorted({call.function_ref.function_id for call in graph.nodes})
        return []

    def validate(self) -> list[str]:
        errors: list[str] = []
        for identity, entry in sorted(self._functions.items()):
            definition = entry.definition
            if definition.workflow_ref not in self._graphs:
                errors.append(f"{identity}: workflow_ref {definition.workflow_ref} has no registered graph")
        return errors

    def deprecate(self, function_id: str, version: str) -> None:
        identity = f"{function_id}@{version}"
        entry = self._functions.get(identity)
        if entry is None:
            raise RegistryError(f"unknown function {identity}")
        deprecated = entry.definition.model_copy(update={"deprecated": True, "status": FunctionStatus.DEPRECATED})
        self._functions[identity] = RegistryEntry(definition=deprecated, function_hash=canonical_digest(deprecated.model_dump(mode="json")))

    def snapshot(self) -> RegistrySnapshot:
        functions = dict(self._functions)
        graphs = dict(self._graphs)
        snapshot_hash = canonical_digest(
            {
                "functions": {
                    identity: {"def": e.definition.model_dump(mode="json"), "hash": e.function_hash}
                    for identity, e in sorted(functions.items())
                },
                "graphs": {
                    identity: graph.model_dump(mode="json") if hasattr(graph, "model_dump") else graph
                    for identity, graph in sorted(graphs.items())
                },
            }
        )
        return RegistrySnapshot(
            snapshot_id=str(uuid4()),
            functions=functions,
            graphs=graphs,
            hash=snapshot_hash,
        )

    def __contains__(self, identity: str) -> bool:
        return identity in self._functions


def _version_key(version: str) -> tuple[int, ...]:
    parts = version.split(".")

    def _part(p: str) -> int:
        digits = "".join(ch for ch in p if ch.isdigit())
        return int(digits or 0)

    return tuple(_part(p) for p in (parts + ["0", "0", "0"])[:3])

