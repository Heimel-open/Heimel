from datetime import datetime, timedelta, timezone

from src.valo_platform.action_envelope.mal_registry import (
    seal_invocation_binding,
    sign_approval_record,
)
from src.valo_platform.api.schemas_governance import GovernanceEvaluationResponse
from src.valo_platform.route_optimization import (
    RouteCandidate,
    RouteGraph,
    RouteNode,
    RouteNodeKind,
    RouteReasonCode,
    RouteRequest,
    SelectionStatus,
    select_fastest_valid_route,
)
from src.valo_platform.route_optimization.integrations.governance_inputs import (
    apply_governance_inputs,
    build_governance_input_snapshot,
    governance_inputs_changed,
)
from src.valo_platform.sol.context import (
    ContextItem,
    ProvenanceRef,
    RetentionPolicy,
    Sensitivity,
    seal_context_envelope,
    value_hash,
)


NOW = datetime(2026, 7, 27, tzinfo=timezone.utc)
SECRET = b"route-governance-input-test-secret"


def make_sol_context(
    *,
    purpose="purpose",
    sensitivity=Sensitivity.INTERNAL,
    consent_ref=None,
    permission_refs=("permission:1",),
    expires_at=None,
):
    value = {"original_language": "norsk", "meaning": "bevar original mening"}
    item = ContextItem(
        item_id="context-item-1",
        key="semantic-input",
        value=value,
        value_hash=value_hash(value),
        provenance=(
            ProvenanceRef(
                source_id="source-1",
                source_type="document",
                source_hash="sha256:source",
                captured_at=NOW - timedelta(minutes=1),
            ),
        ),
        sensitivity=sensitivity,
        purpose=purpose,
        valid_from=NOW - timedelta(minutes=1),
        valid_until=NOW + timedelta(hours=2),
        consent_ref=consent_ref,
        retention=RetentionPolicy(
            policy_id="retention-1",
            retain_until=NOW + timedelta(days=1),
        ),
    )
    return seal_context_envelope(
        envelope_id="sol-envelope-1",
        tenant_id="tenant-1",
        mission_id="mission-1",
        branch="main",
        sequence=1,
        created_at=NOW - timedelta(minutes=1),
        created_by="sol",
        purpose=purpose,
        items=(item,),
        permission_refs=permission_refs,
        expires_at=expires_at or NOW + timedelta(hours=1),
        parent_hash=None,
    )


def make_request(sol_hash, **updates):
    payload = {
        "route_request_id": "request-1",
        "principal_id": "principal-1",
        "purpose_ref": "purpose",
        "intent_digest": "sha256:intent",
        "semantic_state_digest": "sha256:semantic",
        "target_outcome_ref": "outcome",
        "current_state_digest": "sha256:state",
        "authority_snapshot_hash": "sha256:authority",
        "policy_snapshot_hash": "sha256:policy",
        "context_snapshot_hash": sol_hash,
        "max_risk_exposure": 40,
        "as_of": NOW,
    }
    payload.update(updates)
    return RouteRequest(**payload)


def make_mal(sol_hash, *, approval_hash="sha256:approval", invocation_id="inv-1"):
    approval = sign_approval_record(
        secret=SECRET,
        record_id="approval-1",
        approval_payload_hash=approval_hash,
        issuer="mal",
        key_id="key-1",
        issued_at=NOW - timedelta(minutes=1),
        expires_at=NOW + timedelta(hours=1),
    )
    binding = seal_invocation_binding(
        binding_id="binding-1",
        invocation_id=invocation_id,
        mal_clearance_id="mal-clearance-1",
        approval_hash=approval_hash,
        checkpoint_hash="sha256:checkpoint",
        runtime_profile_hash="sha256:runtime",
        sol_context_hash=sol_hash,
        prompt_hash="sha256:prompt",
        tool_manifest_hash="sha256:tools",
        provider_endpoint_hash="sha256:endpoint",
        created_at=NOW - timedelta(minutes=1),
        expires_at=NOW + timedelta(minutes=30),
    )
    return approval, binding


def make_vaig(**updates):
    payload = {
        "request_id": "vaig-request-1",
        "receipt_id": "vaig-receipt-1",
        "decision": "ALLOW",
        "confidence": 0.9,
        "evidence_count": 3,
        "narrative": "evaluation evidence",
        "drift_detected": False,
        "timestamp": NOW,
        "metadata": {
            "policy_conformant": True,
            "semantic_integrity_preserved": True,
            "risk_exposure": 20,
        },
    }
    payload.update(updates)
    return GovernanceEvaluationResponse(**payload)


def make_graph_and_candidate():
    graph = RouteGraph(
        graph_id="graph-1",
        graph_version="1",
        target_node_id="target",
        nodes=(
            RouteNode(node_id="target", kind=RouteNodeKind.OUTCOME),
        ),
    )
    return graph, RouteCandidate(candidate_id="candidate-1", node_ids=("target",))


def make_snapshot(
    *,
    sol=None,
    request=None,
    approval=None,
    binding=None,
    vaig=None,
):
    sol = sol or make_sol_context()
    request = request or make_request(sol.envelope_hash)
    if approval is None or binding is None:
        approval, binding = make_mal(sol.envelope_hash)
    return build_governance_input_snapshot(
        request=request,
        sol_context=sol,
        mal_approval=approval,
        mal_binding=binding,
        mal_secret=SECRET,
        vaig_evaluation=vaig or make_vaig(),
        expected_invocation_id="inv-1",
    ), request


def test_valid_governance_inputs_keep_route_selectable():
    snapshot, request = make_snapshot()
    graph, candidate = make_graph_and_candidate()
    bound = apply_governance_inputs(candidate, snapshot, request=request)
    selection = select_fastest_valid_route(request, graph, (bound,))
    assert selection.status is SelectionStatus.SELECTED
    assert selection.selected_candidate_id == "candidate-1"
    assert all(constraint.satisfied for constraint in snapshot.constraints)


def test_allow_text_does_not_override_failed_vaig_policy():
    vaig = make_vaig(
        decision="ALLOW",
        metadata={
            "policy_conformant": False,
            "semantic_integrity_preserved": True,
            "risk_exposure": 20,
        },
    )
    snapshot, request = make_snapshot(vaig=vaig)
    graph, candidate = make_graph_and_candidate()
    bound = apply_governance_inputs(candidate, snapshot, request=request)
    selection = select_fastest_valid_route(request, graph, (bound,))
    assert selection.status is SelectionStatus.NO_ROUTE
    assert RouteReasonCode.ROUTE_POLICY_INVALID in selection.blockers


def test_sol_context_hash_drift_invalidates_route():
    sol = make_sol_context()
    request = make_request("sha256:different-context")
    approval, binding = make_mal(sol.envelope_hash)
    snapshot, _ = make_snapshot(
        sol=sol,
        request=request,
        approval=approval,
        binding=binding,
    )
    graph, candidate = make_graph_and_candidate()
    bound = apply_governance_inputs(candidate, snapshot, request=request)
    selection = select_fastest_valid_route(request, graph, (bound,))
    assert selection.status is SelectionStatus.NO_ROUTE
    assert RouteReasonCode.ROUTE_EVIDENCE_INSUFFICIENT in selection.blockers


def test_confidential_context_without_consent_fails_closed():
    sol = make_sol_context(
        sensitivity=Sensitivity.CONFIDENTIAL,
        consent_ref=None,
    )
    snapshot, request = make_snapshot(sol=sol)
    graph, candidate = make_graph_and_candidate()
    bound = apply_governance_inputs(candidate, snapshot, request=request)
    selection = select_fastest_valid_route(request, graph, (bound,))
    assert selection.status is SelectionStatus.NO_ROUTE
    assert RouteReasonCode.ROUTE_CONSENT_INVALID in selection.blockers


def test_mal_runtime_binding_mismatch_invalidates_route():
    sol = make_sol_context()
    request = make_request(sol.envelope_hash)
    approval, binding = make_mal("sha256:wrong-sol-context")
    snapshot, _ = make_snapshot(
        sol=sol,
        request=request,
        approval=approval,
        binding=binding,
    )
    graph, candidate = make_graph_and_candidate()
    bound = apply_governance_inputs(candidate, snapshot, request=request)
    selection = select_fastest_valid_route(request, graph, (bound,))
    assert selection.status is SelectionStatus.NO_ROUTE
    assert RouteReasonCode.ROUTE_MAL_INADMISSIBLE in selection.blockers


def test_vaig_semantic_failure_invalidates_route():
    vaig = make_vaig(
        metadata={
            "policy_conformant": True,
            "semantic_integrity_preserved": False,
            "risk_exposure": 20,
        }
    )
    snapshot, request = make_snapshot(vaig=vaig)
    graph, candidate = make_graph_and_candidate()
    bound = apply_governance_inputs(candidate, snapshot, request=request)
    selection = select_fastest_valid_route(request, graph, (bound,))
    assert selection.status is SelectionStatus.NO_ROUTE
    assert RouteReasonCode.ROUTE_SEMANTIC_INTEGRITY_FAILED in selection.blockers


def test_vaig_risk_above_request_limit_invalidates_route():
    vaig = make_vaig(
        metadata={
            "policy_conformant": True,
            "semantic_integrity_preserved": True,
            "risk_exposure": 70,
        }
    )
    snapshot, request = make_snapshot(vaig=vaig)
    graph, candidate = make_graph_and_candidate()
    bound = apply_governance_inputs(candidate, snapshot, request=request)
    selection = select_fastest_valid_route(request, graph, (bound,))
    assert selection.status is SelectionStatus.NO_ROUTE
    assert RouteReasonCode.ROUTE_RISK_EXCEEDED in selection.blockers


def test_snapshot_fingerprint_changes_on_vaig_state_change():
    first, _ = make_snapshot()
    second, _ = make_snapshot(
        vaig=make_vaig(
            receipt_id="vaig-receipt-2",
            confidence=0.8,
        )
    )
    assert governance_inputs_changed(first.fingerprint, second) is True


def test_snapshot_bound_to_old_request_forces_replan():
    snapshot, request = make_snapshot()
    changed_request = make_request(
        request.context_snapshot_hash,
        current_state_digest="sha256:changed-state",
    )
    graph, candidate = make_graph_and_candidate()
    bound = apply_governance_inputs(
        candidate,
        snapshot,
        request=changed_request,
    )
    selection = select_fastest_valid_route(changed_request, graph, (bound,))
    assert selection.status is SelectionStatus.NO_ROUTE
    assert RouteReasonCode.ROUTE_EVIDENCE_INSUFFICIENT in selection.blockers


def test_validity_window_is_minimum_of_bound_artifacts():
    snapshot, _ = make_snapshot()
    assert snapshot.valid_until == NOW + timedelta(minutes=30)
