from __future__ import annotations

from datetime import timedelta

import pytest

from valo_kernel import KernelInvariantViolation, TimeWindow
from valo_kernel.contracts import (
    CanonicalEvent,
    EntityType,
    EventType,
    Relationship,
    RelationType,
    utcnow,
)

from .conftest import entity_event


def relationship_event(tenant: str, rel_id: str, source: str, target: str, rel_type: RelationType) -> CanonicalEvent:
    now = utcnow()
    return CanonicalEvent(
        event_id=f"rel-{rel_id}",
        event_type=EventType.RELATIONSHIP_ESTABLISHED,
        tenant_id=tenant,
        subject=source,
        source="kernel",
        effective_at=now,
        payload={
            "relationship": Relationship(
                relationship_id=rel_id,
                source=source,
                relation_type=rel_type,
                target=target,
                tenant_id=tenant,
                validity=TimeWindow(valid_from=now, valid_until=now + timedelta(days=30)),
            )
        },
    )


def test_relationship_validity(engine) -> None:
    engine.append(entity_event("tenant-a", "worker-1"))
    engine.append(entity_event("tenant-a", "org-1", entity_type=EntityType.ORGANIZATION))
    engine.append(relationship_event("tenant-a", "r1", "worker-1", "org-1", RelationType.EMPLOYED_BY))
    rel = engine.state().relationships["r1"]
    assert rel.is_active()


def test_relationship_unknown_entity_rejected(engine) -> None:
    engine.append(entity_event("tenant-a", "worker-1"))
    with pytest.raises(KernelInvariantViolation, match="unknown entity"):
        engine.append(relationship_event("tenant-a", "r1", "worker-1", "ghost", RelationType.EMPLOYED_BY))


def test_relationship_self_rejected(engine) -> None:
    with pytest.raises(ValueError, match="differ"):
        relationship_event("tenant-a", "r1", "same", "same", RelationType.RELATED_TO)


def test_relationship_termination(engine) -> None:
    engine.append(entity_event("tenant-a", "worker-1"))
    engine.append(entity_event("tenant-a", "org-1", entity_type=EntityType.ORGANIZATION))
    engine.append(relationship_event("tenant-a", "r1", "worker-1", "org-1", RelationType.EMPLOYED_BY))
    now = utcnow()
    engine.append(
        CanonicalEvent(
            event_id="rel-end",
            event_type=EventType.RELATIONSHIP_TERMINATED,
            tenant_id="tenant-a",
            subject="r1",
            source="kernel",
            effective_at=now,
            payload={"relationship_id": "r1"},
        )
    )
    assert not engine.state().relationships["r1"].is_active(now + timedelta(seconds=1))
