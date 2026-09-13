"""Deterministic seed world for the Health Operations Pack P0 runtime."""

from __future__ import annotations

from datetime import timedelta
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


def seed_world(*, revoke_appointment_authority: bool = False) -> KernelEngine:
    """Seed only the minimum explicit reality required by the health demo.

    The world grants exact, narrow capabilities to three executable actors.
    It does not grant a prescribing capability and does not infer authority
    from patient speech, caller identity, provider credentials, or model output.
    """
    kernel = KernelEngine("health")
    now = utcnow()
    provenance = Provenance(
        source_type="system",
        source_id="health-pack-p0",
        source_system="valo-health-pack",
    )

    def add_entity(
        entity_id: str,
        entity_type: EntityType,
        *,
        state: str | None = None,
        **attributes: Any,
    ) -> None:
        kernel.append(
            CanonicalEvent(
                event_id=f"seed-health-entity-{entity_id}",
                event_type=EventType.ENTITY_REGISTERED,
                tenant_id="health",
                subject=entity_id,
                source="health-pack",
                effective_at=now,
                payload={
                    "entity": Entity(
                        entity_id=entity_id,
                        entity_type=entity_type,
                        tenant_id="health",
                        state=state,
                        attributes=attributes,
                        provenance=provenance,
                    )
                },
            )
        )

    add_entity("patient-1", EntityType.PERSON, health_kind="patient")
    add_entity("clinician-1", EntityType.PERSON, health_kind="clinician")
    add_entity("health-admin-1", EntityType.SERVICE_IDENTITY, health_kind="administrator")
    add_entity("health-system-1", EntityType.SERVICE_IDENTITY, health_kind="health-system")
    add_entity("health-record-1", EntityType.CASE, state="DRAFT", health_kind="clinical-record")
    add_entity("appointment-1", EntityType.RESOURCE, state="AVAILABLE", health_kind="appointment")
    add_entity("renewal-1", EntityType.CASE, state="NEW", health_kind="renewal-request")

    for actor, identity_id, claim_type in (
        ("clinician-1", "id-clinician-1", "professional_identity"),
        ("health-admin-1", "id-health-admin-1", "service_identity"),
        ("health-system-1", "id-health-system-1", "service_identity"),
    ):
        kernel.append(
            CanonicalEvent(
                event_id=f"seed-health-identity-{identity_id}",
                event_type=EventType.IDENTITY_CLAIMED,
                tenant_id="health",
                subject=actor,
                source="health-pack",
                effective_at=now,
                payload={
                    "identity": IdentityClaim(
                        identity_id=identity_id,
                        entity_id=actor,
                        tenant_id="health",
                        claim_type=claim_type,
                        value=identity_id,
                        verification_status=VerificationStatus.VERIFIED,
                    )
                },
            )
        )

    valid = TimeWindow(
        valid_from=now - timedelta(days=1),
        valid_until=now + timedelta(days=365),
    )
    grants = (
        ("clinician-1", "CLINICAL_REVIEW", "health-record-1"),
        ("clinician-1", "CLINICAL_RECORD_WRITE", "health-record-1"),
        ("clinician-1", "CLINICAL_DECISION_RECORD", "renewal-1"),
        ("health-admin-1", "APPOINTMENT_ADMIN", "appointment-1"),
        ("health-system-1", "RENEWAL_INTAKE", "renewal-1"),
        ("health-system-1", "RENEWAL_ROUTING", "renewal-1"),
        ("health-system-1", "CLINICAL_REVIEW_REQUEST", "renewal-1"),
        ("health-system-1", "PATIENT_COMMUNICATION", "renewal-1"),
    )
    for principal, capability, target in grants:
        authority_id = f"auth-{principal}-{capability}"
        kernel.append(
            CanonicalEvent(
                event_id=f"seed-health-authority-{principal}-{capability}",
                event_type=EventType.AUTHORITY_GRANTED,
                tenant_id="health",
                subject=principal,
                source="health-pack",
                effective_at=now,
                payload={
                    "authority": Authority(
                        authority_id=authority_id,
                        principal=principal,
                        capability=capability,
                        scope=[target],
                        basis="health-pack-p0.explicit-test-mandate",
                        validity=valid,
                    )
                },
            )
        )

    if revoke_appointment_authority:
        kernel.append(
            CanonicalEvent(
                event_id="seed-health-revoke-appointment-admin",
                event_type=EventType.AUTHORITY_REVOKED,
                tenant_id="health",
                subject="health-admin-1",
                source="health-pack",
                effective_at=now,
                payload={
                    "authority_id": "auth-health-admin-1-APPOINTMENT_ADMIN",
                    "revocation_ref": "health-test-revocation-1",
                },
            )
        )

    return kernel
