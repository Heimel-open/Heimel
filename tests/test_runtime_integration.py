from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from services.harness.route_planner import (
    HarnessRoutePlanner,
    ModelRouteCandidate,
)
from src.valo_platform.route_optimization import (
    RouteEstimate,
    RouteReasonCode,
    RouteRequest,
    SelectionStatus,
)
from src.valo_platform.route_optimization.integrations.workflow_contracts import (
    WorkflowRouteCompilationError,
    compile_workflow_graph,
    workflow_candidate,
)
from src.valo_platform.workflow_contracts.models import (
    WorkflowContract,
    WorkflowNodeContract,
)


NOW = datetime(2026, 7, 27, tzinfo=timezone.utc)


def request(identifier="runtime-1"):
    return RouteRequest(
        route_request_id=identifier,
        principal_id="principal",
        purpose_ref="purpose",
        intent_digest="sha256:intent",
        semantic_state_digest="sha256:semantic",
        target_outcome_ref="outcome",
        current_state_digest="sha256:state",
        authority_snapshot_hash="sha256:authority",
        policy_snapshot_hash="sha256:policy",
        context_snapshot_hash="sha256:context",
        as_of=NOW,
        estimate_set_version="estimate-v1",
    )


def workflow():
    return WorkflowContract(
        workflow_id="workflow-1",
        workflow_version="1",
        objective="produce target artifact",
        nodes=(
            WorkflowNodeContract(
                node_id="source",
                node_version="1",
                objective="collect source",
            ),
            WorkflowNodeContract(
                node_id="transform",
                node_version="1",
                objective="transform source",
                depends_on=("source",),
            ),
            WorkflowNodeContract(
                node_id="target",
                node_version="1",
                objective="produce target",
                depends_on=("transform",),
            ),
            WorkflowNodeContract(
                node_id="unrelated",
                node_version="1",
                objective="unrelated analysis",
            ),
        ),
    )


def test_workflow_compiler_uses_only_target_dependency_closure():
    graph = compile_workflow_graph(
        workflow(),
        target_node_id="target",
        estimates={
            "source": RouteEstimate(execution_ms=5),
            "transform": RouteEstimate(execution_ms=10),
            "target": RouteEstimate(execution_ms=1),
            "unrelated": RouteEstimate(execution_ms=1000),
        },
    )
    candidate = workflow_candidate(graph, candidate_id="target-route")
    assert candidate.node_ids == ("source", "target", "transform")
    assert "unrelated" not in candidate.node_ids


def test_harness_plans_existing_workflow_without_second_contract():
    selection = HarnessRoutePlanner().plan_workflow(
        request=request(),
        contract=workflow(),
        target_node_id="target",
        estimates={
            "source": RouteEstimate(execution_ms=5, version="estimate-v1"),
            "transform": RouteEstimate(execution_ms=10, version="estimate-v1"),
            "target": RouteEstimate(execution_ms=1, version="estimate-v1"),
            "unrelated": RouteEstimate(execution_ms=1000, version="estimate-v1"),
        },
    )
    assert selection.status is SelectionStatus.SELECTED
    assert selection.selected_node_ids == ("source", "target", "transform")
    assert selection.estimated_completion_ms == 16
    dumped = selection.model_dump(mode="json")
    assert "allow" not in dumped
    assert "clearance" not in dumped
    assert "authorization" not in dumped


def test_workflow_linter_failure_blocks_route_compilation():
    invalid = WorkflowContract(
        workflow_id="invalid",
        workflow_version="1",
        objective="invalid external effect",
        nodes=(
            WorkflowNodeContract(
                node_id="execute",
                node_version="1",
                objective="perform external action",
                external_effect=True,
            ),
        ),
    )
    with pytest.raises(WorkflowRouteCompilationError, match="external_effect"):
        compile_workflow_graph(invalid, target_node_id="execute")


def test_mandatory_governance_node_must_be_on_target_path():
    graph = compile_workflow_graph(
        workflow(),
        target_node_id="target",
        mandatory_governance_nodes=("unrelated",),
    )
    with pytest.raises(
        WorkflowRouteCompilationError,
        match="not on the target dependency path",
    ):
        workflow_candidate(graph, candidate_id="target-route")


def test_fastest_inadmissible_model_never_wins():
    plan = HarnessRoutePlanner().plan_model_route(
        request=request("model-route"),
        candidates=(
            ModelRouteCandidate(
                model_id="fast-invalid",
                provider="provider-a",
                mal_admissible=False,
                policy_eligible=True,
                policy_evidence_ref="policy:fast",
                estimated_latency_ms=1,
                evidence_strength=100,
            ),
            ModelRouteCandidate(
                model_id="slower-valid",
                provider="provider-b",
                mal_admissible=True,
                mal_receipt_ref="mal:slower",
                policy_eligible=True,
                policy_evidence_ref="policy:slower",
                estimated_latency_ms=20,
                evidence_strength=100,
            ),
        ),
    )
    assert plan.selected_model_id == "slower-valid"
    assert plan.selection.pruned_candidates[0].reasons == (
        RouteReasonCode.ROUTE_MAL_INADMISSIBLE,
    )


def test_model_route_uses_end_to_end_latency_not_raw_execution_only():
    plan = HarnessRoutePlanner().plan_model_route(
        request=request("model-latency"),
        candidates=(
            ModelRouteCandidate(
                model_id="fast-busy",
                provider="provider-a",
                mal_admissible=True,
                mal_receipt_ref="mal:fast-busy",
                policy_eligible=True,
                policy_evidence_ref="policy:fast-busy",
                estimated_latency_ms=1,
                estimated_queue_ms=100,
                evidence_strength=100,
            ),
            ModelRouteCandidate(
                model_id="steady",
                provider="provider-b",
                mal_admissible=True,
                mal_receipt_ref="mal:steady",
                policy_eligible=True,
                policy_evidence_ref="policy:steady",
                estimated_latency_ms=20,
                evidence_strength=100,
            ),
        ),
    )
    assert plan.selected_model_id == "steady"
    assert plan.selection.estimated_completion_ms == 20


def test_positive_external_status_requires_receipt_binding():
    with pytest.raises(ValidationError, match="MAL receipt"):
        ModelRouteCandidate(
            model_id="unbound",
            provider="provider",
            mal_admissible=True,
            policy_eligible=True,
            policy_evidence_ref="policy:unbound",
        )


def test_empty_model_pool_returns_explicit_no_route():
    plan = HarnessRoutePlanner().plan_model_route(
        request=request("empty-model-route"),
        candidates=(),
    )
    assert plan.selected_model_id is None
    assert plan.selection.status is SelectionStatus.NO_ROUTE
    assert plan.selection.blockers == (
        RouteReasonCode.ROUTE_NO_VALID_CANDIDATE,
    )
