from __future__ import annotations

from collections import deque

from ..contracts.graph import WorkflowEdge, WorkflowGraph
from ..types.system import can_consume


def successors(graph: WorkflowGraph, node_id: str) -> list[WorkflowEdge]:
    return [e for e in graph.edges if e.source == node_id]


def predecessors(graph: WorkflowGraph, node_id: str) -> list[WorkflowEdge]:
    return [e for e in graph.edges if e.target == node_id]


def reachable_from(graph: WorkflowGraph, entry: str) -> set[str]:
    """BFS over all edges (any type) from entry. Reachability is structural."""
    seen: set[str] = set()
    queue: deque[str] = deque([entry])
    while queue:
        current = queue.popleft()
        if current in seen:
            continue
        seen.add(current)
        for edge in successors(graph, current):
            queue.append(edge.target)
    return seen


def can_reach(graph: WorkflowGraph, source: str, target: str) -> bool:
    return target in reachable_from(graph, source)


def producer_for_input(
    graph: WorkflowGraph,
    node_id: str,
    input_name: str,
    input_type: str,
) -> str | None:
    """Find a node that produces `input_name` with a type consumable as
    `input_type`, reachable backwards from `node_id`. Walks through control
    nodes (JOIN/SEQ/PARALLEL/...) that pass values through. Returns the
    producing node id, or None if only the graph input can supply it."""
    node_map = graph.node_map()
    queue: deque[str] = deque([node_id])
    visited: set[str] = set()
    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        node = node_map[current]
        for output in node.outputs:
            if output.name == input_name and can_consume(output.type, input_type):
                return current
        for edge in predecessors(graph, current):
            queue.append(edge.source)
    return None


def producer_types_for_input(
    graph: WorkflowGraph,
    node_id: str,
    input_name: str,
) -> list[tuple[str, str]]:
    """All (producer_node_id, output_type) pairs that can reach `node_id`
    backwards and declare the input name. Used for type-compatibility checks."""
    node_map = graph.node_map()
    queue: deque[str] = deque([node_id])
    visited: set[str] = set()
    found: list[tuple[str, str]] = []
    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        node = node_map[current]
        for output in node.outputs:
            if output.name == input_name:
                found.append((current, output.type))
        for edge in predecessors(graph, current):
            queue.append(edge.source)
    return found


def graph_inputs_satisfy(graph: WorkflowGraph, node_id: str) -> list[str]:
    """Return the input names of `node_id` that must be supplied by the graph
    input_schema (i.e. no node producer exists)."""
    node = graph.node_map()[node_id]
    missing: list[str] = []
    for ref in node.inputs:
        if producer_for_input(graph, node_id, ref.name, ref.type) is None and ref.name not in graph.input_schema:
            missing.append(ref.name)
    return missing
