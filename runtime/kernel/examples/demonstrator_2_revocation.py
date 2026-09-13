"""Demonstrator 2: authority revocation.

Initial: agent A has authority to BOOK. A workflow starts. The authority is
revoked. The workflow attempts WRITE. The execution context is re-read. REHT
sees no authority -> DENY. No booking happens. This is a mandatory negative
test.
"""

from __future__ import annotations

from datetime import timedelta

from valo_kernel import KernelEngine, build_execution_context
from valo_kernel.contracts import (
    Authority,
    CanonicalEvent,
    EntityType,
    EventType,
    IdentityClaim,
    Reservation,
    TimeWindow,
    VerificationStatus,
    utcnow,
)


def run() -> dict:
    tenant = "demo-2"
    engine = KernelEngine(tenant)
    now = utcnow()
    prov = {"source_type": "system", "source_id": "bootstrap", "source_system": "valo-kernel"}

    engine.append(
        CanonicalEvent(
            event_id="entity-agent-a",
            event_type=EventType.ENTITY_REGISTERED,
            tenant_id=tenant,
            subject="agent-a",
            source="kernel",
            effective_at=now,
            payload={"entity": {"entity_id": "agent-a", "entity_type": EntityType.AGENT, "tenant_id": tenant, "provenance": prov}},
        )
    )
    engine.append(
        CanonicalEvent(
            event_id="id-agent-a",
            event_type=EventType.IDENTITY_CLAIMED,
            tenant_id=tenant,
            subject="agent-a",
            source="kernel",
            effective_at=now,
            payload={
                "identity": IdentityClaim(
                    identity_id="id-agent-a",
                    entity_id="agent-a",
                    tenant_id=tenant,
                    claim_type="service_identity",
                    value="agent-a",
                    verification_status=VerificationStatus.VERIFIED,
                )
            },
        )
    )

    def authority_payload(valid_until) -> dict:
        return {
            "authority": Authority(
                authority_id="auth-book",
                principal="agent-a",
                capability="BOOK",
                scope=["job-*"],
                basis="workflow-policy",
                validity=TimeWindow(valid_from=now, valid_until=valid_until),
            )
        }

    engine.append(
        CanonicalEvent(
            event_id="auth-book",
            event_type=EventType.AUTHORITY_GRANTED,
            tenant_id=tenant,
            subject="agent-a",
            source="kernel",
            effective_at=now,
            payload=authority_payload(now + timedelta(days=1)),
        )
    )

    def requested() -> CanonicalEvent:
        return CanonicalEvent(
            event_id="req-book",
            event_type=EventType.RESOURCE_RESERVED,
            tenant_id=tenant,
            subject="resource-x",
            actor="agent-a",
            source="reht",
            effective_at=utcnow(),
            payload={"reservation": Reservation(reservation_id="r1", resource_id="resource-x", holder="agent-a", tenant_id=tenant).model_dump(mode="json")},
        )

    # workflow starts: authority is active
    context_before = build_execution_context(
        engine.state(),
        actor="agent-a",
        capability="BOOK",
        target="resource-x",
        requested_transition=requested(),
        identity_id="id-agent-a",
    )
    assert context_before["authority"], "authority must be active at workflow start"

    # authority is revoked mid-workflow
    engine.append(
        CanonicalEvent(
            event_id="revoke-book",
            event_type=EventType.AUTHORITY_REVOKED,
            tenant_id=tenant,
            subject="agent-a",
            source="kernel",
            effective_at=utcnow(),
            payload={"authority_id": "auth-book", "revocation_ref": "rev-1"},
        )
    )

    # workflow re-reads execution context before WRITE
    context_after = build_execution_context(
        engine.state(),
        actor="agent-a",
        capability="BOOK",
        target="resource-x",
        requested_transition=requested(),
        identity_id="id-agent-a",
    )
    assert context_after["authority"] == [], "REHT must see no authority after revocation"

    # no booking may happen: no reservation event was written
    assert "r1" not in engine.state().reservations
    assert "resource-x" not in engine.state().resources

    return {"authority_before": len(context_before["authority"]), "authority_after": len(context_after["authority"])}


def test_demonstrator_2_revocation() -> None:
    result = run()
    assert result["authority_before"] == 1
    assert result["authority_after"] == 0


if __name__ == "__main__":
    print(run())
