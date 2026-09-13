from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .common import canonical_digest


class SovereignArtifactKind(str, Enum):
    IDENTITY = "IDENTITY"
    AUTHORITATIVE_STATE = "AUTHORITATIVE_STATE"
    RIGHTS = "RIGHTS"
    RELATIONSHIPS = "RELATIONSHIPS"
    EVIDENCE_CHAIN = "EVIDENCE_CHAIN"
    GOVERNANCE = "GOVERNANCE"


REQUIRED_SOVEREIGN_ARTIFACT_KINDS = frozenset(SovereignArtifactKind)


class SovereignArtifact(BaseModel):
    schema_version: Literal["sovereign_artifact.v1"] = "sovereign_artifact.v1"
    artifact_id: str
    kind: SovereignArtifactKind
    artifact_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    format_id: str
    principal_controlled_copy: bool = False
    custodian_ids: tuple[str, ...] = ()
    provider_neutral_format: Literal[True] = True
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_artifact(self) -> SovereignArtifact:
        if not self.artifact_id or not self.format_id:
            raise ValueError("sovereign artifact identity and format are required")
        if not self.principal_controlled_copy and not self.custodian_ids:
            raise ValueError("sovereign artifact needs a reconstructible custody route")
        if any(not item for item in self.custodian_ids):
            raise ValueError("sovereign artifact custodians must be explicit")
        if len(set(self.custodian_ids)) != len(self.custodian_ids):
            raise ValueError("sovereign artifact custodians must be unique")
        return self


class RecoveryAnchor(BaseModel):
    schema_version: Literal["recovery_anchor.v1"] = "recovery_anchor.v1"
    anchor_id: str
    independence_domain: str
    provider_id: str | None = None
    principal_controlled: bool = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_anchor(self) -> RecoveryAnchor:
        if not self.anchor_id or not self.independence_domain:
            raise ValueError("recovery anchor and independence domain are required")
        if self.provider_id is not None and not self.provider_id:
            raise ValueError("provider id must be explicit when present")
        if not self.principal_controlled and self.provider_id is None:
            raise ValueError("non-principal recovery anchor needs an explicit custodian")
        return self


class RecoveryPlan(BaseModel):
    schema_version: Literal["recovery_plan.v1"] = "recovery_plan.v1"
    recovery_method: str
    threshold: int = Field(ge=1)
    anchors: tuple[RecoveryAnchor, ...]
    logical_principal_is_root: Literal[True] = True
    rotatable_credentials: Literal[True] = True
    single_provider_dependency: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_plan(self) -> RecoveryPlan:
        if not self.recovery_method or not self.anchors:
            raise ValueError("recovery method and anchors are required")
        anchor_ids = [item.anchor_id for item in self.anchors]
        if len(set(anchor_ids)) != len(anchor_ids):
            raise ValueError("recovery anchor ids must be unique")
        domains = {item.independence_domain for item in self.anchors}
        if self.threshold > len(domains):
            raise ValueError("recovery threshold exceeds independent recovery domains")
        return self


class CapabilityProviderBinding(BaseModel):
    schema_version: Literal["capability_provider_binding.v1"] = (
        "capability_provider_binding.v1"
    )
    provider_id: str
    capability_classes: tuple[str, ...]
    state_role: Literal["NON_AUTHORITATIVE"] = "NON_AUTHORITATIVE"
    may_keep_ephemeral_state: bool = True
    required_for_reconstruction: Literal[False] = False
    can_issue_clearance: Literal[False] = False
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("capability_classes")
    @classmethod
    def validate_capabilities(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or any(not item for item in value):
            raise ValueError("provider needs explicit capability classes")
        if len(set(value)) != len(value):
            raise ValueError("provider capability classes must be unique")
        return value

    @field_validator("provider_id")
    @classmethod
    def validate_provider_id(cls, value: str) -> str:
        if not value:
            raise ValueError("provider id is required")
        return value


class ExternalIdentityBridge(BaseModel):
    schema_version: Literal["external_identity_bridge.v1"] = (
        "external_identity_bridge.v1"
    )
    bridge_id: str
    principal_id: str
    external_system_id: str
    external_subject_ref: str
    external_subject_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    mapping_only: Literal[True] = True
    external_identifier_is_not_root_identity: Literal[True] = True
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_bridge(self) -> ExternalIdentityBridge:
        required = (
            self.bridge_id,
            self.principal_id,
            self.external_system_id,
            self.external_subject_ref,
        )
        if any(not item for item in required):
            raise ValueError("external identity bridge bindings are required")
        return self


class SovereignDomainManifest(BaseModel):
    schema_version: Literal["sovereign_domain_manifest.v1"] = (
        "sovereign_domain_manifest.v1"
    )
    manifest_id: str
    tenant_id: str
    principal_id: str
    source_state_root: str = Field(pattern=r"^[0-9a-f]{64}$")
    event_chain_head_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifacts: tuple[SovereignArtifact, ...]
    recovery_plan: RecoveryPlan
    providers: tuple[CapabilityProviderBinding, ...] = ()
    manifest_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"manifest_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_manifest(self) -> SovereignDomainManifest:
        if not self.manifest_id or not self.tenant_id or not self.principal_id:
            raise ValueError("manifest identity, tenant and principal are required")
        if not self.artifacts:
            raise ValueError("sovereign manifest requires reconstruction artifacts")
        artifact_ids = [item.artifact_id for item in self.artifacts]
        if len(set(artifact_ids)) != len(artifact_ids):
            raise ValueError("sovereign artifact ids must be unique")
        kinds = {item.kind for item in self.artifacts}
        missing = REQUIRED_SOVEREIGN_ARTIFACT_KINDS - kinds
        if missing:
            names = ", ".join(sorted(item.value for item in missing))
            raise ValueError(f"sovereign manifest is missing required artifacts: {names}")
        provider_ids = [item.provider_id for item in self.providers]
        if len(set(provider_ids)) != len(provider_ids):
            raise ValueError("provider ids must be unique")
        known_providers = set(provider_ids)
        unknown_custodians = sorted(
            {
                custodian
                for artifact in self.artifacts
                for custodian in artifact.custodian_ids
                if custodian not in known_providers
            }
        )
        recovery_provider_ids = {
            anchor.provider_id
            for anchor in self.recovery_plan.anchors
            if anchor.provider_id is not None
        }
        unknown_recovery_providers = sorted(recovery_provider_ids - known_providers)
        if unknown_custodians or unknown_recovery_providers:
            unknown = sorted(set(unknown_custodians) | set(unknown_recovery_providers))
            raise ValueError(
                "manifest references unknown providers: " + ", ".join(unknown)
            )
        if self.manifest_digest and self.manifest_digest != self.computed_digest:
            raise ValueError("sovereign domain manifest digest mismatch")
        return self


class ProviderLossScenario(BaseModel):
    schema_version: Literal["provider_loss_scenario.v1"] = "provider_loss_scenario.v1"
    scenario_id: str
    lost_provider_ids: tuple[str, ...]

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_scenario(self) -> ProviderLossScenario:
        if not self.scenario_id or not self.lost_provider_ids:
            raise ValueError("provider-loss scenario needs an id and lost providers")
        if any(not item for item in self.lost_provider_ids):
            raise ValueError("lost provider ids must be explicit")
        if len(set(self.lost_provider_ids)) != len(self.lost_provider_ids):
            raise ValueError("lost provider ids must be unique")
        return self


class SovereigntyOutcome(str, Enum):
    PASS = "PASS"
    DENY = "DENY"


class SovereigntyViolation(BaseModel):
    code: str
    detail: str
    artifact_id: str | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)


class SovereigntyAssessment(BaseModel):
    schema_version: Literal["sovereignty_assessment.v1"] = "sovereignty_assessment.v1"
    assessment_id: str
    manifest_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    scenario_id: str
    lost_provider_ids: tuple[str, ...]
    outcome: SovereigntyOutcome
    violations: tuple[SovereigntyViolation, ...] = ()
    degraded_capability_classes: tuple[str, ...] = ()
    capability_degradation_allowed: Literal[True] = True
    assessed_at: datetime
    assessment_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"assessment_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_assessment(self) -> SovereigntyAssessment:
        if self.outcome is SovereigntyOutcome.PASS and self.violations:
            raise ValueError("passing sovereignty assessment cannot contain violations")
        if self.outcome is SovereigntyOutcome.DENY and not self.violations:
            raise ValueError("denied sovereignty assessment needs a violation")
        if len(set(self.degraded_capability_classes)) != len(
            self.degraded_capability_classes
        ):
            raise ValueError("degraded capability classes must be unique")
        if self.assessment_digest and self.assessment_digest != self.computed_digest:
            raise ValueError("sovereignty assessment digest mismatch")
        return self


class DisclosureAuthorization(BaseModel):
    schema_version: Literal["disclosure_authorization.v1"] = (
        "disclosure_authorization.v1"
    )
    authorization_id: str
    tenant_id: str
    principal_id: str
    destination_id: str
    purpose_id: str
    projection_id: str
    projection_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_state_root: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_event_position: int = Field(ge=0)
    allowed_object_refs: tuple[str, ...]
    authority_basis_refs: tuple[str, ...]
    authority_state_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    issued_at: datetime
    valid_until: datetime
    authorization_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False
    disclosure_only: Literal[True] = True

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"authorization_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_authorization(self) -> DisclosureAuthorization:
        required = (
            self.authorization_id,
            self.tenant_id,
            self.principal_id,
            self.destination_id,
            self.purpose_id,
            self.projection_id,
        )
        if any(not item for item in required):
            raise ValueError("disclosure identity and bindings are required")
        if self.valid_until <= self.issued_at:
            raise ValueError("disclosure authorization must expire after issue")
        for label, refs in (
            ("allowed object", self.allowed_object_refs),
            ("authority basis", self.authority_basis_refs),
        ):
            if not refs or any(not item for item in refs):
                raise ValueError(f"{label} refs must be explicit")
            if len(set(refs)) != len(refs):
                raise ValueError(f"{label} refs must be unique")
        if self.authorization_digest and self.authorization_digest != self.computed_digest:
            raise ValueError("disclosure authorization digest mismatch")
        return self


class DisclosureOutcome(str, Enum):
    PASS = "PASS"
    DENY = "DENY"


class DisclosureMismatch(BaseModel):
    code: str
    detail: str

    model_config = ConfigDict(extra="forbid", frozen=True)


class DisclosureAssessment(BaseModel):
    schema_version: Literal["disclosure_assessment.v1"] = "disclosure_assessment.v1"
    assessment_id: str
    authorization_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    projection_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    destination_id: str
    outcome: DisclosureOutcome
    mismatches: tuple[DisclosureMismatch, ...] = ()
    evaluated_at: datetime
    assessment_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False
    creates_disclosure: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"assessment_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_assessment(self) -> DisclosureAssessment:
        if self.outcome is DisclosureOutcome.PASS and self.mismatches:
            raise ValueError("passing disclosure assessment cannot contain mismatches")
        if self.outcome is DisclosureOutcome.DENY and not self.mismatches:
            raise ValueError("denied disclosure assessment needs a mismatch")
        if self.assessment_digest and self.assessment_digest != self.computed_digest:
            raise ValueError("disclosure assessment digest mismatch")
        return self
