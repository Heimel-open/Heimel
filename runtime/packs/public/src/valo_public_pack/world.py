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

DISQUALIFYING_RELATIONS = frozenset({"SPOUSE", "CHILD", "PARENT", "SIBLING", "SELF", "CLOSE_BUSINESS"})


def seed_world(
    *,
    legal_basis_active: bool = True,
    competence_active: bool = True,
    revoke_competence: bool = False,
    residency_conflicted: bool = False,
    decision_maker_relationship: str | None = None,
    evidence_stale: bool = False,
    purpose_violation: bool = False,
    has_representation: bool = False,
    representation_scope_ok: bool = True,
    applicant_age: int = 30,
    service: str = "PUBLIC_SERVICE_A",
) -> KernelEngine:
    """Seed ONLY raw reality. No adjudicated flags: whether the case is
    eligible, whether the decision maker is disqualified, whether the evidence
    is acceptable, whether the representation is valid, whether the legal basis
    applies — NONE of that is seeded. It is derived deterministically at the
    decision boundary from the raw facts below."""
    kernel = KernelEngine("public")
    now = utcnow()
    prov = Provenance(source_type="system", source_id="seed", source_system="public-pack")

    def entity(entity_id: str, etype: EntityType, state: str | None = None, **attrs: Any) -> None:
        kernel.append(
            CanonicalEvent(
                event_id=f"seed-entity-{entity_id}",
                event_type=EventType.ENTITY_REGISTERED,
                tenant_id="public",
                subject=entity_id,
                source="kernel",
                effective_at=now,
                payload={
                    "entity": Entity(
                        entity_id=entity_id,
                        entity_type=etype,
                        tenant_id="public",
                        state=state,
                        attributes=attrs,
                        provenance=prov,
                    )
                },
            )
        )

    entity("applicant-1", EntityType.PERSON, attributes={"name": "Applicant A", "age": applicant_age, "residency": "NO"})

    # RAW reality attached to the case: raw facts and raw relations.
    # - residency_fact: raw evidentiary status of the residency fact
    #   (CONFIRMED | CONFLICTED) — a conflicted critical fact must block a
    #   decision, never be force-confirmed.
    # - relations: raw relationships between the decision maker and the
    #   applicant (habilitet), e.g. {"subject", "object", "kind"}.
    # - evidence: raw evidence submissions with their raw status + purpose.
    # - representation: raw representation declaration, or absent.
    # - service: the service the application targets (purpose binding).
    relations: list[dict[str, Any]] = []
    if decision_maker_relationship is not None:
        relations.append(
            {"subject": "system-1", "object": "applicant-1", "kind": decision_maker_relationship}
        )
    evidence: list[dict[str, Any]] = [{
        "type": "residency_document",
        "status": "STALE" if evidence_stale else "ADMITTED",
        "purpose": "SERVICE_B" if purpose_violation else service,
    }]
    representation: dict[str, Any] | None = None
    if has_representation:
        representation = {"representative": "rep-1", "scope": "FULL" if representation_scope_ok else "LIMITED"}

    entity(
        "case-1", EntityType.CASE, state="RECEIVED",
        applicant_id="applicant-1",
        age=applicant_age,
        residency_fact="CONFLICTED" if residency_conflicted else "CONFIRMED",
        relations=relations,
        evidence=evidence,
        representation=representation,
        service=service,
    )
    entity("system-1", EntityType.SERVICE_IDENTITY)

    kernel.append(
        CanonicalEvent(
            event_id="seed-id-system",
            event_type=EventType.IDENTITY_CLAIMED,
            tenant_id="public",
            subject="system-1",
            source="kernel",
            effective_at=now,
            payload={
                "identity": IdentityClaim(
                    identity_id="id-system-1",
                    entity_id="system-1",
                    tenant_id="public",
                    claim_type="service_identity",
                    value="id-system-1",
                    verification_status=VerificationStatus.VERIFIED,
                )
            },
        )
    )

    # Legal basis is a SEPARATE authority from competence. Both carry their own
    # validity window; both must be active at the decision boundary.
    legal_until = now + timedelta(days=3650) if legal_basis_active else now - timedelta(days=1)
    competence_until = now + timedelta(days=3650) if competence_active else now - timedelta(days=1)
    kernel.append(
        CanonicalEvent(
            event_id="seed-auth-legal-basis",
            event_type=EventType.AUTHORITY_GRANTED,
            tenant_id="public",
            subject="system-1",
            source="kernel",
            effective_at=now,
            payload={
                "authority": Authority(
                    authority_id="auth-system-LEGAL_BASIS",
                    principal="system-1",
                    capability="LEGAL_BASIS",
                    scope=["case-1"],
                    constraints={"service": service},
                    basis="basis.public_service_a.v1",
                    validity=TimeWindow(valid_from=now - timedelta(days=365), valid_until=legal_until),
                )
            },
        )
    )
    kernel.append(
        CanonicalEvent(
            event_id="seed-auth-competence",
            event_type=EventType.AUTHORITY_GRANTED,
            tenant_id="public",
            subject="system-1",
            source="kernel",
            effective_at=now,
            payload={
                "authority": Authority(
                    authority_id="auth-system-ISSUE_DECISION",
                    principal="system-1",
                    capability="ISSUE_DECISION",
                    scope=["case-1"],
                    basis="competence.public_body_a",
                    validity=TimeWindow(valid_from=now - timedelta(days=365), valid_until=competence_until),
                )
            },
        )
    )
    if revoke_competence:
        kernel.append(
            CanonicalEvent(
                event_id="seed-revoke-issue",
                event_type=EventType.AUTHORITY_REVOKED,
                tenant_id="public",
                subject="system-1",
                source="kernel",
                effective_at=now,
                payload={"authority_id": "auth-system-ISSUE_DECISION", "revocation_ref": "rev-1"},
            )
        )

    # administrative authority for register/notify/deadline writes
    kernel.append(
        CanonicalEvent(
            event_id="seed-auth-admin",
            event_type=EventType.AUTHORITY_GRANTED,
            tenant_id="public",
            subject="system-1",
            source="kernel",
            effective_at=now,
            payload={
                "authority": Authority(
                    authority_id="auth-system-ADMIN",
                    principal="system-1",
                    capability="ADMIN",
                    scope=["case-1"],
                    basis="system",
                    validity=TimeWindow(valid_from=now - timedelta(days=365), valid_until=now + timedelta(days=3650)),
                )
            },
        )
    )
    return kernel
