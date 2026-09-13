from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from .authority_projection import AuthorityStateReference, ExecutionEndpoint
from .contracts.actor_standing import (
    ActorDecisionStanding,
    AuthorityOriginationState,
    StandingDecision,
)
from .contracts.authority import Authority, Delegation
from .contracts.common import canonical_digest
from .contracts.purpose import Purpose
from .contracts.workspace import ProposedAction


class PrincipalAuthoritySemanticsV2(BaseModel):
    """Authority semantics with mandatory actor decision standing.

    `actor_standing.principal_id` is the represented principal / whose.
    `authority.principal` is the authority-chain holder. V2 binds both and never
    collapses them into one identity.
    """

    schema_version: Literal["principal_authority_semantics.v2"] = (
        "principal_authority_semantics.v2"
    )
    executor_id: str
    authority: Authority
    authority_origination: AuthorityOriginationState
    delegations: tuple[Delegation, ...] = ()
    purpose: Purpose
    proposed_action: ProposedAction
    actor_standing: ActorDecisionStanding
    authority_state: AuthorityStateReference
    evaluated_at: datetime
    valid_until: datetime
    semantics_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"semantics_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_semantics(self) -> PrincipalAuthoritySemanticsV2:
        if not self.executor_id:
            raise ValueError("executor id is required")
        if self.actor_standing.standing_digest != self.actor_standing.computed_digest:
            raise ValueError("actor standing is unsealed or tampered")
        if self.actor_standing.decision is not StandingDecision.PASS:
            raise ValueError("actor standing is not PASS")
        if self.actor_standing.actor_id != self.executor_id:
            raise ValueError("actor standing executor mismatch")
        if self.actor_standing.authority_principal_id != self.authority.principal:
            raise ValueError("actor standing authority principal mismatch")
        if self.actor_standing.authority_id != self.authority.authority_id:
            raise ValueError("actor standing authority mismatch")
        if self.actor_standing.purpose_id != self.purpose.purpose_id:
            raise ValueError("actor standing purpose mismatch")
        if self.actor_standing.action_id != self.proposed_action.action_id:
            raise ValueError("actor standing action mismatch")
        if self.actor_standing.action_digest != canonical_digest(
            self.proposed_action.model_dump(mode="json")
        ):
            raise ValueError("actor standing action digest mismatch")
        if self.actor_standing.capability != self.proposed_action.capability:
            raise ValueError("actor standing capability mismatch")
        if not (
            self.actor_standing.evaluated_at
            <= self.evaluated_at
            < self.actor_standing.valid_until
        ):
            raise ValueError("actor standing is not fresh at authority evaluation")

        if self.authority_origination.authority_id != self.authority.authority_id:
            raise ValueError("authority origination references another authority")
        if self.authority_origination.authority_principal_id != self.authority.principal:
            raise ValueError("authority origination principal mismatch")
        if (
            self.authority_origination.represented_principal_id
            != self.actor_standing.principal_id
        ):
            raise ValueError("represented principal mismatch")
        if not self.authority_origination.is_current(self.evaluated_at):
            raise ValueError("authority origination is not fresh")
        if self.actor_standing.authority_origination_digest != canonical_digest(
            self.authority_origination.model_dump(mode="json")
        ):
            raise ValueError("actor standing authority origination mismatch")

        if not self.authority.is_active(self.evaluated_at):
            raise ValueError("authority is not active at evaluation time")
        if not self.purpose.validity.is_active_at(self.evaluated_at):
            raise ValueError("purpose is not active at evaluation time")
        if not (
            self.authority_state.observed_at
            <= self.evaluated_at
            < self.authority_state.valid_until
        ):
            raise ValueError("authority state is not fresh at evaluation time")

        upper_bounds = [
            self.authority.validity.valid_until,
            self.authority_origination.valid_until,
            self.purpose.validity.valid_until,
            self.actor_standing.valid_until,
            self.authority_state.valid_until,
        ]

        if self.proposed_action.capability != self.authority.capability:
            raise ValueError("action capability is outside authority")
        if self.authority.scope and self.proposed_action.target not in self.authority.scope:
            raise ValueError("action target is outside authority scope")
        if self.proposed_action.purpose_id != self.purpose.purpose_id:
            raise ValueError("action purpose does not match principal purpose")
        if (
            self.purpose.permitted_actions
            and self.proposed_action.capability not in self.purpose.permitted_actions
        ):
            raise ValueError("action capability is outside purpose")
        if self.purpose.scope and self.proposed_action.target not in self.purpose.scope:
            raise ValueError("action target is outside purpose scope")

        if not self.delegations:
            if self.executor_id != self.authority.principal:
                raise ValueError("executor requires an explicit delegation chain")
        else:
            if not self.authority.delegable:
                raise ValueError("authority is not delegable")
            if len(self.delegations) > self.authority_origination.max_delegation_depth:
                raise ValueError("delegation chain exceeds maximum depth")
            previous_actor = self.authority.principal
            for delegation in self.delegations:
                if delegation.authority_ref != self.authority.authority_id:
                    raise ValueError("delegation references another authority")
                if delegation.delegator != previous_actor:
                    raise ValueError("delegation chain is discontinuous")
                if not delegation.is_active(self.evaluated_at):
                    raise ValueError("delegation is not active at evaluation time")
                if (
                    delegation.scope_reduction
                    and self.proposed_action.target not in delegation.scope_reduction
                ):
                    raise ValueError("action target is outside delegated scope")
                if delegation.purpose_restriction and not {
                    self.purpose.purpose_id,
                    self.purpose.purpose_type,
                }.intersection(delegation.purpose_restriction):
                    raise ValueError("action purpose is outside delegation restriction")
                upper_bounds.append(delegation.validity.valid_until)
                previous_actor = delegation.delegate
            if previous_actor != self.executor_id:
                raise ValueError("delegation chain does not terminate at executor")

        if self.valid_until <= self.evaluated_at:
            raise ValueError("authority semantics must have a positive validity window")
        if self.valid_until > min(upper_bounds):
            raise ValueError("authority semantics outlive an authoritative dependency")
        if self.semantics_digest and self.semantics_digest != self.computed_digest:
            raise ValueError("authority semantics digest mismatch")
        return self


class ExecutionAuthorityProjectionV2(BaseModel):
    schema_version: Literal["execution_authority_projection.v2"] = (
        "execution_authority_projection.v2"
    )
    projection_id: str
    semantics: PrincipalAuthoritySemanticsV2
    endpoint: ExecutionEndpoint
    projected_at: datetime
    expires_at: datetime
    projection_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"projection_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_projection(self) -> ExecutionAuthorityProjectionV2:
        if self.semantics.semantics_digest != self.semantics.computed_digest:
            raise ValueError("principal authority semantics are unsealed")
        if self.projected_at < self.semantics.evaluated_at:
            raise ValueError("projection cannot predate authority evaluation")
        if self.projected_at >= self.expires_at:
            raise ValueError("projection must expire after projection time")
        if self.expires_at > self.semantics.valid_until:
            raise ValueError("projection cannot outlive principal authority semantics")
        if self.projection_digest and self.projection_digest != self.computed_digest:
            raise ValueError("execution authority projection digest mismatch")
        return self


def seal_principal_authority_semantics_v2(
    *,
    executor_id: str,
    authority: Authority,
    authority_origination: AuthorityOriginationState,
    delegations: tuple[Delegation, ...],
    purpose: Purpose,
    proposed_action: ProposedAction,
    actor_standing: ActorDecisionStanding,
    authority_state: AuthorityStateReference,
    evaluated_at: datetime,
) -> PrincipalAuthoritySemanticsV2:
    upper_bounds = [
        authority.validity.valid_until,
        authority_origination.valid_until,
        purpose.validity.valid_until,
        actor_standing.valid_until,
        authority_state.valid_until,
        *(item.validity.valid_until for item in delegations),
    ]
    provisional = PrincipalAuthoritySemanticsV2(
        executor_id=executor_id,
        authority=authority,
        authority_origination=authority_origination,
        delegations=delegations,
        purpose=purpose,
        proposed_action=proposed_action,
        actor_standing=actor_standing,
        authority_state=authority_state,
        evaluated_at=evaluated_at,
        valid_until=min(upper_bounds),
    )
    return PrincipalAuthoritySemanticsV2.model_validate(
        {
            **provisional.model_dump(mode="python"),
            "semantics_digest": provisional.computed_digest,
        }
    )


def project_authority_to_endpoints_v2(
    *,
    semantics: PrincipalAuthoritySemanticsV2,
    endpoints: tuple[ExecutionEndpoint, ...],
    projected_at: datetime,
) -> tuple[ExecutionAuthorityProjectionV2, ...]:
    if not endpoints:
        raise ValueError("at least one execution endpoint is required")
    if len({item.endpoint_id for item in endpoints}) != len(endpoints):
        raise ValueError("execution endpoints must be unique")
    if semantics.semantics_digest != semantics.computed_digest:
        raise ValueError("principal authority semantics are unsealed")

    projections: list[ExecutionAuthorityProjectionV2] = []
    for endpoint in endpoints:
        projection_id = canonical_digest(
            {
                "semantics_digest": semantics.semantics_digest,
                "endpoint_id": endpoint.endpoint_id,
                "projected_at": projected_at.isoformat(),
            }
        )
        provisional = ExecutionAuthorityProjectionV2(
            projection_id=projection_id,
            semantics=semantics,
            endpoint=endpoint,
            projected_at=projected_at,
            expires_at=semantics.valid_until,
        )
        projections.append(
            ExecutionAuthorityProjectionV2.model_validate(
                {
                    **provisional.model_dump(mode="python"),
                    "projection_digest": provisional.computed_digest,
                }
            )
        )
    return tuple(projections)
