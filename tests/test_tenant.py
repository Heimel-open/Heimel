from __future__ import annotations

import pytest
from pydantic import ValidationError

from valo_kernel import FailClosedError
from valo_kernel.contracts import EventType, utcnow
from valo_kernel.storage.memory import MemoryStore

from .conftest import entity_event


def test_cross_tenant_event_rejected() -> None:
    from valo_kernel import KernelEngine

    engine = KernelEngine("tenant-a")
    with pytest.raises(FailClosedError, match="tenant mismatch"):
        engine.append(entity_event("tenant-b", "person-1"))


def test_cross_tenant_reference_in_payload_rejected() -> None:
    from valo_kernel import KernelEngine
    from valo_kernel.contracts import CanonicalEvent, Entity, EntityType, Provenance

    engine = KernelEngine("tenant-a")
    now = utcnow()
    with pytest.raises(FailClosedError):
        engine.append(
            CanonicalEvent(
                event_id="x-tenant",
                event_type=EventType.ENTITY_REGISTERED,
                tenant_id="tenant-a",
                subject="person-1",
                source="kernel",
                effective_at=now,
                payload={
                    "entity": Entity(
                        entity_id="person-1",
                        entity_type=EntityType.PERSON,
                        tenant_id="tenant-b",
                        provenance=Provenance(source_type="system", source_id="x", source_system="x"),
                    )
                },
            )
        )


def test_tenant_isolation_between_engines() -> None:
    from valo_kernel import KernelEngine

    a = KernelEngine("tenant-a")
    b = KernelEngine("tenant-b")
    a.append(entity_event("tenant-a", "person-1"))
    b.append(entity_event("tenant-b", "person-2"))
    assert "person-1" not in b.state().entities
    assert "person-2" not in a.state().entities


def test_fail_closed_unknown_schema() -> None:
    from valo_kernel import KernelEngine

    with pytest.raises(FailClosedError, match="schema"):
        KernelEngine("tenant-a", schema_version="future-v2")


def test_fail_closed_missing_tenant() -> None:
    from valo_kernel import KernelEngine

    with pytest.raises(FailClosedError, match="tenant"):
        KernelEngine("")


def test_fail_closed_unknown_event_type(engine) -> None:
    from valo_kernel.contracts import CanonicalEvent

    # An unknown event type is rejected at the contract boundary (strict enum).
    with pytest.raises(ValidationError):
        CanonicalEvent(
            event_id="bad",
            event_type="NOT_A_REAL_EVENT",
            tenant_id="tenant-a",
            subject="x",
            source="kernel",
            effective_at=utcnow(),
        )


def test_storage_agnostic_interface() -> None:
    from valo_kernel import KernelEngine

    store = MemoryStore()
    engine = KernelEngine("tenant-a", storage=store)
    engine.append(entity_event("tenant-a", "person-1"))
    assert len(store.events()) == 1
    assert store.last_event() is not None
