from __future__ import annotations

import pytest

from valo_kernel import ConcurrencyError, KernelInvariantViolation
from valo_kernel.contracts import CanonicalEvent, EventType, Reservation, utcnow

from .conftest import entity_event, reserve_event, resource_event


def test_reservation_moves_available_to_reserved(engine) -> None:
    engine.append(entity_event("tenant-a", "worker-1"))
    engine.append(resource_event("tenant-a", "worker-1"))
    engine.append(reserve_event("tenant-a", "r1", "worker-1", "worker-1", purpose="job-1"))
    resource = engine.state().resources["worker-1"]
    assert resource.state.value == "RESERVED"
    assert resource.holder == "worker-1"
    assert engine.state().reservations["r1"].is_active()


def test_double_reservation_rejected(engine) -> None:
    engine.append(entity_event("tenant-a", "worker-1"))
    engine.append(resource_event("tenant-a", "worker-1"))
    engine.append(reserve_event("tenant-a", "r1", "worker-1", "worker-1", purpose="job-1"))
    with pytest.raises(KernelInvariantViolation, match="not reservable"):
        engine.append(reserve_event("tenant-a", "r2", "worker-1", "worker-1", purpose="job-2"))


def test_reservation_capacity_bound(engine) -> None:
    engine.append(entity_event("tenant-a", "slot"))
    engine.append(resource_event("tenant-a", "slot", capacity=2))
    with pytest.raises(KernelInvariantViolation, match="quantity"):
        engine.append(
            CanonicalEvent(
                event_id="r-oversize",
                event_type=EventType.RESOURCE_RESERVED,
                tenant_id="tenant-a",
                subject="slot",
                actor="b",
                source="reht",
                effective_at=utcnow(),
                payload={
                    "reservation": Reservation(
                        reservation_id="r-oversize",
                        resource_id="slot",
                        holder="b",
                        tenant_id="tenant-a",
                        quantity=5,
                    )
                },
            )
        )


def test_optimistic_concurrency(engine) -> None:
    engine.append(entity_event("tenant-a", "worker-1"))
    engine.append(resource_event("tenant-a", "worker-1"))
    with pytest.raises(ConcurrencyError):
        engine.append(
            reserve_event("tenant-a", "r1", "worker-1", "worker-1", purpose="job-1"),
            expected_version=0,
        )


def test_parallel_workflows_cannot_double_book(engine) -> None:
    """Two workflows race to reserve the same worker. Only one succeeds."""
    engine.append(entity_event("tenant-a", "worker-1"))
    engine.append(resource_event("tenant-a", "worker-1"))
    seq = engine.sequence()
    # workflow A reads version, workflow B reads the same version
    wf_a = reserve_event("tenant-a", "r-a", "worker-1", "wf-a", purpose="job-a")
    wf_b = reserve_event("tenant-a", "r-b", "worker-1", "wf-b", purpose="job-b")
    engine.append(wf_a, expected_version=seq)
    with pytest.raises(ConcurrencyError):
        engine.append(wf_b, expected_version=seq)
    assert engine.state().reservations["r-a"].is_active()
    assert "r-b" not in engine.state().reservations


def test_release_returns_to_available(engine) -> None:
    engine.append(entity_event("tenant-a", "worker-1"))
    engine.append(resource_event("tenant-a", "worker-1"))
    engine.append(reserve_event("tenant-a", "r1", "worker-1", "worker-1", purpose="job-1"))
    now = utcnow()
    engine.append(
        CanonicalEvent(
            event_id="rel-r1",
            event_type=EventType.RESERVATION_RELEASED,
            tenant_id="tenant-a",
            subject="r1",
            source="kernel",
            effective_at=now,
            payload={"reservation_id": "r1"},
        )
    )
    assert engine.state().resources["worker-1"].state.value == "AVAILABLE"
    assert engine.state().reservations["r1"].status == "RELEASED"
