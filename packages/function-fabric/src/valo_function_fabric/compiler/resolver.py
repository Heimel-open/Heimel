from __future__ import annotations

from ..contracts.function import FunctionDefinition
from ..contracts.graph import FunctionGraph
from ..contracts.registry import RegistrySnapshot
from .errors import ResolverError


class ResolvedCall:
    """A FunctionCall resolved to a pinned, registered FunctionDefinition plus
    its compiled workflow graph."""

    def __init__(self, call_id: str, definition: FunctionDefinition, workflow_graph) -> None:
        self.call_id = call_id
        self.definition = definition
        self.workflow_graph = workflow_graph


def resolve_calls(
    fgraph: FunctionGraph, snapshot: RegistrySnapshot
) -> dict[str, ResolvedCall]:
    """Resolve every FunctionCall to a pinned version in the snapshot. Version
    pinning is mandatory: there is no 'call PAY latest' after compilation."""
    resolved: dict[str, ResolvedCall] = {}
    for call in fgraph.nodes:
        definition = snapshot.resolve(call.function_ref.function_id, call.function_ref.version)
        if definition is None:
            raise ResolverError(
                f"call {call.id}: unknown function {call.function_ref.identity}"
            )
        if definition.deprecated:
            raise ResolverError(
                f"call {call.id}: deprecated function {call.function_ref.identity} requires explicit pin (provided)"
            )
        graph = snapshot.graphs.get(definition.workflow_ref)
        if graph is None:
            raise ResolverError(
                f"call {call.id}: {call.function_ref.identity} has no registered workflow graph {definition.workflow_ref}"
            )
        resolved[call.id] = ResolvedCall(call.id, definition, graph)
    return resolved

