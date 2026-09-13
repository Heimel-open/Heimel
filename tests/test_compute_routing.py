from __future__ import annotations

from valo_kernel.contracts.compute_routing import RouteOutcome
from valo_kernel.kernel.compute_routing import (
    assess_compute_route,
    seal_compute_node_profile,
    seal_compute_route_candidate,
    seal_compute_route_request,
)
from valo_kernel.kernel.model_portability import (
    assess_model_portability,
    seal_hardware_capability_profile,
    seal_portable_model_artifact,
    seal_semantic_equivalence_evidence,
)


def _model():
    return seal_portable_model_artifact(
        model_id="personal-model-1",
        format_id="portable-ir.v1",
        graph_digest="a" * 64,
        weights_digest="b" * 64,
        metadata_digest="c" * 64,
        semantic_contract_digest="d" * 64,
        required_operators=("attention", "matmul"),
        allowed_precisions=("FP16", "INT8"),
        minimum_memory_bytes=1_000_000,
        reference_backend_id="cpu-reference",
    )


def _portability(model):
    capability = seal_hardware_capability_profile(
        backend_id="edge-npu-a",
        hardware_class="NPU",
        supported_formats=("portable-ir.v1",),
        supported_operators=("attention", "matmul"),
        supported_precisions=("FP16",),
        available_memory_bytes=4_000_000,
        trust_root_ids=("root-a",),
        cpu_fallback_available=False,
    )
    evidence = seal_semantic_equivalence_evidence(
        evidence_id="eq-1",
        portable_model_digest=model.artifact_digest,
        reference_backend_id=model.reference_backend_id,
        candidate_backend_id=capability.backend_id,
        test_suite_digest="e" * 64,
        tolerance_profile_digest="f" * 64,
        passed=True,
    )
    return assess_model_portability(
        model,
        capability,
        equivalence_evidence=evidence,
    )


def _node(model):
    return seal_compute_node_profile(
        node_id="node-a",
        provider_id="provider-a",
        backend_id="edge-npu-a",
        trust_domain="local",
        locality="on-body",
        capability_classes=("reasoning",),
        supported_model_digests=(model.artifact_digest,),
        latency_budget_ms=50,
        cost_ceiling_minor_units=5,
        allows_raw_personal_data=False,
    )


def _request(model, **updates):
    values = {
        "request_id": "route-request-1",
        "tenant_id": "tenant-a",
        "principal_id": "principal-1",
        "purpose_id": "purpose-1",
        "workload_digest": "1" * 64,
        "portable_model_digest": model.artifact_digest,
        "required_capabilities": ("reasoning",),
        "allowed_provider_ids": ("provider-a", "provider-b"),
        "allowed_trust_domains": ("local", "home"),
        "max_latency_ms": 75,
        "max_cost_minor_units": 10,
        "raw_personal_data_required": False,
        "source_state_root": "2" * 64,
    }
    values.update(updates)
    return seal_compute_route_request(**values)


def _candidate(request, node, portability, **updates):
    values = {
        "candidate_id": "candidate-node-a",
        "request_digest": request.request_digest,
        "node_profile_digest": node.profile_digest,
        "node_id": node.node_id,
        "provider_id": node.provider_id,
        "backend_id": node.backend_id,
        "predicted_latency_ms": 20,
        "predicted_cost_minor_units": 2,
        "model_portability_assessment_digest": portability.assessment_digest,
    }
    values.update(updates)
    return seal_compute_route_candidate(**values)


def test_route_admission_passes_without_choosing_provider() -> None:
    model = _model()
    portability = _portability(model)
    node = _node(model)
    request = _request(model)
    candidate = _candidate(request, node, portability)

    result = assess_compute_route(
        request,
        candidate,
        node,
        portability,
        current_state_root=request.source_state_root,
    )

    assert result.outcome is RouteOutcome.PASS
    assert result.chooses_provider is False
    assert result.can_issue_clearance is False


def test_route_denies_stale_authoritative_state() -> None:
    model = _model()
    portability = _portability(model)
    node = _node(model)
    request = _request(model)
    candidate = _candidate(request, node, portability)

    result = assess_compute_route(
        request,
        candidate,
        node,
        portability,
        current_state_root="9" * 64,
    )

    assert result.outcome is RouteOutcome.DENY
    assert "STALE_STATE" in {item.code for item in result.mismatches}


def test_route_denies_provider_outside_policy() -> None:
    model = _model()
    portability = _portability(model)
    node = _node(model)
    request = _request(model, allowed_provider_ids=("provider-b",))
    candidate = _candidate(request, node, portability)

    result = assess_compute_route(
        request,
        candidate,
        node,
        portability,
        current_state_root=request.source_state_root,
    )

    assert result.outcome is RouteOutcome.DENY
    assert "PROVIDER_NOT_ALLOWED" in {item.code for item in result.mismatches}


def test_route_denies_latency_overshoot() -> None:
    model = _model()
    portability = _portability(model)
    node = _node(model)
    request = _request(model)
    candidate = _candidate(
        request,
        node,
        portability,
        predicted_latency_ms=100,
    )

    result = assess_compute_route(
        request,
        candidate,
        node,
        portability,
        current_state_root=request.source_state_root,
    )

    codes = {item.code for item in result.mismatches}
    assert result.outcome is RouteOutcome.DENY
    assert "REQUEST_LATENCY" in codes
    assert "NODE_LATENCY" in codes


def test_raw_personal_data_requires_disclosure_assessment() -> None:
    model = _model()
    portability = _portability(model)
    node = seal_compute_node_profile(
        node_id="node-a",
        provider_id="provider-a",
        backend_id="edge-npu-a",
        trust_domain="local",
        locality="on-body",
        capability_classes=("reasoning",),
        supported_model_digests=(model.artifact_digest,),
        latency_budget_ms=50,
        cost_ceiling_minor_units=5,
        allows_raw_personal_data=True,
    )
    request = _request(
        model,
        raw_personal_data_required=True,
        disclosure_authorization_digest="3" * 64,
    )
    candidate = _candidate(request, node, portability)

    result = assess_compute_route(
        request,
        candidate,
        node,
        portability,
        current_state_root=request.source_state_root,
    )

    assert result.outcome is RouteOutcome.DENY
    assert "DISCLOSURE_MISSING" in {item.code for item in result.mismatches}
