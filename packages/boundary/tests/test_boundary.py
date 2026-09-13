from datetime import datetime, timedelta, timezone

import pytest

from heimel_boundary import BoundaryError, Effect, ReferenceBoundary


NOW = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)


def effect(target: str = "record:1") -> Effect:
    return Effect("effect-1", "actor-1", "update", target)


def test_fresh_authority_exact_binding_and_receipt():
    boundary = ReferenceBoundary()
    proposed = effect()
    boundary.allow(proposed)
    permit = boundary.authorize(proposed, now=NOW)
    receipt = boundary.execute(
        permit, proposed, now=NOW, local_effect=lambda _: "APPLIED_LOCALLY"
    )
    assert receipt.outcome == "APPLIED_LOCALLY"
    assert receipt.effect_digest == proposed.digest
    assert receipt.receipt_digest == receipt.receipt_id


def test_changed_authority_denies_stale_permit_before_effect():
    boundary = ReferenceBoundary()
    proposed = effect()
    boundary.allow(proposed)
    permit = boundary.authorize(proposed, now=NOW)
    boundary.revoke(proposed)
    with pytest.raises(BoundaryError, match="stale"):
        boundary.execute(permit, proposed, now=NOW, local_effect=lambda _: "BAD")


def test_permit_cannot_be_replayed_or_retargeted():
    boundary = ReferenceBoundary()
    proposed = effect()
    boundary.allow(proposed)
    permit = boundary.authorize(proposed, now=NOW)
    boundary.execute(permit, proposed, now=NOW, local_effect=lambda _: "OK")
    with pytest.raises(BoundaryError, match="consumed"):
        boundary.execute(permit, proposed, now=NOW, local_effect=lambda _: "BAD")
    other = effect("record:2")
    boundary.allow(other)
    permit = boundary.authorize(other, now=NOW)
    with pytest.raises(BoundaryError, match="exact effect"):
        boundary.execute(permit, proposed, now=NOW, local_effect=lambda _: "BAD")


def test_expired_permit_fails_closed():
    boundary = ReferenceBoundary()
    proposed = effect()
    boundary.allow(proposed)
    permit = boundary.authorize(proposed, now=NOW)
    with pytest.raises(BoundaryError, match="expired"):
        boundary.execute(
            permit,
            proposed,
            now=NOW + timedelta(seconds=31),
            local_effect=lambda _: "BAD",
        )
