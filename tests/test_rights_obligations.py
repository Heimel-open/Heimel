from __future__ import annotations

from datetime import timedelta

from valo_kernel.contracts import (
    CanonicalEvent,
    EntityType,
    EventType,
    Obligation,
    Right,
    TimeWindow,
    utcnow,
)

from .conftest import entity_event


def test_rights_first_class(engine) -> None:
    engine.append(entity_event("tenant-a", "person-1"))
    now = utcnow()
    engine.append(
        CanonicalEvent(
            event_id="right-1",
            event_type=EventType.RIGHT_GRANTED,
            tenant_id="tenant-a",
            subject="person-1",
            source="kernel",
            effective_at=now,
            payload={
                "right": Right(
                    right_id="r1",
                    holder="person-1",
                    right_type="APPEAL",
                    object="case-1",
                    basis="law-ref",
                    validity=TimeWindow(valid_from=now, valid_until=now + timedelta(days=30)),
                )
            },
        )
    )
    from valo_kernel import Queries

    q = Queries(engine.state())
    assert q.rights_applying("person-1")[0]["right_type"] == "APPEAL"


def test_obligations_first_class(engine) -> None:
    engine.append(entity_event("tenant-a", "org-1", entity_type=EntityType.ORGANIZATION))
    now = utcnow()
    engine.append(
        CanonicalEvent(
            event_id="ob-1",
            event_type=EventType.OBLIGATION_CREATED,
            tenant_id="tenant-a",
            subject="org-1",
            source="kernel",
            effective_at=now,
            payload={
                "obligation": Obligation(
                    obligation_id="o1",
                    obligated_party="org-1",
                    action_required="deliver_service",
                    beneficiary="customer-1",
                    basis="contract-ref",
                    deadline=now + timedelta(days=7),
                    validity=TimeWindow(valid_from=now, valid_until=now + timedelta(days=30)),
                )
            },
        )
    )
    from valo_kernel import Queries

    q = Queries(engine.state())
    assert q.obligations_active("org-1")[0]["action_required"] == "deliver_service"


def test_obligation_satisfied(engine) -> None:
    engine.append(entity_event("tenant-a", "org-1", entity_type=EntityType.ORGANIZATION))
    now = utcnow()
    engine.append(
        CanonicalEvent(
            event_id="ob-1",
            event_type=EventType.OBLIGATION_CREATED,
            tenant_id="tenant-a",
            subject="org-1",
            source="kernel",
            effective_at=now,
            payload={
                "obligation": Obligation(
                    obligation_id="o1",
                    obligated_party="org-1",
                    action_required="deliver_service",
                    basis="contract-ref",
                    validity=TimeWindow(valid_from=now, valid_until=now + timedelta(days=30)),
                )
            },
        )
    )
    engine.append(
        CanonicalEvent(
            event_id="ob-done",
            event_type=EventType.OBLIGATION_SATISFIED,
            tenant_id="tenant-a",
            subject="o1",
            source="veritas",
            effective_at=now,
            payload={"obligation_id": "o1"},
        )
    )
    assert engine.state().obligations["o1"].status == "SATISFIED"
