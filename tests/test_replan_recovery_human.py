from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from src.valo_platform.route_optimization import (
    AuthorityHolder,
    HumanRouteStatus,
    HumanStepUpRequest,
    MaterialDeltaKind,
    RecoveryMode,
    RecoveryRouteOption,
    ReplanAction,
    ReplanPolicy,
    ReplanTracker,
    RouteCandidate,
    RouteEdge,
    RouteEstimate,
    RouteGraph,
    RouteNode,
    RouteNodeKind,
    RouteReasonCode,
    RouteRequest,
    RouteStateSnapshot,
    decide_replan,
    detect_material_delta,
    invalidate_route,
    route_human_step_up,
    select_fastest_valid_route,
    select_recovery_route,
)


NOW = datetime(2026, 7, 27, 7, 30, tzinfo=timezone.utc)


def state(**updates):
    payload = {
        "authority_hash": "authority:1",
        "policy_hash": "policy:1",
        "context_hash": "context:1",
        "evidence_hash": "evidence:1",
        "mal_hash": "mal:1",
        "vaig_hash": "vaig:1",
        "dependency_hash": "dependency:1",
        "cost_snapshot_hash": "cost:1",
        "capacity_hash": "capacity:1",
        "deadline_hash": "deadline:1",
        "human_availability_hash": "human:1",
        "execution_state_hash": "execution:1",
        "action_payload_digest": "payload:1",
        "captured_at": NOW,
    }
    payload.update(updates)
    return RouteStateSnapshot(**payload)


def tracker(**updates):
    payload = {
        "route_digest": "route:1",
        "route_version": "v1",
    }
    payload.update(updates)
    return ReplanTracker(**payload)


def request():
    return RouteRequest(
        route_request_id="request-1",
        principal_id="principal-1",
        purpose_ref="purpose-1",
        intent_digest="intent:1",
        semantic_state_digest="semantic:1",
        target_outcome_ref="outcome-1",
        current_state_digest="state:1",
        authority_snapshot_hash="authority:1",
        policy_snapshot_hash="policy:1",
        context_snapshot_hash="context:1",
        as_of=NOW,
    )


def selected_route():
    graph = RouteGraph(
        graph_id="normal-route",
        graph_version="1",
        target_node_id="execute",
        nodes=(
            RouteNode(
                node_id="prepare",
                kind=RouteNodeKind.TRANSFORMATION,
                estimate=RouteEstimate(execution_ms=10),
            ),
            RouteNode(
                node_id="execute",
                kind=RouteNodeKind.EXECUTION,
                estimate=RouteEstimate(execution_ms=5),
            ),
        ),
        edges=(RouteEdge(source="prepare", target="execute"),),
    )
    selection = select_fastest_valid_route(
        request(),
        graph,
        (
            RouteCandidate(
                candidate_id="normal",
                node_ids=("prepare", "execute"),
                valid_until=NOW + timedelta(minutes=10),
            ),
        ),
    )
    return selection


def test_unchanged_state_keeps_current_route_without_blocking():
    previous = state()
    current = state(captured_at=NOW + timedelta(seconds=1))
    decision = decide_replan(
        previous=previous,
        current=current,
        tracker=tracker(),
        now=current.captured_at,
    )
    assert decision.action is ReplanAction.KEEP_CURRENT
    assert decision.execution_blocked is False
    assert decision.delta.changed == ()


def test_material_authority_change_forces_replan_and_new_version():
    previous = state()
    current = state(
        authority_hash="authority:2",
        captured_at=NOW + timedelta(seconds=2),
    )
    decision = decide_replan(
        previous=previous,
        current=current,
        tracker=tracker(),
        now=current.captured_at,
    )
    assert decision.action is ReplanAction.REPLAN
    assert decision.execution_blocked is True
    assert decision.delta.changed == (MaterialDeltaKind.AUTHORITY,)
    assert decision.next_route_version == "v1.r1"
    assert decision.next_tracker.replan_count == 1


def test_same_delta_is_deferred_instead_of_replanning_again():
    previous = state()
    current = state(
        policy_hash="policy:2",
        captured_at=NOW + timedelta(seconds=2),
    )
    first = decide_replan(
        previous=previous,
        current=current,
        tracker=tracker(),
        now=current.captured_at,
    )
    second = decide_replan(
        previous=previous,
        current=current,
        tracker=first.next_tracker,
        now=current.captured_at + timedelta(seconds=2),
    )
    assert second.action is ReplanAction.DEFER
    assert second.execution_blocked is True
    assert second.reasons == (RouteReasonCode.ROUTE_REPLAN_DEFERRED,)


def test_replan_budget_exhaustion_forces_safe_halt():
    current = state(
        dependency_hash="dependency:2",
        captured_at=NOW + timedelta(seconds=1),
    )
    decision = decide_replan(
        previous=state(),
        current=current,
        tracker=tracker(replan_count=2),
        policy=ReplanPolicy(max_replans=2),
        now=current.captured_at,
    )
    assert decision.action is ReplanAction.SAFE_HALT
    assert decision.reasons == (
        RouteReasonCode.ROUTE_REPLAN_BUDGET_EXHAUSTED,
    )


def test_critical_flapping_inside_cooldown_forces_safe_halt():
    current = state(
        action_payload_digest="payload:2",
        captured_at=NOW + timedelta(milliseconds=100),
    )
    decision = decide_replan(
        previous=state(),
        current=current,
        tracker=tracker(last_replan_at=NOW),
        policy=ReplanPolicy(min_interval_ms=1000),
        now=current.captured_at,
    )
    assert decision.action is ReplanAction.SAFE_HALT
    assert decision.execution_blocked is True


def test_noncritical_cost_change_inside_cooldown_is_deferred():
    current = state(
        cost_snapshot_hash="cost:2",
        captured_at=NOW + timedelta(milliseconds=100),
    )
    delta = detect_material_delta(state(), current)
    assert delta.critical is False
    decision = decide_replan(
        previous=state(),
        current=current,
        tracker=tracker(last_replan_at=NOW),
        policy=ReplanPolicy(min_interval_ms=1000),
        now=current.captured_at,
    )
    assert decision.action is ReplanAction.DEFER
    assert decision.execution_blocked is True


def test_cancellation_and_expiry_propagate_to_uncompleted_nodes():
    selection = selected_route()
    cancelled = invalidate_route(
        selection=selection,
        completed_node_ids=("prepare",),
        invalidated_at=NOW + timedelta(minutes=1),
        cancelled=True,
    )
    expired = invalidate_route(
        selection=selection,
        completed_node_ids=(),
        invalidated_at=NOW + timedelta(minutes=11),
        expires_at=NOW + timedelta(minutes=10),
    )
    assert cancelled.reason is RouteReasonCode.ROUTE_CANCELLED
    assert cancelled.affected_node_ids == ("execute",)
    assert expired.reason is RouteReasonCode.ROUTE_EXPIRED
    assert expired.affected_node_ids == ("execute", "prepare")


def recovery_graph():
    return RouteGraph(
        graph_id="recovery-graph",
        graph_version="1",
        target_node_id="restored",
        nodes=(
            RouteNode(
                node_id="retry",
                kind=RouteNodeKind.TOOL,
                estimate=RouteEstimate(execution_ms=1, evidence_strength=100),
            ),
            RouteNode(
                node_id="alternate",
                kind=RouteNodeKind.TOOL,
                estimate=RouteEstimate(execution_ms=20, evidence_strength=100),
            ),
            RouteNode(
                node_id="rollback",
                kind=RouteNodeKind.EXECUTION,
                estimate=RouteEstimate(execution_ms=30, evidence_strength=100),
            ),
            RouteNode(
                node_id="restored",
                kind=RouteNodeKind.OUTCOME,
                estimate=RouteEstimate(evidence_strength=100),
            ),
        ),
        edges=(
            RouteEdge(source="retry", target="restored", required=False),
            RouteEdge(source="alternate", target="restored", required=False),
            RouteEdge(source="rollback", target="restored", required=False),
        ),
    )


def recovery_option(option_id, mode, node_id, **updates):
    payload = {
        "option_id": option_id,
        "mode": mode,
        "candidate": RouteCandidate(
            candidate_id=f"candidate:{option_id}",
            node_ids=(node_id, "restored"),
        ),
        "evidence_refs": (f"evidence:{option_id}",),
    }
    payload.update(updates)
    return RecoveryRouteOption(**payload)


def test_recovery_prunes_exhausted_retry_and_selects_fastest_valid_alternative():
    plan = select_recovery_route(
        request=request(),
        graph=recovery_graph(),
        options=(
            recovery_option(
                "retry",
                RecoveryMode.RETRY,
                "retry",
                attempts_used=2,
                max_attempts=2,
            ),
            recovery_option(
                "alternate",
                RecoveryMode.ALTERNATE_PROVIDER,
                "alternate",
            ),
            recovery_option(
                "rollback",
                RecoveryMode.ROLLBACK,
                "rollback",
            ),
        ),
    )
    assert plan.safe_halt is False
    assert plan.selected_mode is RecoveryMode.ALTERNATE_PROVIDER
    assert plan.selected_option_id == "alternate"
    assert plan.route_selection.estimated_completion_ms == 20
    assert plan.recovery_pruned[0].reasons == (
        RouteReasonCode.ROUTE_RETRY_EXHAUSTED,
    )


def test_no_valid_recovery_route_returns_safe_halt():
    plan = select_recovery_route(
        request=request(),
        graph=recovery_graph(),
        options=(
            recovery_option(
                "alternate",
                RecoveryMode.ALTERNATE_PROVIDER,
                "alternate",
                available=False,
            ),
        ),
    )
    assert plan.safe_halt is True
    assert RouteReasonCode.ROUTE_RECOVERY_UNAVAILABLE in plan.blockers


def step_up_request(**updates):
    payload = {
        "step_up_id": "step-up-1",
        "route_request_id": "request-1",
        "route_digest": "route:1",
        "route_version": "v1",
        "action_ref": "action:1",
        "action_payload_digest": "payload:1",
        "required_authority_scope": "payments:approve",
        "evidence_refs": ("evidence:route",),
        "requested_at": NOW,
        "deadline": NOW + timedelta(seconds=30),
    }
    payload.update(updates)
    return HumanStepUpRequest(**payload)


def holder(holder_id, scopes, *, available_ms=0, response_ms=0, **updates):
    payload = {
        "holder_id": holder_id,
        "principal_id": f"principal:{holder_id}",
        "authority_scopes": scopes,
        "active": True,
        "available_at": NOW + timedelta(milliseconds=available_ms),
        "mandate_expires_at": NOW + timedelta(hours=1),
        "expected_response_ms": response_ms,
        "evidence_refs": (f"mandate:{holder_id}",),
    }
    payload.update(updates)
    return AuthorityHolder(**payload)


def test_human_step_up_chooses_correct_scope_not_fastest_wrong_person():
    routed = route_human_step_up(
        request=step_up_request(),
        holders=(
            holder("wrong-fast", ("publishing:approve",), response_ms=1),
            holder(
                "correct",
                ("payments:approve",),
                available_ms=2000,
                response_ms=3000,
            ),
        ),
    )
    assert routed.status is HumanRouteStatus.ROUTED
    assert routed.selected_holder_id == "correct"
    assert routed.expected_wait_ms == 5000
    assert routed.approval_node.owner_ref == "principal:correct"


def test_missing_authority_holder_returns_safe_halt():
    routed = route_human_step_up(
        request=step_up_request(),
        holders=(holder("wrong", ("publishing:approve",)),),
    )
    assert routed.status is HumanRouteStatus.SAFE_HALT
    assert routed.blockers == (
        RouteReasonCode.ROUTE_AUTHORITY_HOLDER_UNAVAILABLE,
    )


def test_authorized_holder_after_deadline_returns_defer():
    routed = route_human_step_up(
        request=step_up_request(deadline=NOW + timedelta(seconds=2)),
        holders=(
            holder(
                "correct",
                ("payments:approve",),
                available_ms=3000,
            ),
        ),
    )
    assert routed.status is HumanRouteStatus.DEFER
    assert RouteReasonCode.ROUTE_REQUIRES_STEP_UP in routed.blockers


def test_approval_wait_enters_route_critical_path():
    routed = route_human_step_up(
        request=step_up_request(),
        holders=(
            holder(
                "correct",
                ("payments:approve",),
                response_ms=5000,
            ),
        ),
    )
    approval = routed.approval_node
    graph = RouteGraph(
        graph_id="step-up-route",
        graph_version="1",
        target_node_id="execute",
        nodes=(
            approval,
            RouteNode(
                node_id="execute",
                kind=RouteNodeKind.EXECUTION,
                estimate=RouteEstimate(execution_ms=100),
            ),
        ),
        edges=(RouteEdge(source=approval.node_id, target="execute"),),
    )
    selection = select_fastest_valid_route(
        request(),
        graph,
        (
            RouteCandidate(
                candidate_id="step-up-candidate",
                node_ids=(approval.node_id, "execute"),
            ),
        ),
    )
    assert selection.estimated_completion_ms == 5100
    assert selection.critical_path == (approval.node_id, "execute")


def test_authority_holder_requires_scope_and_evidence():
    with pytest.raises(ValidationError, match="requires evidence"):
        holder(
            "missing-evidence",
            ("payments:approve",),
            evidence_refs=(),
        )
    with pytest.raises(ValidationError, match="at least one scope"):
        holder("missing-scope", (), evidence_refs=("mandate:1",))
