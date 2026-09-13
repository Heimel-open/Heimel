from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator


class EffectChannelKind(str, Enum):
    DIRECT_API = "DIRECT_API"
    HUMAN_RELAY = "HUMAN_RELAY"
    AGENT_RELAY = "AGENT_RELAY"
    SHARED_STATE = "SHARED_STATE"
    MESSAGE = "MESSAGE"
    FILE_OR_ARTIFACT = "FILE_OR_ARTIFACT"
    CREDENTIAL = "CREDENTIAL"
    ACTUATOR = "ACTUATOR"
    RESOURCE_CONSUMPTION = "RESOURCE_CONSUMPTION"
    SIDE_CHANNEL = "SIDE_CHANNEL"
    DYNAMIC_REFERENCE = "DYNAMIC_REFERENCE"
    TELEMETRY_TRIGGER = "TELEMETRY_TRIGGER"
    FALLBACK_ROUTE = "FALLBACK_ROUTE"
    IMPLICIT_INFLUENCE = "IMPLICIT_INFLUENCE"
    OTHER = "OTHER"


class BoundaryDisposition(str, Enum):
    INTERNAL_ONLY = "INTERNAL_ONLY"
    GOVERNED = "GOVERNED"
    DENY = "DENY"


class EffectChannel(BaseModel):
    schema_version: Literal["effect_channel.v1"] = "effect_channel.v1"
    channel_id: str
    kind: EffectChannelKind
    source_domain: str
    target_domain: str
    crosses_trust_boundary: bool
    governed_boundary_ref: str | None = None
    evidence_refs: tuple[str, ...] = ()
    description: str = ""

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_channel(self) -> "EffectChannel":
        if not self.channel_id or not self.source_domain or not self.target_domain:
            raise ValueError("effect channel identity and domains are required")
        if self.crosses_trust_boundary and self.source_domain == self.target_domain:
            raise ValueError("trust-boundary crossing requires distinct domains")
        if self.governed_boundary_ref is not None and not self.governed_boundary_ref:
            raise ValueError("governed boundary reference cannot be empty")
        return self


class EffectBoundaryAssessment(BaseModel):
    schema_version: Literal["effect_boundary_assessment.v1"] = (
        "effect_boundary_assessment.v1"
    )
    assessment_id: str
    channels: tuple[EffectChannel, ...]
    disposition: BoundaryDisposition
    reason_codes: tuple[str, ...]
    ungoverned_channel_ids: tuple[str, ...] = ()
    invariant: Literal["NO_DIRECT_EFFECT_PATH"] = "NO_DIRECT_EFFECT_PATH"

    model_config = ConfigDict(extra="forbid", frozen=True)


def assess_effect_boundary(
    channels: tuple[EffectChannel, ...],
    *,
    governed_boundary_refs: frozenset[str],
) -> EffectBoundaryAssessment:
    """Fail closed on every causal path that crosses the untrusted trust boundary.

    Internal computation is unrestricted by this invariant. Any channel that
    leaves the untrusted domain is an effect path and must terminate at a known
    governed boundary, regardless of carrier or payload type.
    """
    ids = [channel.channel_id for channel in channels]
    if len(ids) != len(set(ids)):
        raise ValueError("effect channel IDs must be unique")

    ungoverned = sorted(
        channel.channel_id
        for channel in channels
        if channel.crosses_trust_boundary
        and (
            channel.governed_boundary_ref is None
            or channel.governed_boundary_ref not in governed_boundary_refs
        )
    )
    external = any(channel.crosses_trust_boundary for channel in channels)

    if ungoverned:
        disposition = BoundaryDisposition.DENY
        reasons = ("NO_DIRECT_EFFECT_PATH_VIOLATION",)
    elif external:
        disposition = BoundaryDisposition.GOVERNED
        reasons = ()
    else:
        disposition = BoundaryDisposition.INTERNAL_ONLY
        reasons = ()

    return EffectBoundaryAssessment(
        assessment_id="effect-boundary:" + ("|".join(sorted(ids)) if ids else "empty"),
        channels=channels,
        disposition=disposition,
        reason_codes=reasons,
        ungoverned_channel_ids=tuple(ungoverned),
    )
