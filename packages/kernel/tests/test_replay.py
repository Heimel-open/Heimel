from __future__ import annotations

from datetime import timedelta

from valo_kernel import KernelEngine, replay
from valo_kernel.contracts import CanonicalEvent, EventType, utcnow

from .conftest import entity_event


def test_replay_produces_same_state() -> None:
    engine = KernelEngine("tenant-a")
    engine.append(entity_event("tenant-a", "person-1"))
    engine.append(entity_event("tenant-a", "person-2", state="ACTIVE"))

    rebuilt = replay(engine.events())
    assert rebuilt.root_hash() == engine.state().root_hash()


def test_replay_is_deterministic_across_instances() -> None:
    """The same event stream must always produce the same state, regardless of
    which engine instance replays it."""
    engine_a = KernelEngine("tenant-a")
    events = [entity_event("tenant-a", "person-1"), entity_event("tenant-a", "person-2", state="ACTIVE")]
    for event in events:
        engine_a.append(event)

    engine_b = KernelEngine("tenant-a")
    for event in events:
        engine_b.append(event)

    assert engine_a.state().root_hash() == engine_b.state().root_hash()
    assert replay(engine_a.events()).root_hash() == engine_a.state().root_hash()


def test_state_at_reconstructs_past(engine) -> None:
    engine.append(entity_event("tenant-a", "person-1"))
    mid = utcnow()
    engine.append(entity_event("tenant-a", "person-2", state="ACTIVE"))
    past = engine.state_at(mid)
    assert "person-2" not in past.entities
    assert "person-1" in past.entities
    future = engine.state_at(utcnow() + timedelta(seconds=60))
    assert "person-2" in future.entities


def test_historical_state_hash_is_reproducible() -> None:
    engine = KernelEngine("tenant-a")
    engine.append(entity_event("tenant-a", "person-1"))
    mid = utcnow()
    engine.append(entity_event("tenant-a", "person-2", state="ACTIVE"))
    history = engine.state_at(mid)
    # replaying only the events before `mid` must give the same history hash
    prior = [e for e in engine.events() if e.timestamp <= mid]
    assert replay(prior).root_hash() == history.root_hash()


def test_recorded_vs_effective_semantics() -> None:
    """Bitemporal: state_recorded_at(T) != state_effective_at(T) when a fact is
    recorded early but effective late (or corrected with a backdated
    effective_at)."""
    from datetime import timedelta

    engine = KernelEngine("tenant-a")
    t0 = utcnow()
    engine.append(CanonicalEvent(
        event_id="fact-eff-late",
        event_type=EventType.FACT_ASSERTED,
        tenant_id="tenant-a",
        subject="worker-1",
        source="kernel",
        timestamp=t0,
        effective_at=t0 + timedelta(days=1),
        payload={"fact": {
            "fact_id": "f-eff", "subject": "worker-1", "predicate": "certified", "object": "true",
            "tenant_id": "tenant-a",
            "provenance": {"source_type": "system", "source_id": "x", "source_system": "k"},
        }},
    ))
    recorded = engine.state_at(t0 + timedelta(hours=1))          # recorded within T -> fact present
    effective = engine.state_effective_at(t0 + timedelta(hours=1))  # not yet effective at T -> fact absent
    assert "f-eff" in recorded.facts
    assert "f-eff" not in effective.facts
    # effective AFTER the effective time: both see it
    assert "f-eff" in engine.state_effective_at(t0 + timedelta(days=2)).facts

