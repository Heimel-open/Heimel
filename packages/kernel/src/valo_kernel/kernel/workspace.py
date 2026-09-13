from __future__ import annotations

from datetime import datetime
from typing import Any

from ..contracts.common import EvidenceStatus, TruthStatus, canonical_digest, utcnow
from ..contracts.workspace import (
    CandidateKind,
    CandidateResult,
    CapabilityLease,
    ConformanceMismatch,
    ConformanceOutcome,
    ConformanceReport,
    GovernedProjectionEnvelope,
    GovernedWorkspaceEnvelope,
    ProjectedObject,
    StateDependency,
    WorkspaceCapabilitySpec,
    WorkspaceExecutionBinding,
    WorkspaceSpec,
)
from ..world.state import WorldState
from .errors import FailClosedError

_OUTCOME_PRIORITY = {
    ConformanceOutcome.REDO: 10,
    ConformanceOutcome.DEFER: 20,
    ConformanceOutcome.DENY: 30,
    ConformanceOutcome.HALT: 40,
}


def _promote(
    current: ConformanceOutcome,
    proposed: ConformanceOutcome,
) -> ConformanceOutcome:
    if _OUTCOME_PRIORITY[proposed] > _OUTCOME_PRIORITY[current]:
        return proposed
    return current


def _dump(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return dict(value)
    raise FailClosedError("projection object is not serializable")


def _state_object(state: WorldState, collection: str, object_id: str) -> Any:
    values = getattr(state, collection, None)
    if not isinstance(values, dict):
        raise FailClosedError(f"unsupported projection collection: {collection}")
    if object_id not in values:
        raise FailClosedError(f"unknown projection object: {collection}:{object_id}")
    return values[object_id]


def _dependency(collection: str, object_id: str, value: Any) -> StateDependency:
    return StateDependency(
        collection=collection,
        object_id=object_id,
        object_digest=canonical_digest(_dump(value)),
    )


def _evidence_refs(value: Any) -> tuple[str, ...]:
    refs = set(getattr(value, "evidence_refs", ()) or ())
    provenance = getattr(value, "provenance", None)
    refs.update(getattr(provenance, "evidence_refs", ()) or ())
    return tuple(sorted(refs))


def _validate_operative_object(
    state: WorldState,
    collection: str,
    object_id: str,
    value: Any,
    evidence_refs: tuple[str, ...],
) -> None:
    requires_admitted = (
        collection == "facts"
        and getattr(value, "truth_status", None) == TruthStatus.CONFIRMED
    ) or (collection in {"entities", "relationships"} and bool(evidence_refs))
    if not requires_admitted:
        return
    if not evidence_refs:
        raise FailClosedError(
            f"operative projection lacks admitted evidence: {collection}:{object_id}"
        )
    for evidence_id in evidence_refs:
        evidence = state.evidence.get(evidence_id)
        if evidence is None or evidence.status != EvidenceStatus.ADMITTED:
            raise FailClosedError(
                f"operative projection uses non-admitted evidence: {evidence_id}"
            )


def _purpose_allows_data(
    permitted_data: list[str], collection: str, object_id: str
) -> bool:
    return any(
        item in {"*", collection, f"{collection}:*", f"{collection}:{object_id}"}
        for item in permitted_data
    )


def _capability_lease(
    workspace_id: str,
    spec: WorkspaceCapabilitySpec,
    valid_until: datetime,
) -> CapabilityLease:
    payload = {
        "workspace_id": workspace_id,
        "capability": spec.capability,
        "targets": spec.target_refs,
        "valid_until": valid_until.isoformat(),
    }
    return CapabilityLease(
        handle_ref=f"capability:sha256:{canonical_digest(payload)}",
        capability=spec.capability,
        target_refs=spec.target_refs,
        allowed_effects=spec.allowed_effects,
        parameter_constraints=spec.parameter_constraints,
        valid_until=valid_until,
    )


def compile_governed_workspace(
    state: WorldState,
    spec: WorkspaceSpec,
    *,
    source_event_position: int,
    moment: datetime | None = None,
) -> GovernedWorkspaceEnvelope:
    """Compile the least governed world needed by one work unit.

    The result is an immutable, non-authoritative read projection. It cannot
    mutate WorldState, grant authority or execute a capability.
    """
    moment = moment or utcnow()
    if spec.tenant_id != state.tenant_id:
        raise FailClosedError("workspace tenant does not match Kernel state")
    if spec.expires_at <= moment:
        raise FailClosedError("workspace is already expired")
    purpose = state.purposes.get(spec.purpose_id)
    if purpose is None or not purpose.validity.is_active_at(moment):
        raise FailClosedError("workspace requires an active registered purpose")
    if spec.expires_at > purpose.validity.valid_until:
        raise FailClosedError("workspace cannot outlive its registered purpose")

    for contract_id in spec.governing_contract_ids:
        contract = state.contracts.get(contract_id)
        if contract is None:
            raise FailClosedError(f"unknown governing contract: {contract_id}")
        if contract.status not in {"SIGNED", "AMENDED"}:
            raise FailClosedError(f"governing contract is not operative: {contract_id}")
        if not contract.effective_period.is_active_at(moment):
            raise FailClosedError(f"governing contract is not active: {contract_id}")
        if spec.expires_at > contract.effective_period.valid_until:
            raise FailClosedError(
                f"workspace cannot outlive governing contract: {contract_id}"
            )

    for capability in spec.capabilities:
        if capability.capability not in purpose.permitted_actions:
            raise FailClosedError(
                f"workspace capability is outside purpose: {capability.capability}"
            )
        if purpose.scope and "*" not in purpose.scope:
            outside = set(capability.target_refs) - set(purpose.scope)
            if outside:
                raise FailClosedError(
                    "workspace capability target is outside purpose scope: "
                    + ", ".join(sorted(outside))
                )

    requested: set[tuple[str, str]] = {("purposes", spec.purpose_id)}
    for selector in spec.selectors:
        for object_id in selector.object_ids:
            if selector.collection != "purposes" and not _purpose_allows_data(
                purpose.permitted_data, selector.collection, object_id
            ):
                raise FailClosedError(
                    f"projection data is outside purpose: {selector.collection}:{object_id}"
                )
            requested.add((selector.collection, object_id))

    projected: list[ProjectedObject] = []
    dependency_refs = set(requested)
    dependency_refs.update(
        ("contracts", contract_id) for contract_id in spec.governing_contract_ids
    )
    for collection, object_id in sorted(requested):
        value = _state_object(state, collection, object_id)
        evidence_refs = _evidence_refs(value)
        _validate_operative_object(
            state,
            collection,
            object_id,
            value,
            evidence_refs,
        )
        payload = _dump(value)
        digest = canonical_digest(payload)
        projected.append(
            ProjectedObject(
                collection=collection,
                object_id=object_id,
                payload=payload,
                payload_digest=digest,
            )
        )
        if collection == "evidence":
            evidence_refs = tuple(sorted(set(evidence_refs) | {object_id}))
        for evidence_id in evidence_refs:
            evidence = state.evidence.get(evidence_id)
            if evidence is None:
                raise FailClosedError(
                    f"projected state refers to unknown evidence: {evidence_id}"
                )
            dependency_refs.add(("evidence", evidence_id))
            if evidence.admission_decision_ref:
                decision = state.admissions.get(evidence.admission_decision_ref)
                if (
                    decision is None
                    or decision.decision_digest != evidence.admission_digest
                ):
                    raise FailClosedError(
                        f"evidence admission binding is invalid: {evidence_id}"
                    )
                dependency_refs.add(("admissions", decision.decision_id))

    dependencies = [
        _dependency(collection, object_id, _state_object(state, collection, object_id))
        for collection, object_id in sorted(dependency_refs)
    ]

    dependency_digest = canonical_digest(
        [item.model_dump(mode="json") for item in dependencies]
    )
    projection = GovernedProjectionEnvelope(
        projection_id=f"projection:{spec.workspace_id}",
        tenant_id=spec.tenant_id,
        purpose_id=spec.purpose_id,
        source_state_root=state.root_hash(),
        source_event_position=source_event_position,
        projected_at=moment,
        expires_at=spec.expires_at,
        objects=tuple(projected),
        dependencies=tuple(dependencies),
        dependency_digest=dependency_digest,
    )
    provisional = GovernedWorkspaceEnvelope(
        spec=spec,
        projection=projection,
        capability_leases=tuple(
            _capability_lease(spec.workspace_id, capability, spec.expires_at)
            for capability in spec.capabilities
        ),
    )
    return provisional.model_copy(
        update={"workspace_digest": provisional.computed_digest}
    )


def create_candidate_result(**values: Any) -> CandidateResult:
    provisional = CandidateResult(**values)
    return provisional.model_copy(
        update={"candidate_digest": provisional.computed_digest}
    )


def changed_dependencies(
    dependencies: tuple[StateDependency, ...],
    state: WorldState,
) -> tuple[str, ...]:
    changed: list[str] = []
    for item in dependencies:
        try:
            current = _state_object(state, item.collection, item.object_id)
        except FailClosedError:
            changed.append(item.ref)
            continue
        current_digest = _dependency(
            item.collection,
            item.object_id,
            current,
        ).object_digest
        if current_digest != item.object_digest:
            changed.append(item.ref)
    return tuple(changed)


def _parameter_mismatches(
    constraints: dict[str, Any], parameters: dict[str, Any]
) -> list[str]:
    mismatches: list[str] = []
    for key, rule in constraints.items():
        value = parameters.get(key)
        if isinstance(rule, dict):
            if (
                "required" in rule
                and rule["required"] is True
                and key not in parameters
            ):
                mismatches.append(f"{key}:required")
                continue
            if value is None:
                continue
            if "max" in rule and (
                not isinstance(value, (int, float)) or value > rule["max"]
            ):
                mismatches.append(f"{key}:max")
            if "min" in rule and (
                not isinstance(value, (int, float)) or value < rule["min"]
            ):
                mismatches.append(f"{key}:min")
            if "one_of" in rule and value not in rule["one_of"]:
                mismatches.append(f"{key}:one_of")
        elif value != rule:
            mismatches.append(f"{key}:exact")
    return mismatches


def evaluate_candidate_conformance(
    workspace: GovernedWorkspaceEnvelope,
    candidate: CandidateResult,
    current_state: WorldState,
    *,
    moment: datetime | None = None,
) -> ConformanceReport:
    moment = moment or utcnow()
    mismatches: list[ConformanceMismatch] = []
    severity = ConformanceOutcome.REDO

    if workspace.workspace_digest != workspace.computed_digest:
        mismatches.append(
            ConformanceMismatch(
                code="WORKSPACE_TAMPER",
                detail="workspace is unsealed",
            )
        )
        severity = _promote(severity, ConformanceOutcome.HALT)
    if candidate.candidate_digest != candidate.computed_digest:
        mismatches.append(
            ConformanceMismatch(
                code="CANDIDATE_TAMPER",
                detail="candidate is unsealed",
            )
        )
        severity = _promote(severity, ConformanceOutcome.HALT)
    if (
        candidate.workspace_id != workspace.spec.workspace_id
        or candidate.workspace_digest != workspace.workspace_digest
    ):
        mismatches.append(
            ConformanceMismatch(
                code="WORKSPACE_BINDING",
                detail="candidate is bound to another workspace",
            )
        )
        severity = _promote(severity, ConformanceOutcome.HALT)
    if workspace.spec.tenant_id != current_state.tenant_id:
        mismatches.append(
            ConformanceMismatch(
                code="TENANT_MISMATCH",
                detail="current state tenant differs",
            )
        )
        severity = _promote(severity, ConformanceOutcome.HALT)
    if moment >= workspace.spec.expires_at:
        mismatches.append(
            ConformanceMismatch(
                code="WORKSPACE_EXPIRED",
                detail="workspace has expired",
            )
        )
        severity = _promote(severity, ConformanceOutcome.DEFER)

    changed = changed_dependencies(workspace.projection.dependencies, current_state)
    governing_refs = {
        f"contracts:{contract_id}"
        for contract_id in workspace.spec.governing_contract_ids
    }
    governing_changed = tuple(ref for ref in changed if ref in governing_refs)
    other_changed = tuple(ref for ref in changed if ref not in governing_refs)
    if governing_changed:
        mismatches.append(
            ConformanceMismatch(
                code="GOVERNING_CONTRACT_DRIFT",
                detail="governing contract changed during continuation",
                pointer=",".join(governing_changed),
            )
        )
        severity = _promote(severity, ConformanceOutcome.DEFER)
    if other_changed:
        mismatches.append(
            ConformanceMismatch(
                code="RELEVANT_STATE_DRIFT",
                detail="material projected state changed",
                pointer=",".join(other_changed),
            )
        )
        severity = _promote(severity, ConformanceOutcome.DEFER)

    if candidate.output_kind not in workspace.spec.allowed_output_kinds:
        mismatches.append(
            ConformanceMismatch(
                code="OUTPUT_KIND",
                detail="output kind is not allowed",
            )
        )

    if (
        candidate.output_kind == CandidateKind.EXTERNAL_ACTION
        and not candidate.proposed_actions
    ):
        mismatches.append(
            ConformanceMismatch(
                code="MISSING_ACTION",
                detail="external-action output requires a proposed action",
            )
        )
    if (
        candidate.output_kind != CandidateKind.EXTERNAL_ACTION
        and candidate.proposed_actions
    ):
        mismatches.append(
            ConformanceMismatch(
                code="ACTION_KIND_ESCAPE",
                detail="only external-action output may propose actions",
            )
        )
        severity = _promote(severity, ConformanceOutcome.DENY)
    if candidate.output_kind == CandidateKind.DEFER:
        mismatches.append(
            ConformanceMismatch(
                code="WORKER_DEFER",
                detail="worker explicitly deferred the work unit",
            )
        )
        severity = _promote(severity, ConformanceOutcome.DEFER)

    projected_refs = {item.ref for item in workspace.projection.objects}
    for index, claim in enumerate(candidate.claims):
        if not claim.source_refs or not set(claim.source_refs).issubset(projected_refs):
            mismatches.append(
                ConformanceMismatch(
                    code="UNSUPPORTED_CLAIM",
                    detail="candidate claim lacks projected provenance",
                    pointer=f"claims[{index}]",
                )
            )

    leases = {item.capability: item for item in workspace.capability_leases}
    action_ids = [item.action_id for item in candidate.proposed_actions]
    if len(set(action_ids)) != len(action_ids):
        mismatches.append(
            ConformanceMismatch(
                code="DUPLICATE_ACTION_ID",
                detail="candidate action identifiers are ambiguous",
            )
        )
        severity = _promote(severity, ConformanceOutcome.DENY)
    if len(candidate.proposed_actions) > workspace.spec.max_actions:
        mismatches.append(
            ConformanceMismatch(
                code="ACTION_COUNT",
                detail="candidate exceeds action bound",
            )
        )
        severity = _promote(severity, ConformanceOutcome.DENY)
    for index, action in enumerate(candidate.proposed_actions):
        lease = leases.get(action.capability)
        pointer = f"proposed_actions[{index}]"
        if lease is None:
            mismatches.append(
                ConformanceMismatch(
                    code="CAPABILITY_ESCAPE",
                    detail="capability is absent from workspace",
                    pointer=pointer,
                )
            )
            severity = _promote(severity, ConformanceOutcome.DENY)
            continue
        if action.target not in lease.target_refs:
            mismatches.append(
                ConformanceMismatch(
                    code="TARGET_ESCAPE",
                    detail="target is outside capability lease",
                    pointer=pointer,
                )
            )
            severity = _promote(severity, ConformanceOutcome.DENY)
        if action.purpose_id != workspace.spec.purpose_id:
            mismatches.append(
                ConformanceMismatch(
                    code="PURPOSE_DRIFT",
                    detail="action purpose differs from workspace",
                    pointer=pointer,
                )
            )
            severity = _promote(severity, ConformanceOutcome.DENY)
        if not set(action.declared_effects).issubset(set(lease.allowed_effects)):
            mismatches.append(
                ConformanceMismatch(
                    code="EFFECT_ESCAPE",
                    detail="action declares an unleased effect",
                    pointer=pointer,
                )
            )
            severity = _promote(severity, ConformanceOutcome.DENY)
        parameter_errors = _parameter_mismatches(
            lease.parameter_constraints, action.parameters
        )
        for error in parameter_errors:
            mismatches.append(
                ConformanceMismatch(
                    code="PARAMETER_CONSTRAINT", detail=error, pointer=pointer
                )
            )

    if candidate.unknowns:
        mismatches.append(
            ConformanceMismatch(
                code="UNRESOLVED_UNKNOWN",
                detail="candidate reports unresolved information",
            )
        )
        severity = _promote(severity, ConformanceOutcome.DEFER)

    if not mismatches:
        outcome = (
            ConformanceOutcome.STEP_UP
            if workspace.spec.step_up_required
            else ConformanceOutcome.PASS
        )
        if outcome == ConformanceOutcome.STEP_UP:
            mismatches.append(
                ConformanceMismatch(
                    code="EXPLICIT_STEP_UP",
                    detail="workspace requires independent review",
                )
            )
    else:
        outcome = severity

    values = {
        "report_id": f"conformance:{candidate.candidate_id}",
        "workspace_id": workspace.spec.workspace_id,
        "workspace_digest": workspace.workspace_digest,
        "candidate_id": candidate.candidate_id,
        "candidate_digest": candidate.candidate_digest,
        "evaluated_state_root": current_state.root_hash(),
        "dependency_digest": workspace.projection.dependency_digest,
        "outcome": outcome,
        "mismatches": tuple(mismatches),
        "evaluated_at": moment,
    }
    provisional = ConformanceReport(**values)
    return provisional.model_copy(update={"report_digest": provisional.computed_digest})


def bind_workspace_execution(
    workspace: GovernedWorkspaceEnvelope,
    candidate: CandidateResult,
    report: ConformanceReport,
    *,
    action_id: str,
) -> WorkspaceExecutionBinding:
    if report.outcome != ConformanceOutcome.PASS:
        raise FailClosedError("only PASS conformance can produce an execution binding")
    if workspace.workspace_digest != workspace.computed_digest:
        raise FailClosedError("workspace is unsealed")
    if candidate.candidate_digest != candidate.computed_digest:
        raise FailClosedError("candidate is unsealed")
    if (
        candidate.workspace_id != workspace.spec.workspace_id
        or candidate.workspace_digest != workspace.workspace_digest
    ):
        raise FailClosedError("candidate workspace binding mismatch")
    if (
        report.workspace_id != workspace.spec.workspace_id
        or report.workspace_digest != workspace.workspace_digest
    ):
        raise FailClosedError("conformance workspace binding mismatch")
    if (
        report.candidate_id != candidate.candidate_id
        or report.candidate_digest != candidate.candidate_digest
    ):
        raise FailClosedError("conformance candidate binding mismatch")
    if report.report_digest != report.computed_digest:
        raise FailClosedError("conformance report is unsealed")
    if report.dependency_digest != workspace.projection.dependency_digest:
        raise FailClosedError("conformance dependency binding mismatch")
    actions = [
        item for item in candidate.proposed_actions if item.action_id == action_id
    ]
    if len(actions) != 1:
        raise FailClosedError("execution requires one conformed proposed action")
    action = actions[0]
    return WorkspaceExecutionBinding(
        tenant_id=workspace.spec.tenant_id,
        work_unit_id=workspace.spec.work_unit_id,
        workspace_id=workspace.spec.workspace_id,
        workspace_digest=workspace.workspace_digest,
        workspace_expires_at=workspace.spec.expires_at,
        program_ref=workspace.spec.program_ref,
        program_digest=workspace.spec.program_digest,
        governing_contract_ids=workspace.spec.governing_contract_ids,
        invocation_id=candidate.invocation_id,
        candidate_id=candidate.candidate_id,
        candidate_digest=candidate.candidate_digest,
        proposed_action=action,
        proposed_action_digest=canonical_digest(action.model_dump(mode="json")),
        conformance_report_id=report.report_id,
        conformance_digest=report.report_digest,
        source_state_root=workspace.projection.source_state_root,
        conformed_state_root=report.evaluated_state_root,
        source_event_position=workspace.projection.source_event_position,
        conformed_at=report.evaluated_at,
        dependency_digest=workspace.projection.dependency_digest,
        dependencies=workspace.projection.dependencies,
    )
