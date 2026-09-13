from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .common import canonical_digest


class PortabilityOutcome(str, Enum):
    PASS = "PASS"
    DEGRADED = "DEGRADED"
    DENY = "DENY"


class PortableModelArtifact(BaseModel):
    schema_version: Literal["portable_model_artifact.v1"] = "portable_model_artifact.v1"
    model_id: str
    format_id: str
    graph_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    weights_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    metadata_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    semantic_contract_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    required_operators: tuple[str, ...]
    allowed_precisions: tuple[str, ...]
    minimum_memory_bytes: int = Field(ge=1)
    reference_backend_id: str
    provider_neutral_source: Literal[True] = True
    authoritative_state_role: Literal["NONE"] = "NONE"
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False
    artifact_digest: str = ""

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"artifact_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_artifact(self) -> PortableModelArtifact:
        if not self.model_id or not self.format_id or not self.reference_backend_id:
            raise ValueError("model, format and reference backend are required")
        for label, values in (
            ("operator", self.required_operators),
            ("precision", self.allowed_precisions),
        ):
            if not values or any(not value for value in values):
                raise ValueError(f"{label} requirements must be explicit")
            if len(set(values)) != len(values):
                raise ValueError(f"{label} requirements must be unique")
        if self.artifact_digest and self.artifact_digest != self.computed_digest:
            raise ValueError("portable model artifact digest mismatch")
        return self


class HardwareCapabilityProfile(BaseModel):
    schema_version: Literal["hardware_capability_profile.v1"] = (
        "hardware_capability_profile.v1"
    )
    backend_id: str
    hardware_class: str
    supported_formats: tuple[str, ...]
    supported_operators: tuple[str, ...]
    supported_precisions: tuple[str, ...]
    available_memory_bytes: int = Field(ge=1)
    trust_root_ids: tuple[str, ...] = ()
    cpu_fallback_available: bool = False
    capability_digest: str = ""
    authoritative_state_role: Literal["NONE"] = "NONE"
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"capability_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_profile(self) -> HardwareCapabilityProfile:
        if not self.backend_id or not self.hardware_class:
            raise ValueError("backend and hardware class are required")
        for label, values in (
            ("format", self.supported_formats),
            ("operator", self.supported_operators),
            ("precision", self.supported_precisions),
            ("trust root", self.trust_root_ids),
        ):
            if any(not value for value in values):
                raise ValueError(f"{label} values must be explicit")
            if len(set(values)) != len(values):
                raise ValueError(f"{label} values must be unique")
        if not self.supported_formats or not self.supported_operators or not self.supported_precisions:
            raise ValueError("hardware capability profile must declare executable support")
        if self.capability_digest and self.capability_digest != self.computed_digest:
            raise ValueError("hardware capability profile digest mismatch")
        return self


class BackendDeploymentArtifact(BaseModel):
    schema_version: Literal["backend_deployment_artifact.v1"] = (
        "backend_deployment_artifact.v1"
    )
    deployment_id: str
    portable_model_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    backend_id: str
    deployment_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    specialized: Literal[True] = True
    rebuildable_from_portable_source: Literal[True] = True
    portable_source_is_canonical: Literal[True] = True
    authoritative_state_role: Literal["NONE"] = "NONE"
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_deployment(self) -> BackendDeploymentArtifact:
        if not self.deployment_id or not self.backend_id:
            raise ValueError("deployment and backend are required")
        return self


class SemanticEquivalenceEvidence(BaseModel):
    schema_version: Literal["semantic_equivalence_evidence.v1"] = (
        "semantic_equivalence_evidence.v1"
    )
    evidence_id: str
    portable_model_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    reference_backend_id: str
    candidate_backend_id: str
    test_suite_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    tolerance_profile_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    passed: bool
    evidence_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"evidence_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_evidence(self) -> SemanticEquivalenceEvidence:
        required = (self.evidence_id, self.reference_backend_id, self.candidate_backend_id)
        if any(not value for value in required):
            raise ValueError("semantic equivalence evidence bindings are required")
        if self.evidence_digest and self.evidence_digest != self.computed_digest:
            raise ValueError("semantic equivalence evidence digest mismatch")
        return self


class ModelPortabilityAssessment(BaseModel):
    schema_version: Literal["model_portability_assessment.v1"] = (
        "model_portability_assessment.v1"
    )
    assessment_id: str
    portable_model_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    capability_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    backend_id: str
    outcome: PortabilityOutcome
    selected_precision: str | None = None
    missing_operators: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()
    semantic_equivalence_evidence_digest: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    assessment_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"assessment_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @field_validator("missing_operators", "reasons")
    @classmethod
    def unique_values(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item for item in value) or len(set(value)) != len(value):
            raise ValueError("assessment values must be explicit and unique")
        return value

    @model_validator(mode="after")
    def validate_assessment(self) -> ModelPortabilityAssessment:
        if self.outcome is PortabilityOutcome.PASS:
            if self.reasons or self.missing_operators or not self.selected_precision:
                raise ValueError("passing portability assessment cannot contain degradation")
            if self.semantic_equivalence_evidence_digest is None:
                raise ValueError("passing portability requires semantic equivalence evidence")
        else:
            if not self.reasons:
                raise ValueError("non-passing portability assessment needs a reason")
        if self.assessment_digest and self.assessment_digest != self.computed_digest:
            raise ValueError("model portability assessment digest mismatch")
        return self
