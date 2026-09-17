from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .contracts import Authority, Delegation, canonical_digest


class PaseoAgentContext(BaseModel):
    schema_version: Literal["paseo_agent_context.v1"] = "paseo_agent_context.v1"
    agent_id: str
    parent_agent_id: str | None = None
    workspace_id: str
    provider_id: str
    exposed_tools: tuple[str, ...] = ()

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_identity(self) -> "PaseoAgentContext":
        required = (self.agent_id, self.workspace_id, self.provider_id)
        if any(not value.strip() for value in required):
            raise ValueError("Paseo agent, workspace, and provider identity are required")
        if self.parent_agent_id == self.agent_id:
            raise ValueError("Paseo agent cannot be its own parent")
        return self


class PaseoEffectCandidate(BaseModel):
    schema_version: Literal["paseo_effect_candidate.v1"] = "paseo_effect_candidate.v1"
    agent_id: str
    workspace_id: str
    provider_id: str
    action: str
    resource: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    proposed_at: datetime
    candidate_digest: str = ""

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"candidate_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_candidate(self) -> "PaseoEffectCandidate":
        required = (
            self.agent_id,
            self.workspace_id,
            self.provider_id,
            self.action,
            self.resource,
        )
        if any(not value.strip() for value in required):
            raise ValueError("Paseo effect candidate identity and target are required")
        if self.candidate_digest and self.candidate_digest != self.computed_digest:
            raise ValueError("Paseo effect candidate digest mismatch")
        return self


class PaseoREHTBinding(BaseModel):
    schema_version: Literal["paseo_reht_binding.v1"] = "paseo_reht_binding.v1"
    agent_id: str
    parent_agent_id: str | None = None
    workspace_id: str
    provider_id: str
    candidate_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority_ref: str
    delegation_ref: str | None = None
    consequence_at: datetime
    binding_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    paseo_tool_policy_is_authority: Literal[False] = False
    can_issue_clearance: Literal[False] = False
    can_execute_external_effects: Literal[False] = False
    requires_fresh_reht_evaluation: Literal[True] = True

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"binding_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_binding(self) -> "PaseoREHTBinding":
        if self.binding_digest and self.binding_digest != self.computed_digest:
            raise ValueError("Paseo REHT binding digest mismatch")
        return self


def _seal_candidate(candidate: PaseoEffectCandidate) -> PaseoEffectCandidate:
    if candidate.candidate_digest:
        return candidate
    return PaseoEffectCandidate.model_validate(
        {
            **candidate.model_dump(mode="python"),
            "candidate_digest": candidate.computed_digest,
        }
    )


def _validate_candidate_context(
    context: PaseoAgentContext,
    candidate: PaseoEffectCandidate,
) -> None:
    if candidate.agent_id != context.agent_id:
        raise ValueError("candidate agent does not match Paseo agent context")
    if candidate.workspace_id != context.workspace_id:
        raise ValueError("candidate workspace does not match Paseo agent context")
    if candidate.provider_id != context.provider_id:
        raise ValueError("candidate provider does not match Paseo agent context")


def _validate_authority_scope(
    candidate: PaseoEffectCandidate,
    authority: Authority,
) -> None:
    if candidate.action != authority.capability:
        raise ValueError("candidate action exceeds authority capability")
    if candidate.resource not in authority.scope:
        raise ValueError("candidate resource exceeds authority scope")
    for key, expected in authority.constraints.items():
        actual = candidate.parameters.get(key)
        if actual != expected:
            raise ValueError(f"candidate violates authority constraint: {key}")


def _validate_delegation(
    *,
    context: PaseoAgentContext,
    candidate: PaseoEffectCandidate,
    authority: Authority,
    delegation: Delegation,
    consequence_at: datetime,
) -> None:
    if not authority.delegable:
        raise ValueError("authority is not delegable")
    if delegation.authority_ref != authority.authority_id:
        raise ValueError("delegation does not reference supplied authority")
    if delegation.delegator != authority.principal:
        raise ValueError("delegator does not match authority principal")
    if delegation.delegate != context.agent_id:
        raise ValueError("delegation does not target Paseo agent")
    if not delegation.is_active(consequence_at):
        raise ValueError("delegation is not active at consequence time")

    parent_scope = set(authority.scope)
    delegated_scope = set(delegation.scope_reduction)
    if not delegated_scope:
        delegated_scope = parent_scope
    if not delegated_scope.issubset(parent_scope):
        raise ValueError("delegation may narrow but never expand parent authority")
    if candidate.resource not in delegated_scope:
        raise ValueError("candidate resource exceeds delegated scope")


def bind_paseo_effect_for_reht(
    *,
    context: PaseoAgentContext,
    candidate: PaseoEffectCandidate,
    authority: Authority,
    delegation: Delegation | None,
    consequence_at: datetime,
) -> PaseoREHTBinding:
    """Project a Paseo proposal into Heimel's REHT boundary.

    Paseo provider/tool policy is orchestration input only. It never creates
    authority or clearance. Authority is re-evaluated at consequence time and
    the returned binding still requires the canonical REHT/RACS decision path.
    """

    _validate_candidate_context(context, candidate)

    if not authority.is_active(consequence_at):
        raise ValueError("authority is not active at consequence time")

    if authority.principal != context.agent_id:
        if context.parent_agent_id != authority.principal or delegation is None:
            raise ValueError(
                "child agent requires explicit active delegation from authority principal"
            )
        _validate_delegation(
            context=context,
            candidate=candidate,
            authority=authority,
            delegation=delegation,
            consequence_at=consequence_at,
        )
    elif delegation is not None:
        raise ValueError("direct authority must not be widened through delegation")

    _validate_authority_scope(candidate, authority)
    sealed_candidate = _seal_candidate(candidate)

    unsealed = PaseoREHTBinding(
        agent_id=context.agent_id,
        parent_agent_id=context.parent_agent_id,
        workspace_id=context.workspace_id,
        provider_id=context.provider_id,
        candidate_digest=sealed_candidate.candidate_digest,
        authority_ref=authority.authority_id,
        delegation_ref=delegation.delegation_id if delegation else None,
        consequence_at=consequence_at,
    )
    return PaseoREHTBinding.model_validate(
        {
            **unsealed.model_dump(mode="python"),
            "binding_digest": unsealed.computed_digest,
        }
    )
