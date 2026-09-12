from __future__ import annotations

from datetime import timedelta

import pytest

from valo_kernel import ExecutionContextError, build_execution_context
from valo_kernel.contracts import (
    Authority,
    CanonicalEvent,
    Delegation,
    EntityType,
    EventType,
    IdentityClaim,
    TimeWindow,
    VerificationStatus,
    utcnow,
)

from .conftest import entity_event


def _agent(engine, actor_id: str) -> None:
    engine.append(entity_event("tenant-a", actor_id, entity_type=EntityType.AGENT))
    now = utcnow()
    engine.append(
        CanonicalEvent(
            event_id=f"id-{actor_id}",
            event_type=EventType.IDENTITY_CLAIMED,
            tenant_id="tenant-a",
            subject=actor_id,
            source="kernel",
            effective_at=now,
            payload={
                "identity": IdentityClaim(
                    identity_id=f"id-{actor_id}",
                    entity_id=actor_id,
                    tenant_id="tenant-a",
                    claim_type="service_identity",
                    value=actor_id,
                    verification_status=VerificationStatus.VERIFIED,
                )
            },
        )
    )


def _authority(
    engine,
    actor_id: str,
    capability: str,
    scope: list[str],
    *,
    delegable: bool = False,
) -> None:
    now = utcnow()
    engine.append(
        CanonicalEvent(
            event_id=f"auth-{capability}-{actor_id}",
            event_type=EventType.AUTHORITY_GRANTED,
            tenant_id="tenant-a",
            subject=actor_id,
            source="kernel",
            effective_at=now,
            payload={
                "authority": Authority(
                    authority_id=f"auth-{capability}-{actor_id}",
                    principal=actor_id,
                    capability=capability,
                    scope=scope,
                    basis="b",
                    validity=TimeWindow(
                        valid_from=now, valid_until=now + timedelta(days=30)
                    ),
                    delegable=delegable,
                )
            },
        )
    )


def _delegation(
    engine,
    *,
    delegator: str,
    delegate: str,
    capability: str,
    scope: list[str],
    purpose_restriction: list[str] | None = None,
) -> None:
    now = utcnow()
    engine.append(
        CanonicalEvent(
            event_id=f"delegation-{delegator}-{delegate}-{capability}",
            event_type=EventType.DELEGATION_GRANTED,
            tenant_id="tenant-a",
            subject=delegator,
            source="kernel",
            effective_at=now,
            payload={
                "delegation": Delegation(
                    delegation_id=f"delegation-{delegator}-{delegate}-{capability}",
                    delegator=delegator,
                    delegate=delegate,
                    authority_ref=f"auth-{capability}-{delegator}",
                    scope_reduction=scope,
                    purpose_restriction=purpose_restriction or [],
                    validity=TimeWindow(
                        valid_from=now, valid_until=now + timedelta(days=10)
                    ),
                )
            },
        )
    )


def _request(actor_id: str, capability: str, target: str) -> CanonicalEvent:
    now = utcnow()
    return CanonicalEvent(
        event_id="req-1",
        event_type=EventType.RESOURCE_RESERVED,
        tenant_id="tenant-a",
        subject=target,
        actor=actor_id,
        source="reht",
        effective_at=now,
        payload={"capability": capability},
    )


def test_execution_context_delivers_authority(engine) -> None:
    engine.append(
        entity_event("tenant-a", "job-1", entity_type=EntityType.JOB, state="READY")
    )
    _agent(engine, "agent-a")
    _authority(engine, "agent-a", "BOOK", ["job-1"])
    context = build_execution_context(
        engine.state(),
        actor="agent-a",
        capability="BOOK",
        target="job-1",
        requested_transition=_request("agent-a", "BOOK", "job-1"),
        identity_id="id-agent-a",
    )
    assert context["tenant_id"] == "tenant-a"
    assert len(context["authority"]) == 1
    assert context["authority"][0]["capability"] == "BOOK"
    assert context["current_state"]["state"] == "READY"
    assert context["requested_transition"]["event_type"] == "RESOURCE_RESERVED"


def test_execution_context_with_purpose(engine) -> None:
    engine.append(
        entity_event("tenant-a", "job-1", entity_type=EntityType.JOB, state="READY")
    )
    _agent(engine, "agent-a")
    _authority(engine, "agent-a", "BOOK", ["job-1"])
    context = build_execution_context(
        engine.state(),
        actor="agent-a",
        capability="BOOK",
        target="job-1",
        requested_transition=_request("agent-a", "BOOK", "job-1"),
        identity_id="id-agent-a",
        purpose_id="p1",
    )
    assert context["purpose"] is None  # purpose not registered in state


def test_delegation_is_context_only_and_never_implicit_authority(engine) -> None:
    engine.append(
        entity_event("tenant-a", "job-1", entity_type=EntityType.JOB, state="READY")
    )
    _agent(engine, "agent-a")
    _agent(engine, "agent-b")
    _authority(engine, "agent-a", "BOOK", ["job-1"], delegable=True)
    _delegation(
        engine,
        delegator="agent-a",
        delegate="agent-b",
        capability="BOOK",
        scope=["job-1"],
        purpose_restriction=["purpose-1"],
    )

    context = build_execution_context(
        engine.state(),
        actor="agent-b",
        capability="BOOK",
        target="job-1",
        requested_transition=_request("agent-b", "BOOK", "job-1"),
        identity_id="id-agent-b",
        purpose_id="purpose-1",
    )

    assert context["authority"] == []
    assert len(context["delegation"]) == 1
    assert context["delegation"][0]["authority_ref"] == "auth-BOOK-agent-a"
    assert context["delegation"][0]["purpose_restriction"] == ["purpose-1"]


def test_revoked_parent_authority_cannot_reappear_through_delegation(engine) -> None:
    engine.append(
        entity_event("tenant-a", "job-1", entity_type=EntityType.JOB, state="READY")
    )
    _agent(engine, "agent-a")
    _agent(engine, "agent-b")
    _authority(engine, "agent-a", "BOOK", ["job-1"], delegable=True)
    _delegation(
        engine,
        delegator="agent-a",
        delegate="agent-b",
        capability="BOOK",
        scope=["job-1"],
        purpose_restriction=["purpose-1"],
    )
    now = utcnow()
    engine.append(
        CanonicalEvent(
            event_id="revoke-delegator-authority",
            event_type=EventType.AUTHORITY_REVOKED,
            tenant_id="tenant-a",
            subject="agent-a",
            source="kernel",
            effective_at=now,
            payload={
                "authority_id": "auth-BOOK-agent-a",
                "revocation_ref": "rev-parent",
            },
        )
    )

    context = build_execution_context(
        engine.state(),
        actor="agent-b",
        capability="BOOK",
        target="job-1",
        requested_transition=_request("agent-b", "BOOK", "job-1"),
        identity_id="id-agent-b",
        purpose_id="purpose-1",
    )

    assert context["authority"] == []
    assert len(context["delegation"]) == 1
    assert context["delegation"][0]["purpose_restriction"] == ["purpose-1"]


def test_missing_verified_identity_blocks(engine) -> None:
    engine.append(entity_event("tenant-a", "agent-a", entity_type=EntityType.AGENT))
    _authority(engine, "agent-a", "BOOK", ["job-1"])
    with pytest.raises(ExecutionContextError, match="execution identity"):
        build_execution_context(
            engine.state(),
            actor="agent-a",
            capability="BOOK",
            target="job-1",
            requested_transition=_request("agent-a", "BOOK", "job-1"),
        )


def test_service_identity_has_no_type_bypass(engine) -> None:
    """An unverified ServiceIdentity is NOT executable: there is no type-based
    bypass of the verified-identity requirement."""
    engine.append(
        entity_event("tenant-a", "svc-1", entity_type=EntityType.SERVICE_IDENTITY)
    )
    _authority(engine, "svc-1", "BOOK", ["job-1"])
    with pytest.raises(ExecutionContextError, match="execution identity"):
        build_execution_context(
            engine.state(),
            actor="svc-1",
            capability="BOOK",
            target="job-1",
            requested_transition=_request("svc-1", "BOOK", "job-1"),
        )


def test_service_identity_resolves_unique_claim(engine) -> None:
    engine.append(
        entity_event("tenant-a", "svc-1", entity_type=EntityType.SERVICE_IDENTITY)
    )
    now = utcnow()
    engine.append(
        CanonicalEvent(
            event_id="id-svc",
            event_type=EventType.IDENTITY_CLAIMED,
            tenant_id="tenant-a",
            subject="svc-1",
            source="kernel",
            effective_at=now,
            payload={
                "identity": IdentityClaim(
                    identity_id="id-svc",
                    entity_id="svc-1",
                    tenant_id="tenant-a",
                    claim_type="service_identity",
                    value="svc-1",
                    verification_status=VerificationStatus.VERIFIED,
                )
            },
        )
    )
    _authority(engine, "svc-1", "BOOK", ["job-1"])
    context = build_execution_context(
        engine.state(),
        actor="svc-1",
        capability="BOOK",
        target="job-1",
        requested_transition=_request("svc-1", "BOOK", "job-1"),
    )
    assert context["identity"] == "id-svc"
    assert len(context["authority"]) == 1


def test_revoked_authority_gives_empty_authority_list(engine) -> None:
    engine.append(
        entity_event("tenant-a", "job-1", entity_type=EntityType.JOB, state="READY")
    )
    _agent(engine, "agent-a")
    _authority(engine, "agent-a", "BOOK", ["job-1"])
    now = utcnow()
    engine.append(
        CanonicalEvent(
            event_id="revoke",
            event_type=EventType.AUTHORITY_REVOKED,
            tenant_id="tenant-a",
            subject="agent-a",
            source="kernel",
            effective_at=now,
            payload={"authority_id": "auth-BOOK-agent-a", "revocation_ref": "r1"},
        )
    )
    context = build_execution_context(
        engine.state(),
        actor="agent-a",
        capability="BOOK",
        target="job-1",
        requested_transition=_request("agent-a", "BOOK", "job-1"),
        identity_id="id-agent-a",
    )
    # REHT sees no authority -> DENY
    assert context["authority"] == []

