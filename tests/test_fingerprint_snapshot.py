from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from src.valo_platform.decision_governance.continuity import (
    ContinuityIntegrityStatus,
    canonical_fingerprint_digest,
)
from src.valo_platform.operational_continuity.fingerprint_snapshot import (
    CallableDecisionFingerprintReader,
    CompositeCurrentDecisionFingerprintProvider,
    CurrentDecisionFingerprintSnapshot,
    DecisionFingerprintKind,
    DecisionFingerprintObservation,
    DecisionFingerprintSnapshotError,
)
from src.valo_platform.operational_continuity.observers import ObservationBinding


NOW = datetime(2026, 8, 1, 16, 0, tzinfo=timezone.utc)
VALUES = {
    DecisionFingerprintKind.AUTHORITY: "sha256:authority",
    DecisionFingerprintKind.POLICY: "sha256:policy",
    DecisionFingerprintKind.CONTEXT: "sha256:context",
    DecisionFingerprintKind.STATE: "sha256:state",
    DecisionFingerprintKind.EVIDENCE: "sha256:evidence",
}


def binding(**changes) -> ObservationBinding:
    data = {
        "tenant_id": "tenant-1",
        "action_case_id": "case-1",
        "action_case_hash": "sha256:state",
        "clearance_ref": "clearance-1",
        "observer_ref": "runtime:commit-boundary",
    }
    data.update(changes)
    return ObservationBinding(**data)


def observation(
    kind: DecisionFingerprintKind,
    *,
    observed_at: datetime = NOW,
    integrity_status: ContinuityIntegrityStatus = ContinuityIntegrityStatus.VERIFIED,
    observation_binding: ObservationBinding | None = None,
) -> DecisionFingerprintObservation:
    return DecisionFingerprintObservation(
        binding=observation_binding or binding(),
        kind=kind,
        fingerprint=VALUES[kind],
        source_ref=f"{kind.value}-owner:tenant-1",
        reader_ref=f"{kind.value}-reader:1",
        evidence_refs=(f"evidence:{kind.value}",),
        observed_at=observed_at,
        integrity_status=integrity_status,
    )


def observations():
    return tuple(observation(kind) for kind in DecisionFingerprintKind)


def reader(kind, *, factory=None):
    def read(observation_binding, observed_at):
        if factory is not None:
            return factory(observation_binding, observed_at)
        return observation(
            kind,
            observed_at=observed_at,
            observation_binding=observation_binding,
        )

    return CallableDecisionFingerprintReader(kind=kind, reader=read)


def provider(*, replace=None, omit=()):
    readers = []
    for kind in DecisionFingerprintKind:
        if kind in omit:
            continue
        readers.append((replace or {}).get(kind, reader(kind)))
    return CompositeCurrentDecisionFingerprintProvider(tuple(readers))


def test_snapshot_requires_exactly_five_verified_attributed_fingerprints():
    snapshot = CurrentDecisionFingerprintSnapshot(
        binding=binding(),
        observed_at=NOW,
        observations=observations(),
    )

    assert snapshot.as_mapping() == {
        kind.value: VALUES[kind] for kind in DecisionFingerprintKind
    }
    assert snapshot.fingerprint_digest == canonical_fingerprint_digest(
        snapshot.as_mapping()
    )
    assert snapshot.evidence_refs == tuple(
        sorted(f"evidence:{kind.value}" for kind in DecisionFingerprintKind)
    )
    assert snapshot.evidence_ref == (
        f"current-decision-fingerprints:{snapshot.snapshot_digest}"
    )
    assert snapshot.snapshot_digest.startswith("sha256:")


def test_snapshot_rejects_missing_and_duplicate_kinds():
    with pytest.raises(
        (ValidationError, DecisionFingerprintSnapshotError),
        match="coverage mismatch",
    ):
        CurrentDecisionFingerprintSnapshot(
            binding=binding(),
            observed_at=NOW,
            observations=observations()[:-1],
        )

    duplicated = observations() + (observation(DecisionFingerprintKind.AUTHORITY),)
    with pytest.raises(
        (ValidationError, DecisionFingerprintSnapshotError),
        match="duplicate",
    ):
        CurrentDecisionFingerprintSnapshot(
            binding=binding(),
            observed_at=NOW,
            observations=duplicated,
        )


def test_snapshot_rejects_cross_case_unverified_and_future_observations():
    cross_case = list(observations())
    cross_case[0] = observation(
        DecisionFingerprintKind.AUTHORITY,
        observation_binding=binding(action_case_id="other-case"),
    )
    with pytest.raises(
        (ValidationError, DecisionFingerprintSnapshotError),
        match="binding mismatch",
    ):
        CurrentDecisionFingerprintSnapshot(
            binding=binding(),
            observed_at=NOW,
            observations=tuple(cross_case),
        )

    unverified = list(observations())
    unverified[1] = observation(
        DecisionFingerprintKind.POLICY,
        integrity_status=ContinuityIntegrityStatus.UNVERIFIED,
    )
    with pytest.raises(
        (ValidationError, DecisionFingerprintSnapshotError),
        match="integrity is not verified",
    ):
        CurrentDecisionFingerprintSnapshot(
            binding=binding(),
            observed_at=NOW,
            observations=tuple(unverified),
        )

    future = list(observations())
    future[2] = observation(
        DecisionFingerprintKind.CONTEXT,
        observed_at=NOW + timedelta(seconds=1),
    )
    with pytest.raises(
        (ValidationError, DecisionFingerprintSnapshotError),
        match="from the future",
    ):
        CurrentDecisionFingerprintSnapshot(
            binding=binding(),
            observed_at=NOW,
            observations=tuple(future),
        )


def test_observation_and_snapshot_digests_detect_tampering():
    item = observation(DecisionFingerprintKind.AUTHORITY)
    item_payload = item.model_dump(mode="python")
    item_payload["fingerprint"] = "sha256:tampered"
    with pytest.raises(
        (ValidationError, DecisionFingerprintSnapshotError),
        match="observation digest mismatch",
    ):
        DecisionFingerprintObservation(**item_payload)

    snapshot = CurrentDecisionFingerprintSnapshot(
        binding=binding(),
        observed_at=NOW,
        observations=observations(),
    )
    snapshot_payload = snapshot.model_dump(mode="python")
    snapshot_payload["observations"][0]["reader_ref"] = "attacker:reader"
    with pytest.raises(
        (ValidationError, DecisionFingerprintSnapshotError),
        match="observation digest mismatch|snapshot digest mismatch",
    ):
        CurrentDecisionFingerprintSnapshot(**snapshot_payload)


def test_composite_provider_requires_exactly_one_reader_per_kind():
    with pytest.raises(DecisionFingerprintSnapshotError, match="coverage mismatch"):
        provider(omit=(DecisionFingerprintKind.EVIDENCE,))

    duplicate = tuple(reader(kind) for kind in DecisionFingerprintKind) + (
        reader(DecisionFingerprintKind.AUTHORITY),
    )
    with pytest.raises(DecisionFingerprintSnapshotError, match="duplicate"):
        CompositeCurrentDecisionFingerprintProvider(duplicate)


def test_composite_provider_attributes_and_binds_every_reader():
    composite = provider()
    snapshot = composite.snapshot(binding=binding(), observed_at=NOW)

    assert snapshot.binding == binding()
    assert snapshot.observed_at == NOW
    assert {item.reader_ref for item in snapshot.observations} == {
        f"{kind.value}-reader:1" for kind in DecisionFingerprintKind
    }
    assert all(item.binding == binding() for item in snapshot.observations)


def test_composite_provider_rejects_reader_failure_kind_mismatch_and_invalid_type():
    def fail(observation_binding, observed_at):
        raise OSError("authority source unavailable")

    with pytest.raises(DecisionFingerprintSnapshotError, match="read failed: authority"):
        provider(
            replace={
                DecisionFingerprintKind.AUTHORITY: CallableDecisionFingerprintReader(
                    kind=DecisionFingerprintKind.AUTHORITY,
                    reader=fail,
                )
            }
        ).snapshot(binding=binding(), observed_at=NOW)

    def wrong_kind(observation_binding, observed_at):
        return observation(
            DecisionFingerprintKind.POLICY,
            observed_at=observed_at,
            observation_binding=observation_binding,
        )

    with pytest.raises(DecisionFingerprintSnapshotError, match="kind mismatch"):
        provider(
            replace={
                DecisionFingerprintKind.AUTHORITY: CallableDecisionFingerprintReader(
                    kind=DecisionFingerprintKind.AUTHORITY,
                    reader=wrong_kind,
                )
            }
        ).snapshot(binding=binding(), observed_at=NOW)

    with pytest.raises(DecisionFingerprintSnapshotError, match="invalid type"):
        provider(
            replace={
                DecisionFingerprintKind.AUTHORITY: CallableDecisionFingerprintReader(
                    kind=DecisionFingerprintKind.AUTHORITY,
                    reader=lambda observation_binding, observed_at: {
                        "authority": "sha256:authority"
                    },
                )
            }
        ).snapshot(binding=binding(), observed_at=NOW)
