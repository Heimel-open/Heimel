from __future__ import annotations

from base64 import b64decode
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .common import canonical_digest
from .workspace import ProposedAction, StateDependency

_SEAL_ALGORITHM = "X25519+HKDF-SHA256+AES-256-GCM"


def _decoded_length(value: str, *, label: str) -> int:
    try:
        return len(b64decode(value, validate=True))
    except Exception as exc:
        raise ValueError(f"{label} must be valid base64") from exc


class ExecutionBoundaryKey(BaseModel):
    schema_version: Literal["execution_boundary_key.v1"] = "execution_boundary_key.v1"
    key_ref: str
    boundary_id: str
    public_key_b64: str
    valid_from: datetime
    valid_until: datetime
    purpose: Literal["JIT_SEMANTIC_DISCLOSURE"] = "JIT_SEMANTIC_DISCLOSURE"
    algorithm: Literal["X25519+HKDF-SHA256+AES-256-GCM"] = _SEAL_ALGORITHM
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_key(self) -> ExecutionBoundaryKey:
        if not self.key_ref or not self.boundary_id:
            raise ValueError("execution boundary key identity is required")
        if self.valid_until <= self.valid_from:
            raise ValueError("execution boundary key validity is invalid")
        if _decoded_length(self.public_key_b64, label="boundary public key") != 32:
            raise ValueError("boundary public key must be 32-byte X25519 material")
        return self


class SealedConsequenceAction(BaseModel):
    schema_version: Literal["sealed_consequence_action.v1"] = (
        "sealed_consequence_action.v1"
    )
    envelope_id: str
    tenant_id: str
    work_unit_id: str
    workspace_id: str
    action_id: str
    action_commitment: str = Field(pattern=r"^[0-9a-f]{64}$")
    recipient_boundary_id: str
    recipient_key_ref: str
    ephemeral_public_key_b64: str
    nonce_b64: str
    ciphertext_b64: str
    aad_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    sealed_at: datetime
    valid_until: datetime
    disclosure_audience: Literal["REHT_EXECUTION_BOUNDARY"] = (
        "REHT_EXECUTION_BOUNDARY"
    )
    unseal_effect: Literal["NO_EXECUTION_EFFECT"] = "NO_EXECUTION_EFFECT"
    envelope_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"envelope_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_envelope(self) -> SealedConsequenceAction:
        required = (
            self.envelope_id,
            self.tenant_id,
            self.work_unit_id,
            self.workspace_id,
            self.action_id,
            self.recipient_boundary_id,
            self.recipient_key_ref,
            self.ciphertext_b64,
        )
        if any(not value for value in required):
            raise ValueError("sealed consequence action requires explicit bindings")
        if self.valid_until <= self.sealed_at:
            raise ValueError("sealed consequence action validity is invalid")
        if _decoded_length(
            self.ephemeral_public_key_b64, label="ephemeral public key"
        ) != 32:
            raise ValueError("ephemeral public key must be 32-byte X25519 material")
        if _decoded_length(self.nonce_b64, label="nonce") != 12:
            raise ValueError("AES-GCM nonce must be 12 bytes")
        if _decoded_length(self.ciphertext_b64, label="ciphertext") < 17:
            raise ValueError("sealed consequence ciphertext is invalid")
        if self.envelope_digest and self.envelope_digest != self.computed_digest:
            raise ValueError("sealed consequence action digest mismatch")
        return self


class ExecutionBoundaryDisclosureContext(BaseModel):
    schema_version: Literal["execution_boundary_disclosure_context.v1"] = (
        "execution_boundary_disclosure_context.v1"
    )
    disclosure_id: str
    boundary_id: str
    key_ref: str
    tenant_id: str
    work_unit_id: str
    workspace_id: str
    reht_evaluation_id: str
    fresh_state_root: str = Field(pattern=r"^[0-9a-f]{64}$")
    fresh_authority_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    fresh_evidence_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    disclosed_at: datetime
    at_execution_boundary: Literal[True] = True
    commit_performed: Literal[False] = False
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_context(self) -> ExecutionBoundaryDisclosureContext:
        required = (
            self.disclosure_id,
            self.boundary_id,
            self.key_ref,
            self.tenant_id,
            self.work_unit_id,
            self.workspace_id,
            self.reht_evaluation_id,
        )
        if any(not value for value in required):
            raise ValueError("execution-boundary disclosure context is incomplete")
        return self

    @property
    def context_digest(self) -> str:
        return canonical_digest(self.model_dump(mode="json"))


class DisclosedConsequenceAction(BaseModel):
    schema_version: Literal["disclosed_consequence_action.v1"] = (
        "disclosed_consequence_action.v1"
    )
    envelope_id: str
    envelope_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    action: ProposedAction
    action_commitment: str = Field(pattern=r"^[0-9a-f]{64}$")
    disclosure_context_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    disclosed_at: datetime
    execution_effect: Literal["NONE"] = "NONE"
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_disclosure(self) -> DisclosedConsequenceAction:
        if canonical_digest(self.action.model_dump(mode="json")) != self.action_commitment:
            raise ValueError("disclosed action does not match sealed commitment")
        return self


class SealedWorkspaceExecutionBinding(BaseModel):
    schema_version: Literal["sealed_workspace_execution_binding.v1"] = (
        "sealed_workspace_execution_binding.v1"
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
    sealed_action: SealedConsequenceAction
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
    binding_digest: str = ""
    plaintext_action_exposed: Literal[False] = False
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"binding_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_binding(self) -> SealedWorkspaceExecutionBinding:
        if not self.tenant_id:
            raise ValueError("sealed execution tenant binding is required")
        if self.conformed_at >= self.workspace_expires_at:
            raise ValueError("conformance must precede workspace expiry")
        if bool(self.program_ref) != bool(self.program_digest):
            raise ValueError("execution program ref and digest must be bound together")
        if self.sealed_action.envelope_digest != self.sealed_action.computed_digest:
            raise ValueError("sealed action envelope is unsealed")
        if (
            self.sealed_action.tenant_id != self.tenant_id
            or self.sealed_action.work_unit_id != self.work_unit_id
            or self.sealed_action.workspace_id != self.workspace_id
        ):
            raise ValueError("sealed action context binding mismatch")
        if self.sealed_action.action_commitment != self.proposed_action_digest:
            raise ValueError("sealed action commitment mismatch")
        if self.sealed_action.valid_until > self.workspace_expires_at:
            raise ValueError("sealed action cannot outlive workspace")
        expected_dependency_digest = canonical_digest(
            [item.model_dump(mode="json") for item in self.dependencies]
        )
        if expected_dependency_digest != self.dependency_digest:
            raise ValueError("sealed execution dependency digest mismatch")
        dependency_refs = {item.ref for item in self.dependencies}
        missing_contracts = [
            contract_id
            for contract_id in self.governing_contract_ids
            if f"contracts:{contract_id}" not in dependency_refs
        ]
        if missing_contracts:
            raise ValueError("sealed execution governing contract dependency is missing")
        if self.binding_digest and self.binding_digest != self.computed_digest:
            raise ValueError("sealed execution binding digest mismatch")
        return self
