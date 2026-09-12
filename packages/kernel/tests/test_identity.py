from __future__ import annotations

from datetime import timedelta

import pytest

from valo_kernel import ExecutionContextError, build_execution_context
from valo_kernel.contracts import (
    CanonicalEvent,
    EventType,
    IdentityClaim,
    utcnow,
)

from .conftest import entity_event


def claim_event(tenant: str, identity_id: str, entity_id: str, value: str) -> CanonicalEvent:
    now = utcnow()
    return CanonicalEvent(
        event_id=f"claim-{identity_id}",
        event_type=EventType.IDENTITY_CLAIMED,
        tenant_id=tenant,
        subject=entity_id,
        source="kernel",
        effective_at=now,
        payload={
            "identity": IdentityClaim(
                identity_id=identity_id,
                entity_id=entity_id,
                tenant_id=tenant,
                claim_type="employee_id",
                value=value,
                issuer="hr-system",
            )
        },
    )


def verify_event(tenant: str, identity_id: str) -> CanonicalEvent:
    now = utcnow()
    return CanonicalEvent(
        event_id=f"verify-{identity_id}",
        event_type=EventType.IDENTITY_VERIFIED,
        tenant_id=tenant,
        subject=identity_id,
        source="veritas",
        effective_at=now,
        payload={"identity_id": identity_id, "verification_ref": "v-ref-1"},
    )


def test_identity_resolution(engine) -> None:
    engine.append(entity_event("tenant-a", "person-1"))
    engine.append(claim_event("tenant-a", "id-1", "person-1", "emp-42"))
    engine.append(verify_event("tenant-a", "id-1"))
    claim = engine.state().identities["id-1"]
    assert claim.entity_id == "person-1"
    assert claim.is_active()


def test_identity_claim_for_unknown_entity_rejected(engine) -> None:
    with pytest.raises(Exception, match="unknown entity"):
        engine.append(claim_event("tenant-a", "id-1", "ghost", "emp-42"))


def test_unverified_identity_not_executable(engine) -> None:
    engine.append(entity_event("tenant-a", "person-1"))
    engine.append(claim_event("tenant-a", "id-1", "person-1", "emp-42"))
    request = CanonicalEvent(
        event_id="req-1",
        event_type=EventType.RESOURCE_RESERVED,
        tenant_id="tenant-a",
        subject="worker-1",
        actor="person-1",
        source="reht",
        effective_at=utcnow(),
        payload={},
    )
    with pytest.raises(ExecutionContextError, match="execution identity"):
        build_execution_context(
            engine.state(),
            actor="person-1",
            capability="BOOK",
            target="job-1",
            requested_transition=request,
            identity_id="id-1",
        )


def test_revoked_identity_inactive(engine) -> None:
    engine.append(entity_event("tenant-a", "person-1"))
    engine.append(claim_event("tenant-a", "id-1", "person-1", "emp-42"))
    engine.append(verify_event("tenant-a", "id-1"))
    now = utcnow()
    engine.append(
        CanonicalEvent(
            event_id="rev-id-1",
            event_type=EventType.IDENTITY_REVOKED,
            tenant_id="tenant-a",
            subject="id-1",
            source="hr-system",
            effective_at=now,
            payload={"identity_id": "id-1"},
        )
    )
    assert not engine.state().identities["id-1"].is_active(now + timedelta(seconds=1))

