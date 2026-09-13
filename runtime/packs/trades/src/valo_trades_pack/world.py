from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from valo_kernel import KernelEngine
from valo_kernel.contracts import (
    Authority,
    CanonicalEvent,
    Entity,
    EntityType,
    EventType,
    IdentityClaim,
    Provenance,
    TimeWindow,
    VerificationStatus,
    utcnow,
)


def seed_world(
    *,
    expire_worker_b: bool = False,
    dispatch_credential_expired: bool = False,
    revoke_dispatch_authority: bool = False,
) -> KernelEngine:
    """Seed the authoritative world in the Kernel. Workers' credentials are
    authorities in Kernel state with explicit validity windows: at the REHT
    boundary a fresh execution context reflects exactly what is true now."""
    kernel = KernelEngine("trades")
    now = utcnow()
    prov = Provenance(source_type="system", source_id="seed", source_system="trades-pack")

    def entity(entity_id: str, etype: EntityType, state: str | None = None, **attrs: Any) -> None:
        kernel.append(
            CanonicalEvent(
                event_id=f"seed-entity-{entity_id}",
                event_type=EventType.ENTITY_REGISTERED,
                tenant_id="trades",
                subject=entity_id,
                source="kernel",
                effective_at=now,
                payload={
                    "entity": Entity(
                        entity_id=entity_id,
                        entity_type=etype,
                        tenant_id="trades",
                        state=state,
                        attributes=attrs,
                        provenance=prov,
                    )
                },
            )
        )

    entity("customer-1", EntityType.PERSON, attributes={"name": "Anna"})
    entity("site-1", EntityType.LOCATION, attributes={"address": "Exampleveien 1"})
    entity("workorder-1", EntityType.JOB, state="NEW")
    entity("worker-a", EntityType.PERSON, state="AVAILABLE")
    entity("worker-b", EntityType.PERSON, state="AVAILABLE")
    entity("system-1", EntityType.SERVICE_IDENTITY)

    # workers are reservable resources
    for worker in ("worker-a", "worker-b"):
        kernel.append(
            CanonicalEvent(
                event_id=f"seed-resource-{worker}",
                event_type=EventType.RESOURCE_REGISTERED,
                tenant_id="trades",
                subject=worker,
                source="kernel",
                effective_at=now,
                payload={"resource": {"resource_id": worker, "resource_type": "personnel", "tenant_id": "trades", "capacity": 1}},
            )
        )

    # verified identities for actors
    for actor, value in (("worker-a", "id-worker-a"), ("worker-b", "id-worker-b"), ("system-1", "id-system-1")):
        kernel.append(
            CanonicalEvent(
                event_id=f"seed-id-{actor}",
                event_type=EventType.IDENTITY_CLAIMED,
                tenant_id="trades",
                subject=actor,
                source="kernel",
                effective_at=now,
                payload={
                    "identity": IdentityClaim(
                        identity_id=value,
                        entity_id=actor,
                        tenant_id="trades",
                        claim_type="credential_id" if actor.startswith("worker") else "service_identity",
                        value=value,
                        verification_status=VerificationStatus.VERIFIED,
                    )
                },
            )
        )

    def grant_worker_authority(worker: str, valid_until: datetime, capability: str, basis: str) -> None:
        kernel.append(
            CanonicalEvent(
                event_id=f"seed-auth-{worker}-{capability}",
                event_type=EventType.AUTHORITY_GRANTED,
                tenant_id="trades",
                subject=worker,
                source="kernel",
                effective_at=now,
                payload={
                    "authority": Authority(
                        authority_id=f"auth-{worker}-{capability}",
                        principal=worker,
                        capability=capability,
                        scope=["workorder-1"],
                        basis=basis,
                        validity=TimeWindow(valid_from=now - timedelta(days=365), valid_until=valid_until),
                    )
                },
            )
        )

    # worker A fully qualified; worker B's ev competence already expired
    worker_a_dispatch_until = now - timedelta(days=1) if dispatch_credential_expired else now + timedelta(days=1825)
    worker_b_dispatch_until = now - timedelta(days=1)  # Worker B: available, credential expired
    for worker in ("worker-a", "worker-b"):
        grant_worker_authority(worker, now + timedelta(days=1825), "ALLOCATE", "bookable")
    grant_worker_authority("worker-a", worker_a_dispatch_until, "DISPATCH", "electrician_authorization+ev_installation_competence")
    grant_worker_authority("worker-b", worker_b_dispatch_until, "DISPATCH", "electrician_authorization+ev_installation_competence")
    if revoke_dispatch_authority:
        kernel.append(
            CanonicalEvent(
                event_id="seed-revoke-a",
                event_type=EventType.AUTHORITY_REVOKED,
                tenant_id="trades",
                subject="worker-a",
                source="kernel",
                effective_at=now,
                payload={"authority_id": "auth-worker-a-DISPATCH", "revocation_ref": "rev-1"},
            )
        )

    # system authority for administrative writes (register/invoice/notify)
    kernel.append(
        CanonicalEvent(
            event_id="seed-auth-system",
            event_type=EventType.AUTHORITY_GRANTED,
            tenant_id="trades",
            subject="system-1",
            source="kernel",
            effective_at=now,
            payload={
                "authority": Authority(
                    authority_id="auth-system-ADMIN",
                    principal="system-1",
                    capability="ADMIN",
                    scope=["workorder-1"],
                    basis="system",
                    validity=TimeWindow(valid_from=now - timedelta(days=365), valid_until=now + timedelta(days=3650)),
                )
            },
        )
    )
    return kernel
