from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import ValidationError

from src.valo_platform.action_envelope.receipt_ledger import (
    ReceiptLedgerError,
    SQLiteReceiptLedger,
    TrustedReceiptIssuer,
    ZERO_HASH,
)
from src.valo_platform.route_optimization import (
    ObservedEstimateComponents,
    RouteCandidate,
    RouteEstimate,
    RouteGraph,
    RouteNode,
    RouteNodeKind,
    RouteRequest,
    RouteWorkMeasurement,
    SelectionStatus,
    append_route_planning_receipt,
    append_verified_route_outcome,
    compare_route_work,
    propose_estimate_update,
    seal_route_planning_receipt,
    seal_verified_route_outcome,
    select_fastest_valid_route,
)


NOW = datetime(2026, 7, 27, 7, 20, tzinfo=timezone.utc)


def make_request():
    return RouteRequest(
        route_request_id="request-1",
        principal_id="principal-1",
        purpose_ref="purpose-1",
        intent_digest="sha256:intent",
        semantic_state_digest="sha256:semantic",
        target_outcome_ref="outcome-1",
        current_state_digest="sha256:state",
        authority_snapshot_hash="sha256:authority",
        policy_snapshot_hash="sha256:policy",
        context_snapshot_hash="sha256:context",
        as_of=NOW,
        estimate_set_version="estimate-v1",
    )


def make_route():
    request = make_request()
    graph = RouteGraph(
        graph_id="graph-1",
        graph_version="route-v1",
        target_node_id="target",
        nodes=(
            RouteNode(
                node_id="target",
                kind=RouteNodeKind.OUTCOME,
                estimate=RouteEstimate(
                    execution_ms=25,
                    cost_microunits=100,
                    evidence_strength=90,
                    version="estimate-v1",
                ),
            ),
        ),
    )
    candidate = RouteCandidate(
        candidate_id="candidate-1",
        node_ids=("target",),
        valid_until=NOW + timedelta(minutes=30),
    )
    selection = select_fastest_valid_route(request, graph, (candidate,))
    assert selection.status is SelectionStatus.SELECTED
    return request, graph, selection


def issuer(key):
    return TrustedReceiptIssuer(
        issuer_id="route-receipt-issuer",
        issuer_role="RECEIPT_ISSUER",
        key_id="key:route:1",
        tenant_id="tenant-1",
        trust_domain="trust:route",
        public_key=key.public_key(),
    )


def make_work(source_ref="observed-run"):
    return RouteWorkMeasurement(
        evaluated_nodes=3,
        model_calls=1,
        tool_calls=1,
        context_units=500,
        governance_evaluations=2,
        completion_ms=80,
        total_cost_microunits=120,
        human_wait_ms=10,
        retry_count=0,
        replan_count=0,
        rollback_count=0,
        source_ref=source_ref,
    )


def make_outcome(previous_receipt_hash=ZERO_HASH):
    return seal_verified_route_outcome(
        outcome_id="outcome-receipt-1",
        tenant_id="tenant-1",
        execution_id="execution-1",
        route_request_id="request-1",
        route_digest="sha256:route",
        route_commit_binding_digest="sha256:route-commit",
        intended_outcome_ref="outcome-1",
        success=True,
        observed_at=NOW + timedelta(minutes=1),
        work_measurement=make_work(),
        estimate_components=ObservedEstimateComponents(
            execution_ms=80,
            queue_ms=10,
            human_wait_ms=10,
            retry_ms=0,
            rollback_ms=0,
            cost_microunits=120,
        ),
        evidence_refs=("evidence:result", "evidence:execution"),
        verifier_id="outcome-verifier-1",
        verification_method="independent-evidence-check",
        previous_receipt_hash=previous_receipt_hash,
    )


def test_planning_receipt_records_selection_without_clearance_language():
    request, graph, selection = make_route()
    receipt = seal_route_planning_receipt(
        receipt_id="planning-receipt-1",
        tenant_id="tenant-1",
        execution_id="execution-1",
        route_request_fingerprint=request.fingerprint,
        graph_fingerprint=graph.fingerprint,
        selection=selection,
        input_candidate_count=1,
        previous_receipt_hash=ZERO_HASH,
        issued_at=NOW,
    )
    assert receipt.receipt_digest == receipt.computed_digest
    assert receipt.metrics.active_candidate_count == 1
    assert receipt.metrics.pruned_candidate_count == 0
    dumped = receipt.model_dump(mode="json")
    assert "clearance" not in dumped
    assert "authority" not in dumped
    assert "allow" not in dumped


def test_signed_planning_and_outcome_receipts_share_existing_ledger(tmp_path):
    key = Ed25519PrivateKey.generate()
    trusted = issuer(key)
    ledger = SQLiteReceiptLedger(tmp_path / "route-receipts.db")
    request, graph, selection = make_route()
    planning = seal_route_planning_receipt(
        receipt_id="planning-receipt-1",
        tenant_id="tenant-1",
        execution_id="execution-1",
        route_request_fingerprint=request.fingerprint,
        graph_fingerprint=graph.fingerprint,
        selection=selection,
        input_candidate_count=1,
        previous_receipt_hash=ZERO_HASH,
        issued_at=NOW,
    )
    planning_entry = append_route_planning_receipt(
        ledger=ledger,
        receipt=planning,
        private_key=key,
        trusted_issuer=trusted,
        expires_at=NOW + timedelta(days=30),
        recorded_at=NOW,
    )
    outcome = make_outcome(planning_entry.artifact_digest)
    append_verified_route_outcome(
        ledger=ledger,
        outcome=outcome,
        private_key=key,
        trusted_issuer=trusted,
        expires_at=NOW + timedelta(days=30),
        recorded_at=NOW + timedelta(minutes=1),
    )

    ledger.verify_chain("tenant-1")
    dossier = ledger.export_dossier(
        tenant_id="tenant-1",
        execution_id="execution-1",
        required_artifact_types={
            "ROUTE_PLANNING_RECEIPT",
            "ROUTE_OUTCOME_RECEIPT",
        },
    )
    assert dossier["artifact_count"] == 2
    assert [item["artifact_type"] for item in dossier["artifacts"]] == [
        "ROUTE_PLANNING_RECEIPT",
        "ROUTE_OUTCOME_RECEIPT",
    ]


def test_duplicate_route_receipt_is_rejected_by_existing_ledger(tmp_path):
    key = Ed25519PrivateKey.generate()
    trusted = issuer(key)
    ledger = SQLiteReceiptLedger(tmp_path / "route-receipts.db")
    request, graph, selection = make_route()
    receipt = seal_route_planning_receipt(
        receipt_id="planning-receipt-1",
        tenant_id="tenant-1",
        execution_id="execution-1",
        route_request_fingerprint=request.fingerprint,
        graph_fingerprint=graph.fingerprint,
        selection=selection,
        input_candidate_count=1,
        previous_receipt_hash=ZERO_HASH,
        issued_at=NOW,
    )
    kwargs = dict(
        ledger=ledger,
        receipt=receipt,
        private_key=key,
        trusted_issuer=trusted,
        expires_at=NOW + timedelta(days=30),
        recorded_at=NOW,
    )
    append_route_planning_receipt(**kwargs)
    with pytest.raises(ReceiptLedgerError, match="already exists"):
        append_route_planning_receipt(**kwargs)


def test_efficiency_delta_requires_measured_baseline_and_keeps_signed_deltas():
    baseline = RouteWorkMeasurement(
        evaluated_nodes=12,
        model_calls=5,
        tool_calls=4,
        context_units=2000,
        governance_evaluations=6,
        completion_ms=200,
        total_cost_microunits=500,
        source_ref="baseline-run",
    )
    observed = make_work()
    delta = compare_route_work(baseline, observed)
    assert delta.evaluated_nodes_delta == 9
    assert delta.model_calls_delta == 4
    assert delta.context_units_delta == 1500
    assert delta.completion_ms_delta == 120
    assert delta.total_cost_microunits_delta == 380
    assert delta.work_reduced is True
    assert delta.measured_faster is True
    assert delta.measured_lower_cost is True
    assert delta.delta_digest == delta.computed_digest


def test_metrics_do_not_claim_improvement_when_observed_is_worse():
    baseline = make_work("baseline")
    observed = RouteWorkMeasurement(
        evaluated_nodes=4,
        model_calls=2,
        tool_calls=2,
        context_units=700,
        governance_evaluations=3,
        completion_ms=100,
        total_cost_microunits=150,
        source_ref="observed",
    )
    delta = compare_route_work(baseline, observed)
    assert delta.work_reduced is False
    assert delta.measured_faster is False
    assert delta.measured_lower_cost is False
    assert delta.completion_ms_delta == -20


def test_verified_outcome_requires_evidence():
    with pytest.raises(ValidationError, match="evidence references"):
        seal_verified_route_outcome(
            outcome_id="outcome-receipt-1",
            tenant_id="tenant-1",
            execution_id="execution-1",
            route_request_id="request-1",
            route_digest="sha256:route",
            route_commit_binding_digest="sha256:route-commit",
            intended_outcome_ref="outcome-1",
            success=True,
            observed_at=NOW,
            work_measurement=make_work(),
            estimate_components=ObservedEstimateComponents(
                execution_ms=80,
                cost_microunits=120,
            ),
            evidence_refs=(),
            verifier_id="verifier",
            verification_method="evidence-check",
            previous_receipt_hash=ZERO_HASH,
        )


def test_estimate_update_is_performance_only_and_deterministic():
    previous = RouteEstimate(
        execution_ms=100,
        queue_ms=20,
        human_wait_ms=30,
        expected_retry_ms=10,
        expected_rollback_ms=10,
        cost_microunits=200,
        risk_exposure=40,
        reversibility=80,
        evidence_strength=75,
        confidence=0.7,
        source_ref="baseline",
        version="v1",
    )
    outcome = make_outcome()
    proposal = propose_estimate_update(
        proposal_id="proposal-1",
        previous=previous,
        outcome=outcome,
        learning_rate_bps=5000,
    )
    updated = proposal.proposed_estimate
    assert updated.execution_ms == 90
    assert updated.queue_ms == 15
    assert updated.human_wait_ms == 20
    assert updated.expected_retry_ms == 5
    assert updated.expected_rollback_ms == 5
    assert updated.cost_microunits == 160
    assert updated.risk_exposure == previous.risk_exposure
    assert updated.reversibility == previous.reversibility
    assert updated.evidence_strength == previous.evidence_strength
    assert updated.confidence == previous.confidence
    assert proposal.authority_effect == "none"
    assert proposal.policy_effect == "none"
    assert proposal.route_validity_effect == "none"
    assert proposal.clearance_effect == "none"
    assert proposal.proposal_digest == proposal.computed_digest
    assert proposal == propose_estimate_update(
        proposal_id="proposal-1",
        previous=previous,
        outcome=outcome,
        learning_rate_bps=5000,
    )


def test_tampered_outcome_cannot_update_estimates_or_enter_ledger(tmp_path):
    key = Ed25519PrivateKey.generate()
    trusted = issuer(key)
    ledger = SQLiteReceiptLedger(tmp_path / "route-receipts.db")
    outcome = make_outcome().model_copy(update={"outcome_digest": "tampered"})
    previous = RouteEstimate(execution_ms=100)

    with pytest.raises(ValueError, match="outcome digest mismatch"):
        propose_estimate_update(
            proposal_id="proposal-1",
            previous=previous,
            outcome=outcome,
        )
    with pytest.raises(ValueError, match="outcome digest mismatch"):
        append_verified_route_outcome(
            ledger=ledger,
            outcome=outcome,
            private_key=key,
            trusted_issuer=trusted,
            expires_at=NOW + timedelta(days=30),
        )


def test_planning_receipt_tenant_must_match_issuer(tmp_path):
    key = Ed25519PrivateKey.generate()
    trusted = issuer(key)
    ledger = SQLiteReceiptLedger(tmp_path / "route-receipts.db")
    request, graph, selection = make_route()
    receipt = seal_route_planning_receipt(
        receipt_id="planning-receipt-1",
        tenant_id="other-tenant",
        execution_id="execution-1",
        route_request_fingerprint=request.fingerprint,
        graph_fingerprint=graph.fingerprint,
        selection=selection,
        input_candidate_count=1,
        previous_receipt_hash=ZERO_HASH,
        issued_at=NOW,
    )
    with pytest.raises(ValueError, match="tenant differs"):
        append_route_planning_receipt(
            ledger=ledger,
            receipt=receipt,
            private_key=key,
            trusted_issuer=trusted,
            expires_at=NOW + timedelta(days=30),
        )
