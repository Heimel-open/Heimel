from datetime import datetime, timedelta, timezone

import pytest

from src.valo_platform.content_operations.policy_profile import PublicationPolicyProfile
from src.valo_platform.content_operations.policy_registry import PublicationPolicyRegistry
from src.valo_platform.decision_governance.continuity import ContinuityTriggerKind
from src.valo_platform.operational_continuity.observers import ObservationBinding
from src.valo_platform.operational_continuity.registered_policy_source import (
    RegisteredPublicationPolicySourceAdapter,
    capture_registered_policy_baseline,
)
from src.valo_platform.operational_continuity.source_adapters import (
    SourceObservationError,
)


NOW = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
SHA = "sha256:" + "b" * 64


def binding():
    return ObservationBinding(
        tenant_id="tenant-1",
        action_case_id="case-1",
        action_case_hash="sha256:case-1",
        clearance_ref="clearance-1",
        observer_ref="observer:policy-registry",
    )


def profile(version="1"):
    return PublicationPolicyProfile(
        policy_id="publication-default",
        version=version,
        tenant_id="tenant-1",
        established_by="board",
        authority_ref="board-resolution:publication",
        mandate_ref="mandate:tenant-1:publish:1",
        mandate_fingerprint=SHA,
        allowed_principal_ids=("publisher-1",),
        allowed_providers=("provider-1",),
        allowed_account_refs=("account-1",),
        allowed_channel_refs=("channel-1",),
        allowed_languages=("en",),
        allowed_jurisdictions=("NO",),
        effective_from=NOW - timedelta(hours=1),
        effective_until=NOW + timedelta(days=1),
    )


def register(registry, current, *, occurred_at=NOW):
    return registry.register(
        current,
        actor_ref="board-secretary",
        authority_ref=current.authority_ref,
        reason="approved publication policy",
        occurred_at=occurred_at,
        evidence_refs=("board-minutes:1",),
    )


def adapter(registry, version="1"):
    return RegisteredPublicationPolicySourceAdapter(
        binding=binding(),
        registry=registry,
        policy_id="publication-default",
        version=version,
    )


def test_registered_policy_baseline_is_stable_until_registry_state_changes():
    registry = PublicationPolicyRegistry()
    register(registry, profile())
    source = adapter(registry)
    baseline = capture_registered_policy_baseline(source, captured_at=NOW)

    stable = source.observe(
        expected_fingerprint=baseline.fingerprint,
        observed_at=NOW + timedelta(minutes=1),
    )
    assert stable.trigger is None
    assert stable.integrity_status == "verified"

    registry.revoke(
        "tenant-1",
        "publication-default",
        "1",
        actor_ref="board-secretary",
        authority_ref="board-resolution:publication",
        reason="authority withdrawn",
        occurred_at=NOW + timedelta(minutes=2),
        evidence_refs=("board-resolution:revoke",),
    )
    changed = source.observe(
        expected_fingerprint=baseline.fingerprint,
        observed_at=NOW + timedelta(minutes=2),
    )
    assert changed.trigger is not None
    assert changed.trigger.trigger_kind == ContinuityTriggerKind.POLICY_CHANGED
    assert "registry_status:revoked" in changed.changed_fields
    assert changed.trigger.severity.value == "high"


def test_supersession_of_exact_version_invalidates_its_baseline():
    registry = PublicationPolicyRegistry()
    register(registry, profile("1"))
    register(registry, profile("2"), occurred_at=NOW + timedelta(seconds=1))
    source = adapter(registry, "1")
    baseline = capture_registered_policy_baseline(source, captured_at=NOW)

    registry.supersede(
        "tenant-1",
        "publication-default",
        "1",
        replacement_version="2",
        actor_ref="board-secretary",
        authority_ref="board-resolution:publication",
        reason="version 2 adopted",
        occurred_at=NOW + timedelta(minutes=1),
    )
    changed = source.observe(
        expected_fingerprint=baseline.fingerprint,
        observed_at=NOW + timedelta(minutes=1),
    )
    assert changed.trigger is not None
    assert "registry_status:superseded" in changed.changed_fields


def test_registry_tamper_becomes_failed_integrity_trigger_and_cannot_be_baselined():
    registry = PublicationPolicyRegistry()
    register(registry, profile())
    source = adapter(registry)
    baseline = capture_registered_policy_baseline(source, captured_at=NOW)

    key = ("tenant-1", "publication-default", "1")
    event = registry._events[key][0]
    registry._events[key][0] = event.model_copy(update={"reason": "tampered"})

    changed = source.observe(
        expected_fingerprint=baseline.fingerprint,
        observed_at=NOW + timedelta(minutes=1),
    )
    assert changed.trigger is not None
    assert changed.integrity_status == "failed"
    assert changed.trigger.freshness == 0.0
    assert "registry_integrity" in changed.changed_fields

    with pytest.raises(SourceObservationError, match="invalid registered policy"):
        capture_registered_policy_baseline(source, captured_at=NOW)


def test_missing_exact_registered_version_fails_closed():
    registry = PublicationPolicyRegistry()
    source = adapter(registry)
    changed = source.observe(
        expected_fingerprint="sha256:expected",
        observed_at=NOW,
    )
    assert changed.trigger is not None
    assert changed.integrity_status == "failed"
    assert "registry_status:invalid" in changed.changed_fields
    with pytest.raises(SourceObservationError, match="invalid registered policy"):
        capture_registered_policy_baseline(source, captured_at=NOW)
