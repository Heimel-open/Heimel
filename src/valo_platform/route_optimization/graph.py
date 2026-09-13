"""Canonical route graph validation and dependency helpers."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Dict, Iterable, Mapping, Set, Tuple

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from src.valo_platform.canonical import canonical_digest
from src.valo_platform.route_optimization.contracts import (
    RouteCandidate,
    RouteEdge,
    RouteEdgeKind,
    RouteNode,
)


_NON_DAG_EDGE_KINDS = {RouteEdgeKind.RETRY, RouteEdgeKind.RECOVERY}


def _node_key(item: object) -> str:
    if isinstance(item, RouteNode):
        return item.node_id
    return str(item.get("node_id", ""))


def _edge_key(item: object) -> Tuple[str, str, str, bool, int]:
    if isinstance(item, RouteEdge):
        return (
            item.source,
            item.target,
            item.kind.value,
            item.required,
            item.max_traversals,
        )
    kind = item.get("kind", RouteEdgeKind.DEPENDENCY)
    kind_value = kind.value if isinstance(kind, RouteEdgeKind) else str(kind)
    return (
        str(item.get("source", "")),
        str(item.get("target", "")),
        kind_value,
        bool(item.get("required", True)),
        int(item.get("max_traversals", 1)),
    )


class RouteGraph(BaseModel):
    """Immutable graph. Retry/recovery edges may be cyclic but are bounded."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    graph_id: str
    graph_version: str
    target_node_id: str
    nodes: Tuple[RouteNode, ...]
    edges: Tuple[RouteEdge, ...] = ()

    @field_validator("nodes", mode="before")
    @classmethod
    def _sort_nodes(cls, value: object) -> object:
        return tuple(sorted(value or (), key=_node_key))

    @field_validator("edges", mode="before")
    @classmethod
    def _sort_edges(cls, value: object) -> object:
        return tuple(sorted(value or (), key=_edge_key))

    @model_validator(mode="after")
    def _validate_graph(self) -> "RouteGraph":
        node_ids = [node.node_id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("route graph contains duplicate node_id values")
        if self.target_node_id not in set(node_ids):
            raise ValueError("target_node_id is not present in nodes")

        known = set(node_ids)
        seen_edges = set()
        for edge in self.edges:
            if edge.source not in known or edge.target not in known:
                raise ValueError(
                    f"edge references unknown node: {edge.source}->{edge.target}"
                )
            edge_key = (
                edge.source,
                edge.target,
                edge.kind,
                edge.required,
                edge.max_traversals,
            )
            if edge_key in seen_edges:
                raise ValueError("route graph contains a duplicate edge")
            seen_edges.add(edge_key)

        self._assert_acyclic()
        return self

    @property
    def fingerprint(self) -> str:
        return canonical_digest(self)

    def node_map(self) -> Dict[str, RouteNode]:
        return {node.node_id: node for node in self.nodes}

    def dependency_predecessors(
        self, node_id: str, within: Iterable[str] = ()
    ) -> Tuple[str, ...]:
        allowed = set(within)
        restrict = bool(allowed)
        predecessors = {
            edge.source
            for edge in self.edges
            if edge.kind not in _NON_DAG_EDGE_KINDS
            and edge.target == node_id
            and (not restrict or edge.source in allowed)
        }
        return tuple(sorted(predecessors))

    def dependency_successors(
        self, node_id: str, within: Iterable[str] = ()
    ) -> Tuple[str, ...]:
        allowed = set(within)
        restrict = bool(allowed)
        successors = {
            edge.target
            for edge in self.edges
            if edge.kind not in _NON_DAG_EDGE_KINDS
            and edge.source == node_id
            and (not restrict or edge.target in allowed)
        }
        return tuple(sorted(successors))

    def candidate_error(self, candidate: RouteCandidate) -> str:
        selected = set(candidate.node_ids)
        known = set(self.node_map())
        missing = selected - known
        if missing:
            return f"candidate references unknown nodes: {sorted(missing)}"
        if self.target_node_id not in selected:
            return "candidate does not include target_node_id"

        mandatory = {
            node.node_id
            for node in self.nodes
            if node.mandatory_governance
        }
        missing_mandatory = mandatory - selected
        if missing_mandatory:
            return (
                "candidate omits mandatory governance nodes: "
                f"{sorted(missing_mandatory)}"
            )

        for node_id in selected:
            required = {
                edge.source
                for edge in self.edges
                if edge.kind not in _NON_DAG_EDGE_KINDS
                and edge.required
                and edge.target == node_id
            }
            missing_dependencies = required - selected
            if missing_dependencies:
                return (
                    f"candidate omits required dependencies for {node_id}: "
                    f"{sorted(missing_dependencies)}"
                )

        reachable_to_target = self._reverse_reachable(
            self.target_node_id, selected
        )
        unreachable = selected - reachable_to_target
        if unreachable:
            return (
                "candidate includes nodes that cannot reach target: "
                f"{sorted(unreachable)}"
            )
        return ""

    def topological_order(self, within: Iterable[str]) -> Tuple[str, ...]:
        selected = set(within)
        indegree = {node_id: 0 for node_id in selected}
        successors: Mapping[str, Set[str]] = defaultdict(set)
        for edge in self.edges:
            if edge.kind in _NON_DAG_EDGE_KINDS:
                continue
            if edge.source in selected and edge.target in selected:
                if edge.target not in successors[edge.source]:
                    successors[edge.source].add(edge.target)
                    indegree[edge.target] += 1

        ready = deque(
            sorted(node_id for node_id, degree in indegree.items() if degree == 0)
        )
        order = []
        while ready:
            current = ready.popleft()
            order.append(current)
            for successor in sorted(successors[current]):
                indegree[successor] -= 1
                if indegree[successor] == 0:
                    ready.append(successor)
        if len(order) != len(selected):
            raise ValueError("candidate dependency subgraph contains a cycle")
        return tuple(order)

    def _assert_acyclic(self) -> None:
        self.topological_order(node.node_id for node in self.nodes)

    def _reverse_reachable(
        self, target: str, within: Set[str]
    ) -> Set[str]:
        reverse: Mapping[str, Set[str]] = defaultdict(set)
        for edge in self.edges:
            if edge.kind in _NON_DAG_EDGE_KINDS:
                continue
            if edge.source in within and edge.target in within:
                reverse[edge.target].add(edge.source)

        seen = {target}
        stack = [target]
        while stack:
            current = stack.pop()
            for predecessor in reverse[current]:
                if predecessor not in seen:
                    seen.add(predecessor)
                    stack.append(predecessor)
        return seen


__all__ = ["RouteGraph"]
