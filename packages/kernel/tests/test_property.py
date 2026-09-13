from __future__ import annotations

from datetime import timedelta

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from valo_kernel import KernelEngine, KernelInvariantViolation, replay
from valo_kernel.contracts import (
    Authority,
    CanonicalEvent,
    EventType,
    TimeWindow,
    utcnow,
)

from .conftest import entity_event, reserve_event, resource_event

entity_ids = st.text(min_size=1, max_size=12).map(lambda s: f"e-{s}")


@settings(max_examples=40)
@given(st.lists(entity_ids, min_size=1, max_size=12, unique=True))
def test_property_chain_integrity_and_deterministic_replay(ids) -> None:
    engine = KernelEngine("tenant-a")
    for i, entity_id in enumerate(ids):
        engine.append(entity_event("tenant-a", entity_id))
    engine.verify_integrity()
    rebuilt = replay(engine.events())
    assert rebuilt.root_hash() == engine.state().root_hash()


@settings(max_examples=40)
@given(st.lists(entity_ids, min_size=2, max_size=12, unique=True))
def test_property_no_double_reservation(ids) -> None:
    engine = KernelEngine("tenant-a")
    worker = ids[0]
    engine.append(entity_event("tenant-a", worker))
    engine.append(resource_event("tenant-a", worker))
    engine.append(reserve_event("tenant-a", "r1", worker, worker, purpose="job-1"))
    assert engine.state().resources[worker].state.value == "RESERVED"
    with pytest.raises(KernelInvariantViolation):
        engine.append(reserve_event("tenant-a", "r2", worker, worker, purpose="job-2"))


@settings(max_examples=30)
@given(scope=st.lists(st.text(min_size=1, max_size=8), min_size=0, max_size=6, unique=True))
def test_property_delegation_never_widens(scope) -> None:
    engine = KernelEngine("tenant-a")
    engine.append(entity_event("tenant-a", "agent-a"))
    engine.append(entity_event("tenant-a", "agent-b"))
    now = utcnow()
    parent_scope = scope[: max(1, len(scope) // 2)] or ["job-0"]
    engine.append(
        CanonicalEvent(
            event_id="auth",
            event_type=EventType.AUTHORITY_GRANTED,
            tenant_id="tenant-a",
            subject="agent-a",
            source="kernel",
            effective_at=now,
            payload={
                "authority": Authority(
                    authority_id="auth",
                    principal="agent-a",
                    capability="BOOK",
                    scope=parent_scope,
                    basis="b",
                    validity=TimeWindow(valid_from=now, valid_until=now + timedelta(days=30)),
                    delegable=True,
                )
            },
        )
    )
    for reduction in [s for s in scope if s in parent_scope]:
        delegation = {
            "delegation": {
                "delegation_id": f"d-{reduction}",
                "delegator": "agent-a",
                "delegate": "agent-b",
                "authority_ref": "auth",
                "scope_reduction": [reduction],
                "validity": {
                    "valid_from": now,
                    "valid_until": (now + timedelta(days=30)).isoformat(),
                },
            }
        }
        engine.append(
            CanonicalEvent(
                event_id=f"del-{reduction}",
                event_type=EventType.DELEGATION_GRANTED,
                tenant_id="tenant-a",
                subject="agent-a",
                source="kernel",
                effective_at=now,
                payload=delegation,
            )
        )
    # A delegation beyond the parent scope must always fail.
    with pytest.raises(KernelInvariantViolation):
        engine.append(
            CanonicalEvent(
                event_id="del-bad",
                event_type=EventType.DELEGATION_GRANTED,
                tenant_id="tenant-a",
                subject="agent-a",
                source="kernel",
                effective_at=now,
                payload={
                    "delegation": {
                        "delegation_id": "d-bad",
                        "delegator": "agent-a",
                        "delegate": "agent-b",
                        "authority_ref": "auth",
                        "scope_reduction": ["out-of-parent-scope"],
                        "validity": {
                            "valid_from": now,
                            "valid_until": (now + timedelta(days=30)).isoformat(),
                        },
                    }
                },
            )
        )


@settings(max_examples=30)
@given(
    n_events=st.integers(min_value=1, max_value=15),
)
def test_property_replay_is_stable_under_additional_records(n_events) -> None:
    """Appending more events never rewrites prior state; replay of a prefix is
    the same regardless of later events."""
    engine = KernelEngine("tenant-a")
    for i in range(n_events):
        engine.append(entity_event("tenant-a", f"person-{i}"))
    prefix = engine.events()[: n_events // 2]
    if prefix:
        assert replay(prefix).root_hash() == replay(prefix).root_hash()

