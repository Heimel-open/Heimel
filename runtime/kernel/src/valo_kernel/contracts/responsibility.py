from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .common import canonical_digest, normalize_extensible_type


class ResponsibilityRole(str, Enum):
    PRINCIPAL = "PRINCIPAL"
    AUTHORITY_SOURCE = "AUTHORITY_SOURCE"
    STATE_PROVIDER = "STATE_PROVIDER"
    POLICY_OWNER = "POLICY_OWNER"
    AUTHORIZATION_EVALUATOR = "AUTHORIZATION_EVALUATOR"
    DISPOSITION_ISSUER = "DISPOSITION_ISSUER"
    ENFORCEMENT_OWNER = "ENFORCEMENT_OWNER"
    EXECUTION_PROVIDER = "EXECUTION_PROVIDER"


_REQUIRED_ROLES = frozenset(
    {
        ResponsibilityRole.PRINCIPAL,
        ResponsibilityRole.AUTHORITY_SOURCE,
        ResponsibilityRole.STATE_PROVIDER,
        ResponsibilityRole.AUTHORIZATION_EVALUATOR,
        ResponsibilityRole.DISPOSITION_ISSUER,
        ResponsibilityRole.ENFORCEMENT_OWNER,
        ResponsibilityRole.EXECUTION_PROVIDER,
    }
)

_SINGLETON_ROLES = frozenset(
    {
        ResponsibilityRole.PRINCIPAL,
        ResponsibilityRole.AUTHORITY_SOURCE,
        ResponsibilityRole.POLICY_OWNER,
        ResponsibilityRole.AUTHORIZATION_EVALUATOR,
        ResponsibilityRole.DISPOSITION_ISSUER,
        ResponsibilityRole.ENFORCEMENT_OWNER,
        ResponsibilityRole.EXECUTION_PROVIDER,
    }
)


class ResponsibilityAssignment(BaseModel):
    role: ResponsibilityRole | str
    actor_ref: str = Field(min_length=1)
    basis_refs: tuple[str, ...] = Field(min_length=1)
    obligation_refs: tuple[str, ...] = ()
    contractual_refs: tuple[str, ...] = ()
    regulatory_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role(cls, value: object) -> ResponsibilityRole | str:
        return normalize_extensible_type(
            value,
            ResponsibilityRole,
            label="responsibility role",
        )

    @field_validator(
        "basis_refs",
        "obligation_refs",
        "contractual_refs",
        "regulatory_refs",
        "evidence_refs",
    )
    @classmethod
    def reject_blank_refs(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not value.strip() for value in values):
            raise ValueError("responsibility references cannot be blank")
        return values


class ExecutionResponsibilityBinding(BaseModel):
    binding_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    action_ref: str = Field(min_length=1)
    authority_ref: str = Field(min_length=1)
    delegation_refs: tuple[str, ...] = ()
    purpose_ref: str = Field(min_length=1)
    authority_state_ref: str = Field(min_length=1)
    state_root: str = Field(min_length=1)
    decision_ref: str = Field(min_length=1)
    disposition_ref: str = Field(min_length=1)
    clearance_ref: str = Field(min_length=1)
    assignments: tuple[ResponsibilityAssignment, ...] = Field(min_length=7)
    bound_at: datetime
    legal_liability_determined: Literal[False] = False
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False
    can_issue_disposition: Literal[False] = False
    binding_digest: str

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("delegation_refs")
    @classmethod
    def reject_blank_delegations(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not value.strip() for value in values):
            raise ValueError("delegation references cannot be blank")
        return values

    @model_validator(mode="after")
    def validate_responsibility_contract(self) -> ExecutionResponsibilityBinding:
        roles = tuple(assignment.role for assignment in self.assignments)
        core_roles = {role for role in roles if isinstance(role, ResponsibilityRole)}
        missing = sorted(role.value for role in _REQUIRED_ROLES - core_roles)
        if missing:
            raise ValueError(f"missing required responsibility roles: {','.join(missing)}")

        for role in _SINGLETON_ROLES:
            count = sum(1 for value in roles if value == role)
            if count > 1:
                raise ValueError(f"duplicate singleton responsibility role: {role.value}")

        payload = self.model_dump(mode="python", exclude={"binding_digest"})
        if canonical_digest(payload) != self.binding_digest:
            raise ValueError("responsibility binding digest mismatch")
        return self


class EffectResponsibilityEvidence(BaseModel):
    evidence_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    action_ref: str = Field(min_length=1)
    responsibility_binding_digest: str = Field(min_length=1)
    decision_ref: str = Field(min_length=1)
    disposition_ref: str = Field(min_length=1)
    clearance_ref: str = Field(min_length=1)
    effect_ref: str = Field(min_length=1)
    receipt_ref: str = Field(min_length=1)
    verifier_ref: str = Field(min_length=1)
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    observed_at: datetime
    legal_liability_determined: Literal[False] = False
    effect_binding_digest: str

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("evidence_refs")
    @classmethod
    def reject_blank_evidence_refs(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not value.strip() for value in values):
            raise ValueError("effect evidence references cannot be blank")
        return values

    @model_validator(mode="after")
    def validate_effect_binding(self) -> EffectResponsibilityEvidence:
        payload = self.model_dump(mode="python", exclude={"effect_binding_digest"})
        if canonical_digest(payload) != self.effect_binding_digest:
            raise ValueError("effect responsibility digest mismatch")
        return self


def seal_execution_responsibility_binding(
    *,
    binding_id: str,
    tenant_id: str,
    action_ref: str,
    authority_ref: str,
    delegation_refs: tuple[str, ...] = (),
    purpose_ref: str,
    authority_state_ref: str,
    state_root: str,
    decision_ref: str,
    disposition_ref: str,
    clearance_ref: str,
    assignments: tuple[ResponsibilityAssignment, ...],
    bound_at: datetime,
) -> ExecutionResponsibilityBinding:
    assignment_payload = tuple(
        assignment.model_dump(mode="python") for assignment in assignments
    )
    payload = {
        "binding_id": binding_id,
        "tenant_id": tenant_id,
        "action_ref": action_ref,
        "authority_ref": authority_ref,
        "delegation_refs": delegation_refs,
        "purpose_ref": purpose_ref,
        "authority_state_ref": authority_state_ref,
        "state_root": state_root,
        "decision_ref": decision_ref,
        "disposition_ref": disposition_ref,
        "clearance_ref": clearance_ref,
        "assignments": assignment_payload,
        "bound_at": bound_at,
        "legal_liability_determined": False,
        "authority_effect": "NO_AUTHORITY_CREATION",
        "can_issue_clearance": False,
        "can_issue_disposition": False,
    }
    return ExecutionResponsibilityBinding(
        **payload,
        binding_digest=canonical_digest(payload),
    )


def seal_effect_responsibility_evidence(
    *,
    evidence_id: str,
    binding: ExecutionResponsibilityBinding,
    effect_ref: str,
    receipt_ref: str,
    verifier_ref: str,
    evidence_refs: tuple[str, ...],
    observed_at: datetime,
) -> EffectResponsibilityEvidence:
    payload = {
        "evidence_id": evidence_id,
        "tenant_id": binding.tenant_id,
        "action_ref": binding.action_ref,
        "responsibility_binding_digest": binding.binding_digest,
        "decision_ref": binding.decision_ref,
        "disposition_ref": binding.disposition_ref,
        "clearance_ref": binding.clearance_ref,
        "effect_ref": effect_ref,
        "receipt_ref": receipt_ref,
        "verifier_ref": verifier_ref,
        "evidence_refs": evidence_refs,
        "observed_at": observed_at,
        "legal_liability_determined": False,
    }
    return EffectResponsibilityEvidence(
        **payload,
        effect_binding_digest=canonical_digest(payload),
    )
