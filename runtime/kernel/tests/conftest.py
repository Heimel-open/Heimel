from __future__ import annotations

from datetime import timedelta

import pytest

from valo_kernel import KernelEngine, create_admission_event
from valo_kernel.contracts import (
    AdmissionCandidate,
    AdmissionPolicy,
    CanonicalEvent,
    Entity,
    EntityType,
    EventType,
    Evidence,
    Provenance,
    Reservation,
    Resource,
    TimeWindow,
    utcnow,
)


def make_provenance(source_id: str = "bootstrap") -> Provenance:
    return Provenance(
        source_type="system", source_id=source_id, source_system="valo-kernel"
    )


def entity_event(
    tenant: str,
    entity_id: str,
    entity_type: EntityType = EntityType.PERSON,
    state: str | None = None,
    attributes: dict | None = None,
) -> CanonicalEvent:
    now = utcnow()
    return CanonicalEvent(
        event_id=f"entity-{entity_id}",
        event_type=EventType.ENTITY_REGISTERED,
        tenant_id=tenant,
        subject=entity_id,
        source="kernel",
        effective_at=now,
        payload={
            "entity": Entity(
                entity_id=entity_id,
                entity_type=entity_type,
                tenant_id=tenant,
                state=state,
                attributes=attributes or {},
                provenance=make_provenance(entity_id),
            )
        },
    )


def resource_event(tenant: str, resource_id: str, capacity: int = 1) -> CanonicalEvent:
    now = utcnow()
    return CanonicalEvent(
        event_id=f"resource-{resource_id}",
        event_type=EventType.RESOURCE_REGISTERED,
        tenant_id=tenant,
        subject=resource_id,
        source="kernel",
        effective_at=now,
        payload={
            "resource": Resource(
                resource_id=resource_id,
                resource_type="personnel",
                tenant_id=tenant,
                capacity=capacity,
            )
        },
    )


def evidence_event(
    tenant: str,
    evidence_id: str,
    subject: str,
    *,
    fingerprint: str = "a" * 64,
) -> CanonicalEvent:
    now = utcnow()
    return CanonicalEvent(
        event_id=f"receive-{evidence_id}",
        event_type=EventType.EVIDENCE_RECEIVED,
        tenant_id=tenant,
        subject=subject,
        source="external",
        timestamp=now,
        effective_at=now,
        payload={
            "evidence": Evidence(
                evidence_id=evidence_id,
                type="document",
                source="test-source",
                subject=subject,
                tenant_id=tenant,
                captured_at=now,
                integrity_hash=fingerprint,
            )
        },
    )


def admit_evidence(engine: KernelEngine, evidence_id: str) -> None:
    evidence = engine.state().evidence[evidence_id]
    candidate = AdmissionCandidate(
        candidate_id=f"candidate-{evidence_id}",
        tenant_id=engine.tenant_id,
        evidence_id=evidence_id,
        material_type=evidence.type,
        source_fingerprint=evidence.integrity_hash,
        subject_refs=(evidence.subject,),
        entity_refs=(evidence.subject,),
        provenance_refs=(f"source:{evidence.source}",),
        captured_at=evidence.captured_at,
    )
    policy = AdmissionPolicy(
        policy_id="native-default",
        tenant_id=engine.tenant_id,
    )
    engine.append(
        create_admission_event(
            engine.state(),
            candidate,
            policy,
            event_id=f"admit-{evidence_id}",
        )
    )


def reserve_event(
    tenant: str,
    reservation_id: str,
    resource_id: str,
    holder: str,
    purpose: str | None = None,
) -> CanonicalEvent:
    now = utcnow()
    return CanonicalEvent(
        event_id=f"reserve-{reservation_id}",
        event_type=EventType.RESOURCE_RESERVED,
        tenant_id=tenant,
        subject=resource_id,
        actor=holder,
        source="reht",
        effective_at=now,
        payload={
            "reservation": Reservation(
                reservation_id=reservation_id,
                resource_id=resource_id,
                holder=holder,
                tenant_id=tenant,
                purpose=purpose,
            )
        },
    )


def window(days: int = 30, from_now: bool = True) -> TimeWindow:
    now = utcnow()
    return TimeWindow(
        valid_from=now - (timedelta(0) if from_now else timedelta(days=30)),
        valid_until=now + timedelta(days=days),
    )


@pytest.fixture
def engine() -> KernelEngine:
    return KernelEngine("tenant-a")
