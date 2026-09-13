from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .common import canonical_digest
from .workspace import (
    ConformanceMismatch,
    ConformanceOutcome,
    ConformanceReport,
    GovernedWorkspaceEnvelope,
    WorkspaceExecutionBinding,
)


class AttestationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    INVALID = "INVALID"
    REVOKED = "REVOKED"
    UNKNOWN = "UNKNOWN"


class ExecutionSubstrateRequirement(BaseModel):
    schema_version: Literal["execution_substrate_requirement.v1"] = (
        "execution_substrate_requirement.v1"
    )
    substrate_kind: Literal["TEE"] = "TEE"
    allowed_tee_types: tuple[str, ...]
    allowed_measurements: tuple[str, ...] = ()
    max_attestation_age_seconds: int = Field(default=300, gt=0)
    expected_model_digest: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    expected_workload_digest: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    require_confidentiality: Literal[True] = True
    require_integrity: Literal[True] = True
    require_isolation: Literal[True] = True

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("allowed_tee_types")
    @classmethod
    def require_explicit_tee_types(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or any(not item for item in value):
            raise ValueError("TEE requirement needs explicit allowed TEE types")
        if len(set(value)) != len(value):
            raise ValueError("allowed TEE types must be unique")
        return value

    @field_validator("allowed_measurements")
    @classmethod
    def require_unique_measurements(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item for item in value):
            raise ValueError("allowed measurements must be explicit")
        if len(set(value)) != len(value):
            raise ValueError("allowed measurements must be unique")
        return value


class ExecutionSubstrateAttestation(BaseModel):
    schema_version: Literal["execution_substrate_attestation.v1"] = (
        "execution_substrate_attestation.v1"
    )
    attestation_id: str
    substrate_id: str
    substrate_kind: Literal["TEE"] = "TEE"
    tee_type: str
    gpu_identity: str
    cc_mode: str
    measurement: str
    attestation_verifier: str
    attestation_evidence_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    attested_at: datetime
    valid_until: datetime
    status: AttestationStatus
    confidentiality_protected: bool
    integrity_protected: bool
    isolation_enforced: bool
    model_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    workload_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    attestation_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"attestation_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_attestation(self) -> ExecutionSubstrateAttestation:
        required = (
            self.attestation_id,
            self.substrate_id,
            self.tee_type,
            self.gpu_identity,
            self.cc_mode,
            self.measurement,
            self.attestation_verifier,
        )
        if any(not value for value in required):
            raise ValueError("attestation identity and environment claims are required")
        if self.valid_until <= self.attested_at:
            raise ValueError("attestation validity must end after attestation time")
        if self.attestation_digest and self.attestation_digest != self.computed_digest:
            raise ValueError("execution substrate attestation digest mismatch")
        return self


def seal_execution_substrate_attestation(
    **values: object,
) -> ExecutionSubstrateAttestation:
    provisional = ExecutionSubstrateAttestation(**values)
    return provisional.model_copy(
        update={"attestation_digest": provisional.computed_digest}
    )


class AttestedGovernedWorkspaceEnvelope(BaseModel):
    schema_version: Literal["attested_governed_workspace.v1"] = (
        "attested_governed_workspace.v1"
    )
    workspace: GovernedWorkspaceEnvelope
    substrate_requirement: ExecutionSubstrateRequirement
    substrate_attestation: ExecutionSubstrateAttestation
    attested_workspace_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"attested_workspace_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_workspace(self) -> AttestedGovernedWorkspaceEnvelope:
        if self.workspace.workspace_digest != self.workspace.computed_digest:
            raise ValueError("nested governed workspace is unsealed")
        attestation = self.substrate_attestation
        if attestation.attestation_digest != attestation.computed_digest:
            raise ValueError("execution substrate attestation is unsealed")
        if (
            self.attested_workspace_digest
            and self.attested_workspace_digest != self.computed_digest
        ):
            raise ValueError("attested governed workspace digest mismatch")
        return self


class AttestedConformanceReport(BaseModel):
    schema_version: Literal["attested_workspace_conformance.v1"] = (
        "attested_workspace_conformance.v1"
    )
    base_report: ConformanceReport
    attested_workspace_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    substrate_attestation_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    outcome: ConformanceOutcome
    mismatches: tuple[ConformanceMismatch, ...] = ()
    evaluated_at: datetime
    report_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"report_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_report(self) -> AttestedConformanceReport:
        if self.base_report.report_digest != self.base_report.computed_digest:
            raise ValueError("base conformance report is unsealed")
        if self.evaluated_at != self.base_report.evaluated_at:
            raise ValueError("attested conformance time must match base report")
        if self.outcome == ConformanceOutcome.PASS and self.mismatches:
            raise ValueError("passing attested conformance cannot contain mismatches")
        if self.outcome != ConformanceOutcome.PASS and not self.mismatches:
            raise ValueError("non-passing attested conformance needs a mismatch")
        if self.report_digest and self.report_digest != self.computed_digest:
            raise ValueError("attested conformance report digest mismatch")
        return self


class AttestedWorkspaceExecutionBinding(BaseModel):
    schema_version: Literal["attested_workspace_execution_binding.v1"] = (
        "attested_workspace_execution_binding.v1"
    )
    base_binding: WorkspaceExecutionBinding
    attested_workspace_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    substrate_attestation_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    substrate_id: str
    tee_type: str
    gpu_identity: str
    cc_mode: str
    measurement: str
    attestation_verifier: str
    attestation_evidence_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    attested_at: datetime
    attestation_valid_until: datetime
    model_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    workload_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    binding_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"binding_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_binding(self) -> AttestedWorkspaceExecutionBinding:
        if self.attested_at > self.base_binding.conformed_at:
            raise ValueError("attestation cannot postdate conformance")
        if self.attestation_valid_until <= self.base_binding.conformed_at:
            raise ValueError("attestation must be valid at conformance")
        if self.binding_digest and self.binding_digest != self.computed_digest:
            raise ValueError("attested execution binding digest mismatch")
        return self
