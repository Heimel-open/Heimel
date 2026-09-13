from __future__ import annotations

import pytest

from valo_kernel.causal_capacity import (
    GovernedEffectBoundary,
    assess_causal_capacity,
)
from valo_kernel.effect_boundary import (
    BoundaryDisposition,
    EffectChannel,
    EffectChannelKind,
)


def _boundary(**overrides: bool) -> GovernedEffectBoundary:
    values: dict[str, object] = {
        "boundary_ref": "reht-boundary",
        "explicit_declared": True,
        "exact_effect_bound": True,
        "authorized_now": True,
        "deny_enforceable": True,
        "fail_closed": True,
        "evidence_capable": True,
    }
    values.update(overrides)
    return GovernedEffectBoundary(**values)


def _channel(kind: EffectChannelKind, *, boundary: str | None = None) -> EffectChannel:
    return EffectChannel(
        channel_id=kind.value.lower(),
        kind=kind,
        source_domain="untrusted-compute",
        target_domain="external-world",
        crosses_trust_boundary=True,
        governed_boundary_ref=boundary,
    )


ALL_EXTERNAL_KINDS = tuple(EffectChannelKind)


@pytest.mark.parametrize("kind", ALL_EXTERNAL_KINDS)
def test_all_external_causal_capacity_requires_governed_boundary(
    kind: EffectChannelKind,
) -> None:
    result = assess_causal_capacity(
        (_channel(kind),),
        boundaries=(_boundary(),),
    )
    assert result.disposition is BoundaryDisposition.DENY
    assert result.reason_codes == ("NO_UNGOVERNED_CAUSAL_EFFECT_PATH_VIOLATION",)


@pytest.mark.parametrize("kind", ALL_EXTERNAL_KINDS)
def test_all_external_causal_capacity_may_cross_fully_governed_boundary(
    kind: EffectChannelKind,
) -> None:
    result = assess_causal_capacity(
        (_channel(kind, boundary="reht-boundary"),),
        boundaries=(_boundary(),),
    )
    assert result.disposition is BoundaryDisposition.GOVERNED
    assert result.ungoverned_channel_ids == ()


@pytest.mark.parametrize(
    "failed_property",
    [
        "explicit_declared",
        "exact_effect_bound",
        "authorized_now",
        "deny_enforceable",
        "fail_closed",
        "evidence_capable",
    ],
)
def test_boundary_is_not_governed_when_required_property_is_false(
    failed_property: str,
) -> None:
    boundary = _boundary(**{failed_property: False})
    result = assess_causal_capacity(
        (_channel(EffectChannelKind.DIRECT_API, boundary="reht-boundary"),),
        boundaries=(boundary,),
    )
    assert result.disposition is BoundaryDisposition.DENY
    assert result.invalid_boundary_refs == ("reht-boundary",)


def test_rollback_is_not_required_for_governed_status() -> None:
    boundary = _boundary(
        rollback_or_compensation_capable=False,
        isolation_capable=False,
    )
    result = assess_causal_capacity(
        (_channel(EffectChannelKind.ACTUATOR, boundary="reht-boundary"),),
        boundaries=(boundary,),
    )
    assert result.disposition is BoundaryDisposition.GOVERNED


def test_internal_computation_does_not_require_effect_boundary() -> None:
    channel = EffectChannel(
        channel_id="internal",
        kind=EffectChannelKind.OTHER,
        source_domain="untrusted-compute",
        target_domain="untrusted-compute",
        crosses_trust_boundary=False,
    )
    result = assess_causal_capacity((channel,), boundaries=())
    assert result.disposition is BoundaryDisposition.INTERNAL_ONLY


def test_unknown_boundary_reference_fails_closed() -> None:
    result = assess_causal_capacity(
        (_channel(EffectChannelKind.FALLBACK_ROUTE, boundary="unknown"),),
        boundaries=(_boundary(),),
    )
    assert result.disposition is BoundaryDisposition.DENY


def test_duplicate_boundary_refs_rejected() -> None:
    with pytest.raises(ValueError, match="unique"):
        assess_causal_capacity(
            (_channel(EffectChannelKind.DIRECT_API, boundary="reht-boundary"),),
            boundaries=(_boundary(), _boundary()),
        )
