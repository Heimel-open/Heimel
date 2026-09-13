"""Demonstrator 1: electrician job reservation.

Initial world: customer exists, job exists, electrician exists, credential
valid, electrician available, job READY. Request: reserve electrician for job.

Kernel reads state and returns execution context; REHT ALLOWs; the reservation
event is written; the new WorldState has the worker RESERVED for the job. A
parallel attempt to reserve the same worker FAILS.

Proves: identity, resource, state, authority context, events, concurrency,
replay.
"""

from __future__ import annotations

from datetime import timedelta

from valo_kernel import (
    ConcurrencyError,
    KernelEngine,
    KernelInvariantViolation,
    build_execution_context,
    replay,
)
from valo_kernel.contracts import (
    Authority,
    CanonicalEvent,
    EntityType,
    EventType,
    IdentityClaim,
    Provenance,
    Reservation,
    TimeWindow,
    VerificationStatus,
    utcnow,
)


def _provenance(source_id: str) -> Provenance:
    return Provenance(source_type="system", source_id=source_id, source_system="valo-kernel")


def run() -> dict:
    tenant = "demo-1"
    engine = KernelEngine(tenant)
    now = utcnow()
    prov = _provenance("bootstrap")

    def entity(entity_id: str, entity_type: EntityType, state: str | None = None) -> CanonicalEvent:
        return CanonicalEvent(
            event_id=f"entity-{entity_id}",
            event_type=EventType.ENTITY_REGISTERED,
            tenant_id=tenant,
            subject=entity_id,
            source="kernel",
            effective_at=now,
            payload={
                "entity": {
                    "entity_id": entity_id,
                    "entity_type": entity_type,
                    "tenant_id": tenant,
                    "state": state,
                    "provenance": prov.model_dump(mode="json"),
                }
            },
        )

    # 1. initial world
    engine.append(entity("customer-1", EntityType.PERSON))
    engine.append(entity("electrician-1", EntityType.PERSON))
    engine.append(entity("job-1", EntityType.JOB, state="READY"))
    engine.append(
        CanonicalEvent(
            event_id="resource-electrician-1",
            event_type=EventType.RESOURCE_REGISTERED,
            tenant_id=tenant,
            subject="electrician-1",
            source="kernel",
            effective_at=now,
            payload={
                "resource": {
                    "resource_id": "electrician-1",
                    "resource_type": "personnel",
                    "tenant_id": tenant,
                    "capacity": 1,
                }
            },
        )
    )
    # verified execution identity for the electrician
    engine.append(
        CanonicalEvent(
            event_id="id-electrician",
            event_type=EventType.IDENTITY_CLAIMED,
            tenant_id=tenant,
            subject="electrician-1",
            source="kernel",
            effective_at=now,
            payload={
                "identity": IdentityClaim(
                    identity_id="id-electrician",
                    entity_id="electrician-1",
                    tenant_id=tenant,
                    claim_type="credential_id",
                    value="cert-42",
                    verification_status=VerificationStatus.VERIFIED,
                )
            },
        )
    )
    # authority context for the booking
    engine.append(
        CanonicalEvent(
            event_id="auth-book",
            event_type=EventType.AUTHORITY_GRANTED,
            tenant_id=tenant,
            subject="electrician-1",
            source="kernel",
            effective_at=now,
            payload={
                "authority": Authority(
                    authority_id="auth-book",
                    principal="electrician-1",
                    capability="BOOK",
                    scope=["job-1"],
                    basis="schedule-policy",
                    validity=TimeWindow(valid_from=now, valid_until=now + timedelta(days=1)),
                )
            },
        )
    )

    # 2. kernel returns execution context to REHT
    requested = CanonicalEvent(
        event_id="req-reserve",
        event_type=EventType.RESOURCE_RESERVED,
        tenant_id=tenant,
        subject="electrician-1",
        actor="electrician-1",
        source="reht",
        effective_at=now,
        payload={"reservation": Reservation(reservation_id="r1", resource_id="electrician-1", holder="electrician-1", tenant_id=tenant, purpose="job-1").model_dump(mode="json")},
    )
    context = build_execution_context(
        engine.state(),
        actor="electrician-1",
        capability="BOOK",
        target="job-1",
        requested_transition=requested,
        identity_id="id-electrician",
    )
    assert context["authority"], "REHT must see active authority"
    assert context["current_state"]["state"] == "READY"

    # 3. REHT ALLOW -> reservation event written
    engine.append(requested)

    resource = engine.state().resources["electrician-1"]
    assert resource.state.value == "RESERVED", "electrician must be RESERVED"
    assert resource.holder == "electrician-1"
    assert engine.state().reservations["r1"].is_active()

    # 4. parallel attempt to reserve the same worker FAILS
    seq = engine.sequence()
    parallel = CanonicalEvent(
        event_id="req-reserve-2",
        event_type=EventType.RESOURCE_RESERVED,
        tenant_id=tenant,
        subject="electrician-1",
        actor="electrician-1",
        source="reht",
        effective_at=now,
        payload={"reservation": Reservation(reservation_id="r2", resource_id="electrician-1", holder="electrician-1", tenant_id=tenant, purpose="job-2").model_dump(mode="json")},
    )
    try:
        engine.append(parallel, expected_version=seq)
        raise AssertionError("parallel reservation must fail")
    except ConcurrencyError:
        pass
    try:
        engine.append(parallel)
        raise AssertionError("double reservation must fail")
    except KernelInvariantViolation:
        pass

    # 5. deterministic replay
    rebuilt = replay(engine.events())
    assert rebuilt.root_hash() == engine.state().root_hash()

    engine.verify_integrity()
    return {"reserved": resource.state.value, "sequence": engine.sequence(), "root": engine.snapshot().state_root_hash}


def test_demonstrator_1_reservation() -> None:
    result = run()
    assert result["reserved"] == "RESERVED"


if __name__ == "__main__":
    print(run())
