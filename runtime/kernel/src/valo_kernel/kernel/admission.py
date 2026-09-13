from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from ..contracts.admission import (
    AdmissionCandidate,
    AdmissionDecision,
    AdmissionOutcome,
    AdmissionPolicy,
    ProviderAdmissionAssessment,
    ProviderAdmissionDisposition,
)
from ..contracts.common import EvidenceStatus, utcnow
from ..contracts.events import CanonicalEvent, EventType
from ..world.state import WorldState
from .errors import FailClosedError


def _seal_candidate(candidate: AdmissionCandidate) -> AdmissionCandidate:
    if candidate.candidate_digest:
        if candidate.candidate_digest != candidate.computed_digest:
            raise FailClosedError("admission candidate digest mismatch")
        return candidate
    return candidate.model_copy(update={"candidate_digest": candidate.computed_digest})


def _seal_policy(policy: AdmissionPolicy) -> AdmissionPolicy:
    if policy.policy_digest:
        if policy.policy_digest != policy.computed_digest:
            raise FailClosedError("admission policy digest mismatch")
        return policy
    return policy.model_copy(update={"policy_digest": policy.computed_digest})


def _seal_assessment(
    assessment: ProviderAdmissionAssessment,
) -> ProviderAdmissionAssessment:
    if assessment.assessment_digest:
        if assessment.assessment_digest != assessment.computed_digest:
            raise FailClosedError("provider assessment digest mismatch")
        return assessment
    return assessment.model_copy(
        update={"assessment_digest": assessment.computed_digest}
    )


def evaluate_state_admission(
    state: WorldState,
    candidate: AdmissionCandidate,
    policy: AdmissionPolicy,
    assessments: Iterable[ProviderAdmissionAssessment] = (),
    *,
    moment: datetime | None = None,
    decision_id: str | None = None,
) -> AdmissionDecision:
    """Apply VALO-owned deterministic admission policy to candidate material.

    Provider assessments are optional inputs. They may narrow or preclude an
    admission only when the tenant policy explicitly trusts them. They never
    create state, authority or clearance.
    """
    moment = moment or utcnow()
    candidate = _seal_candidate(candidate)
    policy = _seal_policy(policy)
    assessments = tuple(_seal_assessment(item) for item in assessments)

    if state.tenant_id != candidate.tenant_id or policy.tenant_id != state.tenant_id:
        raise FailClosedError("admission tenant binding mismatch")
    evidence = state.evidence.get(candidate.evidence_id)
    if evidence is None:
        raise FailClosedError("admission candidate refers to unknown evidence")
    if evidence.tenant_id != state.tenant_id:
        raise FailClosedError("admission evidence tenant mismatch")
    if evidence.status == EvidenceStatus.SUPERSEDED:
        raise FailClosedError("superseded evidence cannot be admitted")
    if evidence.type != candidate.material_type:
        raise FailClosedError("candidate material type differs from evidence")
    if evidence.subject not in candidate.subject_refs:
        raise FailClosedError("candidate subject binding differs from evidence")
    if evidence.captured_at != candidate.captured_at:
        raise FailClosedError("candidate capture time differs from evidence")

    reasons: set[str] = set()
    contradictions = set(candidate.contradiction_refs)
    unresolved = set(candidate.unresolved_refs)
    unresolved.update(
        f"entity:{entity_id}"
        for entity_id in candidate.entity_refs
        if entity_id not in state.entities
    )
    unresolved.update(
        f"relationship:{relationship_id}"
        for relationship_id in candidate.relationship_refs
        if relationship_id not in state.relationships
    )
    provider_ids: list[str] = []
    assessment_digests: list[str] = []
    dispositions: list[ProviderAdmissionDisposition] = []

    seen_providers: set[str] = set()
    for assessment in assessments:
        if assessment.tenant_id != state.tenant_id:
            raise FailClosedError("provider assessment tenant mismatch")
        if assessment.provider_id not in policy.trusted_provider_ids:
            raise FailClosedError("untrusted provider assessment")
        if assessment.provider_id in seen_providers:
            raise FailClosedError("multiple assessments from one provider")
        if (
            assessment.candidate_id != candidate.candidate_id
            or assessment.candidate_digest != candidate.candidate_digest
        ):
            raise FailClosedError("provider assessment candidate binding mismatch")
        if not assessment.validity.is_active_at(moment):
            raise FailClosedError("provider assessment is not currently valid")
        seen_providers.add(assessment.provider_id)
        provider_ids.append(assessment.provider_id)
        assessment_digests.append(assessment.assessment_digest)
        dispositions.append(assessment.disposition)
        reasons.update(assessment.reason_codes)
        contradictions.update(assessment.contradiction_refs)
        unresolved.update(assessment.unresolved_refs)

    missing = set(policy.required_provider_ids) - seen_providers
    if (
        evidence.integrity_hash is None
        or evidence.integrity_hash != candidate.source_fingerprint
    ):
        reasons.add("SOURCE_INTEGRITY_MISMATCH")
        outcome = AdmissionOutcome.QUARANTINE
    elif ProviderAdmissionDisposition.QUARANTINE in dispositions:
        reasons.add("TRUSTED_PROVIDER_QUARANTINE")
        outcome = AdmissionOutcome.QUARANTINE
    elif (
        "*" not in policy.allowed_material_types
        and candidate.material_type not in policy.allowed_material_types
    ):
        reasons.add("MATERIAL_TYPE_NOT_ALLOWED")
        outcome = AdmissionOutcome.REJECT
    elif ProviderAdmissionDisposition.PRECLUDE in dispositions:
        reasons.add("TRUSTED_PROVIDER_PRECLUDE")
        outcome = AdmissionOutcome.REJECT
    elif evidence.captured_at > moment:
        reasons.add("EVIDENCE_CAPTURED_IN_FUTURE")
        outcome = AdmissionOutcome.HOLD
    elif evidence.validity is not None and not evidence.validity.is_active_at(moment):
        reasons.add("EVIDENCE_NOT_CURRENT")
        outcome = AdmissionOutcome.HOLD
    elif missing:
        reasons.update(f"REQUIRED_PROVIDER_MISSING:{item}" for item in missing)
        outcome = AdmissionOutcome.HOLD
    elif ProviderAdmissionDisposition.REVIEW in dispositions:
        reasons.add("TRUSTED_PROVIDER_REVIEW")
        outcome = AdmissionOutcome.HOLD
    elif contradictions:
        reasons.add("CONTRADICTION_UNRESOLVED")
        outcome = AdmissionOutcome.HOLD
    elif unresolved:
        reasons.add("REFERENCE_UNRESOLVED")
        outcome = AdmissionOutcome.HOLD
    else:
        reasons.add("VALO_POLICY_SATISFIED")
        outcome = AdmissionOutcome.ADMIT

    values = {
        "decision_id": decision_id or f"admission:{candidate.candidate_id}",
        "tenant_id": state.tenant_id,
        "candidate_id": candidate.candidate_id,
        "evidence_id": candidate.evidence_id,
        "candidate_digest": candidate.candidate_digest,
        "policy_id": policy.policy_id,
        "policy_digest": policy.policy_digest,
        "assessment_digests": tuple(assessment_digests),
        "assessed_provider_ids": tuple(provider_ids),
        "outcome": outcome,
        "reason_codes": tuple(reasons),
        "contradiction_refs": tuple(contradictions),
        "unresolved_refs": tuple(unresolved),
        "decided_at": moment,
        "can_enter_operational_state": outcome == AdmissionOutcome.ADMIT,
    }
    provisional = AdmissionDecision(**values)
    return provisional.model_copy(
        update={"decision_digest": provisional.computed_digest}
    )


def create_admission_event(
    state: WorldState,
    candidate: AdmissionCandidate,
    policy: AdmissionPolicy,
    assessments: Iterable[ProviderAdmissionAssessment] = (),
    *,
    event_id: str,
    decision_id: str | None = None,
    actor: str | None = None,
    moment: datetime | None = None,
) -> CanonicalEvent:
    moment = moment or utcnow()
    candidate = _seal_candidate(candidate)
    policy = _seal_policy(policy)
    assessments = tuple(_seal_assessment(item) for item in assessments)
    decision = evaluate_state_admission(
        state,
        candidate,
        policy,
        assessments,
        moment=moment,
        decision_id=decision_id,
    )
    return CanonicalEvent(
        event_id=event_id,
        event_type=EventType.STATE_ADMISSION_DECIDED,
        tenant_id=state.tenant_id,
        subject=candidate.evidence_id,
        actor=actor,
        timestamp=moment,
        effective_at=moment,
        source="valo-kernel:admission",
        payload={
            "candidate": candidate.model_dump(mode="json"),
            "policy": policy.model_dump(mode="json"),
            "assessments": [item.model_dump(mode="json") for item in assessments],
            "decision": decision.model_dump(mode="json"),
        },
        evidence_refs=[candidate.evidence_id],
        idempotency_key=f"state-admission:{decision.decision_id}",
    )
