import json
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import validate

from src.valo_platform.route_optimization import (
    RouteCandidate,
    RouteGraph,
    RouteNode,
    RouteNodeKind,
    RouteRequest,
    select_fastest_valid_route,
)


ROOT = Path(__file__).resolve().parents[2]


def _schema(name: str):
    return json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))


def test_route_models_validate_against_committed_schemas():
    graph = RouteGraph(
        graph_id="graph-schema",
        graph_version="1",
        target_node_id="target",
        nodes=(
            RouteNode(
                node_id="target",
                kind=RouteNodeKind.OUTCOME,
                mandatory_governance=True,
            ),
        ),
    )
    request = RouteRequest(
        route_request_id="request-schema",
        principal_id="principal",
        purpose_ref="purpose",
        intent_digest="sha256:intent",
        semantic_state_digest="sha256:semantic",
        target_outcome_ref="outcome",
        current_state_digest="sha256:state",
        authority_snapshot_hash="sha256:authority",
        policy_snapshot_hash="sha256:policy",
        context_snapshot_hash="sha256:context",
        as_of=datetime(2026, 7, 27, tzinfo=timezone.utc),
    )
    selection = select_fastest_valid_route(
        request,
        graph,
        (RouteCandidate(candidate_id="direct", node_ids=("target",)),),
    )

    validate(
        graph.model_dump(mode="json"),
        _schema("action-route-graph-v1.schema.json"),
    )
    validate(
        request.model_dump(mode="json"),
        _schema("action-route-request-v1.schema.json"),
    )
    validate(
        selection.model_dump(mode="json"),
        _schema("action-route-selection-v1.schema.json"),
    )
