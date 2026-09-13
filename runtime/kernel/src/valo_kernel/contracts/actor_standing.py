from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .common import canonical_digest
from .time import TimeWindow


class DecisionFunction(str, Enum):
    ASSESS = "ASSESS"
    RECOMMEND = "RECOMMEND"
    APPROVE = "APPROVE"
    AUTHORIZE = "AUTHORIZE"
    EXECUTE = "EXECUTE"
    VERIFY = "VERIFY"
    ACCEPT_RISK = "ACCEPT_RISK"


class RoleBindingStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"


class CompetenceDisposition(str, Enum):
    CALIBRATED = "CALIBRATED"
    CONDITIONAL = "CONDITIONAL"
    STEP_UP_REQUIRED = "STEP_UP_REQUIRED"
    NOT_CALIBRATED = "NOT_CALIBRATED"
    UNKNOWN = "UNKNOWN"


class AttentionDisposition(str, Enum):
    READY = "READY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class EligibilityDisposition(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    CONFLICTED = "CONFLICTED"
    RECUSED = "RECUSED"
    DISQUALIFIED = "DISQUALIFIED"
    UNKNOWN = "UNKNOWN"


class ConsentDisposition(str, Enum):
    SATISFIED = "SATISFIED"
    MISSING = "MISSING"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class ApprovalDisposition(str, Enum):
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class AuthorityConflictDisposition(str, Enum):
    CLEAR = "CLEAR"
    CONFLICTED = "CONFLICTED"
    UNKNOWN = "UNKNOWN"


class StandingDecision(str, Enum):
    PASS = "PASS"
    STEP_UP = "STEP_UP"
    DENY = "DENY"


class ActiveRoleBinding(BaseModel):
    schema_version: Literal["active_role_binding.v1"] = "active_role_binding.v1"
    role_binding_id: str
    actor_id: str
    role_id: str
    principal_id: str
    decision_functions: tuple[DecisionFunction, ...]
    capability_scope: tuple[str, ...] = ()
    resource_scope: tuple[str, ...] = ()
    jurisdiction_refs: tuple[str, ...] = ()
    basis_ref: str
    evidence_refs: tuple[str, ...]
    validity: TimeWindow
    status: RoleBindingStatus = RoleBindingStatus.ACTIVE
    revoked_at: datetime | None = None
    revocation_ref: str | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_role(self) -> ActiveRoleBinding:
        required = (
            self.role_binding_id,
            self.actor_id,
            self.role_id,
            self.principal_id,
            self.basis_ref,
        )
        if any(not item for item in required):
            raise ValueError(
                "role binding identity, actor, role, principal and basis are required"
            )
        if not self.decision_functions:
            raise ValueError("role binding requires at least one decision function")
        if not self.evidence_refs:
            raise ValueError("role binding requires evidence")
        if self.revoked_at is not None and not self.revocation_ref:
            raise ValueError("role revocation requires revocation_ref")
        return self

    def is_active(self, moment: datetime) -> bool:
        if self.status is not RoleBindingStatus.ACTIVE:
            return False
        if self.revoked_at is not None and self.revoked_at <= moment:
            return False
        return self.validity.is_active_at(moment)


class CalibratedCompetence(BaseModel):
    schema_version: Literal["calibrated_competence.v1"] = "calibrated_competence.v1"
    competence_id: str
    actor_id: str
    role_binding_ref: str
    decision_function: DecisionFunction
    capability: str
    domain: str
    system_refs: tuple[str, ...] = ()
    context_refs: tuple[str, ...] = ()
    risk_ceiling: str | None = None
    credential_refs: tuple[str, ...] = ()
    demonstrated_capability_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...]
    calibration_basis: str
    evaluated_at: datetime
    validity: TimeWindow
    disposition: CompetenceDisposition
    confidence: float = Field(ge=0.0, le=1.0)
    limitations: tuple[str, ...] = ()
    revalidation_triggers: tuple[str, ...] = ()

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_competence(self) -> CalibratedCompetence:
        required = (
            self.competence_id,
            self.actor_id,
            self.role_binding_ref,
            self.capability,
            self.domain,
            self.calibration_basis,
        )
        if any(not item for item in required):
            raise ValueError("calibrated competence fields are required")
        if not self.evidence_refs:
            raise ValueError("calibrated competence requires evidence")
        if not self.validity.is_active_at(self.evaluated_at):
            raise ValueError(
                "calibration evaluation must fall inside its validity window"
            )
        return self

    def is_current(self, moment: datetime) -> bool:
        return self.validity.is_active_at(moment)


class AttentionState(BaseModel):
    schema_version: Literal["attention_state.v1"] = "attention_state.v1"
    attention_id: str
    actor_id: str
    role_binding_ref: str
    observed_at: datetime
    valid_until: datetime
    disposition: AttentionDisposition
    evidence_refs: tuple[str, ...]
    limitations: tuple[str, ...] = ()

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_attention(self) -> AttentionState:
        if self.valid_until <= self.observed_at:
            raise ValueError("attention state requires a positive validity window")
        if not self.evidence_refs:
            raise ValueError("attention state requires evidence")
        return self

    def is_current(self, moment: datetime) -> bool:
        return self.observed_at <= moment < self.valid_until


class EligibilityState(BaseModel):
    schema_version: Literal["eligibility_state.v1"] = "eligibility_state.v1"
    eligibility_id: str
    actor_id: str
    role_binding_ref: str
    principal_id: str
    jurisdiction_ref: str
    disposition: EligibilityDisposition
    evaluated_at: datetime
    valid_until: datetime
    evidence_refs: tuple[str, ...]
    conflict_refs: tuple[str, ...] = ()

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_eligibility(self) -> EligibilityState:
        if self.valid_until <= self.evaluated_at:
            raise ValueError("eligibility state requires a positive validity window")
        if not self.evidence_refs:
            raise ValueError("eligibility state requires evidence")
        if self.disposition in {
            EligibilityDisposition.CONFLICTED,
            EligibilityDisposition.DISQUALIFIED,
        } and not self.conflict_refs:
            raise ValueError(
                "conflicted or disqualified eligibility must identify conflict evidence"
            )
        return self

    def is_current(self, moment: datetime) -> bool:
        return self.evaluated_at <= moment < self.valid_until


class ConsentState(BaseModel):
    schema_version: Literal["consent_state.v1"] = "consent_state.v1"
    consent_id: str
    subject_id: str
    action_id: str
    purpose_id: str
    disposition: ConsentDisposition
    observed_at: datetime
    valid_until: datetime
    evidence_refs: tuple[str, ...]

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_consent(self) -> ConsentState:
        if self.valid_until <= self.observed_at:
            raise ValueError("consent state requires a positive validity window")
        if not self.evidence_refs:
            raise ValueError("consent state requires evidence")
        return self

    def is_current(self, moment: datetime) -> bool:
        return self.observed_at <= moment < self.valid_until


class ApprovalAttestation(BaseModel):
    schema_version: Literal["approval_attestation.v1"] = "approval_attestation.v1"
    approval_id: str
    approver_id: str
    approver_role_ref: str
    action_id: str
    decision_function: DecisionFunction
    disposition: ApprovalDisposition
    issued_at: datetime
    valid_until: datetime
    evidence_refs: tuple[str, ...]

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_approval(self) -> ApprovalAttestation:
        if self.valid_until <= self.issued_at:
            raise ValueError("approval attestation requires a positive validity window")
        if not self.evidence_refs:
            raise ValueError("approval attestation requires evidence")
        return self

    def is_current(self, moment: datetime) -> bool:
        return self.issued_at <= moment < self.valid_until


class ApprovalRequirement(BaseModel):
    schema_version: Literal["approval_requirement.v1"] = "approval_requirement.v1"
    required_role_refs: tuple[str, ...]
    minimum_approvals: int = Field(ge=1)
    require_distinct_approvers: bool = True
    prohibit_self_approval: bool = True

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_requirement(self) -> ApprovalRequirement:
        if not self.required_role_refs:
            raise ValueError("approval requirement requires roles")
        if self.minimum_approvals > len(self.required_role_refs):
            raise ValueError("minimum approvals cannot exceed required roles")
        return self


class RiskAcceptanceState(BaseModel):
    schema_version: Literal["risk_acceptance_state.v1"] = "risk_acceptance_state.v1"
    acceptance_id: str
    risk_owner_id: str
    risk_owner_role_ref: str
    action_id: str
    risk_ref: str
    accepted: bool
    accepted_at: datetime
    valid_until: datetime
    evidence_refs: tuple[str, ...]

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_risk_acceptance(self) -> RiskAcceptanceState:
        if self.valid_until <= self.accepted_at:
            raise ValueError("risk acceptance requires a positive validity window")
        if not self.evidence_refs:
            raise ValueError("risk acceptance requires evidence")
        return self

    def is_current(self, moment: datetime) -> bool:
        return self.accepted_at <= moment < self.valid_until


class AuthorityOriginationState(BaseModel):
    schema_version: Literal["authority_origination_state.v1"] = (
        "authority_origination_state.v1"
    )
    origination_id: str
    authority_id: str
    authority_principal_id: str
    represented_principal_id: str
    grantor_id: str
    grantor_standing_ref: str
    evidence_refs: tuple[str, ...]
    evaluated_at: datetime
    valid_until: datetime
    max_delegation_depth: int = Field(ge=0)
    revocation_registry_ref: str | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_origination(self) -> AuthorityOriginationState:
        required = (
            self.origination_id,
            self.authority_id,
            self.authority_principal_id,
            self.represented_principal_id,
            self.grantor_id,
            self.grantor_standing_ref,
        )
        if any(not item for item in required):
            raise ValueError("authority origination fields are required")
        if not self.evidence_refs:
            raise ValueError("authority origination requires evidence")
        if self.valid_until <= self.evaluated_at:
            raise ValueError("authority origination requires positive validity")
        return self

    def is_current(self, moment: datetime) -> bool:
        return self.evaluated_at <= moment < self.valid_until


class AuthorityConflictAssessment(BaseModel):
    schema_version: Literal["authority_conflict_assessment.v1"] = (
        "authority_conflict_assessment.v1"
    )
    assessment_id: str
    authority_principal_id: str
    capability: str
    target_ref: str
    disposition: AuthorityConflictDisposition
    evaluated_at: datetime
    valid_until: datetime
    evidence_refs: tuple[str, ...]
    conflicting_authority_refs: tuple[str, ...] = ()
    resolution_ref: str | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_conflict(self) -> AuthorityConflictAssessment:
        if self.valid_until <= self.evaluated_at:
            raise ValueError("authority conflict assessment requires positive validity")
        if not self.evidence_refs:
            raise ValueError("authority conflict assessment requires evidence")
        if (
            self.disposition is AuthorityConflictDisposition.CONFLICTED
            and not self.conflicting_authority_refs
        ):
            raise ValueError("authority conflict must identify conflicting authorities")
        return self

    def is_current(self, moment: datetime) -> bool:
        return self.evaluated_at <= moment < self.valid_until


class ActorDecisionStanding(BaseModel):
    schema_version: Literal["actor_decision_standing.v1"] = "actor_decision_standing.v1"
    standing_id: str
    actor_id: str
    role_binding_id: str
    principal_id: str
    authority_principal_id: str
    decision_function: DecisionFunction
    capability: str
    jurisdiction_ref: str
    action_id: str
    action_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority_id: str
    purpose_id: str
    role_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    competence_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    attention_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    eligibility_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    consent_digests: tuple[str, ...] = ()
    approval_digests: tuple[str, ...] = ()
    risk_acceptance_digest: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    authority_origination_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority_conflict_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    evaluated_at: datetime
    valid_until: datetime
    decision: StandingDecision
    reason_codes: tuple[str, ...]
    standing_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"standing_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_standing(self) -> ActorDecisionStanding:
        if self.valid_until <= self.evaluated_at:
            raise ValueError("actor standing requires a positive validity window")
        if self.decision is StandingDecision.PASS and self.reason_codes:
            raise ValueError("PASS standing cannot carry failure reasons")
        if self.decision is not StandingDecision.PASS and not self.reason_codes:
            raise ValueError("non-PASS standing requires reason codes")
        if self.standing_digest and self.standing_digest != self.computed_digest:
            raise ValueError("actor standing digest mismatch")
        return self
