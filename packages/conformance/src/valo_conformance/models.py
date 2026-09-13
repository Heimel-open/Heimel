from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .canonical import canonical_digest

Digest = str
TruthStatus = Literal["CONFIRMED", "ASSERTED", "INFERRED", "CONFLICTED", "STALE", "REVOKED", "UNKNOWN"]
SurfaceType = Literal["organization_projection", "ui", "rag", "agent_memory", "adapter", "scheduler", "digital_twin", "partner", "other"]
ClaimOrigin = Literal["kernel_state", "inference", "external_evidence"]


def _aware(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value


class GovernedPresentationClaimV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["governed_presentation_claim.v1"] = "governed_presentation_claim.v1"
    claim_id: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    predicate: str = Field(min_length=1)
    value: Any
    truth_status: TruthStatus
    origin: ClaimOrigin
    evidence_refs: tuple[str, ...] = ()
    provenance_refs: tuple[str, ...] = ()
    source_object_refs: tuple[str, ...] = ()
    inferred_by: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_truth_boundary(self) -> GovernedPresentationClaimV1:
        if self.origin == "inference":
            if self.truth_status != "INFERRED":
                raise ValueError("model inference must remain INFERRED")
            if not self.inferred_by or self.confidence is None:
                raise ValueError("INFERRED claim requires inferred_by and confidence")
        if self.origin == "external_evidence" and self.truth_status == "CONFIRMED":
            raise ValueError("external evidence cannot bypass Kernel admission to CONFIRMED")
        if self.truth_status == "CONFIRMED" and (self.origin != "kernel_state" or not self.provenance_refs or not self.evidence_refs):
            raise ValueError("CONFIRMED claims require Kernel origin, provenance and evidence references")
        return self


class GovernedPresentationEnvelopeV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["governed_presentation_envelope.v1"] = "governed_presentation_envelope.v1"
    tenant_id: str = Field(min_length=1)
    surface_id: str = Field(min_length=1)
    surface_type: SurfaceType
    source_state_root: Digest = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    projected_at: datetime
    fresh_until: datetime | None = None
    claims: tuple[GovernedPresentationClaimV1, ...] = ()
    can_authorize: Literal[False] = False
    can_execute: Literal[False] = False
    can_mutate_authoritative_state: Literal[False] = False
    envelope_digest: Digest = ""

    @field_validator("projected_at")
    @classmethod
    def projected_is_aware(cls, value: datetime) -> datetime:
        return _aware(value, "projected_at")

    @field_validator("fresh_until")
    @classmethod
    def fresh_is_aware(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _aware(value, "fresh_until")

    @model_validator(mode="after")
    def validate_envelope(self) -> GovernedPresentationEnvelopeV1:
        if self.fresh_until is not None and self.fresh_until < self.projected_at:
            raise ValueError("fresh_until cannot precede projected_at")
        if self.envelope_digest and self.envelope_digest != self.computed_digest:
            raise ValueError("presentation envelope digest mismatch")
        return self

    def canonical_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"envelope_digest"})

    @property
    def computed_digest(self) -> Digest:
        return canonical_digest(self.canonical_payload())

    def is_fresh(self, moment: datetime) -> bool:
        moment = _aware(moment, "moment")
        return self.fresh_until is None or moment <= self.fresh_until


class SurfaceConformanceObservationV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["surface_conformance_observation.v1"] = "surface_conformance_observation.v1"
    surface_id: str = Field(min_length=1)
    surface_type: SurfaceType
    used_for_execution: bool = False
    current_kernel_state_root: Digest | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    owns_authoritative_state: bool = False
    writes_world_state_directly: bool = False
    creates_authority: bool = False
    issues_clearance: bool = False
    promotes_inference_to_confirmed: bool = False
    overrides_kernel_conflict: bool = False
    executes_without_fresh_kernel_context: bool = False
    external_effect_claimed: bool = False
    receipt_refs: tuple[str, ...] = ()


class SurfaceConformanceReportV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["surface_conformance_report.v1"] = "surface_conformance_report.v1"
    surface_id: str
    passed: bool
    findings: tuple[str, ...]
    can_issue_clearance: Literal[False] = False
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    report_digest: Digest = ""

    @model_validator(mode="after")
    def validate_report(self) -> SurfaceConformanceReportV1:
        if self.passed != (not self.findings):
            raise ValueError("conformance pass flag differs from findings")
        if self.report_digest and self.report_digest != self.computed_digest:
            raise ValueError("conformance report digest mismatch")
        return self

    def canonical_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"report_digest"})

    @property
    def computed_digest(self) -> Digest:
        return canonical_digest(self.canonical_payload())
