from __future__ import annotations

from ..contracts.compute_routing import (
    ComputeNodeProfile,
    ComputeRouteAssessment,
    ComputeRouteCandidate,
    ComputeRouteRequest,
    RouteMismatch,
    RouteOutcome,
)
from ..contracts.model_portability import ModelPortabilityAssessment, PortabilityOutcome
from ..contracts.sovereignty import DisclosureAssessment, DisclosureOutcome
from .errors import FailClosedError


def seal_compute_node_profile(**values: object) -> ComputeNodeProfile:
    provisional = ComputeNodeProfile(**values)
    return provisional.model_copy(update={"profile_digest": provisional.computed_digest})


def seal_compute_route_request(**values: object) -> ComputeRouteRequest:
    provisional = ComputeRouteRequest(**values)
    return provisional.model_copy(update={"request_digest": provisional.computed_digest})


def seal_compute_route_candidate(**values: object) -> ComputeRouteCandidate:
    provisional = ComputeRouteCandidate(**values)
    return provisional.model_copy(update={"candidate_digest": provisional.computed_digest})


def assess_compute_route(
    request: ComputeRouteRequest,
    candidate: ComputeRouteCandidate,
    node: ComputeNodeProfile,
    portability: ModelPortabilityAssessment,
    *,
    current_state_root: str,
    disclosure: DisclosureAssessment | None = None,
) -> ComputeRouteAssessment:
    if request.request_digest != request.computed_digest:
        raise FailClosedError("compute route request is unsealed or tampered")
    if candidate.candidate_digest != candidate.computed_digest:
        raise FailClosedError("compute route candidate is unsealed or tampered")
    if node.profile_digest != node.computed_digest:
        raise FailClosedError("compute node profile is unsealed or tampered")
    if portability.assessment_digest != portability.computed_digest:
        raise FailClosedError("model portability assessment is unsealed or tampered")

    mismatches: list[RouteMismatch] = []

    def mismatch(code: str, detail: str) -> None:
        mismatches.append(RouteMismatch(code=code, detail=detail))

    if current_state_root != request.source_state_root:
        mismatch("STALE_STATE", "authoritative state changed before route admission")
    if candidate.request_digest != request.request_digest:
        mismatch("REQUEST_BINDING", "route candidate is bound to another request")
    if candidate.node_profile_digest != node.profile_digest:
        mismatch("NODE_PROFILE_BINDING", "route candidate is bound to another node profile")
    if candidate.node_id != node.node_id:
        mismatch("NODE_BINDING", "candidate node does not match node profile")
    if candidate.provider_id != node.provider_id:
        mismatch("PROVIDER_BINDING", "candidate provider does not match node profile")
    if candidate.backend_id != node.backend_id:
        mismatch("BACKEND_BINDING", "candidate backend does not match node profile")

    if request.allowed_provider_ids and node.provider_id not in request.allowed_provider_ids:
        mismatch("PROVIDER_NOT_ALLOWED", "provider is outside route request allow-list")
    if node.trust_domain not in request.allowed_trust_domains:
        mismatch("TRUST_DOMAIN", "node trust domain is not allowed for this workload")

    missing_capabilities = sorted(
        set(request.required_capabilities) - set(node.capability_classes)
    )
    if missing_capabilities:
        mismatch(
            "CAPABILITY_GAP",
            "node lacks required capabilities: " + ", ".join(missing_capabilities),
        )

    if node.supported_model_digests and request.portable_model_digest not in node.supported_model_digests:
        mismatch("MODEL_NOT_DECLARED", "node does not declare the requested portable model")

    if candidate.predicted_latency_ms > request.max_latency_ms:
        mismatch("REQUEST_LATENCY", "candidate exceeds request latency ceiling")
    if candidate.predicted_latency_ms > node.latency_budget_ms:
        mismatch("NODE_LATENCY", "candidate exceeds node latency budget")

    if request.max_cost_minor_units is not None:
        if candidate.predicted_cost_minor_units is None:
            mismatch("COST_UNKNOWN", "route cost is required by request")
        elif candidate.predicted_cost_minor_units > request.max_cost_minor_units:
            mismatch("REQUEST_COST", "candidate exceeds request cost ceiling")
    if node.cost_ceiling_minor_units is not None:
        if candidate.predicted_cost_minor_units is None:
            mismatch("NODE_COST_UNKNOWN", "route cost is required by node profile")
        elif candidate.predicted_cost_minor_units > node.cost_ceiling_minor_units:
            mismatch("NODE_COST", "candidate exceeds node cost ceiling")

    if portability.portable_model_digest != request.portable_model_digest:
        mismatch("PORTABILITY_MODEL_BINDING", "portability assessment covers another model")
    if portability.backend_id != node.backend_id:
        mismatch("PORTABILITY_BACKEND_BINDING", "portability assessment covers another backend")
    if candidate.model_portability_assessment_digest != portability.assessment_digest:
        mismatch("PORTABILITY_ASSESSMENT_BINDING", "candidate portability digest mismatch")
    if portability.outcome is PortabilityOutcome.DENY:
        mismatch("MODEL_PORTABILITY_DENY", "model is not admissible on candidate backend")

    if request.raw_personal_data_required:
        if not node.allows_raw_personal_data:
            mismatch("RAW_DATA_NOT_ALLOWED", "node does not accept raw personal data")
        if disclosure is None:
            mismatch("DISCLOSURE_MISSING", "raw personal data route requires disclosure assessment")
        else:
            if disclosure.assessment_digest != disclosure.computed_digest:
                raise FailClosedError("disclosure assessment is unsealed or tampered")
            if disclosure.outcome is not DisclosureOutcome.PASS:
                mismatch("DISCLOSURE_DENY", "disclosure assessment did not pass")
            if disclosure.authorization_digest != request.disclosure_authorization_digest:
                mismatch("DISCLOSURE_BINDING", "route request disclosure authorization mismatch")
            if disclosure.destination_id != node.provider_id:
                mismatch("DISCLOSURE_DESTINATION", "disclosure destination does not match provider")

    outcome = RouteOutcome.DENY if mismatches else RouteOutcome.PASS
    provisional = ComputeRouteAssessment(
        assessment_id=f"route:{request.request_id}:{candidate.candidate_id}",
        request_digest=request.request_digest,
        candidate_digest=candidate.candidate_digest,
        node_profile_digest=node.profile_digest,
        outcome=outcome,
        mismatches=tuple(mismatches),
    )
    return provisional.model_copy(
        update={"assessment_digest": provisional.computed_digest}
    )
