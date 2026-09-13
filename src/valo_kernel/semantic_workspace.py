from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .contracts.common import canonical_digest, utcnow
from .contracts.workspace import (
    CandidateResult,
    ConformanceMismatch,
    ConformanceOutcome,
    ConformanceReport,
    GovernedWorkspaceEnvelope,
    StateDependency,
    WorkspaceExecutionBinding,
    WorkspaceSpec,
)
from .kernel.errors import FailClosedError
from .kernel.workspace import (
    compile_governed_workspace,
    create_candidate_result,
    evaluate_candidate_conformance,
)
from .world.state import WorldState


class SemanticTermKind(str, Enum):
    ENTITY_TYPE = "ENTITY_TYPE"
    RELATION_TYPE = "RELATION_TYPE"
    PREDICATE = "PREDICATE"


class SemanticTerm(BaseModel):
    term_id: str
    kind: SemanticTermKind
    kernel_value: str
    definition: str
    aliases: tuple[str, ...] = ()

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_term(self) -> SemanticTerm:
        if not self.term_id or not self.kernel_value or not self.definition:
            raise ValueError("semantic term id, kernel value and definition are required")
        if len(set(self.aliases)) != len(self.aliases):
            raise ValueError("semantic aliases must be unique")
        if self.kernel_value in self.aliases:
            raise ValueError("semantic aliases must not repeat the kernel value")
        if any(not item for item in self.aliases):
            raise ValueError("semantic aliases cannot be empty")
        return self

    @property
    def surfaces(self) -> tuple[str, ...]:
        return (self.kernel_value, *self.aliases)


class WorkspaceSemanticContract(BaseModel):
    schema_version: Literal["workspace_semantics.v1"] = "workspace_semantics.v1"
    ontology_id: str
    ontology_version: str
    terms: tuple[SemanticTerm, ...]
    contract_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"contract_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_contract(self) -> WorkspaceSemanticContract:
        if not self.ontology_id or not self.ontology_version or not self.terms:
            raise ValueError("semantic contract requires ontology identity and terms")
        term_ids = [item.term_id for item in self.terms]
        if len(set(term_ids)) != len(term_ids):
            raise ValueError("semantic term ids must be unique")
        surfaces: dict[tuple[SemanticTermKind, str], str] = {}
        for term in self.terms:
            for surface in term.surfaces:
                key = (term.kind, surface)
                prior = surfaces.get(key)
                if prior is not None and prior != term.term_id:
                    raise ValueError("semantic surface maps to multiple terms")
                surfaces[key] = term.term_id
        if self.contract_digest and self.contract_digest != self.computed_digest:
            raise ValueError("semantic contract digest mismatch")
        return self


class SemanticGovernedWorkspaceEnvelope(BaseModel):
    schema_version: Literal["semantic_governed_workspace.v1"] = (
        "semantic_governed_workspace.v1"
    )
    base_workspace: GovernedWorkspaceEnvelope
    semantic_contract: WorkspaceSemanticContract
    workspace_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"workspace_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_workspace(self) -> SemanticGovernedWorkspaceEnvelope:
        if self.base_workspace.workspace_digest != self.base_workspace.computed_digest:
            raise ValueError("base governed workspace is unsealed")
        if self.semantic_contract.contract_digest != self.semantic_contract.computed_digest:
            raise ValueError("semantic contract is unsealed")
        if self.workspace_digest and self.workspace_digest != self.computed_digest:
            raise ValueError("semantic workspace digest mismatch")
        return self


class SemanticResolution(BaseModel):
    claim_id: str
    subject_ref: str
    predicate_term_id: str
    predicate_surface: str
    object_ref: str | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)


class SemanticConformanceReport(ConformanceReport):
    semantic_contract_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    ontology_id: str
    ontology_version: str
    resolutions: tuple[SemanticResolution, ...] = ()


class SemanticWorkspaceExecutionBinding(WorkspaceExecutionBinding):
    semantic_contract_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    ontology_id: str
    ontology_version: str


_OUTCOME_PRIORITY = {
    ConformanceOutcome.PASS: 0,
    ConformanceOutcome.STEP_UP: 5,
    ConformanceOutcome.REDO: 10,
    ConformanceOutcome.DEFER: 20,
    ConformanceOutcome.DENY: 30,
    ConformanceOutcome.HALT: 40,
}

_KNOWN_REF_COLLECTIONS = {
    "entities",
    "relationships",
    "facts",
    "evidence",
    "rights",
    "obligations",
    "purposes",
    "contracts",
    "constraints",
    "resources",
    "reservations",
}


def _stronger(
    current: ConformanceOutcome,
    proposed: ConformanceOutcome,
) -> ConformanceOutcome:
    if _OUTCOME_PRIORITY[proposed] > _OUTCOME_PRIORITY[current]:
        return proposed
    return current


def create_semantic_contract(**values: Any) -> WorkspaceSemanticContract:
    provisional = WorkspaceSemanticContract(**values)
    return provisional.model_copy(
        update={"contract_digest": provisional.computed_digest}
    )


def _semantic_term_for_kernel_value(
    contract: WorkspaceSemanticContract,
    kind: SemanticTermKind,
    value: str,
) -> SemanticTerm | None:
    matches = [
        item
        for item in contract.terms
        if item.kind == kind and item.kernel_value == value
    ]
    if len(matches) != 1:
        return None
    return matches[0]


def _semantic_term_for_surface(
    contract: WorkspaceSemanticContract,
    kind: SemanticTermKind,
    surface: str,
) -> SemanticTerm | None:
    matches = [
        item for item in contract.terms if item.kind == kind and surface in item.surfaces
    ]
    if len(matches) != 1:
        return None
    return matches[0]


def _validate_projection_semantics(
    workspace: GovernedWorkspaceEnvelope,
    contract: WorkspaceSemanticContract,
) -> None:
    missing: list[str] = []
    for item in workspace.projection.objects:
        if item.collection == "entities":
            kind = SemanticTermKind.ENTITY_TYPE
            value = item.payload.get("entity_type")
        elif item.collection == "relationships":
            kind = SemanticTermKind.RELATION_TYPE
            value = item.payload.get("relation_type")
        else:
            continue
        if not isinstance(value, str) or _semantic_term_for_kernel_value(
            contract, kind, value
        ) is None:
            missing.append(f"{item.ref}:{value}")
    if missing:
        raise FailClosedError(
            "semantic contract does not cover projected Kernel meaning: "
            + ", ".join(sorted(missing))
        )


def compile_semantic_governed_workspace(
    state: WorldState,
    spec: WorkspaceSpec,
    semantic_contract: WorkspaceSemanticContract,
    *,
    source_event_position: int,
    moment: datetime | None = None,
) -> SemanticGovernedWorkspaceEnvelope:
    """Bind canonical meaning to one governed workspace without granting authority."""
    if not semantic_contract.contract_digest:
        semantic_contract = semantic_contract.model_copy(
            update={"contract_digest": semantic_contract.computed_digest}
        )
    if semantic_contract.contract_digest != semantic_contract.computed_digest:
        raise FailClosedError("semantic contract is not sealed")
    base_workspace = compile_governed_workspace(
        state,
        spec,
        source_event_position=source_event_position,
        moment=moment,
    )
    _validate_projection_semantics(base_workspace, semantic_contract)
    provisional = SemanticGovernedWorkspaceEnvelope(
        base_workspace=base_workspace,
        semantic_contract=semantic_contract,
    )
    return provisional.model_copy(
        update={"workspace_digest": provisional.computed_digest}
    )


def _projected_ref_index(
    workspace: SemanticGovernedWorkspaceEnvelope,
) -> tuple[set[str], dict[str, tuple[str, ...]]]:
    refs = {item.ref for item in workspace.base_workspace.projection.objects}
    by_id: dict[str, list[str]] = {}
    for item in workspace.base_workspace.projection.objects:
        by_id.setdefault(item.object_id, []).append(item.ref)
    return refs, {key: tuple(sorted(value)) for key, value in by_id.items()}


def _resolve_ref(
    surface: str,
    projected_refs: set[str],
    by_id: dict[str, tuple[str, ...]],
) -> tuple[str | None, bool]:
    if surface in projected_refs:
        return surface, False
    if ":" in surface:
        prefix = surface.split(":", 1)[0]
        if prefix in _KNOWN_REF_COLLECTIONS:
            return None, True
    matches = by_id.get(surface, ())
    if len(matches) == 1:
        return matches[0], False
    if len(matches) > 1:
        return None, True
    return None, False


def _semantic_checks(
    workspace: SemanticGovernedWorkspaceEnvelope,
    candidate: CandidateResult,
) -> tuple[
    list[ConformanceMismatch],
    tuple[SemanticResolution, ...],
    ConformanceOutcome,
]:
    mismatches: list[ConformanceMismatch] = []
    resolutions: list[SemanticResolution] = []
    outcome = ConformanceOutcome.PASS
    projected_refs, by_id = _projected_ref_index(workspace)

    for index, claim in enumerate(candidate.claims):
        pointer = f"claims[{index}]"
        subject_ref, subject_invalid = _resolve_ref(
            claim.subject, projected_refs, by_id
        )
        if subject_ref is None:
            mismatches.append(
                ConformanceMismatch(
                    code="SEMANTIC_SUBJECT_ESCAPE",
                    detail=(
                        "claim subject is ambiguous or outside canonical workspace identity"
                        if subject_invalid
                        else "claim subject is not a canonical projected identity"
                    ),
                    pointer=pointer,
                )
            )
            outcome = _stronger(outcome, ConformanceOutcome.DENY)

        predicate_term = _semantic_term_for_surface(
            workspace.semantic_contract,
            SemanticTermKind.PREDICATE,
            claim.predicate,
        )
        if predicate_term is None:
            mismatches.append(
                ConformanceMismatch(
                    code="SEMANTIC_PREDICATE_ESCAPE",
                    detail="claim predicate is outside the workspace semantic contract",
                    pointer=pointer,
                )
            )
            outcome = _stronger(outcome, ConformanceOutcome.REDO)

        if subject_ref is not None and subject_ref not in claim.source_refs:
            mismatches.append(
                ConformanceMismatch(
                    code="SEMANTIC_SUBJECT_PROVENANCE",
                    detail="claim provenance does not bind its canonical subject",
                    pointer=pointer,
                )
            )
            outcome = _stronger(outcome, ConformanceOutcome.DENY)

        object_ref: str | None = None
        object_candidate, object_invalid = _resolve_ref(
            claim.object, projected_refs, by_id
        )
        if object_candidate is not None:
            object_ref = object_candidate
        elif object_invalid:
            mismatches.append(
                ConformanceMismatch(
                    code="SEMANTIC_OBJECT_ESCAPE",
                    detail="claim object is ambiguous or outside canonical workspace identity",
                    pointer=pointer,
                )
            )
            outcome = _stronger(outcome, ConformanceOutcome.DENY)

        if subject_ref is not None and predicate_term is not None and not object_invalid:
            resolutions.append(
                SemanticResolution(
                    claim_id=claim.claim_id,
                    subject_ref=subject_ref,
                    predicate_term_id=predicate_term.term_id,
                    predicate_surface=claim.predicate,
                    object_ref=object_ref,
                )
            )

    return mismatches, tuple(resolutions), outcome


def _candidate_for_base_workspace(
    workspace: SemanticGovernedWorkspaceEnvelope,
    candidate: CandidateResult,
) -> CandidateResult:
    values = candidate.model_dump(mode="python")
    values["workspace_digest"] = workspace.base_workspace.workspace_digest
    values["candidate_digest"] = ""
    return create_candidate_result(**values)


def evaluate_semantic_candidate_conformance(
    workspace: SemanticGovernedWorkspaceEnvelope,
    candidate: CandidateResult,
    current_state: WorldState,
    *,
    moment: datetime | None = None,
) -> SemanticConformanceReport:
    moment = moment or utcnow()
    wrapper_mismatches: list[ConformanceMismatch] = []
    wrapper_outcome = ConformanceOutcome.PASS

    if workspace.workspace_digest != workspace.computed_digest:
        wrapper_mismatches.append(
            ConformanceMismatch(
                code="SEMANTIC_WORKSPACE_TAMPER",
                detail="semantic workspace is unsealed",
            )
        )
        wrapper_outcome = ConformanceOutcome.HALT
    if candidate.candidate_digest != candidate.computed_digest:
        wrapper_mismatches.append(
            ConformanceMismatch(
                code="CANDIDATE_TAMPER",
                detail="candidate is unsealed",
            )
        )
        wrapper_outcome = ConformanceOutcome.HALT
    if (
        candidate.workspace_id != workspace.base_workspace.spec.workspace_id
        or candidate.workspace_digest != workspace.workspace_digest
    ):
        wrapper_mismatches.append(
            ConformanceMismatch(
                code="SEMANTIC_WORKSPACE_BINDING",
                detail="candidate is bound to another semantic workspace",
            )
        )
        wrapper_outcome = ConformanceOutcome.HALT

    base_candidate = _candidate_for_base_workspace(workspace, candidate)
    base_report = evaluate_candidate_conformance(
        workspace.base_workspace,
        base_candidate,
        current_state,
        moment=moment,
    )
    semantic_mismatches, resolutions, semantic_outcome = _semantic_checks(
        workspace, candidate
    )

    outcome = base_report.outcome
    outcome = _stronger(outcome, semantic_outcome)
    outcome = _stronger(outcome, wrapper_outcome)
    mismatches = (
        tuple(base_report.mismatches)
        + tuple(semantic_mismatches)
        + tuple(wrapper_mismatches)
    )

    values = {
        "report_id": f"semantic-conformance:{candidate.candidate_id}",
        "workspace_id": workspace.base_workspace.spec.workspace_id,
        "workspace_digest": workspace.workspace_digest,
        "candidate_id": candidate.candidate_id,
        "candidate_digest": candidate.candidate_digest,
        "evaluated_state_root": current_state.root_hash(),
        "dependency_digest": workspace.base_workspace.projection.dependency_digest,
        "outcome": outcome,
        "mismatches": mismatches,
        "evaluated_at": moment,
        "semantic_contract_digest": workspace.semantic_contract.contract_digest,
        "ontology_id": workspace.semantic_contract.ontology_id,
        "ontology_version": workspace.semantic_contract.ontology_version,
        "resolutions": resolutions,
    }
    provisional = SemanticConformanceReport(**values)
    return provisional.model_copy(update={"report_digest": provisional.computed_digest})


def bind_semantic_workspace_execution(
    workspace: SemanticGovernedWorkspaceEnvelope,
    candidate: CandidateResult,
    report: SemanticConformanceReport,
    *,
    action_id: str,
) -> SemanticWorkspaceExecutionBinding:
    if report.outcome != ConformanceOutcome.PASS:
        raise FailClosedError("only PASS semantic conformance can produce execution binding")
    if workspace.workspace_digest != workspace.computed_digest:
        raise FailClosedError("semantic workspace is unsealed")
    if candidate.candidate_digest != candidate.computed_digest:
        raise FailClosedError("candidate is unsealed")
    if candidate.workspace_digest != workspace.workspace_digest:
        raise FailClosedError("candidate semantic workspace binding mismatch")
    if report.report_digest != report.computed_digest:
        raise FailClosedError("semantic conformance report is unsealed")
    if (
        report.workspace_id != workspace.base_workspace.spec.workspace_id
        or report.workspace_digest != workspace.workspace_digest
    ):
        raise FailClosedError("semantic conformance workspace binding mismatch")
    if (
        report.candidate_id != candidate.candidate_id
        or report.candidate_digest != candidate.candidate_digest
    ):
        raise FailClosedError("semantic conformance candidate binding mismatch")
    if report.semantic_contract_digest != workspace.semantic_contract.contract_digest:
        raise FailClosedError("semantic contract binding mismatch")
    if report.dependency_digest != workspace.base_workspace.projection.dependency_digest:
        raise FailClosedError("semantic conformance dependency binding mismatch")

    actions = [
        item for item in candidate.proposed_actions if item.action_id == action_id
    ]
    if len(actions) != 1:
        raise FailClosedError("execution requires one semantically conformed action")
    action = actions[0]
    base = workspace.base_workspace
    return SemanticWorkspaceExecutionBinding(
        tenant_id=base.spec.tenant_id,
        work_unit_id=base.spec.work_unit_id,
        workspace_id=base.spec.workspace_id,
        workspace_digest=workspace.workspace_digest,
        workspace_expires_at=base.spec.expires_at,
        program_ref=base.spec.program_ref,
        program_digest=base.spec.program_digest,
        invocation_id=candidate.invocation_id,
        candidate_id=candidate.candidate_id,
        candidate_digest=candidate.candidate_digest,
        proposed_action=action,
        proposed_action_digest=canonical_digest(action.model_dump(mode="json")),
        conformance_report_id=report.report_id,
        conformance_digest=report.report_digest,
        source_state_root=base.projection.source_state_root,
        conformed_state_root=report.evaluated_state_root,
        source_event_position=base.projection.source_event_position,
        conformed_at=report.evaluated_at,
        dependency_digest=base.projection.dependency_digest,
        dependencies=tuple(
            StateDependency(**item.model_dump(mode="python"))
            for item in base.projection.dependencies
        ),
        semantic_contract_digest=workspace.semantic_contract.contract_digest,
        ontology_id=workspace.semantic_contract.ontology_id,
        ontology_version=workspace.semantic_contract.ontology_version,
    )
