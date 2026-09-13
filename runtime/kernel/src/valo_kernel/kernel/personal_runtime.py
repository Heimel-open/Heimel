from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..contracts.common import canonical_digest, utcnow
from ..contracts.compute_routing import (
    ComputeNodeProfile,
    ComputeRouteAssessment,
    ComputeRouteCandidate,
    ComputeRouteRequest,
    RouteOutcome,
)
from ..contracts.events import CanonicalEvent
from ..contracts.model_portability import ModelPortabilityAssessment
from ..contracts.semantic_disclosure import (
    DisclosedConsequenceAction,
    ExecutionBoundaryDisclosureContext,
    ExecutionBoundaryKey,
    SealedWorkspaceExecutionBinding,
)
from ..contracts.sovereignty import DisclosureAssessment, DisclosureOutcome
from ..contracts.workspace import (
    CandidateResult,
    ConformanceOutcome,
    ConformanceReport,
    GovernedWorkspaceEnvelope,
)
from ..world.state import WorldState
from .compute_routing import assess_compute_route
from .errors import FailClosedError
from .execution_context import build_execution_context
from .semantic_disclosure import (
    bind_sealed_workspace_execution,
    disclose_consequence_action,
)
from .workspace import bind_workspace_execution, evaluate_candidate_conformance


@dataclass(frozen=True)
class PreparedWorkerInvocation:
    workspace: GovernedWorkspaceEnvelope
    destination_id: str
    route_assessment: ComputeRouteAssessment
    disclosure_assessment: DisclosureAssessment | None


@dataclass(frozen=True)
class PreparedExecutionHandoff:
    conformance_report: ConformanceReport
    sealed_binding: SealedWorkspaceExecutionBinding


@dataclass(frozen=True)
class RehtBoundaryHandoff:
    disclosed_action: DisclosedConsequenceAction
    disclosure_context: ExecutionBoundaryDisclosureContext
    execution_context: dict[str, Any]


def prepare_worker_invocation(
    workspace: GovernedWorkspaceEnvelope,
    request: ComputeRouteRequest,
    candidate: ComputeRouteCandidate,
    node: ComputeNodeProfile,
    portability: ModelPortabilityAssessment,
    *,
    current_state_root: str,
    disclosure: DisclosureAssessment | None = None,
) -> PreparedWorkerInvocation:
    """Admit a proposed compute route for one governed workspace.

    Selection/optimization remains external. This function only verifies that
    the proposed destination is admissible for the exact workspace and current
    state. It creates no disclosure and no authority.
    """
    if workspace.workspace_digest != workspace.computed_digest:
        raise FailClosedError("governed workspace is unsealed or tampered")
    if request.tenant_id != workspace.spec.tenant_id:
        raise FailClosedError("route request tenant differs from workspace")
    if request.purpose_id != workspace.spec.purpose_id:
        raise FailClosedError("route request purpose differs from workspace")
    if request.source_state_root != workspace.projection.source_state_root:
        raise FailClosedError("route request is bound to another source state")
    if current_state_root != request.source_state_root:
        raise FailClosedError("authoritative state changed before worker dispatch")

    if request.raw_personal_data_required:
        if disclosure is None:
            raise FailClosedError("external personal-data route requires disclosure PASS")
        if disclosure.outcome is not DisclosureOutcome.PASS:
            raise FailClosedError("external personal-data disclosure did not pass")
        if disclosure.destination_id != node.provider_id:
            raise FailClosedError("disclosure destination differs from compute provider")

    assessment = assess_compute_route(
        request,
        candidate,
        node,
        portability,
        current_state_root=current_state_root,
        disclosure=disclosure,
    )
    if assessment.outcome is not RouteOutcome.PASS:
        codes = ", ".join(item.code for item in assessment.mismatches)
        raise FailClosedError(f"compute route is not admissible: {codes}")

    return PreparedWorkerInvocation(
        workspace=workspace,
        destination_id=node.provider_id,
        route_assessment=assessment,
        disclosure_assessment=disclosure,
    )


def prepare_execution_handoff(
    workspace: GovernedWorkspaceEnvelope,
    candidate: CandidateResult,
    current_state: WorldState,
    *,
    action_id: str,
    recipient_key: ExecutionBoundaryKey,
    moment: datetime | None = None,
) -> PreparedExecutionHandoff:
    """Conform a worker candidate and seal one exact consequence action.

    The returned binding is safe to cross toward REHT because the clear action
    semantics remain encrypted for the execution boundary.
    """
    moment = moment or utcnow()
    report = evaluate_candidate_conformance(
        workspace,
        candidate,
        current_state,
        moment=moment,
    )
    if report.outcome is not ConformanceOutcome.PASS:
        raise FailClosedError(
            f"candidate cannot cross to execution boundary: {report.outcome.value}"
        )
    sealed = bind_sealed_workspace_execution(
        workspace,
        candidate,
        report,
        action_id=action_id,
        recipient_key=recipient_key,
    )
    return PreparedExecutionHandoff(
        conformance_report=report,
        sealed_binding=sealed,
    )


def open_execution_handoff_at_reht(
    handoff: PreparedExecutionHandoff,
    workspace: GovernedWorkspaceEnvelope,
    candidate: CandidateResult,
    current_state: WorldState,
    *,
    actor: str,
    requested_transition: CanonicalEvent,
    boundary_private_key: bytes,
    identity_id: str | None = None,
    event_position: int,
    reht_evaluation_id: str,
    moment: datetime | None = None,
) -> RehtBoundaryHandoff:
    """Open an exact action only at the REHT boundary and build fresh context.

    This function does not authorize or execute. It re-validates current state
    through `build_execution_context`, derives fresh authority/evidence digests,
    and then performs JIT semantic disclosure for the already sealed action.
    """
    moment = moment or utcnow()
    sealed = handoff.sealed_binding
    if sealed.binding_digest != sealed.computed_digest:
        raise FailClosedError("sealed execution handoff is unsealed or tampered")

    clear_binding = bind_workspace_execution(
        workspace,
        candidate,
        handoff.conformance_report,
        action_id=sealed.sealed_action.action_id,
    )
    execution_context = build_execution_context(
        current_state,
        actor=actor,
        capability=clear_binding.proposed_action.capability,
        target=clear_binding.proposed_action.target,
        requested_transition=requested_transition,
        identity_id=identity_id,
        purpose_id=clear_binding.proposed_action.purpose_id,
        moment=moment,
        event_position=event_position,
        workspace_binding=clear_binding,
    )

    disclosure_context = ExecutionBoundaryDisclosureContext(
        disclosure_id=f"jit:{sealed.sealed_action.envelope_id}",
        boundary_id=sealed.sealed_action.recipient_boundary_id,
        key_ref=sealed.sealed_action.recipient_key_ref,
        tenant_id=sealed.tenant_id,
        work_unit_id=sealed.work_unit_id,
        workspace_id=sealed.workspace_id,
        reht_evaluation_id=reht_evaluation_id,
        fresh_state_root=current_state.root_hash(),
        fresh_authority_digest=canonical_digest(execution_context["authority"]),
        fresh_evidence_digest=canonical_digest(execution_context["evidence"]),
        disclosed_at=moment,
    )
    disclosed = disclose_consequence_action(
        sealed.sealed_action,
        disclosure_context,
        boundary_private_key=boundary_private_key,
    )
    if canonical_digest(disclosed.action.model_dump(mode="json")) != clear_binding.proposed_action_digest:
        raise FailClosedError("JIT disclosed action differs from conformed action")

    return RehtBoundaryHandoff(
        disclosed_action=disclosed,
        disclosure_context=disclosure_context,
        execution_context=execution_context,
    )
