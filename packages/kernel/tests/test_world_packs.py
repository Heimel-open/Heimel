from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from valo_kernel import (
    CanonicalEvent,
    ConcurrencyError,
    Entity,
    EventType,
    FailClosedError,
    IdempotentReplay,
    KernelEngine,
    Provenance,
    Relationship,
    TimeWindow,
)
from valo_kernel.packs import WorldPack

NOW = datetime(2026, 8, 9, 19, 0, tzinfo=UTC)


def provenance(source_id: str) -> Provenance:
    return Provenance(
        source_type="system",
        source_id=source_id,
        source_system="olav-world-os",
        observed_at=NOW,
    )


def entity_event(entity_id: str, entity_type: str, tenant: str = "olav") -> CanonicalEvent:
    entity = Entity(
        entity_id=entity_id,
        entity_type=entity_type,
        tenant_id=tenant,
        attributes={"canonical_name": entity_id},
        provenance=provenance(entity_id),
        valid_from=NOW,
    )
    return CanonicalEvent(
        event_id=f"register-{entity_id}",
        event_type=EventType.ENTITY_REGISTERED,
        tenant_id=tenant,
        subject=entity_id,
        source="olav-world-os",
        timestamp=NOW,
        effective_at=NOW,
        payload={"entity": entity},
        idempotency_key=f"register:{entity_id}",
    )


def relationship_event(tenant: str = "olav") -> CanonicalEvent:
    relationship = Relationship(
        relationship_id="olav-belongs-family",
        source="character:olav",
        relation_type="olav:BelongsToFamily",
        target="family:home",
        tenant_id=tenant,
        validity=TimeWindow(valid_from=NOW, valid_until=NOW + timedelta(days=365)),
        basis="OLAV canon",
    )
    return CanonicalEvent(
        event_id="relationship-olav-family",
        event_type=EventType.RELATIONSHIP_ESTABLISHED,
        tenant_id=tenant,
        subject="character:olav",
        source="olav-world-os",
        timestamp=NOW,
        effective_at=NOW,
        payload={"relationship": relationship},
    )


def advance_world(state, event):
    clocks = dict(state.clocks)
    clocks["olav:world_time"] = event.payload["time"]
    return state.model_copy(update={"clocks": clocks})


def olav_pack() -> WorldPack:
    return WorldPack(
        name="OLAV World OS",
        namespace="olav",
        entity_types=frozenset({"olav:Character", "olav:Family"}),
        relationship_types=frozenset({"olav:BelongsToFamily"}),
        event_types=frozenset({"olav:WorldAdvanced"}),
        reducers={"olav:WorldAdvanced": advance_world},
    )


def world_advance_event(tenant: str = "olav") -> CanonicalEvent:
    return CanonicalEvent(
        event_id="world-advance-1",
        event_type="olav:WorldAdvanced",
        tenant_id=tenant,
        subject="world:olav",
        source="olav-world-os",
        timestamp=NOW,
        effective_at=NOW,
        payload={"time": 1},
        idempotency_key="olav:world-advance:1",
    )


def test_custom_type_requires_namespace() -> None:
    with pytest.raises(ValidationError, match="namespaced"):
        Entity(
            entity_id="olav",
            entity_type="Character",
            tenant_id="olav",
            provenance=provenance("olav"),
        )


def test_unregistered_pack_entity_type_fails_closed() -> None:
    engine = KernelEngine("olav")
    with pytest.raises(FailClosedError, match="unregistered pack entity type"):
        engine.append(entity_event("character:olav", "olav:Character"))


def test_registered_pack_entity_and_relationship_types_are_applied() -> None:
    engine = KernelEngine("olav", packs=[olav_pack()])
    engine.append(entity_event("character:olav", "olav:Character"))
    engine.append(entity_event("family:home", "olav:Family"))
    engine.append(relationship_event())

    state = engine.state()
    assert state.entities["character:olav"].entity_type == "olav:Character"
    assert (
        state.relationships["olav-belongs-family"].relation_type
        == "olav:BelongsToFamily"
    )
    engine.verify_integrity()


def test_unregistered_pack_event_type_fails_closed() -> None:
    engine = KernelEngine("olav")
    with pytest.raises(FailClosedError, match="unregistered pack event type"):
        engine.append(world_advance_event())


def test_pack_event_replays_to_same_state_root() -> None:
    first = KernelEngine("olav", packs=[olav_pack()])
    second = KernelEngine("olav", packs=[olav_pack()])
    event = world_advance_event()

    first.append(event, expected_version=0)
    second.append(event, expected_version=0)

    assert first.state().clocks["olav:world_time"] == 1
    assert first.state().root_hash() == second.state().root_hash()
    assert first.state_at(NOW).root_hash() == first.state().root_hash()
    assert first.state_effective_at(NOW).root_hash() == first.state().root_hash()
    first.verify_integrity()
    second.verify_integrity()


def test_pack_event_keeps_idempotency_and_version_fences() -> None:
    engine = KernelEngine("olav", packs=[olav_pack()])
    event = world_advance_event()
    engine.append(event, expected_version=0)

    with pytest.raises(IdempotentReplay):
        engine.append(event, expected_version=1)

    next_event = world_advance_event().model_copy(
        update={
            "event_id": "world-advance-2",
            "idempotency_key": "olav:world-advance:2",
            "payload": {"time": 2},
        }
    )
    with pytest.raises(ConcurrencyError):
        engine.append(next_event, expected_version=0)


def test_pack_cannot_leave_event_without_reducer() -> None:
    with pytest.raises(ValueError, match="exactly one deterministic reducer"):
        WorldPack(
            name="broken",
            namespace="broken",
            event_types=frozenset({"broken:Changed"}),
        )


def test_duplicate_pack_namespace_fails_closed() -> None:
    with pytest.raises(FailClosedError, match="duplicate pack namespace"):
        KernelEngine("olav", packs=[olav_pack(), olav_pack()])


def test_pack_event_cannot_cross_tenant() -> None:
    engine = KernelEngine("olav", packs=[olav_pack()])
    with pytest.raises(FailClosedError, match="tenant mismatch"):
        engine.append(world_advance_event("other"))

