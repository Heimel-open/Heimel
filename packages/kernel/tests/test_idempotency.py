from __future__ import annotations

import pytest

from valo_kernel import IdempotentReplay, KernelEngine
from valo_kernel.contracts import CanonicalEvent, EventType, utcnow
from valo_kernel.storage.memory import MemoryStore

from .conftest import admit_evidence, entity_event, evidence_event


def test_idempotent_ingestion(engine) -> None:
    engine.append(
        entity_event("tenant-a", "person-1").model_copy(
            update={"idempotency_key": "ext-key-1"}
        )
    )
    before = engine.sequence()
    with pytest.raises(IdempotentReplay, match="already applied"):
        engine.append(
            entity_event("tenant-a", "person-1").model_copy(
                update={"idempotency_key": "ext-key-1"}
            )
        )
    assert engine.sequence() == before
    assert len(engine.state().entities) == 1


def test_duplicate_payment_event_rejected(engine) -> None:
    """A duplicated external payment event must not produce two transitions."""
    engine.append(entity_event("tenant-a", "account-1"))
    engine.append(evidence_event("tenant-a", "ev-pay", "account-1"))
    admit_evidence(engine, "ev-pay")
    now = utcnow()
    engine.append(
        CanonicalEvent(
            event_id="pay-fact",
            event_type=EventType.FACT_ASSERTED,
            tenant_id="tenant-a",
            subject="account-1",
            source="veritas",
            effective_at=now,
            payload={
                "fact": {
                    "fact_id": "f-pay",
                    "subject": "account-1",
                    "predicate": "payment",
                    "object": "received",
                    "tenant_id": "tenant-a",
                    "provenance": {
                        "source_type": "external",
                        "source_id": "bank-x",
                        "source_system": "bank",
                    },
                }
            },
        )
    )
    pay = CanonicalEvent(
        event_id="pay-1",
        event_type=EventType.FACT_CONFIRMED,
        tenant_id="tenant-a",
        subject="account-1",
        source="gateway",
        effective_at=now,
        payload={"fact_id": "f-pay"},
        evidence_refs=["ev-pay"],
        idempotency_key="payment-abc",
    )
    engine.append(pay)
    seq = engine.sequence()
    with pytest.raises(IdempotentReplay):
        engine.append(pay)
    assert engine.sequence() == seq


def test_idempotency_survives_engine_restart() -> None:
    """Idempotency is owned by the append-only store, not the engine instance.
    A freshly constructed engine over the same store must reject the same key."""
    store = MemoryStore()
    now = utcnow()

    engine_a = KernelEngine("tenant-a", storage=store)
    engine_a.append(entity_event("tenant-a", "account-1"))
    engine_a.append(evidence_event("tenant-a", "ev-pay", "account-1"))
    admit_evidence(engine_a, "ev-pay")
    engine_a.append(
        CanonicalEvent(
            event_id="pay-fact",
            event_type=EventType.FACT_ASSERTED,
            tenant_id="tenant-a",
            subject="account-1",
            source="veritas",
            effective_at=now,
            payload={
                "fact": {
                    "fact_id": "f-pay",
                    "subject": "account-1",
                    "predicate": "payment",
                    "object": "received",
                    "tenant_id": "tenant-a",
                    "provenance": {
                        "source_type": "external",
                        "source_id": "bank-x",
                        "source_system": "bank",
                    },
                }
            },
        )
    )
    pay = CanonicalEvent(
        event_id="pay-1",
        event_type=EventType.FACT_CONFIRMED,
        tenant_id="tenant-a",
        subject="account-1",
        source="gateway",
        effective_at=now,
        payload={"fact_id": "f-pay"},
        evidence_refs=["ev-pay"],
        idempotency_key="payment-abc",
    )
    engine_a.append(pay)

    engine_b = KernelEngine("tenant-a", storage=store)
    assert engine_b.sequence() == 5
    with pytest.raises(IdempotentReplay, match="already applied"):
        engine_b.append(pay)
    assert engine_b.sequence() == 5
    assert engine_b.state().root_hash() == engine_a.state().root_hash()

