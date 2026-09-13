from datetime import datetime, timedelta, timezone

from src.valo_platform.decision_governance.continuity import (
    ContinuitySeverity,
    ContinuityTriggerKind,
)
from src.valo_platform.operational_continuity.observers import (
    DeadlineObserver,
    FingerprintObserver,
    ManualObservationAdapter,
    ObservationBinding,
    SafetyStopObserver,
)


NOW = datetime(2026, 8, 1, 10, 30, tzinfo=timezone.utc)


def binding():
    return ObservationBinding(
        tenant_id="tenant-1",
        action_case_id="case-1",
        action_case_hash="sha256:case",
        clearance_ref="clearance-1",
        observer_ref="observer:asset-registry",
    )


def test_fingerprint_observer_is_deterministic_and_non_authorizing():
    observer = FingerprintObserver(
        binding=binding(),
        source_ref="asset:engine-1",
        trigger_kind=ContinuityTriggerKind.ASSET_STATE_CHANGED,
    )
    kwargs = dict(
        previous_fingerprint="sha256:old",
        current_fingerprint="sha256:new",
        observed_at=NOW,
        changed_fields=("temperature", "rpm"),
        evidence_refs=("telemetry:2", "telemetry:1"),
    )
    first = observer.observe(**kwargs)
    second = observer.observe(**kwargs)

    assert first.trigger_id == second.trigger_id
    assert first.trigger_digest == second.trigger_digest
    assert first.source_evidence_refs == ("telemetry:1", "telemetry:2")
    assert not hasattr(first, "clearance")
    assert not hasattr(first, "racs_outcome")
    assert not hasattr(first, "execute")


def test_deadline_observer_emits_only_after_expiry():
    observer = DeadlineObserver(
        binding=binding(),
        source_ref="clearance-window:1",
    )
    valid_until = NOW + timedelta(minutes=5)
    assert observer.observe(
        valid_until=valid_until,
        observed_at=NOW,
    ) is None

    expired = observer.observe(
        valid_until=valid_until,
        observed_at=valid_until,
        evidence_refs=("clock:trusted",),
    )
    assert expired is not None
    assert expired.trigger_kind == ContinuityTriggerKind.TIME_WINDOW_EXPIRED
    assert expired.severity == ContinuitySeverity.HIGH


def test_explicit_stop_becomes_critical_trigger_but_not_authority():
    observer = SafetyStopObserver(
        binding=binding(),
        source_ref="safety-plc:1",
    )
    assert observer.observe(
        stop_active=False,
        previous_fingerprint="sha256:running",
        current_fingerprint="sha256:running",
        observed_at=NOW,
        evidence_refs=(),
    ) is None

    trigger = observer.observe(
        stop_active=True,
        previous_fingerprint="sha256:running",
        current_fingerprint="sha256:stopped",
        observed_at=NOW,
        evidence_refs=("plc-event:1",),
    )
    assert trigger is not None
    assert trigger.severity == ContinuitySeverity.CRITICAL
    assert trigger.trigger_kind == ContinuityTriggerKind.EXTERNAL_CONDITION_CHANGED


def test_manual_observation_is_attributed_review_evidence():
    trigger = ManualObservationAdapter(
        binding=binding(),
        source_ref="operator-console:1",
    ).observe(
        observed_at=NOW,
        evidence_refs=("operator-note:1",),
    )
    assert trigger.trigger_kind == ContinuityTriggerKind.MANUAL_REVIEW_REQUESTED
    assert trigger.observer_ref == "observer:asset-registry"
