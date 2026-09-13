from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from .effect_boundary import BoundaryDisposition, EffectChannel


FORMAL_INVARIANT = "NO_UNGOVERNED_CAUSAL_EFFECT_PATH"
CANONICAL_COMPATIBILITY_INVARIANT = "NO_DIRECT_EFFECT_PATH"


class GovernedEffectBoundary(BaseModel):
    schema_version: Literal["governed_effect_boundary.v1"] = "governed_effect_boundary.v1"
    boundary_ref: str
    explicit_declared: bool
    exact_effect_bound: bool
    authorized_now: bool
    deny_enforceable: bool
    fail_closed: bool
    evidence_capable: bool
    isolation_capable: bool = False
    rollback_or_compensation_capable: bool = False
    description: str = ""

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_boundary(self) -> "GovernedEffectBoundary":
        if not self.boundary_ref:
            raise ValueError("boundary_ref is required")
        return self

    @property
    def is_governed(self) -> bool:
        return all(
            (
                self.explicit_declared,
                self.exact_effect_bound,
                self.authorized_now,
                self.deny_enforceable,
                self.fail_closed,
                self.evidence_capable,
            )
        )


class CausalCapacityAssessment(BaseModel):
    schema_version: Literal["causal_capacity_assessment.v1"] = (
        "causal_capacity_assessment.v1"
    )
    assessment_id: str
    disposition: BoundaryDisposition
    formal_invariant: Literal["NO_UNGOVERNED_CAUSAL_EFFECT_PATH"] = FORMAL_INVARIANT
    compatibility_invariant: Literal["NO_DIRECT_EFFECT_PATH"] = (
        CANONICAL_COMPATIBILITY_INVARIANT
    )
    ungoverned_channel_ids: tuple[str, ...] = ()
    invalid_boundary_refs: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()

    model_config = ConfigDict(extra="forbid", frozen=True)


def assess_causal_capacity(
    channels: tuple[EffectChannel, ...],
    *,
    boundaries: tuple[GovernedEffectBoundary, ...],
) -> CausalCapacityAssessment:
    """Evaluate complete mediation of consequential causal capacity.

    The worker/model is treated as untrusted. Any channel that can cross a trust
    boundary is consequential causal capacity and must terminate at one explicit,
    currently authorized, exact-effect-bound, enforceable, fail-closed and
    evidenced boundary. Rollback is not required: prevention before commitment is.
    """
    channel_ids = [channel.channel_id for channel in channels]
    if len(channel_ids) != len(set(channel_ids)):
        raise ValueError("effect channel IDs must be unique")

    boundary_refs = [boundary.boundary_ref for boundary in boundaries]
    if len(boundary_refs) != len(set(boundary_refs)):
        raise ValueError("governed boundary refs must be unique")

    boundary_by_ref = {boundary.boundary_ref: boundary for boundary in boundaries}
    invalid_boundary_refs = sorted(
        ref for ref, boundary in boundary_by_ref.items() if not boundary.is_governed
    )

    ungoverned: list[str] = []
    for channel in channels:
        if not channel.crosses_trust_boundary:
            continue
        ref = channel.governed_boundary_ref
        if ref is None:
            ungoverned.append(channel.channel_id)
            continue
        boundary = boundary_by_ref.get(ref)
        if boundary is None or not boundary.is_governed:
            ungoverned.append(channel.channel_id)

    external = any(channel.crosses_trust_boundary for channel in channels)
    if ungoverned:
        disposition = BoundaryDisposition.DENY
        reasons = ("NO_UNGOVERNED_CAUSAL_EFFECT_PATH_VIOLATION",)
    elif external:
        disposition = BoundaryDisposition.GOVERNED
        reasons = ()
    else:
        disposition = BoundaryDisposition.INTERNAL_ONLY
        reasons = ()

    return CausalCapacityAssessment(
        assessment_id="causal-capacity:"
        + ("|".join(sorted(channel_ids)) if channel_ids else "empty"),
        disposition=disposition,
        ungoverned_channel_ids=tuple(sorted(ungoverned)),
        invalid_boundary_refs=tuple(invalid_boundary_refs),
        reason_codes=reasons,
    )
