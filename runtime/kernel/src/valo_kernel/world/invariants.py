from __future__ import annotations

from ..contracts.admission import AdmissionOutcome
from ..contracts.common import EvidenceStatus, ResourceState, TruthStatus
from ..world.state import WorldState

IDENTITY_EQUIVALENCE_PREDICATES = frozenset(
    {
        "same_as",
        "same_entity_as",
        "identity_equivalent",
    }
)


def check_invariants(state: WorldState) -> list[str]:
    """Static world-invariant checks. Returns a list of violated invariant
    descriptions (empty == consistent). The engine fail-closes on any."""
    violations: list[str] = []

    for entity_id in state.entities:
        if entity_id != state.entities[entity_id].entity_id:
            violations.append(f"entity map key mismatch: {entity_id}")

    for authority in state.authorities.values():
        if authority.status == "REVOKED" and authority.revoked_at is None:
            violations.append(
                f"authority {authority.authority_id} is REVOKED without revoked_at"
            )

    for delegation in state.delegations.values():
        parent = state.authorities.get(delegation.authority_ref)
        if parent is None:
            violations.append(
                f"delegation {delegation.delegation_id} has unknown parent authority"
            )
            continue
        if not parent.delegable:
            violations.append(
                f"delegation {delegation.delegation_id} from non-delegable authority"
            )
        if not set(delegation.scope_reduction).issubset(set(parent.scope)):
            violations.append(
                f"delegation {delegation.delegation_id} exceeds parent authority scope"
            )

    for resource in state.resources.values():
        if resource.allocated > resource.capacity:
            violations.append(
                f"resource {resource.resource_id} allocation exceeds capacity"
            )
        if resource.allocated > 0 and resource.state == ResourceState.AVAILABLE:
            violations.append(
                f"resource {resource.resource_id} has allocation but is AVAILABLE"
            )

    for fact in state.facts.values():
        if fact.truth_status == TruthStatus.CONFLICTED and fact.object is None:
            violations.append(
                f"conflicted fact {fact.fact_id} has no conflicting value"
            )

        # Semantic identity integrity: similarity, correlation, shared structure,
        # or model inference must never silently become entity identity.
        # Explicit identity-equivalence claims are admissible only when both
        # entities exist and the claim is backed by evidence.
        if fact.predicate in IDENTITY_EQUIVALENCE_PREDICATES:
            if fact.subject not in state.entities:
                violations.append(
                    f"identity-equivalence fact {fact.fact_id} has unknown subject entity"
                )
            if fact.object not in state.entities:
                violations.append(
                    f"identity-equivalence fact {fact.fact_id} has unknown object entity"
                )
            if not fact.evidence_refs:
                violations.append(
                    f"identity-equivalence fact {fact.fact_id} has no evidence"
                )

        if fact.truth_status == TruthStatus.CONFIRMED:
            if not fact.evidence_refs:
                violations.append(
                    f"confirmed fact {fact.fact_id} has no admitted evidence"
                )
            for evidence_id in fact.evidence_refs:
                evidence = state.evidence.get(evidence_id)
                if evidence is None or evidence.status != EvidenceStatus.ADMITTED:
                    violations.append(
                        f"confirmed fact {fact.fact_id} uses non-admitted evidence"
                    )

    for decision_id, decision in state.admissions.items():
        if decision_id != decision.decision_id:
            violations.append(f"admission map key mismatch: {decision_id}")
        if decision.tenant_id != state.tenant_id:
            violations.append(f"cross-tenant admission decision {decision_id}")

    for evidence_id, evidence in state.evidence.items():
        if evidence.status != EvidenceStatus.ADMITTED:
            continue
        decision = (
            state.admissions.get(evidence.admission_decision_ref)
            if evidence.admission_decision_ref
            else None
        )
        if (
            decision is None
            or decision.outcome != AdmissionOutcome.ADMIT
            or decision.evidence_id != evidence_id
            or decision.decision_digest != evidence.admission_digest
        ):
            violations.append(
                f"admitted evidence {evidence_id} lacks a valid VALO decision"
            )

    for purpose_id, purpose in state.purposes.items():
        if purpose_id != purpose.purpose_id:
            violations.append(f"purpose map key mismatch: {purpose_id}")

    collections = (
        state.entities.values(),
        state.identities.values(),
        state.relationships.values(),
        state.facts.values(),
        state.evidence.values(),
        state.admissions.values(),
        state.resources.values(),
        state.reservations.values(),
        state.contracts.values(),
    )
    for collection in collections:
        for obj in collection:
            tenant_id = getattr(obj, "tenant_id", None)
            if tenant_id is not None and tenant_id != state.tenant_id:
                violations.append(
                    f"cross-tenant object {getattr(obj, 'id', '?')} in state"
                )

    return violations
