from __future__ import annotations

from datetime import timedelta

import pytest

from valo_kernel import KernelInvariantViolation
from valo_kernel.contracts import (
    Authority,
    CanonicalEvent,
    Delegation,
    EventType,
    TimeWindow,
    utcnow,
)

from .conftest import entity_event


def grant_authority(engine, authority_id: str, principal: str, capability: str, scope: list[str], delegable: bool = False) -> None:
    now = utcnow()
    engine.append(
        CanonicalEvent(
            event_id=f"auth-{authority_id}",
            event_type=EventType.AUTHORITY_GRANTED,
            tenant_id="tenant-a",
            subject=principal,
            source="kernel",
            effective_at=now,
            payload={
                "authority": Authority(
                    authority_id=authority_id,
                    principal=principal,
                    capability=capability,
                    scope=scope,
                    basis="role-schema",
                    validity=TimeWindow(valid_from=now, valid_until=now + timedelta(days=30)),
                    delegable=delegable,
                )
            },
        )
    )


def test_authority_validity(engine) -> None:
    engine.append(entity_event("tenant-a", "agent-a"))
    grant_authority(engine, "a1", "agent-a", "BOOK", ["job-*"])
    authority = engine.state().authorities["a1"]
    assert authority.is_active()


def test_expired_authority_inactive(engine) -> None:
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
                    authority_id="a-exp",
                    principal="agent-a",
                    capability="BOOK",
                    scope=[],
                    basis="x",
                    validity=TimeWindow(valid_from=now - timedelta(days=5), valid_until=now - timedelta(days=1)),
                )
            },
        )
    )
    assert not engine.state().authorities["a-exp"].is_active(now)


def test_authority_granted_to_unknown_principal_rejected(engine) -> None:
    with pytest.raises(KernelInvariantViolation, match="principal"):
        grant_authority(engine, "a1", "ghost", "BOOK", ["job-*"])


def test_revocation(engine) -> None:
    engine.append(entity_event("tenant-a", "agent-a"))
    grant_authority(engine, "a1", "agent-a", "BOOK", ["job-*"])
    now = utcnow()
    engine.append(
        CanonicalEvent(
            event_id="rev-a1",
            event_type=EventType.AUTHORITY_REVOKED,
            tenant_id="tenant-a",
            subject="agent-a",
            source="kernel",
            effective_at=now,
            payload={"authority_id": "a1", "revocation_ref": "rev-1"},
        )
    )
    assert not engine.state().authorities["a1"].is_active(now)


def test_no_authority_after_revocation(engine) -> None:
    """Workflow started under authority, authority revoked, subsequent WRITE
    is denied by the kernel's execution-context view (no active authority)."""
    engine.append(entity_event("tenant-a", "agent-a"))
    grant_authority(engine, "a1", "agent-a", "BOOK", ["job-*"])
    engine.append(
        CanonicalEvent(
            event_id="rev-a1",
            event_type=EventType.AUTHORITY_REVOKED,
            tenant_id="tenant-a",
            subject="agent-a",
            source="kernel",
            effective_at=utcnow(),
            payload={"authority_id": "a1", "revocation_ref": "rev-1"},
        )
    )
    from valo_kernel import Queries

    q = Queries(engine.state())
    assert q.who_may_act("BOOK") == []


def test_delegation_narrowing(engine) -> None:
    engine.append(entity_event("tenant-a", "agent-a"))
    engine.append(entity_event("tenant-a", "agent-b"))
    grant_authority(engine, "a1", "agent-a", "BOOK", ["job-1", "job-2", "job-3"], delegable=True)
    now = utcnow()
    engine.append(
        CanonicalEvent(
            event_id="del-1",
            event_type=EventType.DELEGATION_GRANTED,
            tenant_id="tenant-a",
            subject="agent-a",
            source="kernel",
            effective_at=now,
            payload={
                "delegation": Delegation(
                    delegation_id="d1",
                    delegator="agent-a",
                    delegate="agent-b",
                    authority_ref="a1",
                    scope_reduction=["job-1"],
                    validity=TimeWindow(valid_from=now, valid_until=now + timedelta(days=10)),
                )
            },
        )
    )
    assert engine.state().delegations["d1"].is_active()


def test_delegation_expansion_rejected(engine) -> None:
    engine.append(entity_event("tenant-a", "agent-a"))
    engine.append(entity_event("tenant-a", "agent-b"))
    grant_authority(engine, "a1", "agent-a", "BOOK", ["job-1"], delegable=True)
    now = utcnow()
    with pytest.raises(KernelInvariantViolation, match="exceed"):
        engine.append(
            CanonicalEvent(
                event_id="del-bad",
                event_type=EventType.DELEGATION_GRANTED,
                tenant_id="tenant-a",
                subject="agent-a",
                source="kernel",
                effective_at=now,
                payload={
                    "delegation": Delegation(
                        delegation_id="d-bad",
                        delegator="agent-a",
                        delegate="agent-b",
                        authority_ref="a1",
                        scope_reduction=["job-1", "job-2"],
                        validity=TimeWindow(valid_from=now, valid_until=now + timedelta(days=10)),
                    )
                },
            )
        )


def test_delegation_from_non_delegable_rejected(engine) -> None:
    engine.append(entity_event("tenant-a", "agent-a"))
    engine.append(entity_event("tenant-a", "agent-b"))
    grant_authority(engine, "a1", "agent-a", "BOOK", ["job-1"], delegable=False)
    now = utcnow()
    with pytest.raises(KernelInvariantViolation, match="not delegable"):
        engine.append(
            CanonicalEvent(
                event_id="del-bad",
                event_type=EventType.DELEGATION_GRANTED,
                tenant_id="tenant-a",
                subject="agent-a",
                source="kernel",
                effective_at=now,
                payload={
                    "delegation": Delegation(
                        delegation_id="d-bad",
                        delegator="agent-a",
                        delegate="agent-b",
                        authority_ref="a1",
                        scope_reduction=["job-1"],
                        validity=TimeWindow(valid_from=now, valid_until=now + timedelta(days=10)),
                    )
                },
            )
        )
