from __future__ import annotations

import pytest

from valo_kernel import (
    ConcurrencyError,
    FailClosedError,
    IntegrityError,
    KernelInvariantViolation,
)
from valo_kernel.contracts import (
    Authority,
    CanonicalEvent,
    EventType,
    TimeWindow,
    TruthStatus,
    utcnow,
)

from .conftest import entity_event, reserve_event, resource_event


def test_direct_state_mutation_rejected_via_public_api(engine) -> None:
    """The public state() view is immutable: mutating it can never reach the
    authoritative state. All mutation must flow through events."""
    engine.append(entity_event("tenant-a", "person-1"))
    snapshot_root = engine.snapshot().state_root_hash

    view = engine.state()
    assert view.entities["person-1"].state is None
    view.entities["person-1"] = view.entities["person-1"].model_copy(
        update={"state": "EVIL"}
    )

    authoritative = engine.state()
    assert authoritative.entities["person-1"].state is None, "mutation leaked into authoritative state"
    assert engine.snapshot().state_root_hash == snapshot_root


def test_future_authority_used_early_rejected(engine) -> None:
    from datetime import timedelta

    engine.append(entity_event("tenant-a", "agent-a"))
    now = utcnow()
    future = now + timedelta(days=1)
    engine.append(
        CanonicalEvent(
            event_id="auth-future",
            event_type=EventType.AUTHORITY_GRANTED,
            tenant_id="tenant-a",
            subject="agent-a",
            source="kernel",
            effective_at=now,
            payload={
                "authority": Authority(
                    authority_id="auth-future",
                    principal="agent-a",
                    capability="BOOK",
                    scope=[],
                    basis="b",
                    validity=TimeWindow(valid_from=future, valid_until=future + timedelta(days=1)),
                )
            },
        )
    )
    from valo_kernel import Queries

    q = Queries(engine.state())
    assert q.who_may_act("BOOK") == []


def test_expired_authority_rejected(engine) -> None:
    from datetime import timedelta

    engine.append(entity_event("tenant-a", "agent-a"))
    now = utcnow()
    engine.append(
        CanonicalEvent(
            event_id="auth-exp",
            event_type=EventType.AUTHORITY_GRANTED,
            tenant_id="tenant-a",
            subject="agent-a",
            source="kernel",
            effective_at=now,
            payload={
                "authority": Authority(
                    authority_id="auth-exp",
                    principal="agent-a",
                    capability="BOOK",
                    scope=[],
                    basis="b",
                    validity=TimeWindow(
                        valid_from=now - timedelta(days=5), valid_until=now - timedelta(days=1)
                    ),
                )
            },
        )
    )
    from valo_kernel import Queries

    assert Queries(engine.state()).who_may_act("BOOK") == []


def test_stale_evidence_not_state(engine) -> None:
    engine.append(entity_event("tenant-a", "worker-1"))
    now = utcnow()
    engine.append(
        CanonicalEvent(
            event_id="ev-1",
            event_type=EventType.EVIDENCE_RECEIVED,
            tenant_id="tenant-a",
            subject="worker-1",
            source="external",
            effective_at=now,
            payload={
                "evidence": {
                    "evidence_id": "ev-1",
                    "type": "document",
                    "source": "hr",
                    "subject": "worker-1",
                    "tenant_id": "tenant-a",
                    "status": "RECEIVED",
                }
            },
        )
    )
    engine.append(
        CanonicalEvent(
            event_id="ev-sup",
            event_type=EventType.EVIDENCE_SUPERSEDED,
            tenant_id="tenant-a",
            subject="ev-1",
            source="veritas",
            effective_at=now,
            payload={"evidence_id": "ev-1"},
        )
    )
    # a superseded document must never become a confirmed fact by itself
    assert all(f.truth_status != TruthStatus.CONFIRMED for f in engine.state().facts.values())


def test_backdated_mutation_via_event_rejected(engine) -> None:
    from datetime import timedelta

    engine.append(entity_event("tenant-a", "worker-1"))
    now = utcnow()
    with pytest.raises(ValueError, match="precede"):
        CanonicalEvent(
            event_id="bd",
            event_type=EventType.ENTITY_UPDATED,
            tenant_id="tenant-a",
            subject="worker-1",
            source="kernel",
            timestamp=now,
            effective_at=now - timedelta(days=3),
            payload={"entity_id": "worker-1", "state": "X"},
        )


def test_event_chain_modification_detected(engine) -> None:
    engine.append(entity_event("tenant-a", "a"))
    engine.append(entity_event("tenant-a", "b"))
    events = engine.events()
    evil = events[0].model_copy(update={"subject": "evil"})
    with pytest.raises(IntegrityError):
        from valo_kernel import verify_chain

        verify_chain([evil, events[1]])


def test_missing_tenant_fail_closed() -> None:
    from valo_kernel import KernelEngine

    with pytest.raises(FailClosedError):
        KernelEngine(None)  # type: ignore[arg-type]


def test_state_version_conflict_is_optimistic(engine) -> None:
    engine.append(entity_event("tenant-a", "a"))
    engine.append(entity_event("tenant-a", "b"))
    with pytest.raises(ConcurrencyError):
        engine.append(entity_event("tenant-a", "c"), expected_version=1)


def test_double_reservation_end_to_end(engine) -> None:
    engine.append(entity_event("tenant-a", "worker-1"))
    engine.append(resource_event("tenant-a", "worker-1"))
    engine.append(reserve_event("tenant-a", "r1", "worker-1", "worker-1", purpose="job-1"))
    with pytest.raises(KernelInvariantViolation):
        engine.append(reserve_event("tenant-a", "r2", "worker-1", "worker-1", purpose="job-2"))


def test_cross_tenant_reference_in_relationship(engine) -> None:
    from datetime import timedelta

    from valo_kernel.contracts import Relationship, RelationType

    engine.append(entity_event("tenant-a", "worker-1"))
    now = utcnow()
    with pytest.raises(FailClosedError):
        engine.append(
            CanonicalEvent(
                event_id="rel-x",
                event_type=EventType.RELATIONSHIP_ESTABLISHED,
                tenant_id="tenant-a",
                subject="worker-1",
                source="kernel",
                effective_at=now,
                payload={
                    "relationship": Relationship(
                        relationship_id="rel-x",
                        source="worker-1",
                        relation_type=RelationType.EMPLOYED_BY,
                        target="org-b",  # belongs to tenant-b
                        tenant_id="tenant-b",
                        validity=TimeWindow(valid_from=now, valid_until=now + timedelta(days=1)),
                    )
                },
            )
        )

