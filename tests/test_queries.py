from __future__ import annotations

from datetime import timedelta

from valo_kernel import Queries
from valo_kernel.contracts import (
    Authority,
    CanonicalEvent,
    EventType,
    TimeWindow,
    utcnow,
)

from .conftest import entity_event, make_provenance, reserve_event, resource_event


def _grant(engine, actor: str, capability: str, scope: list[str]) -> None:
    now = utcnow()
    engine.append(
        CanonicalEvent(
            event_id=f"auth-{actor}-{capability}",
            event_type=EventType.AUTHORITY_GRANTED,
            tenant_id="tenant-a",
            subject=actor,
            source="kernel",
            effective_at=now,
            payload={
                "authority": Authority(
                    authority_id=f"auth-{actor}-{capability}",
                    principal=actor,
                    capability=capability,
                    scope=scope,
                    basis="b",
                    validity=TimeWindow(valid_from=now, valid_until=now + timedelta(days=30)),
                )
            },
        )
    )


def test_query_who_may_act(engine) -> None:
    engine.append(entity_event("tenant-a", "agent-a"))
    _grant(engine, "agent-a", "BOOK", ["job-1"])
    q = Queries(engine.state())
    assert q.who_may_act("BOOK") == ["agent-a"]


def test_query_resources_available(engine) -> None:
    engine.append(entity_event("tenant-a", "worker-1"))
    engine.append(resource_event("tenant-a", "worker-1"))
    engine.append(resource_event("tenant-a", "worker-2"))
    engine.append(reserve_event("tenant-a", "r1", "worker-1", "worker-1", purpose="job-1"))
    q = Queries(engine.state())
    assert q.resources_available() == ["worker-2"]


def test_query_what_was_true_at(engine) -> None:
    engine.append(entity_event("tenant-a", "worker-1"))
    now = utcnow()
    engine.append(
        CanonicalEvent(
            event_id="fact-1",
            event_type=EventType.FACT_ASSERTED,
            tenant_id="tenant-a",
            subject="worker-1",
            source="kernel",
            effective_at=now,
            payload={
                "fact": {
                    "fact_id": "f1",
                    "subject": "worker-1",
                    "predicate": "certified",
                    "object": "true",
                    "tenant_id": "tenant-a",
                    "provenance": make_provenance("f1").model_dump(mode="json"),
                }
            },
        )
    )
    q = Queries(engine.state())
    after = utcnow()
    past = q.what_was_true_at("worker-1", after - timedelta(seconds=5), events=engine.events())
    assert past == []  # fact recorded after the query moment
    present = q.what_was_true_at("worker-1", after, events=engine.events())
    assert present[0]["predicate"] == "certified"


def test_query_expiring_soon(engine) -> None:
    engine.append(entity_event("tenant-a", "agent-a"))
    now = utcnow()
    engine.append(
        CanonicalEvent(
            event_id="auth-short",
            event_type=EventType.AUTHORITY_GRANTED,
            tenant_id="tenant-a",
            subject="agent-a",
            source="kernel",
            effective_at=now,
            payload={
                "authority": Authority(
                    authority_id="auth-short",
                    principal="agent-a",
                    capability="BOOK",
                    scope=[],
                    basis="b",
                    validity=TimeWindow(
                        valid_from=now, valid_until=now + timedelta(hours=1)
                    ),
                )
            },
        )
    )
    q = Queries(engine.state())
    soon = q.expiring_soon(timedelta(days=1), moment=now)
    assert [a["authority_id"] for a in soon["authorities"]] == ["auth-short"]
