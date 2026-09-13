from datetime import datetime, timedelta, timezone

import pytest

from src.valo_platform.governance.pre_execution import (
    Decision,
    GovernanceSignal,
    PreExecutionPipeline,
)
from src.valo_platform.governance.reht_racs_binding import REHTRACSBinding
from src.valo_platform.route_optimization import (
    RouteCandidate,
    RouteEstimate,
    RouteGraph,
    RouteNode,
    RouteNodeKind,
    RouteRequest,
    SelectionStatus,
    select_fastest_valid_route,
)
from src.valo_platform.route_optimization.integrations.execution_binding import (
    RouteBoundClearanceInput,
    RouteBoundClearanceReceipt,
    RouteBoundCommitEnvelope,
    assert_route_bound_commit,
    bind_route_to_clearance,
    clear_route_bound_input,
    create_route_bound_commit,
    verify_route_bound_commit,
)


NOW = datetime(2026, 7, 27, 7, 15, tzinfo=timezone.utc)


def make_request(**updates):
    payload = {
        "route_request_id": "route-request-1",
        "principal_id": "principal-1",
        "purpose_ref": "purpose-1",
        "intent_digest": "sha256:intent",
        "semantic_state_digest": "sha256:semantic",
        "target_outcome_ref": "outcome-1",
        "current_state_digest": "sha256:state",
        "authority_snapshot_hash": "sha256:mandate",
        "policy_snapshot_hash": "sha256:policy",
        "context_snapshot_hash": "sha256:context",
        "as_of": NOW,
        "estimate_set_version": "estimate-v1",
    }
    payload.update(updates)
    return RouteRequest(**payload)


def make_selection(request=None, *, valid_until=None):
    request = request or make_request()
    graph = RouteGraph(
        graph_id="execution-route",
        graph_version="route-v1",
        target_node_id="execute",
        nodes=(
            RouteNode(
                node_id="execute",
                kind=RouteNodeKind.EXECUTION,
                estimate=RouteEstimate(
                    execution_ms=5,
                    evidence_strength=100,
                    version="estimate-v1",
                ),
                mandatory_governance=True,
            ),
        ),
    )
    candidate = RouteCandidate(
        candidate_id="candidate-1",
        node_ids=("execute",),
        valid_until=valid_until or NOW + timedelta(minutes=20),
    )
    selection = select_fastest_valid_route(request, graph, (candidate,))
    assert selection.status is SelectionStatus.SELECTED
    assert selection.active_frontier == ("execute",)
    return selection


def make_clearance_input(
    request=None,
    *,
    decision=Decision.ALLOW,
    action_ref="action:1",
    issued_at=None,
    expires_at=None,
):
    request = request or make_request()
    evaluation = PreExecutionPipeline().evaluate(
        action_ref=action_ref,
        mandate_digest=request.authority_snapshot_hash,
        context_digest=request.context_snapshot_hash,
        commitment_digest="sha256:commitment",
        consequential=True,
        signals=(
            GovernanceSignal(
                name="vaig",
                decision=decision,
                evidence_digest="sha256:vaig-evidence",
            ),
        ),
    )
    binding = REHTRACSBinding()
    clearance_input = binding.derive_clearance_input(
        evaluation=evaluation,
        evaluation_issued_at=(issued_at or NOW - timedelta(minutes=1)).isoformat(),
        evaluation_expires_at=(expires_at or NOW + timedelta(minutes=10)).isoformat(),
        now=NOW.isoformat(),
    )
    return binding, clearance_input


def make_bound_chain(*, decision=Decision.ALLOW, action_payload=None):
    request = make_request()
    selection = make_selection(request)
    binding, clearance_input = make_clearance_input(
        request,
        decision=decision,
    )
    payload = action_payload or {"recipient": "person-1", "amount": 10}
    route_input = bind_route_to_clearance(
        selection=selection,
        request=request,
        route_version="route-v1",
        route_step_id="execute",
        action_payload=payload,
        reht_clearance_input=clearance_input,
        now=NOW,
    )
    reht_receipt, route_receipt = clear_route_bound_input(
        route_input=route_input,
        reht_clearance_input=clearance_input,
        binding=binding,
        consumed_replay_keys=set(),
        now=NOW,
    )
    return (
        request,
        selection,
        binding,
        clearance_input,
        payload,
        route_input,
        reht_receipt,
        route_receipt,
    )


def test_happy_path_binds_route_clearance_and_commit_separately():
    (
        request,
        selection,
        binding,
        clearance_input,
        payload,
        route_input,
        reht_receipt,
        route_receipt,
    ) = make_bound_chain()

    racs_commit, route_commit = create_route_bound_commit(
        route_input=route_input,
        route_receipt=route_receipt,
        reht_clearance_input=clearance_input,
        reht_receipt=reht_receipt,
        binding=binding,
    )

    assert isinstance(route_input, RouteBoundClearanceInput)
    assert isinstance(route_receipt, RouteBoundClearanceReceipt)
    assert isinstance(route_commit, RouteBoundCommitEnvelope)
    assert route_receipt.receipt_digest != reht_receipt.clearance_digest
    assert route_commit.commit_binding_digest != racs_commit.commit_digest
    assert verify_route_bound_commit(
        route_commit=route_commit,
        racs_commit=racs_commit,
        selection=selection,
        request=request,
        route_version="route-v1",
        route_step_id="execute",
        action_ref="action:1",
        action_payload=payload,
        now=NOW,
    )


def test_route_step_must_be_current_active_frontier():
    request = make_request()
    selection = make_selection(request)
    _, clearance_input = make_clearance_input(request)

    with pytest.raises(ValueError, match="active frontier"):
        bind_route_to_clearance(
            selection=selection,
            request=request,
            route_version="route-v1",
            route_step_id="later-step",
            action_payload={"value": 1},
            reht_clearance_input=clearance_input,
            now=NOW,
        )


def test_reht_context_and_mandate_must_match_route_request():
    request = make_request()
    selection = make_selection(request)
    wrong_context_request = make_request(
        context_snapshot_hash="sha256:other-context"
    )
    _, clearance_input = make_clearance_input(wrong_context_request)

    with pytest.raises(ValueError, match="context digest"):
        bind_route_to_clearance(
            selection=selection,
            request=request,
            route_version="route-v1",
            route_step_id="execute",
            action_payload={"value": 1},
            reht_clearance_input=clearance_input,
            now=NOW,
        )


def test_changed_payload_is_rejected_at_execution():
    (
        request,
        selection,
        binding,
        clearance_input,
        payload,
        route_input,
        reht_receipt,
        route_receipt,
    ) = make_bound_chain()
    racs_commit, route_commit = create_route_bound_commit(
        route_input=route_input,
        route_receipt=route_receipt,
        reht_clearance_input=clearance_input,
        reht_receipt=reht_receipt,
        binding=binding,
    )

    assert not verify_route_bound_commit(
        route_commit=route_commit,
        racs_commit=racs_commit,
        selection=selection,
        request=request,
        route_version="route-v1",
        route_step_id="execute",
        action_ref="action:1",
        action_payload={**payload, "amount": 11},
        now=NOW,
    )


def test_changed_state_invalidates_existing_route_commit():
    (
        request,
        selection,
        binding,
        clearance_input,
        payload,
        route_input,
        reht_receipt,
        route_receipt,
    ) = make_bound_chain()
    racs_commit, route_commit = create_route_bound_commit(
        route_input=route_input,
        route_receipt=route_receipt,
        reht_clearance_input=clearance_input,
        reht_receipt=reht_receipt,
        binding=binding,
    )
    changed_request = make_request(
        current_state_digest="sha256:changed-state"
    )

    assert not verify_route_bound_commit(
        route_commit=route_commit,
        racs_commit=racs_commit,
        selection=selection,
        request=changed_request,
        route_version="route-v1",
        route_step_id="execute",
        action_ref="action:1",
        action_payload=payload,
        now=NOW,
    )


def test_replanned_route_digest_invalidates_existing_commit():
    (
        request,
        selection,
        binding,
        clearance_input,
        payload,
        route_input,
        reht_receipt,
        route_receipt,
    ) = make_bound_chain()
    racs_commit, route_commit = create_route_bound_commit(
        route_input=route_input,
        route_receipt=route_receipt,
        reht_clearance_input=clearance_input,
        reht_receipt=reht_receipt,
        binding=binding,
    )
    replanned = selection.model_copy(update={"route_digest": "sha256:new-route"})

    assert not verify_route_bound_commit(
        route_commit=route_commit,
        racs_commit=racs_commit,
        selection=replanned,
        request=request,
        route_version="route-v1",
        route_step_id="execute",
        action_ref="action:1",
        action_payload=payload,
        now=NOW,
    )


def test_action_substitution_is_rejected():
    (
        request,
        selection,
        binding,
        clearance_input,
        payload,
        route_input,
        reht_receipt,
        route_receipt,
    ) = make_bound_chain()
    racs_commit, route_commit = create_route_bound_commit(
        route_input=route_input,
        route_receipt=route_receipt,
        reht_clearance_input=clearance_input,
        reht_receipt=reht_receipt,
        binding=binding,
    )

    with pytest.raises(ValueError, match="execution differs"):
        assert_route_bound_commit(
            route_commit=route_commit,
            racs_commit=racs_commit,
            selection=selection,
            request=request,
            route_version="route-v1",
            route_step_id="execute",
            action_ref="action:substituted",
            action_payload=payload,
            now=NOW,
        )


def test_expired_route_binding_is_rejected_before_clearance():
    request = make_request()
    selection = make_selection(
        request,
        valid_until=NOW + timedelta(seconds=30),
    )
    binding, clearance_input = make_clearance_input(request)
    route_input = bind_route_to_clearance(
        selection=selection,
        request=request,
        route_version="route-v1",
        route_step_id="execute",
        action_payload={"value": 1},
        reht_clearance_input=clearance_input,
        now=NOW,
    )

    with pytest.raises(ValueError, match="expired"):
        clear_route_bound_input(
            route_input=route_input,
            reht_clearance_input=clearance_input,
            binding=binding,
            consumed_replay_keys=set(),
            now=NOW + timedelta(minutes=1),
        )


def test_tampered_route_binding_digest_is_rejected():
    request = make_request()
    selection = make_selection(request)
    binding, clearance_input = make_clearance_input(request)
    route_input = bind_route_to_clearance(
        selection=selection,
        request=request,
        route_version="route-v1",
        route_step_id="execute",
        action_payload={"value": 1},
        reht_clearance_input=clearance_input,
        now=NOW,
    ).model_copy(update={"binding_digest": "tampered"})

    with pytest.raises(ValueError, match="binding digest mismatch"):
        clear_route_bound_input(
            route_input=route_input,
            reht_clearance_input=clearance_input,
            binding=binding,
            consumed_replay_keys=set(),
            now=NOW,
        )


def test_replayed_clearance_input_is_rejected_by_existing_reht_binding():
    request = make_request()
    selection = make_selection(request)
    binding, clearance_input = make_clearance_input(request)
    route_input = bind_route_to_clearance(
        selection=selection,
        request=request,
        route_version="route-v1",
        route_step_id="execute",
        action_payload={"value": 1},
        reht_clearance_input=clearance_input,
        now=NOW,
    )
    consumed = set()
    clear_route_bound_input(
        route_input=route_input,
        reht_clearance_input=clearance_input,
        binding=binding,
        consumed_replay_keys=consumed,
        now=NOW,
    )

    with pytest.raises(ValueError, match="replayed"):
        clear_route_bound_input(
            route_input=route_input,
            reht_clearance_input=clearance_input,
            binding=binding,
            consumed_replay_keys=consumed,
            now=NOW,
        )


def test_non_executable_reht_decision_cannot_create_racs_commit():
    (
        _,
        _,
        binding,
        clearance_input,
        _,
        route_input,
        reht_receipt,
        route_receipt,
    ) = make_bound_chain(decision=Decision.DENY)
    assert reht_receipt.executable is False
    assert route_receipt.executable is False

    with pytest.raises(ValueError, match="not executable"):
        create_route_bound_commit(
            route_input=route_input,
            route_receipt=route_receipt,
            reht_clearance_input=clearance_input,
            reht_receipt=reht_receipt,
            binding=binding,
        )
