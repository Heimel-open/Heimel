from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from src.valo_platform.route_optimization import (
    ConstraintKind,
    RouteCandidate,
    RouteConstraint,
    RouteEdge,
    RouteEstimate,
    RouteGraph,
    RouteNode,
    RouteNodeKind,
    RouteReasonCode,
    RouteRequest,
    SelectionStatus,
    reduce_frontier,
    select_fastest_valid_route,
)


NOW = datetime(2026, 7, 27, tzinfo=timezone.utc)


def request(**updates):
    payload = {
        "route_request_id": "req-1",
        "principal_id": "principal-1",
        "purpose_ref": "purpose-1",
        "intent_digest": "sha256:intent",
        "semantic_state_digest": "sha256:semantic",
        "target_outcome_ref": "outcome-1",
        "current_state_digest": "sha256:state",
        "authority_snapshot_hash": "sha256:authority",
        "policy_snapshot_hash": "sha256:policy",
        "context_snapshot_hash": "sha256:context",
        "required_constraint_kinds": (ConstraintKind.AUTHORITY,),
        "as_of": NOW,
    }
    payload.update(updates)
    return RouteRequest(**payload)


def constraint(identifier, satisfied=True):
    return RouteConstraint(
        constraint_id=identifier,
        kind=ConstraintKind.AUTHORITY,
        satisfied=satisfied,
        evidence_refs=("evidence-1",),
    )


def node(
    identifier,
    duration,
    *,
    cost=0,
    risk=0,
    reversibility=100,
    evidence=100,
    constraints=(),
    resources=(),
    mandatory=False,
):
    return RouteNode(
        node_id=identifier,
        kind=RouteNodeKind.EVALUATION,
        estimate=RouteEstimate(
            execution_ms=duration,
            cost_microunits=cost,
            risk_exposure=risk,
            reversibility=reversibility,
            evidence_strength=evidence,
            version="est-v1",
        ),
        constraints=constraints,
        owned_resources=resources,
        mandatory_governance=mandatory,
    )


def graph_for_alternatives():
    return RouteGraph(
        graph_id="graph-1",
        graph_version="1",
        target_node_id="target",
        nodes=(
            node("target", 1, constraints=(constraint("target-auth"),), mandatory=True),
            node("slow-local", 20, constraints=(constraint("slow-auth"),)),
            RouteNode(
                node_id="fast-local",
                kind=RouteNodeKind.MODEL,
                estimate=RouteEstimate(
                    execution_ms=1,
                    human_wait_ms=200,
                    evidence_strength=100,
                    version="est-v1",
                ),
                constraints=(constraint("fast-auth"),),
            ),
        ),
        edges=(
            RouteEdge(source="slow-local", target="target", required=False),
            RouteEdge(source="fast-local", target="target", required=False),
        ),
    )


def test_graph_digest_is_independent_of_input_order():
    first = graph_for_alternatives()
    second = RouteGraph(
        graph_id=first.graph_id,
        graph_version=first.graph_version,
        target_node_id=first.target_node_id,
        nodes=tuple(reversed(first.nodes)),
        edges=tuple(reversed(first.edges)),
    )
    assert first.fingerprint == second.fingerprint


def test_unknown_contract_field_is_rejected():
    with pytest.raises(ValidationError):
        RouteCandidate(
            candidate_id="candidate",
            node_ids=("target",),
            clearance="smuggled",
        )


def test_graph_rejects_unbounded_normal_cycle():
    with pytest.raises(ValidationError):
        RouteGraph(
            graph_id="cycle",
            graph_version="1",
            target_node_id="a",
            nodes=(node("a", 1), node("b", 1)),
            edges=(
                RouteEdge(source="a", target="b"),
                RouteEdge(source="b", target="a"),
            ),
        )


def test_fastest_local_node_loses_when_end_to_end_route_is_slower():
    graph = graph_for_alternatives()
    selection = select_fastest_valid_route(
        request(),
        graph,
        (
            RouteCandidate(candidate_id="fast", node_ids=("fast-local", "target")),
            RouteCandidate(candidate_id="slow", node_ids=("slow-local", "target")),
        ),
    )
    assert selection.status is SelectionStatus.SELECTED
    assert selection.selected_candidate_id == "slow"
    assert selection.estimated_completion_ms == 21


def test_fastest_invalid_route_never_wins():
    graph = RouteGraph(
        graph_id="invalid-fast",
        graph_version="1",
        target_node_id="target",
        nodes=(
            node("target", 1, constraints=(constraint("target"),), mandatory=True),
            node("invalid", 1, constraints=(constraint("invalid", False),)),
            node("valid", 10, constraints=(constraint("valid"),)),
        ),
        edges=(
            RouteEdge(source="invalid", target="target", required=False),
            RouteEdge(source="valid", target="target", required=False),
        ),
    )
    selection = select_fastest_valid_route(
        request(),
        graph,
        (
            RouteCandidate(candidate_id="invalid", node_ids=("invalid", "target")),
            RouteCandidate(candidate_id="valid", node_ids=("valid", "target")),
        ),
    )
    assert selection.selected_candidate_id == "valid"
    assert selection.pruned_candidates[0].reasons == (
        RouteReasonCode.ROUTE_AUTHORITY_INVALID,
    )


def test_pareto_dominated_route_is_pruned():
    graph = RouteGraph(
        graph_id="dominance",
        graph_version="1",
        target_node_id="target",
        nodes=(
            node("target", 1, constraints=(constraint("target"),), mandatory=True),
            node("better", 5, cost=5, risk=1, constraints=(constraint("better"),)),
            node("worse", 8, cost=8, risk=2, constraints=(constraint("worse"),)),
        ),
        edges=(
            RouteEdge(source="better", target="target", required=False),
            RouteEdge(source="worse", target="target", required=False),
        ),
    )
    reduction = reduce_frontier(
        request(),
        graph,
        (
            RouteCandidate(candidate_id="better", node_ids=("better", "target")),
            RouteCandidate(candidate_id="worse", node_ids=("worse", "target")),
        ),
    )
    assert [item.candidate.candidate_id for item in reduction.active_candidates] == [
        "better"
    ]
    assert reduction.pruned_candidates[0].reasons == (
        RouteReasonCode.ROUTE_DOMINATED,
    )


def test_resource_collision_is_serialized():
    graph = RouteGraph(
        graph_id="parallel",
        graph_version="1",
        target_node_id="target",
        nodes=(
            node("a", 10, resources=("file:x",), constraints=(constraint("a"),)),
            node("b", 20, resources=("file:x",), constraints=(constraint("b"),)),
            node("target", 1, constraints=(constraint("target"),), mandatory=True),
        ),
        edges=(
            RouteEdge(source="a", target="target"),
            RouteEdge(source="b", target="target"),
        ),
    )
    selection = select_fastest_valid_route(
        request(),
        graph,
        (RouteCandidate(candidate_id="route", node_ids=("a", "b", "target")),),
    )
    assert selection.parallel_groups == (("a",), ("b",), ("target",))
    assert selection.estimated_completion_ms == 31


def test_independent_nodes_are_parallel():
    graph = RouteGraph(
        graph_id="parallel",
        graph_version="1",
        target_node_id="target",
        nodes=(
            node("a", 10, resources=("file:a",), constraints=(constraint("a"),)),
            node("b", 20, resources=("file:b",), constraints=(constraint("b"),)),
            node("target", 1, constraints=(constraint("target"),), mandatory=True),
        ),
        edges=(
            RouteEdge(source="a", target="target"),
            RouteEdge(source="b", target="target"),
        ),
    )
    selection = select_fastest_valid_route(
        request(),
        graph,
        (RouteCandidate(candidate_id="route", node_ids=("a", "b", "target")),),
    )
    assert selection.parallel_groups == (("a", "b"), ("target",))
    assert selection.estimated_completion_ms == 21


def test_stale_route_forces_no_route():
    graph = graph_for_alternatives()
    selection = select_fastest_valid_route(
        request(),
        graph,
        (
            RouteCandidate(
                candidate_id="stale",
                node_ids=("slow-local", "target"),
                valid_until=NOW - timedelta(seconds=1),
            ),
        ),
    )
    assert selection.status is SelectionStatus.NO_ROUTE
    assert selection.blockers == (RouteReasonCode.ROUTE_STATE_STALE,)


def test_route_digest_changes_with_material_state():
    graph = graph_for_alternatives()
    candidates = (
        RouteCandidate(candidate_id="slow", node_ids=("slow-local", "target")),
    )
    first = select_fastest_valid_route(request(), graph, candidates)
    second = select_fastest_valid_route(
        request(current_state_digest="sha256:changed"),
        graph,
        candidates,
    )
    assert first.route_digest != second.route_digest
