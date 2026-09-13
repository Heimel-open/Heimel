"""Compile existing WorkflowContract DAGs into canonical route graphs.

The adapter performs planning only. It reuses the workflow linter and does not
add authority, admissibility, clearance or execution semantics.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, Mapping, Optional, Tuple

from src.valo_platform.route_optimization.contracts import (
    RouteCandidate,
    RouteConstraint,
    RouteEdge,
    RouteEstimate,
    RouteNode,
    RouteNodeKind,
)
from src.valo_platform.route_optimization.graph import RouteGraph
from src.valo_platform.workflow_contracts.linter import lint_workflow
from src.valo_platform.workflow_contracts.models import WorkflowContract


class WorkflowRouteCompilationError(ValueError):
    """Raised when an existing workflow cannot become a valid route graph."""


def compile_workflow_graph(
    contract: WorkflowContract,
    *,
    target_node_id: str,
    estimates: Optional[Mapping[str, RouteEstimate]] = None,
    constraints: Optional[Mapping[str, Tuple[RouteConstraint, ...]]] = None,
    evidence_refs: Optional[Mapping[str, Tuple[str, ...]]] = None,
    owner_refs: Optional[Mapping[str, str]] = None,
    owned_resources: Optional[Mapping[str, Tuple[str, ...]]] = None,
    mandatory_governance_nodes: Iterable[str] = (),
    verifier_registry: Optional[Mapping[str, str]] = None,
) -> RouteGraph:
    """Compile a linted workflow into a deterministic planning graph."""
    errors = lint_workflow(contract, verifier_registry=verifier_registry)
    if errors:
        detail = "; ".join(
            f"{error.code}:{error.node_id or '-'}:{error.message}"
            for error in errors
        )
        raise WorkflowRouteCompilationError(detail)

    node_ids = {node.node_id for node in contract.nodes}
    if target_node_id not in node_ids:
        raise WorkflowRouteCompilationError(
            f"target node '{target_node_id}' is not present in workflow"
        )

    estimate_map = estimates or {}
    constraint_map = constraints or {}
    evidence_map = evidence_refs or {}
    owner_map = owner_refs or {}
    resource_map = owned_resources or {}
    mandatory = set(mandatory_governance_nodes)
    unknown_mandatory = mandatory - node_ids
    if unknown_mandatory:
        raise WorkflowRouteCompilationError(
            "mandatory governance nodes are absent from workflow: "
            f"{sorted(unknown_mandatory)}"
        )

    route_nodes = []
    route_edges = []
    for workflow_node in contract.nodes:
        kind = (
            RouteNodeKind.EVALUATION
            if workflow_node.criteria
            else RouteNodeKind.TRANSFORMATION
        )
        route_nodes.append(
            RouteNode(
                node_id=workflow_node.node_id,
                kind=kind,
                estimate=estimate_map.get(
                    workflow_node.node_id,
                    RouteEstimate(),
                ),
                constraints=constraint_map.get(workflow_node.node_id, ()),
                evidence_refs=evidence_map.get(workflow_node.node_id, ()),
                owner_ref=owner_map.get(workflow_node.node_id, ""),
                owned_resources=resource_map.get(workflow_node.node_id, ()),
                mandatory_governance=workflow_node.node_id in mandatory,
            )
        )
        route_edges.extend(
            RouteEdge(source=dependency, target=workflow_node.node_id)
            for dependency in workflow_node.depends_on
        )

    return RouteGraph(
        graph_id=f"workflow:{contract.workflow_id}",
        graph_version=contract.workflow_version,
        target_node_id=target_node_id,
        nodes=tuple(route_nodes),
        edges=tuple(route_edges),
    )


def workflow_candidate(
    graph: RouteGraph,
    *,
    candidate_id: str,
    constraints: Tuple[RouteConstraint, ...] = (),
    assumptions: Tuple[str, ...] = (),
    valid_until: Optional[datetime] = None,
) -> RouteCandidate:
    """Create the minimal dependency-closed candidate for the target node."""
    required = {graph.target_node_id}
    stack = [graph.target_node_id]
    while stack:
        current = stack.pop()
        for predecessor in graph.dependency_predecessors(current):
            if predecessor not in required:
                required.add(predecessor)
                stack.append(predecessor)

    mandatory = {
        node.node_id
        for node in graph.nodes
        if node.mandatory_governance
    }
    missing_mandatory = mandatory - required
    if missing_mandatory:
        raise WorkflowRouteCompilationError(
            "mandatory governance nodes are not on the target dependency path: "
            f"{sorted(missing_mandatory)}"
        )

    return RouteCandidate(
        candidate_id=candidate_id,
        node_ids=tuple(sorted(required)),
        constraints=constraints,
        assumptions=assumptions,
        valid_until=valid_until,
    )


__all__ = [
    "WorkflowRouteCompilationError",
    "compile_workflow_graph",
    "workflow_candidate",
]
