from __future__ import annotations

from datetime import timedelta

import pytest

from valo_kernel.contracts import (
    CanonicalEvent,
    EventType,
    TruthStatus,
    utcnow,
)

from .conftest import admit_evidence, entity_event, evidence_event, make_provenance


def fact_event(
    tenant: str,
    fact_id: str,
    subject: str,
    predicate: str,
    obj: str,
    event_type: EventType = EventType.FACT_ASSERTED,
) -> CanonicalEvent:
    now = utcnow()
    return CanonicalEvent(
        event_id=f"fact-{fact_id}",
        event_type=event_type,
        tenant_id=tenant,
        subject=subject,
        source="kernel",
        effective_at=now,
        payload={
            "fact": {
                "fact_id": fact_id,
                "subject": subject,
                "predicate": predicate,
                "object": obj,
                "tenant_id": tenant,
                "provenance": make_provenance(fact_id).model_dump(mode="json"),
            }
        },
    )


def test_asserted_then_confirmed(engine) -> None:
    engine.append(entity_event("tenant-a", "worker-1"))
    engine.append(evidence_event("tenant-a", "ev-1", "worker-1"))
    admit_evidence(engine, "ev-1")
    engine.append(fact_event("tenant-a", "f1", "worker-1", "certified", "true"))
    assert engine.state().facts["f1"].truth_status == TruthStatus.ASSERTED

    now = utcnow()
    engine.append(
        CanonicalEvent(
            event_id="confirm-f1",
            event_type=EventType.FACT_CONFIRMED,
            tenant_id="tenant-a",
            subject="worker-1",
            source="veritas",
            effective_at=now,
            payload={"fact_id": "f1"},
            evidence_refs=["ev-1"],
        )
    )
    assert engine.state().facts["f1"].truth_status == TruthStatus.CONFIRMED
    assert "ev-1" in engine.state().facts["f1"].evidence_refs


def test_backdated_mutation_rejected(engine) -> None:
    """No backwards effective-time transition without a correction event."""
    engine.append(entity_event("tenant-a", "worker-1"))
    now = utcnow()
    with pytest.raises(Exception, match="precede"):
        CanonicalEvent(
            event_id="backdated",
            event_type=EventType.ENTITY_UPDATED,
            tenant_id="tenant-a",
            subject="worker-1",
            source="kernel",
            timestamp=now,
            effective_at=now - timedelta(days=10),
            payload={"entity_id": "worker-1", "state": "SUSPENDED"},
        )


def test_correction_event_may_backdate(engine) -> None:
    """Corrections are the explicit path for fixing past state. History is
    never rewritten; the working state is corrected with a version bump."""
    engine.append(entity_event("tenant-a", "worker-1", state="ACTIVE"))
    now = utcnow()
    correction = CanonicalEvent(
        event_id="corr-1",
        event_type=EventType.CORRECTION,
        tenant_id="tenant-a",
        subject="worker-1",
        source="kernel",
        timestamp=now,
        effective_at=now - timedelta(days=1),
        payload={"entity_id": "worker-1", "new_state": "SUSPENDED"},
    )
    engine.append(correction)
    assert engine.sequence() == 2
    assert engine.state().entities["worker-1"].state == "SUSPENDED"
    assert engine.state().entities["worker-1"].version == 2


def test_observed_vs_effective_are_distinct(engine) -> None:
    """Kernel owns explicit time: when we learned it vs when it applied."""
    engine.append(entity_event("tenant-a", "worker-1"))
    observed_at = utcnow()
    now = utcnow()
    event = CanonicalEvent(
        event_id="time-1",
        event_type=EventType.ENTITY_UPDATED,
        tenant_id="tenant-a",
        subject="worker-1",
        source="kernel",
        timestamp=now,
        effective_at=now,
        payload={"entity_id": "worker-1", "state": "HIRED"},
    )
    engine.append(event)
    assert event.timestamp >= observed_at
    assert event.effective_at is not None

