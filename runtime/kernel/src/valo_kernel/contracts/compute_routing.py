from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .common import canonical_digest


class RouteOutcome(str, Enum):
    PASS = "PASS"
    DENY = "DENY"


class ComputeNodeProfile(BaseModel):
    schema_version: Literal["compute_node_profile.v1"] = "compute_node_profile.v1"
    node_id: str
    provider_id: str
    backend_id: str
    trust_domain: str
    locality: str
    capability_classes: tuple[str, ...]
    supported_model_digests: tuple[str, ...] = ()
    latency_budget_ms: float = Field(gt=0)
    energy_budget_joules: float | None = Field(default=None, gt=0)
    cost_ceiling_minor_units: int | None = Field(default=None, ge=0)
    allows_raw_personal_data: bool = False
    profile_digest: str = ""
    state_role: Literal["NON_AUTHORITATIVE"] = "NON_AUTHORITATIVE"
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"profile_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @field_validator("capability_classes", "supported_model_digests")
    @classmethod
    def explicit_unique_values(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item for item in value) or len(set(value)) != len(value):
            raise ValueError("routing profile values must be explicit and unique")
        return value

    @model_validator(mode="after")
    def validate_profile(self) -> ComputeNodeProfile:
        if not self.node_id or not self.provider_id or not self.backend_id or not self.trust_domain:
            raise ValueError("compute node identity, backend and trust domain are required")
        if not self.capability_classes:
            raise ValueError("compute node must advertise capabilities")
        if self.profile_digest and self.profile_digest != self.computed_digest:
            raise ValueError("compute node profile digest mismatch")
        return self


class ComputeRouteRequest(BaseModel):
    schema_version: Literal["compute_route_request.v1"] = "compute_route_request.v1"
    request_id: str
    tenant_id: str
    principal_id: str
    purpose_id: str
    workload_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    portable_model_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    required_capabilities: tuple[str, ...]
    allowed_provider_ids: tuple[str, ...] = ()
    allowed_trust_domains: tuple[str, ...]
    max_latency_ms: float = Field(gt=0)
    max_cost_minor_units: int | None = Field(default=None, ge=0)
    raw_personal_data_required: bool = False
    disclosure_authorization_digest: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    source_state_root: str = Field(pattern=r"^[0-9a-f]{64}$")
    request_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"request_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_request(self) -> ComputeRouteRequest:
        required = (self.request_id, self.tenant_id, self.principal_id, self.purpose_id)
        if any(not item for item in required):
            raise ValueError("route request identity and purpose are required")
        for label, values in (
            ("capability", self.required_capabilities),
            ("provider", self.allowed_provider_ids),
            ("trust domain", self.allowed_trust_domains),
        ):
            if any(not item for item in values) or len(set(values)) != len(values):
                raise ValueError(f"{label} values must be explicit and unique")
        if not self.required_capabilities or not self.allowed_trust_domains:
            raise ValueError("route request needs capabilities and allowed trust domains")
        if self.raw_personal_data_required and self.disclosure_authorization_digest is None:
            raise ValueError("raw personal data routing requires disclosure authorization")
        if self.request_digest and self.request_digest != self.computed_digest:
            raise ValueError("compute route request digest mismatch")
        return self


class ComputeRouteCandidate(BaseModel):
    schema_version: Literal["compute_route_candidate.v1"] = "compute_route_candidate.v1"
    candidate_id: str
    request_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    node_profile_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    node_id: str
    provider_id: str
    backend_id: str
    predicted_latency_ms: float = Field(gt=0)
    predicted_cost_minor_units: int | None = Field(default=None, ge=0)
    model_portability_assessment_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"candidate_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_candidate(self) -> ComputeRouteCandidate:
        if not self.candidate_id or not self.node_id or not self.provider_id or not self.backend_id:
            raise ValueError("route candidate bindings are required")
        if self.candidate_digest and self.candidate_digest != self.computed_digest:
            raise ValueError("compute route candidate digest mismatch")
        return self


class RouteMismatch(BaseModel):
    code: str
    detail: str

    model_config = ConfigDict(extra="forbid", frozen=True)


class ComputeRouteAssessment(BaseModel):
    schema_version: Literal["compute_route_assessment.v1"] = "compute_route_assessment.v1"
    assessment_id: str
    request_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    node_profile_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    outcome: RouteOutcome
    mismatches: tuple[RouteMismatch, ...] = ()
    assessment_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False
    chooses_provider: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"assessment_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_assessment(self) -> ComputeRouteAssessment:
        if self.outcome is RouteOutcome.PASS and self.mismatches:
            raise ValueError("passing route assessment cannot contain mismatches")
        if self.outcome is RouteOutcome.DENY and not self.mismatches:
            raise ValueError("denied route assessment needs a mismatch")
        if self.assessment_digest and self.assessment_digest != self.computed_digest:
            raise ValueError("compute route assessment digest mismatch")
        return self
