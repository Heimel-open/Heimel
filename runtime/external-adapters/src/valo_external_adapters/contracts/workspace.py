from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .common import TruthStatus, canonical_digest


class CandidateKind(str, Enum):
    ARTIFACT = "ARTIFACT"
    EVIDENCE = "EVIDENCE"
    STATE_TRANSITION = "STATE_TRANSITION"
    EXTERNAL_ACTION = "EXTERNAL_ACTION"
    DEFER = "DEFER"


class ConformanceOutcome(str, Enum):
    PASS = "PASS"
    REDO = "REDO"
    DEFER = "DEFER"
    STEP_UP = "STEP_UP"
    DENY = "DENY"
    HALT = "HALT"


class ProjectionSelector(BaseModel):
    collection: Literal[
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
    ]
    object_ids: tuple[str, ...]

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("object_ids")
    @classmethod
    def require_object_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or any(not item for item in value):
            raise ValueError("projection selector requires explicit object ids")
        if len(set(value)) != len(value):
            raise ValueError("projection selector object ids must be unique")
        return value


class WorkspaceCapabilitySpec(BaseModel):
    capability: str
    target_refs: tuple[str, ...]
    allowed_effects: tuple[str, ...] = ()
    parameter_constraints: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_scope(self) -> WorkspaceCapabilitySpec:
        if not self.capability or not self.target_refs:
            raise ValueError("workspace capability requires capability and targets")
        if "*" in self.target_refs:
            raise ValueError("workspace capability targets must be explicit")
        if len(set(self.target_refs)) != len(self.target_refs):
            raise ValueError("workspace capability targets must be unique")
        if len(set(self.allowed_effects)) != len(self.allowed_effects):
            raise ValueError("workspace capability effects must be unique")
        return self


class WorkspaceSpec(BaseModel):
    workspace_id: str
    work_unit_id: str
    tenant_id: str
    purpose_id: str
    program_ref: str | None = None
    program_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    governing_contract_ids: tuple[str, ...] = ()
    selectors: tuple[ProjectionSelector, ...]
    capabilities: tuple[WorkspaceCapabilitySpec, ...]
    allowed_output_kinds: tuple[CandidateKind, ...]
    expires_at: datetime
    max_actions: int = Field(default=1, ge=0)
    step_up_required: bool = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_contract(self) -> WorkspaceSpec:
        required = (
            self.workspace_id,
            self.work_unit_id,
            self.tenant_id,
            self.purpose_id,
        )
        if any(not value for value in required):
            raise ValueError("workspace identity, tenant and purpose are required")
        if not self.selectors or not self.allowed_output_kinds:
            raise ValueError(
                "workspace requires a bounded projection and output contract"
            )
        capabilities = [item.capability for item in self.capabilities]
        if len(set(capabilities)) != len(capabilities):
            raise ValueError("workspace capabilities must be unique")
        if bool(self.program_ref) != bool(self.program_digest):
            raise ValueError("workspace program ref and digest must be bound together")
        if any(not item for item in self.governing_contract_ids):
            raise ValueError("governing contract ids must be explicit")
        if len(set(self.governing_contract_ids)) != len(self.governing_contract_ids):
            raise ValueError("governing contract ids must be unique")
        return self


class StateDependency(BaseModel):
    collection: str
    object_id: str
    object_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    model_config = ConfigDict(extra="forbid", frozen=True)

    @property
    def ref(self) -> str:
        return f"{self.collection}:{self.object_id}"


class ProjectedObject(BaseModel):
    collection: str
    object_id: str
    payload: dict[str, Any]
    payload_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_digest(self) -> ProjectedObject:
        if canonical_digest(self.payload) != self.payload_digest:
            raise ValueError("projected object digest mismatch")
        return self

    @property
    def ref(self) -> str:
        return f"{self.collection}:{self.object_id}"


class GovernedProjectionEnvelope(BaseModel):
    projection_id: str
    tenant_id: str
    purpose_id: str
    source_state_root: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_event_position: int = Field(ge=0)
    projected_at: datetime
    expires_at: datetime
    objects: tuple[ProjectedObject, ...]
    dependencies: tuple[StateDependency, ...]
    dependency_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_projection(self) -> GovernedProjectionEnvelope:
        if self.expires_at <= self.projected_at:
            raise ValueError("projection must expire after it is created")
        refs = [item.ref for item in self.objects]
        if len(set(refs)) != len(refs):
            raise ValueError("projection object references must be unique")
        dependency_refs = [item.ref for item in self.dependencies]
        if len(set(dependency_refs)) != len(dependency_refs):
            raise ValueError("projection dependency references must be unique")
        if tuple(sorted(dependency_refs)) != tuple(dependency_refs):
            raise ValueError("projection dependencies must be sorted")
        if not set(refs).issubset(set(dependency_refs)):
            raise ValueError(
                "projection dependencies must bind every projected object"
            )
        expected = canonical_digest(
            [item.model_dump(mode="json") for item in self.dependencies]
        )
        if expected != self.dependency_digest:
            raise ValueError("projection dependency digest mismatch")
        return self


class CapabilityLease(BaseModel):
    handle_ref: str = Field(pattern=r"^capability:sha256:[0-9a-f]{64}$")
    capability: str
    target_refs: tuple[str, ...]
    allowed_effects: tuple[str, ...] = ()
    parameter_constraints: dict[str, Any] = Field(default_factory=dict)
    valid_until: datetime
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)


class GovernedWorkspaceEnvelope(BaseModel):
    schema_version: Literal["governed_workspace.v1"] = "governed_workspace.v1"
    spec: WorkspaceSpec
    projection: GovernedProjectionEnvelope
    capability_leases: tuple[CapabilityLease, ...]
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
    def validate_workspace(self) -> GovernedWorkspaceEnvelope:
        if self.spec.tenant_id != self.projection.tenant_id:
            raise ValueError("workspace tenant binding mismatch")
        if self.spec.purpose_id != self.projection.purpose_id:
            raise ValueError("workspace purpose binding mismatch")
        if self.spec.expires_at != self.projection.expires_at:
            raise ValueError("workspace expiry binding mismatch")
        expected_leases = {
            (
                item.capability,
                item.target_refs,
                item.allowed_effects,
                canonical_digest(item.parameter_constraints),
                self.spec.expires_at,
            )
            for item in self.spec.capabilities
        }
        actual_leases = {
            (
                item.capability,
                item.target_refs,
                item.allowed_effects,
                canonical_digest(item.parameter_constraints),
                item.valid_until,
            )
            for item in self.capability_leases
        }
        if expected_leases != actual_leases:
            raise ValueError("workspace capability lease binding mismatch")
        if self.workspace_digest and self.workspace_digest != self.computed_digest:
            raise ValueError("workspace digest mismatch")
        return self


class CandidateClaim(BaseModel):
    claim_id: str
    subject: str
    predicate: str
    object: str
    truth_status: TruthStatus
    source_refs: tuple[str, ...] = ()

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("truth_status")
    @classmethod
    def candidate_never_confirms(cls, value: TruthStatus) -> TruthStatus:
        if value == TruthStatus.CONFIRMED:
            raise ValueError("worker candidate cannot create CONFIRMED truth")
        return value


class ProposedAction(BaseModel):
    action_id: str
    capability: str
    target: str
    purpose_id: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    declared_effects: tuple[str, ...] = ()

    model_config = ConfigDict(extra="forbid", frozen=True)


class ArtifactContextBinding(BaseModel):
    schema_version: Literal["artifact_context_binding.v1"] = "artifact_context_binding.v1"
    artifact_ref: str
    artifact_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    workspace_id: str
    workspace_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    invocation_id: str
    candidate_id: str
    worker_id: str
    session_id: str
    continuation_nonce: str
    predecessor_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    producer_model_ref: str | None = None
    binding_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False
    single_use_required: Literal[True] = True

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"binding_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_binding(self) -> ArtifactContextBinding:
        required = (
            self.artifact_ref,
            self.workspace_id,
            self.invocation_id,
            self.candidate_id,
            self.worker_id,
            self.session_id,
            self.continuation_nonce,
        )
        if any(not value for value in required):
            raise ValueError("artifact continuation context is required")
        if self.predecessor_digest == self.artifact_digest:
            raise ValueError("artifact cannot name itself as predecessor")
        if self.binding_digest and self.binding_digest != self.computed_digest:
            raise ValueError("artifact context binding digest mismatch")
        return self


class CandidateResult(BaseModel):
    schema_version: Literal["workspace_candidate.v1"] = "workspace_candidate.v1"
    candidate_id: str
    invocation_id: str
    worker_id: str
    workspace_id: str
    workspace_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    output_kind: CandidateKind
    claims: tuple[CandidateClaim, ...] = ()
    proposed_actions: tuple[ProposedAction, ...] = ()
    artifact_refs: tuple[str, ...] = ()
    artifact_bindings: tuple[ArtifactContextBinding, ...] = ()
    unknowns: tuple[str, ...] = ()
    candidate_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"candidate_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_candidate(self) -> CandidateResult:
        required = (
            self.candidate_id,
            self.invocation_id,
            self.worker_id,
            self.workspace_id,
        )
        if any(not value for value in required):
            raise ValueError("candidate identity and workspace binding are required")
        refs = tuple(binding.artifact_ref for binding in self.artifact_bindings)
        if self.artifact_refs and not self.artifact_bindings:
            raise ValueError("artifact refs require explicit context bindings")
        if self.artifact_bindings and self.artifact_refs != refs:
            raise ValueError("artifact refs must exactly match context bindings")
        if len(set(refs)) != len(refs):
            raise ValueError("artifact context bindings must be unique")
        for binding in self.artifact_bindings:
            if binding.binding_digest != binding.computed_digest:
                raise ValueError("artifact context binding is unsealed")
            if (
                binding.workspace_id != self.workspace_id
                or binding.workspace_digest != self.workspace_digest
            ):
                raise ValueError("artifact is bound to another workspace")
            if binding.invocation_id != self.invocation_id:
                raise ValueError("artifact is bound to another invocation")
            if binding.candidate_id != self.candidate_id:
                raise ValueError("artifact is bound to another candidate")
            if binding.worker_id != self.worker_id:
                raise ValueError("artifact is bound to another worker")
        if self.candidate_digest and self.candidate_digest != self.computed_digest:
            raise ValueError("candidate digest mismatch")
        return self


class ConformanceMismatch(BaseModel):
    code: str
    detail: str
    pointer: str | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)


class ConformanceReport(BaseModel):
    schema_version: Literal["workspace_conformance.v1"] = "workspace_conformance.v1"
    report_id: str
    workspace_id: str
    workspace_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_id: str
    candidate_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    evaluated_state_root: str = Field(pattern=r"^[0-9a-f]{64}$")
    dependency_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    outcome: ConformanceOutcome
    mismatches: tuple[ConformanceMismatch, ...] = ()
    evaluated_at: datetime
    report_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"report_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_report(self) -> ConformanceReport:
        if self.outcome == ConformanceOutcome.PASS and self.mismatches:
            raise ValueError("passing conformance report cannot contain mismatches")
        if self.outcome != ConformanceOutcome.PASS and not self.mismatches:
            raise ValueError("non-passing conformance report requires a mismatch")
        if self.report_digest and self.report_digest != self.computed_digest:
            raise ValueError("conformance report digest mismatch")
        return self


class WorkspaceExecutionBinding(BaseModel):
    schema_version: Literal["workspace_execution_binding.v1"] = (
        "workspace_execution_binding.v1"
    )
    tenant_id: str
    work_unit_id: str
    workspace_id: str
    workspace_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    workspace_expires_at: datetime
    program_ref: str | None = None
    program_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    governing_contract_ids: tuple[str, ...] = ()
    invocation_id: str
    candidate_id: str
    candidate_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    proposed_action: ProposedAction
    proposed_action_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    conformance_report_id: str
    conformance_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_state_root: str = Field(pattern=r"^[0-9a-f]{64}$")
    conformed_state_root: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_event_position: int = Field(ge=0)
    conformed_at: datetime
    dependency_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    dependencies: tuple[StateDependency, ...]
    conformance_outcome: Literal["PASS"] = "PASS"
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_binding(self) -> WorkspaceExecutionBinding:
        if not self.tenant_id:
            raise ValueError("execution tenant binding is required")
        if self.conformed_at >= self.workspace_expires_at:
            raise ValueError("conformance must precede workspace expiry")
        if bool(self.program_ref) != bool(self.program_digest):
            raise ValueError("execution program ref and digest must be bound together")
        if any(not item for item in self.governing_contract_ids):
            raise ValueError("execution governing contract ids must be explicit")
        if len(set(self.governing_contract_ids)) != len(self.governing_contract_ids):
            raise ValueError("execution governing contract ids must be unique")
        if (
            canonical_digest(self.proposed_action.model_dump(mode="json"))
            != self.proposed_action_digest
        ):
            raise ValueError("proposed action digest mismatch")
        expected_dependency_digest = canonical_digest(
            [item.model_dump(mode="json") for item in self.dependencies]
        )
        if expected_dependency_digest != self.dependency_digest:
            raise ValueError("execution dependency digest mismatch")
        dependency_refs = {item.ref for item in self.dependencies}
        missing_contracts = [
            contract_id
            for contract_id in self.governing_contract_ids
            if f"contracts:{contract_id}" not in dependency_refs
        ]
        if missing_contracts:
            raise ValueError("execution governing contract dependency is missing")
        return self