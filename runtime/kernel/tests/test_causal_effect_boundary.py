from __future__ import annotations

import pytest
from pydantic import ValidationError

from valo_kernel.effect_boundary import (
    BoundaryDisposition,
    EffectChannel,
    EffectChannelKind,
    assess_effect_boundary,
)


def _channel(
    kind: EffectChannelKind,
    *,
    crosses: bool = True,
    boundary: str | None = None,
    channel_id: str | None = None,
) -> EffectChannel:
    return EffectChannel(
        channel_id=channel_id or kind.value.lower(),
        kind=kind,
        source_domain="untrusted-compute",
        target_domain="external-world" if crosses else "untrusted-compute",
        crosses_trust_boundary=crosses,
        governed_boundary_ref=boundary,
    )


@pytest.mark.parametrize(
    "kind",
    [
        EffectChannelKind.DIRECT_API,
        EffectChannelKind.HUMAN_RELAY,
        EffectChannelKind.AGENT_RELAY,
        EffectChannelKind.SHARED_STATE,
        EffectChannelKind.MESSAGE,
        EffectChannelKind.FILE_OR_ARTIFACT,
        EffectChannelKind.CREDENTIAL,
        EffectChannelKind.ACTUATOR,
        EffectChannelKind.RESOURCE_CONSUMPTION,
        EffectChannelKind.SIDE_CHANNEL,
        EffectChannelKind.OTHER,
    ],
)
def test_every_ungoverned_boundary_crossing_fails_closed(
    kind: EffectChannelKind,
) -> None:
    result = assess_effect_boundary(
        (_channel(kind),),
        governed_boundary_refs=frozenset({"reht-boundary"}),
    )

    assert result.disposition is BoundaryDisposition.DENY
    assert result.reason_codes == ("NO_DIRECT_EFFECT_PATH_VIOLATION",)
    assert result.ungoverned_channel_ids == (kind.value.lower(),)


@pytest.mark.parametrize(
    "kind",
    [
        EffectChannelKind.HUMAN_RELAY,
        EffectChannelKind.AGENT_RELAY,
        EffectChannelKind.SHARED_STATE,
        EffectChannelKind.SIDE_CHANNEL,
        EffectChannelKind.RESOURCE_CONSUMPTION,
    ],
)
def test_indirect_channels_are_governed_when_bound(
    kind: EffectChannelKind,
) -> None:
    result = assess_effect_boundary(
        (_channel(kind, boundary="reht-boundary"),),
        governed_boundary_refs=frozenset({"reht-boundary"}),
    )

    assert result.disposition is BoundaryDisposition.GOVERNED
    assert result.ungoverned_channel_ids == ()


def test_internal_computation_remains_free() -> None:
    result = assess_effect_boundary(
        (_channel(EffectChannelKind.OTHER, crosses=False),),
        governed_boundary_refs=frozenset({"reht-boundary"}),
    )

    assert result.disposition is BoundaryDisposition.INTERNAL_ONLY


def test_unknown_boundary_reference_fails_closed() -> None:
    result = assess_effect_boundary(
        (_channel(EffectChannelKind.DIRECT_API, boundary="fake-boundary"),),
        governed_boundary_refs=frozenset({"reht-boundary"}),
    )

    assert result.disposition is BoundaryDisposition.DENY


def test_duplicate_channel_ids_rejected() -> None:
    first = _channel(EffectChannelKind.HUMAN_RELAY, channel_id="duplicate")
    second = _channel(EffectChannelKind.AGENT_RELAY, channel_id="duplicate")

    with pytest.raises(ValueError, match="unique"):
        assess_effect_boundary((first, second), governed_boundary_refs=frozenset())


def test_crossing_same_domain_rejected() -> None:
    with pytest.raises(ValidationError, match="distinct domains"):
        EffectChannel(
            channel_id="bad",
            kind=EffectChannelKind.MESSAGE,
            source_domain="same",
            target_domain="same",
            crosses_trust_boundary=True,
        )
