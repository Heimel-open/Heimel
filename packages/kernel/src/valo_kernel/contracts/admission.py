from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .common import canonical_digest
from .time import TimeWindow


class AdmissionOutcome(str, Enum):
    ADMIT = "ADMIT"
    HOLD = "HOLD"
    REJECT = "REJECT"
    QUARANTINE = "QUARANTINE"


class ProviderAdmissionDisposition(str, Enum):
    SUPPORT = "SUPPORT"
    REVIEW = "REVIEW"
    PRECLUDE = "PRECLUDE"
    QUARANTINE = "QUARANTINE"


_RACS_OUTCOME_VALUES = frozenset(
    {"ALLOW", "MODIFY", "DEFER", "DENY", "STEP_UP", "HALT"}
)


def _sorted_unique(value: tuple[str, ...], label: str) -> tuple[str, ...]:
    if any(not item for item in value):
        raise ValueError(f"{label} cannot contain empty values")
    if len(set(value)) != len(value):
        raise ValueError(f"{label} must be unique")
    return tuple(sorted(value))


class AdmissionCandidate(BaseModel):
    schema_version: Literal["kernel_admission_candidate.v1"] = (
        "kernel_admission_candidate.v1"
    )
    candidate_id: str
    tenant_id: str
    evidence_id: str
    material_type: str
    source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    subject_refs: tuple[str, ...]
    entity_refs: tuple[str, ...] = ()
    relationship_refs: tuple[str, ...] = ()
    provenance_refs: tuple[str, ...]
    contradiction_refs: tuple[str, ...] = ()
    unresolved_refs: tuple[str, ...] = ()
    captured_at: datetime
    candidate_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_create_state: Literal[False] = False
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator(
        "subject_refs",
        "entity_refs",
        "relationship_refs",
        "provenance_refs",
        "contradiction_refs",
        "unresolved_refs",
    )
    @classmethod
    def normalize_refs(
        cls, value: tuple[str, ...], info
    ) -> tuple[str, ...]:
        return _sorted_unique(value, info.field_name)

    def canonical_payload(self) -> dict:
        return self.model_dump(mode="json", exclude={"candidate_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_candidate(self) -> AdmissionCandidate:
        required = (
            self.candidate_id,
            self.tenant_id,
            self.evidence_id,
            self.material_type,
        )
        if any(not item for item in required):
            raise ValueError("admission candidate identity and material are required")
        if not self.subject_refs or not self.provenance_refs:
            raise ValueError("admission candidate requires subject and provenance refs")
        if self.candidate_digest and self.candidate_digest != self.computed_digest:
            raise ValueError("admission candidate digest mismatch")
        return self


class ProviderAdmissionAssessment(BaseModel):
    schema_version: Literal["provider_admission_assessment.v1"] = (
        "provider_admission_assessment.v1"
    )
    assessment_id: str
    provider_id: str
    tenant_id: str
    candidate_id: str
    candidate_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    disposition: ProviderAdmissionDisposition
    reason_codes: tuple[str, ...] = ()
    contradiction_refs: tuple[str, ...] = ()
    unresolved_refs: tuple[str, ...] = ()
    validity: TimeWindow
    source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    assessment_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_create_state: Literal[False] = False
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("reason_codes", "contradiction_refs", "unresolved_refs")
    @classmethod
    def normalize_refs(
        cls, value: tuple[str, ...], info
    ) -> tuple[str, ...]:
        return _sorted_unique(value, info.field_name)

    def canonical_payload(self) -> dict:
        return self.model_dump(mode="json", exclude={"assessment_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_assessment(self) -> ProviderAdmissionAssessment:
        required = (
            self.assessment_id,
            self.provider_id,
            self.tenant_id,
            self.candidate_id,
        )
        if any(not item for item in required):
            raise ValueError("provider assessment identity is required")
        if self.assessment_digest and self.assessment_digest != self.computed_digest:
            raise ValueError("provider assessment digest mismatch")
        return self


class AdmissionPolicy(BaseModel):
    schema_version: Literal["kernel_admission_policy.v1"] = (
        "kernel_admission_policy.v1"
    )
    policy_id: str
    tenant_id: str
    allowed_material_types: tuple[str, ...] = ("*",)
    trusted_provider_ids: tuple[str, ...] = ()
    required_provider_ids: tuple[str, ...] = ()
    policy_digest: str = ""
    decision_owner: Literal["VALO_KERNEL"] = "VALO_KERNEL"
    external_provider_required_by_default: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator(
        "allowed_material_types", "trusted_provider_ids", "required_provider_ids"
    )
    @classmethod
    def normalize_values(
        cls, value: tuple[str, ...], info
    ) -> tuple[str, ...]:
        return _sorted_unique(value, info.field_name)

    def canonical_payload(self) -> dict:
        return self.model_dump(mode="json", exclude={"policy_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_policy(self) -> AdmissionPolicy:
        if not self.policy_id or not self.tenant_id or not self.allowed_material_types:
            raise ValueError("admission policy identity and material scope are required")
        if not set(self.required_provider_ids).issubset(
            set(self.trusted_provider_ids)
        ):
            raise ValueError("required providers must also be trusted providers")
        if self.policy_digest and self.policy_digest != self.computed_digest:
            raise ValueError("admission policy digest mismatch")
        return self


class AdmissionDecision(BaseModel):
    schema_version: Literal["kernel_admission_decision.v1"] = (
        "kernel_admission_decision.v1"
    )
    decision_id: str
    tenant_id: str
    candidate_id: str
    evidence_id: str
    candidate_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy_id: str
    policy_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    assessment_digests: tuple[str, ...] = ()
    assessed_provider_ids: tuple[str, ...] = ()
    outcome: AdmissionOutcome
    reason_codes: tuple[str, ...]
    contradiction_refs: tuple[str, ...] = ()
    unresolved_refs: tuple[str, ...] = ()
    decided_at: datetime
    decision_digest: str = ""
    can_enter_operational_state: bool
    decision_owner: Literal["VALO_KERNEL"] = "VALO_KERNEL"
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_create_authority: Literal[False] = False
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator(
        "assessment_digests",
        "assessed_provider_ids",
        "reason_codes",
        "contradiction_refs",
        "unresolved_refs",
    )
    @classmethod
    def normalize_values(
        cls, value: tuple[str, ...], info
    ) -> tuple[str, ...]:
        normalized = _sorted_unique(value, info.field_name)
        if info.field_name == "assessment_digests" and any(
            len(item) != 64 or any(char not in "0123456789abcdef" for char in item)
            for item in normalized
        ):
            raise ValueError("assessment_digests must contain sha256 digests")
        return normalized

    def canonical_payload(self) -> dict:
        return self.model_dump(mode="json", exclude={"decision_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @property
    def is_epistemic_non_commitment(self) -> bool:
        """True only when standing remains unresolved rather than denied."""
        return self.outcome == AdmissionOutcome.HOLD

    @property
    def racs_outcome(self) -> None:
        """Admission and standing never emit a downstream RACS outcome."""
        return None

    @property
    def can_authorize_execution(self) -> bool:
        """Epistemic decisions cannot authorize execution."""
        return False

    @model_validator(mode="after")
    def validate_decision(self) -> AdmissionDecision:
        required = (
            self.decision_id,
            self.tenant_id,
            self.candidate_id,
            self.evidence_id,
            self.policy_id,
        )
        if any(not item for item in required) or not self.reason_codes:
            raise ValueError("admission decision identity and reasons are required")
        if self.outcome.value in _RACS_OUTCOME_VALUES:
            raise ValueError("epistemic admission cannot emit a RACS outcome")
        expected_operational = self.outcome == AdmissionOutcome.ADMIT
        if self.can_enter_operational_state != expected_operational:
            raise ValueError("only ADMIT may enter operational state")
        if expected_operational and (
            self.contradiction_refs or self.unresolved_refs
        ):
            raise ValueError("ADMIT cannot retain contradictions or unresolved refs")
        if self.decision_digest and self.decision_digest != self.computed_digest:
            raise ValueError("admission decision digest mismatch")
        return self

