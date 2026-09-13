from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .contracts import Authority, Delegation, ProposedAction, Purpose, canonical_digest


class AuthorityStateReference(BaseModel):
    """Opaque binding to fresh authoritative principal-side state.

    The payload is intentionally not exported. REHT or another authorized
    decision point resolves the referenced state locally before commitment.
    """

    schema_version: Literal["authority_state_ref.v1"] = "authority_state_ref.v1"
    tenant_id: str
    state_root: str = Field(pattern=r"^[0-9a-f]{64}$")
    dependency_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    observed_at: datetime
    valid_until: datetime

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_window(self) -> AuthorityStateReference:
        if not self.tenant_id:
            raise ValueError("authority state tenant is required")
        if self.valid_until <= self.observed_at:
            raise ValueError("authority state must expire after observation")
        return self


class ExecutionEndpoint(BaseModel):
    """Non-authoritative description of a downstream enforcement point."""

    endpoint_id: str
    adapter_id: str
    rail_type: str
    enforcement_ref: str
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_endpoint(self) -> ExecutionEndpoint:
        required = (
            self.endpoint_id,
            self.adapter_id,
            self.rail_type,
            self.enforcement_ref,
        )
        if any(not item for item in required):
            raise ValueError("execution endpoint fields are required")
        return self


class PrincipalAuthoritySemantics(BaseModel):
    """Canonical authority meaning before it is projected to any rail.

    This is not a REHT clearance and cannot authorize an external effect.
    It binds the exact principal authority, delegation chain, purpose, action,
    and fresh-state reference that a downstream commit-time decision must use.
    """

    schema_version: Literal["principal_authority_semantics.v1"] = (
        "principal_authority_semantics.v1"
    )
    executor_id: str
    authority: Authority
    delegations: tuple[Delegation, ...] = ()
    purpose: Purpose
    proposed_action: ProposedAction
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
    def validate_semantics(self) -> PrincipalAuthoritySemantics:
        if not self.executor_id:
            raise ValueError("executor id is required")
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
        if self.valid_until <= self.evaluated_at:
            raise ValueError("authority semantics must have a positive validity window")

        upper_bounds = [
            self.authority.validity.valid_until,
            self.purpose.validity.valid_until,
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

        if self.valid_until > min(upper_bounds):
            raise ValueError("authority semantics outlive an authoritative dependency")
        if self.semantics_digest and self.semantics_digest != self.computed_digest:
            raise ValueError("authority semantics digest mismatch")
        return self


class ExecutionAuthorityProjection(BaseModel):
    """Rail-specific transport of immutable principal authority semantics.

    Endpoint binding may differ between rails. The embedded semantics digest
    must not. This projection cannot issue clearance or create authority.
    """

    schema_version: Literal["execution_authority_projection.v1"] = (
        "execution_authority_projection.v1"
    )
    projection_id: str
    semantics: PrincipalAuthoritySemantics
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
    def validate_projection(self) -> ExecutionAuthorityProjection:
        if not self.projection_id:
            raise ValueError("projection id is required")
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


def seal_principal_authority_semantics(
    *,
    executor_id: str,
    authority: Authority,
    delegations: tuple[Delegation, ...],
    purpose: Purpose,
    proposed_action: ProposedAction,
    authority_state: AuthorityStateReference,
    evaluated_at: datetime,
) -> PrincipalAuthoritySemantics:
    """Build and seal canonical principal authority meaning.

    Expiry is deterministically bounded by every authoritative dependency.
    """

    upper_bounds = [
        authority.validity.valid_until,
        purpose.validity.valid_until,
        authority_state.valid_until,
        *(item.validity.valid_until for item in delegations),
    ]
    unsealed = PrincipalAuthoritySemantics(
        executor_id=executor_id,
        authority=authority,
        delegations=delegations,
        purpose=purpose,
        proposed_action=proposed_action,
        authority_state=authority_state,
        evaluated_at=evaluated_at,
        valid_until=min(upper_bounds),
    )
    return PrincipalAuthoritySemantics.model_validate(
        {
            **unsealed.model_dump(mode="python"),
            "semantics_digest": unsealed.computed_digest,
        }
    )


def project_authority_to_endpoints(
    *,
    semantics: PrincipalAuthoritySemantics,
    endpoints: tuple[ExecutionEndpoint, ...],
    projected_at: datetime,
) -> tuple[ExecutionAuthorityProjection, ...]:
    """Project one sealed authority meaning to many independent rails.

    The endpoint may change; the authority semantics cannot. No endpoint is
    allowed to add or rewrite principal authority in this contract.
    """

    if not endpoints:
        raise ValueError("at least one execution endpoint is required")
    if len({item.endpoint_id for item in endpoints}) != len(endpoints):
        raise ValueError("execution endpoints must be unique")
    if semantics.semantics_digest != semantics.computed_digest:
        raise ValueError("principal authority semantics are unsealed")

    projections: list[ExecutionAuthorityProjection] = []
    for endpoint in endpoints:
        projection_id = canonical_digest(
            {
                "semantics_digest": semantics.semantics_digest,
                "endpoint_id": endpoint.endpoint_id,
                "projected_at": projected_at.isoformat(),
            }
        )
        unsealed = ExecutionAuthorityProjection(
            projection_id=projection_id,
            semantics=semantics,
            endpoint=endpoint,
            projected_at=projected_at,
            expires_at=semantics.valid_until,
        )
        projections.append(
            ExecutionAuthorityProjection.model_validate(
                {
                    **unsealed.model_dump(mode="python"),
                    "projection_digest": unsealed.computed_digest,
                }
            )
        )
    return tuple(projections)
