from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from ..contracts.admission import (
    AdmissionCandidate,
    AdmissionDecision,
    AdmissionOutcome,
    AdmissionPolicy,
    ProviderAdmissionAssessment,
)
from ..contracts.authority import Authority, Delegation
from ..contracts.common import (
    EvidenceStatus,
    ResourceState,
    TruthStatus,
    VerificationStatus,
)
from ..contracts.contract import Contract
from ..contracts.entity import Entity
from ..contracts.events import CanonicalEvent, EventType
from ..contracts.evidence import Evidence
from ..contracts.fact import Fact
from ..contracts.identity import IdentityClaim
from ..contracts.obligations import Obligation
from ..contracts.purpose import Purpose
from ..contracts.relationship import Relationship
from ..contracts.resource import Reservation, Resource
from ..contracts.rights import Right
from ..world.state import WorldState
from .admission import evaluate_state_admission
from .errors import KernelInvariantViolation


def _take(payload: dict[str, Any], key: str, cls: type[BaseModel]) -> BaseModel:
    obj = payload.get(key)
    if obj is None:
        raise KernelInvariantViolation(f"missing payload field: {key}")
    if isinstance(obj, dict):
        return cls.model_validate(obj)
    if isinstance(obj, cls):
        return obj
    raise KernelInvariantViolation(f"payload field {key} has invalid type")


def _check_tenant(value: BaseModel, event: CanonicalEvent) -> None:
    tenant_id = getattr(value, "tenant_id", None)
    if tenant_id is not None and tenant_id != event.tenant_id:
        raise KernelInvariantViolation(
            f"cross-tenant reference denied: object tenant {tenant_id} != event tenant {event.tenant_id}"
        )


def _require_admitted_evidence(
    state: WorldState,
    evidence_refs: list[str] | tuple[str, ...],
    *,
    require_nonempty: bool = False,
) -> None:
    if require_nonempty and not evidence_refs:
        raise KernelInvariantViolation("operative state requires admitted evidence")
    for evidence_id in evidence_refs:
        evidence = state.evidence.get(evidence_id)
        if evidence is None or evidence.status != EvidenceStatus.ADMITTED:
            raise KernelInvariantViolation(
                f"evidence is not admitted: {evidence_id}"
            )
        decision_id = evidence.admission_decision_ref
        decision = state.admissions.get(decision_id) if decision_id else None
        if (
            decision is None
            or decision.outcome != AdmissionOutcome.ADMIT
            or decision.evidence_id != evidence_id
            or decision.decision_digest != evidence.admission_digest
        ):
            raise KernelInvariantViolation(
                f"evidence admission binding is invalid: {evidence_id}"
            )


def _register_entity(state: WorldState, event: CanonicalEvent) -> WorldState:
    entity: Entity = _take(event.payload, "entity", Entity)
    _check_tenant(entity, event)
    _require_admitted_evidence(state, entity.provenance.evidence_refs)
    if entity.entity_id in state.entities:
        raise KernelInvariantViolation(
            f"duplicate canonical entity ID: {entity.entity_id}"
        )
    state = state.model_copy(
        update={"entities": {**state.entities, entity.entity_id: entity}}
    )
    return state


def _identity_claimed(state: WorldState, event: CanonicalEvent) -> WorldState:
    claim: IdentityClaim = _take(event.payload, "identity", IdentityClaim)
    _check_tenant(claim, event)
    if claim.entity_id not in state.entities:
        raise KernelInvariantViolation(
            f"identity refers to unknown entity: {claim.entity_id}"
        )
    if claim.identity_id in state.identities:
        raise KernelInvariantViolation(f"duplicate identity claim: {claim.identity_id}")
    return state.model_copy(
        update={"identities": {**state.identities, claim.identity_id: claim}}
    )


def _identity_verified(state: WorldState, event: CanonicalEvent) -> WorldState:
    claim = _must(state.identities, event.payload, "identity_id", "identity")
    updated = claim.model_copy(
        update={
            "verification_status": VerificationStatus.VERIFIED,
            "verification_ref": event.payload.get("verification_ref"),
        }
    )
    return state.model_copy(
        update={"identities": {**state.identities, claim.identity_id: updated}}
    )


def _identity_revoked(state: WorldState, event: CanonicalEvent) -> WorldState:
    claim = _must(state.identities, event.payload, "identity_id", "identity")
    updated = claim.model_copy(update={"revoked_at": event.timestamp})
    return state.model_copy(
        update={"identities": {**state.identities, claim.identity_id: updated}}
    )


def _relationship_established(state: WorldState, event: CanonicalEvent) -> WorldState:
    rel: Relationship = _take(event.payload, "relationship", Relationship)
    _check_tenant(rel, event)
    _require_admitted_evidence(state, rel.evidence_refs)
    if rel.source not in state.entities or rel.target not in state.entities:
        raise KernelInvariantViolation("relationship refers to unknown entity")
    if rel.relationship_id in state.relationships:
        raise KernelInvariantViolation(f"duplicate relationship: {rel.relationship_id}")
    return state.model_copy(
        update={"relationships": {**state.relationships, rel.relationship_id: rel}}
    )


def _relationship_terminated(state: WorldState, event: CanonicalEvent) -> WorldState:
    rel = _must(state.relationships, event.payload, "relationship_id", "relationship")
    updated = rel.model_copy(
        update={
            "validity": rel.validity.model_copy(
                update={"valid_until": event.effective_at}
            )
        }
    )
    return state.model_copy(
        update={"relationships": {**state.relationships, rel.relationship_id: updated}}
    )


def _fact_asserted(state: WorldState, event: CanonicalEvent) -> WorldState:
    fact: Fact = _take(event.payload, "fact", Fact)
    _check_tenant(fact, event)
    # Probabilistic output keeps INFERRED; plain assertions default to ASSERTED.
    # CONFIRMED can never arrive through this event.
    status = fact.truth_status
    if status in (TruthStatus.UNKNOWN, TruthStatus.ASSERTED):
        status = TruthStatus.ASSERTED
    fact = fact.model_copy(update={"truth_status": status})
    return state.model_copy(update={"facts": {**state.facts, fact.fact_id: fact}})


def _fact_admitted(state: WorldState, event: CanonicalEvent) -> WorldState:
    fact = _must(state.facts, event.payload, "fact_id", "fact")
    evidence_refs = sorted(set(fact.evidence_refs) | set(event.evidence_refs))
    _require_admitted_evidence(state, evidence_refs, require_nonempty=True)
    updated = fact.model_copy(
        update={
            "truth_status": TruthStatus.ASSERTED,
            "evidence_refs": evidence_refs,
        }
    )
    return state.model_copy(update={"facts": {**state.facts, fact.fact_id: updated}})


def _fact_confirmed(state: WorldState, event: CanonicalEvent) -> WorldState:
    fact = _must(state.facts, event.payload, "fact_id", "fact")
    if fact.truth_status not in (TruthStatus.ASSERTED, TruthStatus.CONFIRMED):
        raise KernelInvariantViolation(
            f"cannot confirm fact {fact.fact_id} from truth status {fact.truth_status.value}"
        )
    evidence_refs = sorted(set(fact.evidence_refs) | set(event.evidence_refs))
    _require_admitted_evidence(state, evidence_refs, require_nonempty=True)
    updated = fact.model_copy(
        update={
            "truth_status": TruthStatus.CONFIRMED,
            "version": fact.version + 1,
            "evidence_refs": evidence_refs,
        }
    )
    return state.model_copy(update={"facts": {**state.facts, fact.fact_id: updated}})


def _fact_superseded(state: WorldState, event: CanonicalEvent) -> WorldState:
    fact = _must(state.facts, event.payload, "fact_id", "fact")
    updated = fact.model_copy(
        update={"truth_status": TruthStatus.STALE, "version": fact.version + 1}
    )
    return state.model_copy(update={"facts": {**state.facts, fact.fact_id: updated}})


def _fact_revoked(state: WorldState, event: CanonicalEvent) -> WorldState:
    fact = _must(state.facts, event.payload, "fact_id", "fact")
    updated = fact.model_copy(
        update={"truth_status": TruthStatus.REVOKED, "version": fact.version + 1}
    )
    return state.model_copy(update={"facts": {**state.facts, fact.fact_id: updated}})


def _fact_conflicted(state: WorldState, event: CanonicalEvent) -> WorldState:
    fact = _must(state.facts, event.payload, "fact_id", "fact")
    updated = fact.model_copy(
        update={
            "truth_status": TruthStatus.CONFLICTED,
            "object": event.payload.get("conflicting_value", fact.object),
            "version": fact.version + 1,
        }
    )
    return state.model_copy(update={"facts": {**state.facts, fact.fact_id: updated}})


def _evidence_received(state: WorldState, event: CanonicalEvent) -> WorldState:
    evidence: Evidence = _take(event.payload, "evidence", Evidence)
    _check_tenant(evidence, event)
    if evidence.status != EvidenceStatus.RECEIVED:
        raise KernelInvariantViolation("received evidence must begin as RECEIVED")
    if evidence.admission_decision_ref or evidence.admission_digest:
        raise KernelInvariantViolation("received evidence cannot arrive pre-admitted")
    if evidence.evidence_id in state.evidence:
        raise KernelInvariantViolation(f"duplicate evidence: {evidence.evidence_id}")
    return state.model_copy(
        update={"evidence": {**state.evidence, evidence.evidence_id: evidence}}
    )


def _state_admission_decided(
    state: WorldState, event: CanonicalEvent
) -> WorldState:
    if event.source != "valo-kernel:admission":
        raise KernelInvariantViolation("admission decision must be VALO-owned")
    try:
        candidate = AdmissionCandidate.model_validate(event.payload.get("candidate"))
        policy = AdmissionPolicy.model_validate(event.payload.get("policy"))
        assessments = tuple(
            ProviderAdmissionAssessment.model_validate(item)
            for item in event.payload.get("assessments", [])
        )
        supplied = AdmissionDecision.model_validate(event.payload.get("decision"))
    except (TypeError, ValueError) as exc:
        raise KernelInvariantViolation("invalid state admission payload") from exc
    if supplied.decision_id in state.admissions:
        raise KernelInvariantViolation(
            f"duplicate admission decision: {supplied.decision_id}"
        )
    if supplied.decided_at != event.effective_at:
        raise KernelInvariantViolation("admission decision time mismatch")
    recomputed = evaluate_state_admission(
        state,
        candidate,
        policy,
        assessments,
        moment=supplied.decided_at,
        decision_id=supplied.decision_id,
    )
    if recomputed.model_dump(mode="json") != supplied.model_dump(mode="json"):
        raise KernelInvariantViolation("admission decision is not reproducible")

    evidence = state.evidence.get(supplied.evidence_id)
    if evidence is None:
        raise KernelInvariantViolation("admission decision evidence is missing")
    status = {
        AdmissionOutcome.ADMIT: EvidenceStatus.ADMITTED,
        AdmissionOutcome.REJECT: EvidenceStatus.REJECTED,
        AdmissionOutcome.QUARANTINE: EvidenceStatus.QUARANTINED,
        AdmissionOutcome.HOLD: (
            EvidenceStatus.CONTRADICTED
            if supplied.contradiction_refs
            else EvidenceStatus.UNVERIFIED
        ),
    }[supplied.outcome]
    updated_evidence = evidence.model_copy(
        update={
            "status": status,
            "admission_decision_ref": supplied.decision_id,
            "admission_digest": supplied.decision_digest,
        }
    )

    facts = dict(state.facts)
    if supplied.outcome != AdmissionOutcome.ADMIT:
        for fact_id, fact in state.facts.items():
            if supplied.evidence_id not in fact.evidence_refs:
                continue
            next_status = (
                TruthStatus.CONFLICTED
                if supplied.contradiction_refs
                else TruthStatus.STALE
            )
            if fact.truth_status not in (TruthStatus.REVOKED, TruthStatus.STALE):
                facts[fact_id] = fact.model_copy(
                    update={
                        "truth_status": next_status,
                        "version": fact.version + 1,
                    }
                )

    return state.model_copy(
        update={
            "evidence": {**state.evidence, evidence.evidence_id: updated_evidence},
            "admissions": {
                **state.admissions,
                supplied.decision_id: supplied,
            },
            "facts": facts,
        }
    )


def _evidence_admitted(state: WorldState, event: CanonicalEvent) -> WorldState:
    evidence = _must(state.evidence, event.payload, "evidence_id", "evidence")
    decision_id = event.payload.get("admission_decision_id")
    decision = state.admissions.get(decision_id)
    if (
        decision is None
        or decision.outcome != AdmissionOutcome.ADMIT
        or decision.evidence_id != evidence.evidence_id
        or evidence.admission_decision_ref != decision_id
        or evidence.admission_digest != decision.decision_digest
    ):
        raise KernelInvariantViolation(
            "EVIDENCE_ADMITTED requires a matching VALO admission decision"
        )
    updated = evidence.model_copy(update={"status": EvidenceStatus.ADMITTED})
    return state.model_copy(
        update={"evidence": {**state.evidence, evidence.evidence_id: updated}}
    )


def _evidence_rejected(state: WorldState, event: CanonicalEvent) -> WorldState:
    evidence = _must(state.evidence, event.payload, "evidence_id", "evidence")
    decision_id = event.payload.get("admission_decision_id")
    decision = state.admissions.get(decision_id)
    if (
        decision is None
        or decision.outcome
        not in (AdmissionOutcome.REJECT, AdmissionOutcome.QUARANTINE)
        or decision.evidence_id != evidence.evidence_id
        or evidence.admission_decision_ref != decision_id
        or evidence.admission_digest != decision.decision_digest
    ):
        raise KernelInvariantViolation(
            "EVIDENCE_REJECTED requires a matching VALO admission decision"
        )
    updated = evidence.model_copy(
        update={
            "status": (
                EvidenceStatus.QUARANTINED
                if decision.outcome == AdmissionOutcome.QUARANTINE
                else EvidenceStatus.REJECTED
            )
        }
    )
    return state.model_copy(
        update={"evidence": {**state.evidence, evidence.evidence_id: updated}}
    )


def _evidence_superseded(state: WorldState, event: CanonicalEvent) -> WorldState:
    evidence = _must(state.evidence, event.payload, "evidence_id", "evidence")
    updated = evidence.model_copy(update={"status": evidence.status.SUPERSEDED})
    return state.model_copy(
        update={"evidence": {**state.evidence, evidence.evidence_id: updated}}
    )


def _authority_granted(state: WorldState, event: CanonicalEvent) -> WorldState:
    authority: Authority = _take(event.payload, "authority", Authority)
    if authority.principal not in state.entities:
        raise KernelInvariantViolation(
            f"authority principal is unknown entity: {authority.principal}"
        )
    if authority.authority_id in state.authorities:
        raise KernelInvariantViolation(f"duplicate authority: {authority.authority_id}")
    return state.model_copy(
        update={"authorities": {**state.authorities, authority.authority_id: authority}}
    )


def _authority_revoked(state: WorldState, event: CanonicalEvent) -> WorldState:
    authority = _must(state.authorities, event.payload, "authority_id", "authority")
    updated = authority.model_copy(
        update={
            "status": "REVOKED",
            "revoked_at": event.timestamp,
            "revocation_ref": event.payload.get("revocation_ref"),
        }
    )
    return state.model_copy(
        update={"authorities": {**state.authorities, authority.authority_id: updated}}
    )


def _delegation_granted(state: WorldState, event: CanonicalEvent) -> WorldState:
    delegation: Delegation = _take(event.payload, "delegation", Delegation)
    parent = state.authorities.get(delegation.authority_ref)
    if parent is None:
        raise KernelInvariantViolation(
            f"delegation refers to unknown authority: {delegation.authority_ref}"
        )
    if not parent.delegable:
        raise KernelInvariantViolation(
            f"authority {parent.authority_id} is not delegable"
        )
    # Canonical rule: delegation can never increase authority.
    parent_scope = set(parent.scope)
    if not set(delegation.scope_reduction).issubset(parent_scope):
        raise KernelInvariantViolation(
            "delegation scope would exceed parent authority scope"
        )
    if delegation.delegation_id in state.delegations:
        raise KernelInvariantViolation(
            f"duplicate delegation: {delegation.delegation_id}"
        )
    return state.model_copy(
        update={
            "delegations": {**state.delegations, delegation.delegation_id: delegation}
        }
    )


def _delegation_revoked(state: WorldState, event: CanonicalEvent) -> WorldState:
    delegation = _must(state.delegations, event.payload, "delegation_id", "delegation")
    updated = delegation.model_copy(update={"revoked_at": event.timestamp})
    return state.model_copy(
        update={"delegations": {**state.delegations, delegation.delegation_id: updated}}
    )


def _right_granted(state: WorldState, event: CanonicalEvent) -> WorldState:
    right: Right = _take(event.payload, "right", Right)
    if right.right_id in state.rights:
        raise KernelInvariantViolation(f"duplicate right: {right.right_id}")
    return state.model_copy(update={"rights": {**state.rights, right.right_id: right}})


def _right_revoked(state: WorldState, event: CanonicalEvent) -> WorldState:
    right = _must(state.rights, event.payload, "right_id", "right")
    updated = right.model_copy(update={"status": "REVOKED"})
    return state.model_copy(
        update={"rights": {**state.rights, right.right_id: updated}}
    )


def _obligation_created(state: WorldState, event: CanonicalEvent) -> WorldState:
    obligation: Obligation = _take(event.payload, "obligation", Obligation)
    if obligation.obligation_id in state.obligations:
        raise KernelInvariantViolation(
            f"duplicate obligation: {obligation.obligation_id}"
        )
    return state.model_copy(
        update={
            "obligations": {**state.obligations, obligation.obligation_id: obligation}
        }
    )


def _obligation_satisfied(state: WorldState, event: CanonicalEvent) -> WorldState:
    obligation = _must(state.obligations, event.payload, "obligation_id", "obligation")
    updated = obligation.model_copy(update={"status": "SATISFIED"})
    return state.model_copy(
        update={"obligations": {**state.obligations, obligation.obligation_id: updated}}
    )


def _obligation_failed(state: WorldState, event: CanonicalEvent) -> WorldState:
    obligation = _must(state.obligations, event.payload, "obligation_id", "obligation")
    updated = obligation.model_copy(update={"status": "FAILED"})
    return state.model_copy(
        update={"obligations": {**state.obligations, obligation.obligation_id: updated}}
    )


def _purpose_registered(state: WorldState, event: CanonicalEvent) -> WorldState:
    purpose: Purpose = _take(event.payload, "purpose", Purpose)
    if purpose.purpose_id in state.purposes:
        raise KernelInvariantViolation(f"duplicate purpose: {purpose.purpose_id}")
    if purpose.validity.valid_until <= event.effective_at:
        raise KernelInvariantViolation("cannot register an already-expired purpose")
    return state.model_copy(
        update={"purposes": {**state.purposes, purpose.purpose_id: purpose}}
    )


def _purpose_revoked(state: WorldState, event: CanonicalEvent) -> WorldState:
    purpose = _must(state.purposes, event.payload, "purpose_id", "purpose")
    if event.effective_at <= purpose.validity.valid_from:
        raise KernelInvariantViolation("purpose revocation must follow its valid_from")
    if event.effective_at >= purpose.validity.valid_until:
        raise KernelInvariantViolation("purpose is already inactive")
    validity = purpose.validity.model_copy(update={"valid_until": event.effective_at})
    updated = purpose.model_copy(update={"validity": validity})
    return state.model_copy(
        update={"purposes": {**state.purposes, purpose.purpose_id: updated}}
    )


def _resource_registered(state: WorldState, event: CanonicalEvent) -> WorldState:
    resource: Resource = _take(event.payload, "resource", Resource)
    _check_tenant(resource, event)
    if resource.resource_id in state.resources:
        raise KernelInvariantViolation(f"duplicate resource: {resource.resource_id}")
    return state.model_copy(
        update={"resources": {**state.resources, resource.resource_id: resource}}
    )


def _resource_reserved(state: WorldState, event: CanonicalEvent) -> WorldState:
    reservation: Reservation = _take(event.payload, "reservation", Reservation)
    _check_tenant(reservation, event)
    resource = state.resources.get(reservation.resource_id)
    if resource is None:
        raise KernelInvariantViolation(f"unknown resource: {reservation.resource_id}")
    if not resource.can_reserve():
        raise KernelInvariantViolation(
            f"resource {resource.resource_id} is not reservable (state={resource.state.value})"
        )
    if reservation.quantity > resource.available:
        raise KernelInvariantViolation(
            "reservation quantity exceeds available capacity"
        )
    updated_resource = resource.model_copy(
        update={
            "state": ResourceState.RESERVED,
            "allocated": reservation.quantity,
            "holder": reservation.holder,
        }
    )
    if reservation.reservation_id in state.reservations:
        raise KernelInvariantViolation(
            f"duplicate reservation: {reservation.reservation_id}"
        )
    return state.model_copy(
        update={
            "resources": {**state.resources, resource.resource_id: updated_resource},
            "reservations": {
                **state.reservations,
                reservation.reservation_id: reservation,
            },
        }
    )


def _resource_allocated(state: WorldState, event: CanonicalEvent) -> WorldState:
    resource = _must(state.resources, event.payload, "resource_id", "resource")
    quantity = int(event.payload.get("quantity", 1))
    if resource.state != ResourceState.RESERVED:
        raise KernelInvariantViolation("allocation requires a prior reservation")
    if quantity > resource.available:
        raise KernelInvariantViolation("allocation exceeds capacity")
    updated = resource.model_copy(
        update={
            "state": ResourceState.ALLOCATED,
            "allocated": resource.allocated + quantity,
            "holder": event.payload.get("holder", resource.holder),
        }
    )
    return state.model_copy(
        update={"resources": {**state.resources, resource.resource_id: updated}}
    )


def _resource_released(state: WorldState, event: CanonicalEvent) -> WorldState:
    resource = _must(state.resources, event.payload, "resource_id", "resource")
    updated = resource.model_copy(
        update={"state": ResourceState.AVAILABLE, "allocated": 0, "holder": None}
    )
    return state.model_copy(
        update={"resources": {**state.resources, resource.resource_id: updated}}
    )


def _resource_consumed(state: WorldState, event: CanonicalEvent) -> WorldState:
    resource = _must(state.resources, event.payload, "resource_id", "resource")
    updated = resource.model_copy(
        update={"state": ResourceState.CONSUMED, "allocated": 0}
    )
    return state.model_copy(
        update={"resources": {**state.resources, resource.resource_id: updated}}
    )


def _resource_unavailable(state: WorldState, event: CanonicalEvent) -> WorldState:
    resource = _must(state.resources, event.payload, "resource_id", "resource")
    updated = resource.model_copy(update={"state": ResourceState.UNAVAILABLE})
    return state.model_copy(
        update={"resources": {**state.resources, resource.resource_id: updated}}
    )


def _contract_signed(state: WorldState, event: CanonicalEvent) -> WorldState:
    contract: Contract = _take(event.payload, "contract", Contract)
    _check_tenant(contract, event)
    if contract.contract_id in state.contracts:
        raise KernelInvariantViolation(f"duplicate contract: {contract.contract_id}")
    return state.model_copy(
        update={"contracts": {**state.contracts, contract.contract_id: contract}}
    )


def _contract_amended(state: WorldState, event: CanonicalEvent) -> WorldState:
    contract = _must(state.contracts, event.payload, "contract_id", "contract")
    updated = contract.model_copy(
        update={"version": contract.version + 1, "status": "AMENDED"}
    )
    return state.model_copy(
        update={"contracts": {**state.contracts, contract.contract_id: updated}}
    )


def _contract_terminated(state: WorldState, event: CanonicalEvent) -> WorldState:
    contract = _must(state.contracts, event.payload, "contract_id", "contract")
    updated = contract.model_copy(update={"status": "TERMINATED"})
    return state.model_copy(
        update={"contracts": {**state.contracts, contract.contract_id: updated}}
    )


def _reservation_released(state: WorldState, event: CanonicalEvent) -> WorldState:
    reservation = _must(
        state.reservations, event.payload, "reservation_id", "reservation"
    )
    resource = state.resources.get(reservation.resource_id)
    updated_reservation = reservation.model_copy(update={"status": "RELEASED"})
    new_state = state.model_copy(
        update={
            "reservations": {
                **state.reservations,
                reservation.reservation_id: updated_reservation,
            }
        }
    )
    if resource is not None and resource.state == ResourceState.RESERVED:
        released = resource.model_copy(
            update={"state": ResourceState.AVAILABLE, "allocated": 0, "holder": None}
        )
        new_state = new_state.model_copy(
            update={
                "resources": {**new_state.resources, resource.resource_id: released}
            }
        )
    return new_state


def _reservation_expired(state: WorldState, event: CanonicalEvent) -> WorldState:
    reservation = _must(
        state.reservations, event.payload, "reservation_id", "reservation"
    )
    updated = reservation.model_copy(update={"status": "EXPIRED"})
    return state.model_copy(
        update={
            "reservations": {**state.reservations, reservation.reservation_id: updated}
        }
    )


def _reservation_consumed(state: WorldState, event: CanonicalEvent) -> WorldState:
    reservation = _must(
        state.reservations, event.payload, "reservation_id", "reservation"
    )
    updated = reservation.model_copy(update={"status": "CONSUMED"})
    return state.model_copy(
        update={
            "reservations": {**state.reservations, reservation.reservation_id: updated}
        }
    )


def _entity_updated(state: WorldState, event: CanonicalEvent) -> WorldState:
    entity = _must(state.entities, event.payload, "entity_id", "entity")
    update: dict[str, Any] = {"version": entity.version + 1}
    if "attributes" in event.payload:
        update["attributes"] = {**entity.attributes, **event.payload["attributes"]}
    if "state" in event.payload:
        update["state"] = event.payload["state"]
    return state.model_copy(
        update={
            "entities": {
                **state.entities,
                entity.entity_id: entity.model_copy(update=update),
            }
        }
    )


def _execution_phase_updated(state: WorldState, event: CanonicalEvent) -> WorldState:
    process_ref = event.payload.get("process_ref", event.subject)
    phase = event.payload.get("phase")
    if phase is None:
        raise KernelInvariantViolation("EXECUTION_PHASE_UPDATED requires a phase")
    clocks = dict(state.clocks)
    clocks[f"{process_ref}:phase"] = phase
    return state.model_copy(update={"clocks": clocks})


def _correction(state: WorldState, event: CanonicalEvent) -> WorldState:
    """Correction path: history is never rewritten. A correction updates the
    entity's working state (state field) with a version bump. Backdated
    effective_at is allowed for CORRECTION events only."""
    entity = _must(state.entities, event.payload, "entity_id", "entity")
    new_state = event.payload.get("new_state", event.payload.get("state"))
    if new_state is None:
        raise KernelInvariantViolation("CORRECTION requires a new_state")
    updated = entity.model_copy(
        update={"state": new_state, "version": entity.version + 1}
    )
    return state.model_copy(
        update={"entities": {**state.entities, entity.entity_id: updated}}
    )


def _divergence_recorded(state: WorldState, event: CanonicalEvent) -> WorldState:
    process_ref = event.payload.get("process_ref", event.subject)
    clocks = dict(state.clocks)
    clocks[f"{process_ref}:divergence"] = {
        "expected": event.payload.get("expected"),
        "observed": event.payload.get("observed"),
    }
    return state.model_copy(update={"clocks": clocks})


def _must(
    collection: dict[str, Any], payload: dict[str, Any], key: str, label: str
) -> BaseModel:
    obj_id = payload.get(key)
    obj = collection.get(obj_id) if obj_id is not None else None
    if obj is None:
        raise KernelInvariantViolation(f"unknown {label}: {obj_id}")
    return obj


def _noop(state: WorldState, event: CanonicalEvent) -> WorldState:
    return state


REDUCERS: dict[EventType, Callable[[WorldState, CanonicalEvent], WorldState]] = {
    EventType.ENTITY_REGISTERED: _register_entity,
    EventType.ENTITY_UPDATED: _entity_updated,
    EventType.IDENTITY_CLAIMED: _identity_claimed,
    EventType.IDENTITY_VERIFIED: _identity_verified,
    EventType.IDENTITY_REVOKED: _identity_revoked,
    EventType.RELATIONSHIP_ESTABLISHED: _relationship_established,
    EventType.RELATIONSHIP_TERMINATED: _relationship_terminated,
    EventType.FACT_ASSERTED: _fact_asserted,
    EventType.FACT_ADMITTED: _fact_admitted,
    EventType.FACT_CONFIRMED: _fact_confirmed,
    EventType.FACT_SUPERSEDED: _fact_superseded,
    EventType.FACT_REVOKED: _fact_revoked,
    EventType.FACT_CONFLICTED: _fact_conflicted,
    EventType.EVIDENCE_RECEIVED: _evidence_received,
    EventType.STATE_ADMISSION_DECIDED: _state_admission_decided,
    EventType.EVIDENCE_ADMITTED: _evidence_admitted,
    EventType.EVIDENCE_REJECTED: _evidence_rejected,
    EventType.EVIDENCE_SUPERSEDED: _evidence_superseded,
    EventType.AUTHORITY_GRANTED: _authority_granted,
    EventType.AUTHORITY_REVOKED: _authority_revoked,
    EventType.DELEGATION_GRANTED: _delegation_granted,
    EventType.DELEGATION_REVOKED: _delegation_revoked,
    EventType.RIGHT_GRANTED: _right_granted,
    EventType.RIGHT_REVOKED: _right_revoked,
    EventType.OBLIGATION_CREATED: _obligation_created,
    EventType.OBLIGATION_SATISFIED: _obligation_satisfied,
    EventType.OBLIGATION_FAILED: _obligation_failed,
    EventType.PURPOSE_REGISTERED: _purpose_registered,
    EventType.PURPOSE_REVOKED: _purpose_revoked,
    EventType.RESOURCE_REGISTERED: _resource_registered,
    EventType.RESOURCE_RESERVED: _resource_reserved,
    EventType.RESOURCE_ALLOCATED: _resource_allocated,
    EventType.RESOURCE_RELEASED: _resource_released,
    EventType.RESOURCE_CONSUMED: _resource_consumed,
    EventType.RESOURCE_UNAVAILABLE: _resource_unavailable,
    EventType.CONTRACT_SIGNED: _contract_signed,
    EventType.CONTRACT_AMENDED: _contract_amended,
    EventType.CONTRACT_TERMINATED: _contract_terminated,
    EventType.RESERVATION_RELEASED: _reservation_released,
    EventType.RESERVATION_EXPIRED: _reservation_expired,
    EventType.RESERVATION_CONSUMED: _reservation_consumed,
    EventType.EXECUTION_PHASE_UPDATED: _execution_phase_updated,
    EventType.DIVERGENCE_RECORDED: _divergence_recorded,
    EventType.CORRECTION: _correction,
    EventType.EXTERNAL_EFFECT_OBSERVED: _noop,
    EventType.TRANSITION_VALIDATED: _noop,
}


def reduce(
    state: WorldState,
    event: CanonicalEvent,
    extra_reducers: dict[str, Callable[[WorldState, CanonicalEvent], WorldState]]
    | None = None,
) -> WorldState:
    """Deterministic reducer: Previous State + Canonical Event -> New State.

    Pack reducers are explicit engine dependencies. They run inside the same
    tenant, invariant, version, idempotency and chain checks as core reducers.
    """
    reducer = REDUCERS.get(event.event_type)
    if reducer is None and isinstance(event.event_type, str) and extra_reducers:
        reducer = extra_reducers.get(event.event_type)
    if reducer is None:
        raise KernelInvariantViolation(f"unknown event type: {event.event_type}")
    return reducer(state, event)
