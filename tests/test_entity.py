from __future__ import annotations

import pytest
from pydantic import ValidationError

from valo_kernel import KernelEngine, KernelInvariantViolation
from valo_kernel.contracts import (
    CanonicalEvent,
    Entity,
    EventType,
    utcnow,
)

from .conftest import entity_event, make_provenance


def test_entity_integrity(engine: KernelEngine) -> None:
    engine.append(entity_event("tenant-a", "person-1"))
    entity = engine.state().entities["person-1"]
    assert entity.entity_id == "person-1"
    assert entity.tenant_id == "tenant-a"


def test_duplicate_entity_id_rejected(engine: KernelEngine) -> None:
    engine.append(entity_event("tenant-a", "person-1"))
    with pytest.raises(KernelInvariantViolation, match="duplicate"):
        engine.append(entity_event("tenant-a", "person-1"))


def test_duplicate_entity_id_rejected_across_replay(engine: KernelEngine) -> None:
    first = entity_event("tenant-a", "person-1")
    engine.append(first)
    state = engine.state()
    with pytest.raises(KernelInvariantViolation):
        from valo_kernel.kernel.reducers import reduce

        reduce(state, entity_event("tenant-a", "person-1"))


def test_no_direct_state_mutation(engine: KernelEngine) -> None:
    """Kernel owns state: there is no public mutate API, only append."""
    assert not hasattr(engine, "mutate")
    engine.append(entity_event("tenant-a", "person-1", state="ACTIVE"))
    state = engine.state()
    assert state.entities["person-1"].state == "ACTIVE"


def test_entity_update_only_through_event(engine: KernelEngine) -> None:
    engine.append(entity_event("tenant-a", "person-1", state="ACTIVE"))
    now = utcnow()
    event = CanonicalEvent(
        event_id="update-1",
        event_type=EventType.ENTITY_UPDATED,
        tenant_id="tenant-a",
        subject="person-1",
        source="kernel",
        effective_at=now,
        payload={"entity_id": "person-1", "state": "SUSPENDED"},
    )
    engine.append(event)
    assert engine.state().entities["person-1"].state == "SUSPENDED"
    assert engine.state().entities["person-1"].version == 2


def test_unknown_entity_type_pack_gap() -> None:
    """Entity types are explicit; a random string is not a canonical type."""
    with pytest.raises(ValidationError):
        Entity(
            entity_id="x",
            entity_type="Electrician",
            tenant_id="t",
            provenance=make_provenance(),
        )
