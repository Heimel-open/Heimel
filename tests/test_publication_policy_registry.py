from datetime import datetime, timedelta, timezone

import pytest

from src.valo_platform.content_operations.policy_profile import PublicationPolicyProfile
from src.valo_platform.content_operations.policy_registry import (
    PublicationPolicyRegistry,
    PublicationPolicyRegistryError,
    PublicationPolicyRegistryStatus,
)


NOW = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
SHA = "sha256:" + "a" * 64


def profile(version="1", **updates):
    data = dict(
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
    data.update(updates)
    return PublicationPolicyProfile(**data)


def register(registry, current, *, occurred_at=NOW):
    return registry.register(
        current,
        actor_ref="board-secretary",
        authority_ref=current.authority_ref,
        reason="approved publication policy",
        occurred_at=occurred_at,
        evidence_refs=("board-minutes:1",),
    )


def test_registers_exact_immutable_version_and_verifies_chain():
    registry = PublicationPolicyRegistry()
    current = profile()
    registered = register(registry, current)

    assert registered.profile == current
    assert registered.profile_digest == current.digest()
    assert registered.status == PublicationPolicyRegistryStatus.ACTIVE
    assert registry.verify_chain("tenant-1", "publication-default", "1")
    assert registry.resolve_active(
        "tenant-1", "publication-default", at=NOW
    ).version == "1"

    with pytest.raises(PublicationPolicyRegistryError, match="already registered"):
        register(registry, current)


def test_registration_and_transition_require_exact_policy_authority():
    registry = PublicationPolicyRegistry()
    with pytest.raises(PublicationPolicyRegistryError, match="registration authority"):
        registry.register(
            profile(),
            actor_ref="operator",
            authority_ref="authority:other",
            reason="invalid",
            occurred_at=NOW,
        )

    register(registry, profile())
    with pytest.raises(PublicationPolicyRegistryError, match="transition authority"):
        registry.revoke(
            "tenant-1",
            "publication-default",
            "1",
            actor_ref="operator",
            authority_ref="authority:other",
            reason="invalid",
            occurred_at=NOW + timedelta(minutes=1),
        )


def test_overlapping_active_versions_fail_closed_until_old_version_is_superseded():
    registry = PublicationPolicyRegistry()
    register(registry, profile("1"))
    register(registry, profile("2"), occurred_at=NOW + timedelta(seconds=1))

    with pytest.raises(PublicationPolicyRegistryError, match="ambiguous active"):
        registry.resolve_active("tenant-1", "publication-default", at=NOW)

    old = registry.supersede(
        "tenant-1",
        "publication-default",
        "1",
        replacement_version="2",
        actor_ref="board-secretary",
        authority_ref="board-resolution:publication",
        reason="version 2 adopted",
        occurred_at=NOW + timedelta(minutes=1),
        evidence_refs=("board-minutes:2",),
    )
    assert old.status == PublicationPolicyRegistryStatus.SUPERSEDED
    assert old.replacement_version == "2"
    assert registry.resolve_active(
        "tenant-1", "publication-default", at=NOW + timedelta(minutes=1)
    ).version == "2"


def test_revoke_is_append_only_and_removes_version_from_active_resolution():
    registry = PublicationPolicyRegistry()
    register(registry, profile())
    revoked = registry.revoke(
        "tenant-1",
        "publication-default",
        "1",
        actor_ref="board-secretary",
        authority_ref="board-resolution:publication",
        reason="authority withdrawn",
        occurred_at=NOW + timedelta(minutes=1),
        evidence_refs=("board-resolution:revoke",),
    )

    assert revoked.status == PublicationPolicyRegistryStatus.REVOKED
    assert len(registry.event_chain("tenant-1", "publication-default", "1")) == 2
    assert registry.verify_chain("tenant-1", "publication-default", "1")
    with pytest.raises(PublicationPolicyRegistryError, match="no active"):
        registry.resolve_active(
            "tenant-1",
            "publication-default",
            at=NOW + timedelta(minutes=2),
        )
    with pytest.raises(PublicationPolicyRegistryError, match="only an active"):
        registry.revoke(
            "tenant-1",
            "publication-default",
            "1",
            actor_ref="board-secretary",
            authority_ref="board-resolution:publication",
            reason="duplicate revoke",
            occurred_at=NOW + timedelta(minutes=2),
        )


def test_registry_detects_event_tamper_and_rejects_backward_time():
    registry = PublicationPolicyRegistry()
    register(registry, profile())

    with pytest.raises(PublicationPolicyRegistryError, match="cannot precede"):
        registry.revoke(
            "tenant-1",
            "publication-default",
            "1",
            actor_ref="board-secretary",
            authority_ref="board-resolution:publication",
            reason="backdated",
            occurred_at=NOW - timedelta(seconds=1),
        )

    key = ("tenant-1", "publication-default", "1")
    original = registry._events[key][0]
    registry._events[key][0] = original.model_copy(update={"reason": "tampered"})
    assert not registry.verify_chain(*key)
    with pytest.raises(PublicationPolicyRegistryError, match="chain verification"):
        registry.get_exact(*key)


def test_supersession_requires_registered_active_same_authority_replacement():
    registry = PublicationPolicyRegistry()
    register(registry, profile("1"))

    with pytest.raises(PublicationPolicyRegistryError, match="not registered"):
        registry.supersede(
            "tenant-1",
            "publication-default",
            "1",
            replacement_version="2",
            actor_ref="board-secretary",
            authority_ref="board-resolution:publication",
            reason="missing replacement",
            occurred_at=NOW + timedelta(minutes=1),
        )

    replacement = profile("2", authority_ref="board-resolution:other")
    register(registry, replacement, occurred_at=NOW + timedelta(seconds=1))
    with pytest.raises(PublicationPolicyRegistryError, match="authority must match"):
        registry.supersede(
            "tenant-1",
            "publication-default",
            "1",
            replacement_version="2",
            actor_ref="board-secretary",
            authority_ref="board-resolution:publication",
            reason="authority mismatch",
            occurred_at=NOW + timedelta(minutes=1),
        )
