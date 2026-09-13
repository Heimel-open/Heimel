import itertools
import json
from datetime import datetime, timezone
from pathlib import Path

from benchmarks.route_optimization.run_benchmark import run_benchmarks
from src.valo_platform.route_optimization import (
    ConstraintKind,
    RouteCandidate,
    RouteConstraint,
    RouteEdge,
    RouteEstimate,
    RouteGraph,
    RouteNode,
    RouteNodeKind,
    RouteRequest,
    SelectionStatus,
    select_fastest_valid_route,
    validate_candidate,
)
from src.valo_platform.route_optimization.estimates import (
    estimate_candidate,
    objective_key,
)


ROOT = Path(__file__).resolve().parents[2]
VECTOR_PATH = ROOT / "tests" / "route_optimization" / "vectors" / "route-conformance-v1.json"
EXPECTED_BENCHMARK_PATH = ROOT / "benchmarks" / "route_optimization" / "expected-results-v1.json"


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
        timezone.utc
    )


def _request(name, as_of, overrides):
    payload = {
        "route_request_id": f"vector:{name}",
        "principal_id": "principal-1",
        "purpose_ref": "vector-purpose",
        "intent_digest": "sha256:intent",
        "semantic_state_digest": "sha256:semantic",
        "target_outcome_ref": "vector-outcome",
        "current_state_digest": "sha256:state",
        "authority_snapshot_hash": "sha256:authority",
        "policy_snapshot_hash": "sha256:policy",
        "context_snapshot_hash": "sha256:context",
        "as_of": as_of,
        "estimate_set_version": "vector-v1",
    }
    payload.update(overrides)
    return RouteRequest(**payload)


def _graph(name, payload):
    nodes = []
    for item in payload["nodes"]:
        constraints = tuple(
            RouteConstraint(
                constraint_id=constraint["id"],
                kind=ConstraintKind(constraint["kind"]),
                satisfied=constraint["satisfied"],
                evidence_refs=(f"evidence:{constraint['id']}",),
            )
            for constraint in item.get("constraints", ())
        )
        nodes.append(
            RouteNode(
                node_id=item["id"],
                kind=RouteNodeKind(item["kind"]),
                estimate=RouteEstimate(
                    execution_ms=item.get("execution_ms", 0),
                    cost_microunits=item.get("cost_microunits", 0),
                    risk_exposure=item.get("risk_exposure", 0),
                    reversibility=item.get("reversibility", 100),
                    evidence_strength=item.get("evidence_strength", 0),
                    version="vector-v1",
                ),
                constraints=constraints,
                owned_resources=tuple(item.get("owned_resources", ())),
            )
        )
    edges = tuple(
        RouteEdge(
            source=item["source"],
            target=item["target"],
            required=item.get("required", True),
        )
        for item in payload.get("edges", ())
    )
    return RouteGraph(
        graph_id=f"vector:{name}",
        graph_version="1",
        target_node_id=payload["target"],
        nodes=tuple(nodes),
        edges=edges,
    )


def _candidates(payload):
    return tuple(
        RouteCandidate(
            candidate_id=item["id"],
            node_ids=tuple(item["nodes"]),
        )
        for item in payload
    )


def test_shared_golden_vectors():
    vectors = json.loads(VECTOR_PATH.read_text(encoding="utf-8"))
    as_of = _parse_time(vectors["as_of"])
    assert vectors["schema_version"] == "route-conformance-v1"

    for vector in vectors["vectors"]:
        request = _request(vector["name"], as_of, vector.get("request", {}))
        graph = _graph(vector["name"], vector["graph"])
        selection = select_fastest_valid_route(
            request,
            graph,
            _candidates(vector["candidates"]),
        )
        expected = vector["expected"]
        assert selection.status.value == expected["status"], vector["name"]
        assert selection.selected_candidate_id == expected["selected_candidate_id"], vector["name"]
        assert selection.estimated_completion_ms == expected["completion_ms"], vector["name"]
        if "parallel_groups" in expected:
            assert [list(group) for group in selection.parallel_groups] == expected["parallel_groups"]
        if "blockers" in expected:
            assert [reason.value for reason in selection.blockers] == expected["blockers"]
        if "pruned" in expected:
            actual = {
                item.candidate_id: [reason.value for reason in item.reasons]
                for item in selection.pruned_candidates
            }
            for candidate_id, reasons in expected["pruned"].items():
                assert actual[candidate_id] == reasons, vector["name"]


def test_structural_benchmark_matches_committed_release_baseline():
    actual = run_benchmarks(iterations=1)
    expected = json.loads(EXPECTED_BENCHMARK_PATH.read_text(encoding="utf-8"))
    assert actual["structural"] == expected["structural"]
    assert actual["timing"]["median_planning_ns"] > 0
    assert actual["timing"]["environment_dependent"] is True


def test_candidate_order_cannot_change_selected_route_or_digest():
    request = _request("permutation", datetime(2026, 7, 27, tzinfo=timezone.utc), {})
    graph = RouteGraph(
        graph_id="permutation",
        graph_version="1",
        target_node_id="target",
        nodes=(
            RouteNode(
                node_id="best",
                kind=RouteNodeKind.MODEL,
                estimate=RouteEstimate(execution_ms=5, evidence_strength=100),
            ),
            RouteNode(
                node_id="second",
                kind=RouteNodeKind.MODEL,
                estimate=RouteEstimate(execution_ms=10, evidence_strength=100),
            ),
            RouteNode(
                node_id="third",
                kind=RouteNodeKind.MODEL,
                estimate=RouteEstimate(execution_ms=15, evidence_strength=100),
            ),
            RouteNode(
                node_id="target",
                kind=RouteNodeKind.OUTCOME,
                estimate=RouteEstimate(evidence_strength=100),
            ),
        ),
        edges=(
            RouteEdge(source="best", target="target", required=False),
            RouteEdge(source="second", target="target", required=False),
            RouteEdge(source="third", target="target", required=False),
        ),
    )
    candidates = (
        RouteCandidate(candidate_id="best", node_ids=("best", "target")),
        RouteCandidate(candidate_id="second", node_ids=("second", "target")),
        RouteCandidate(candidate_id="third", node_ids=("third", "target")),
    )
    selections = tuple(
        select_fastest_valid_route(request, graph, permutation)
        for permutation in itertools.permutations(candidates)
    )
    assert {selection.selected_candidate_id for selection in selections} == {"best"}
    assert len({selection.route_digest for selection in selections}) == 1


def test_frontier_reduction_never_loses_bruteforce_optimum():
    request = _request("bruteforce", datetime(2026, 7, 27, tzinfo=timezone.utc), {})
    nodes = tuple(
        RouteNode(
            node_id=f"route-{index}",
            kind=RouteNodeKind.MODEL,
            estimate=RouteEstimate(
                execution_ms=5 + index * 3,
                cost_microunits=10 + index,
                risk_exposure=index,
                reversibility=100 - index,
                evidence_strength=100,
            ),
        )
        for index in range(6)
    )
    target = RouteNode(
        node_id="target",
        kind=RouteNodeKind.OUTCOME,
        estimate=RouteEstimate(evidence_strength=100),
    )
    graph = RouteGraph(
        graph_id="bruteforce",
        graph_version="1",
        target_node_id="target",
        nodes=(*nodes, target),
        edges=tuple(
            RouteEdge(source=node.node_id, target="target", required=False)
            for node in nodes
        ),
    )
    candidates = tuple(
        RouteCandidate(
            candidate_id=node.node_id,
            node_ids=(node.node_id, "target"),
        )
        for node in nodes
    )
    brute_force = []
    for candidate in candidates:
        validity = validate_candidate(request, graph, candidate)
        if validity.valid:
            metrics = estimate_candidate(graph, candidate)
            brute_force.append(
                (
                    objective_key(metrics, candidate.fingerprint),
                    candidate.candidate_id,
                )
            )
    expected = min(brute_force)[1]
    selection = select_fastest_valid_route(request, graph, candidates)
    assert selection.selected_candidate_id == expected


def test_narrower_authority_can_only_remove_routes_not_create_them():
    request = _request("authority", datetime(2026, 7, 27, tzinfo=timezone.utc), {})
    graph = RouteGraph(
        graph_id="authority",
        graph_version="1",
        target_node_id="target",
        nodes=(
            RouteNode(
                node_id="target",
                kind=RouteNodeKind.OUTCOME,
                estimate=RouteEstimate(evidence_strength=100),
            ),
        ),
    )
    allowed = RouteCandidate(
        candidate_id="allowed",
        node_ids=("target",),
        constraints=(
            RouteConstraint(
                constraint_id="authority:allowed",
                kind=ConstraintKind.AUTHORITY,
                satisfied=True,
            ),
        ),
    )
    narrowed = allowed.model_copy(
        update={
            "candidate_id": "narrowed",
            "constraints": (
                RouteConstraint(
                    constraint_id="authority:narrowed",
                    kind=ConstraintKind.AUTHORITY,
                    satisfied=False,
                ),
            ),
        }
    )
    before = select_fastest_valid_route(request, graph, (allowed,))
    after = select_fastest_valid_route(request, graph, (narrowed,))
    assert before.status is SelectionStatus.SELECTED
    assert after.status is SelectionStatus.NO_ROUTE
