from __future__ import annotations

import pytest

from valo_kernel import FailClosedError, IntegrityError, verify_event
from valo_kernel.contracts import CanonicalEvent, EventType, utcnow
from valo_kernel.kernel.integrity import GENESIS_HASH, digest_event_content, seal_event

from .conftest import entity_event


def test_events_are_sealed_with_chain_hashes(engine) -> None:
    engine.append(entity_event("tenant-a", "person-1"))
    engine.append(entity_event("tenant-a", "person-2"))
    events = engine.events()
    assert events[0].sequence == 1
    assert events[0].previous_hash == GENESIS_HASH
    assert events[1].previous_hash == events[0].event_hash
    assert events[1].sequence == 2
    engine.verify_integrity()


def test_tamper_detection_chain(engine) -> None:
    engine.append(entity_event("tenant-a", "person-1"))
    events = engine.events()
    tampered = events[0].model_copy(update={"subject": "evil"})
    with pytest.raises(IntegrityError):
        verify_event(tampered)


def test_tamper_detection_state_root(engine) -> None:
    engine.append(entity_event("tenant-a", "person-1"))
    root_before = engine.state().root_hash()
    state = engine.state()
    state.entities["person-1"] = state.entities["person-1"].model_copy(
        update={"state": "TAMPERED"}
    )
    assert state.root_hash() != root_before


def test_event_hash_deterministic() -> None:
    now = utcnow()
    event = CanonicalEvent(
        event_id="e1",
        event_type=EventType.ENTITY_REGISTERED,
        tenant_id="t",
        subject="s",
        source="kernel",
        effective_at=now,
    )
    sealed = seal_event(event, 1, GENESIS_HASH)
    sealed2 = seal_event(event, 1, GENESIS_HASH)
    assert sealed.event_hash == sealed2.event_hash
    assert digest_event_content(sealed) == sealed.event_hash


def test_engine_fails_closed_on_broken_existing_chain(engine) -> None:
    engine.append(entity_event("tenant-a", "person-1"))
    events = engine.events()
    tampered = events[0].model_copy(update={"subject": "evil"})
    engine._storage._events = [tampered]
    with pytest.raises(FailClosedError):
        engine.append(entity_event("tenant-a", "person-2"))


def test_snapshot_binds_event_position(engine) -> None:
    engine.append(entity_event("tenant-a", "person-1"))
    snap = engine.snapshot()
    assert snap.event_position == 1
    assert snap.state_root_hash == engine.state().root_hash()

