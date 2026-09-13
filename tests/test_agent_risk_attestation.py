from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from valo_kernel.agent_risk_attestation import (
    AgentRiskAttestation,
    AssuranceEvidenceKind,
    AttestationDisposition,
    AttestationStage,
    assess_agent_risk_attestation,
    seal_agent_risk_control_profile,
    seal_assurance_evidence_reference,
)
from valo_kernel.authority_projection import (
    AuthorityStateReference,
    seal_principal_authority_semantics,
)
from valo_kernel.contracts import (
    Authority,
    Delegation,
    ProposedAction,
    Purpose,
    TimeWindow,
    canonical_digest,
)


def _semantics(now: datetime):
    authority = Authority(
        authority_id="authority:procurement",
        principal="cfo",
        capability="CREATE_PURCHASE_ORDER",
        scope=["supplier:42"],
        constraints={"max_amount_eur": "500000"},
        basis="board-resolution:2026-08",
        validity=TimeWindow(
            valid_from=now - timedelta(hours=1),
            valid_until=now + timedelta(hours=2),
        ),
        delegable=True,
    )
    delegation = Delegation(
        delegation_id="delegation:cfo:buyer-agent",
        delegator="cfo",
        delegate="buyer-agent",
        authority_ref=authority.authority_id,
        scope_reduction=["supplier:42"],
        purpose_restriction=["purpose:approved-procurement"],
        validity=TimeWindow(
            valid_from=now - timedelta(minutes=30),
            valid_until=now + timedelta(hours=1),
        ),
    )
    purpose = Purpose(
        purpose_id="purpose:approved-procurement",
        purpose_type="procurement",
        scope=["supplier:42"],
        basis="requisition:1001",
        permitted_data=["requisition:1001"],
        permitted_actions=["CREATE_PURCHASE_ORDER"],
        validity=TimeWindow(
            valid_from=now - timedelta(hours=1),
            valid_until=now + timedelta(hours=3),
        ),
    )
    action = ProposedAction(
        action_id="po:1001",
        capability="CREATE_PURCHASE_ORDER",
        target="supplier:42",
        purpose_id=purpose.purpose_id,
        parameters={"amount": "340000", "currency": "EUR"},
        declared_effects=("CREATE_PURCHASE_ORDER",),
    )
    state = AuthorityStateReference(
        tenant_id="acme",
        state_root="a" * 64,
        dependency_digest="b" * 64,
        observed_at=now - timedelta(seconds=5),
        valid_until=now + timedelta(minutes=30),
    )
    return seal_principal_authority_semantics(
        executor_id="buyer-agent",
        authority=authority,
        delegations=(delegation,),
        purpose=purpose,
        proposed_action=action,
        authority_state=state,
        evaluated_at=now,
    )


def _profile(now: datetime):
    return seal_agent_risk_control_profile(
        profile_id="underwriting:agent-actions:v1",
        insurer_ref="insurer:nordic-a",
        product_ref="product:autonomous-actions",
        effective_from=now - timedelta(days=1),
        valid_until=now + timedelta(days=30),
        max_evidence_age_seconds=600,
    )


def _evidence(now: datetime, semantics, *, include_post: bool = True):
    execution_ref = "execution:po:1001"

    def item(
        kind: AssuranceEvidenceKind,
        suffix: str,
        *,
        decision_outcome: str | None = None,
        assertions: tuple[str, ...] = (),
        effect_ref: str | None = None,
        valid_until: datetime | None = None,
        action_id: str | None = None,
        authority_semantics_digest: str | None = None,
        contradictory: bool = False,
        execution: str | None = None,
    ):
        return seal_assurance_evidence_reference(
            evidence_id=f"evidence:{suffix}",
            kind=kind,
            action_id=action_id or semantics.proposed_action.action_id,
            execution_ref=execution or execution_ref,
            authority_semantics_digest=(
                authority_semantics_digest or semantics.semantics_digest
            ),
            source_ref=f"source:{suffix}",
            evidence_digest=canonical_digest({"kind": kind.value, "suffix": suffix}),
            observed_at=now - timedelta(seconds=10),
            valid_until=valid_until or now + timedelta(minutes=5),
            decision_outcome=decision_outcome,
            effect_ref=effect_ref,
            assertions=assertions,
            contradictory=contradictory,
        )

    values = [
        item(AssuranceEvidenceKind.REHT_AUTHORIZATION, "reht"),
        item(
            AssuranceEvidenceKind.RACS_DECISION,
            "racs",
            decision_outcome="ALLOW",
        ),
        item(
            AssuranceEvidenceKind.EFFECT_PATH_CONFORMANCE,
            "path",
            assertions=(
                "NO_DIRECT_EFFECT_PATH",
                "FRESH_AUTHORITY_AT_COMMIT",
                "GOVERNED_EFFECT_PATH",
                "NULL_EFFECT_ON_DENY",
            ),
        ),
    ]
    if include_post:
        values.extend(
            [
                item(
                    AssuranceEvidenceKind.EFFECT_RECEIPT,
                    "receipt",
                    effect_ref="effect:po:1001",
                ),
                item(
                    AssuranceEvidenceKind.OUTCOME_EVIDENCE,
                    "outcome",
                    effect_ref="effect:po:1001",
                ),
            ]
        )
    return tuple(values)


def test_pre_commit_attests_without_creating_authority_or_coverage():
    now = datetime(2026, 8, 16, 10, 0, tzinfo=UTC)
    semantics = _semantics(now)
    attestation = assess_agent_risk_attestation(
        profile=_profile(now),
        authority_semantics=semantics,
        evidence=_evidence(now, semantics, include_post=False),
        stage=AttestationStage.PRE_COMMIT,
        execution_ref="execution:po:1001",
        evaluated_at=now + timedelta(seconds=1),
    )

    assert attestation.disposition is AttestationDisposition.ATTESTED
    assert attestation.authority_effect == "NO_AUTHORITY_CREATION"
    assert attestation.can_issue_clearance is False
    assert attestation.can_determine_coverage is False
    assert attestation.authority_semantics_digest == semantics.semantics_digest


def test_post_effect_attests_only_when_receipt_and_outcome_correlate():
    now = datetime(2026, 8, 16, 10, 0, tzinfo=UTC)
    semantics = _semantics(now)
    attestation = assess_agent_risk_attestation(
        profile=_profile(now),
        authority_semantics=semantics,
        evidence=_evidence(now, semantics),
        stage=AttestationStage.POST_EFFECT,
        execution_ref="execution:po:1001",
        evaluated_at=now + timedelta(seconds=1),
    )
    assert attestation.disposition is AttestationDisposition.ATTESTED


def test_missing_required_evidence_fails_closed():
    now = datetime(2026, 8, 16, 10, 0, tzinfo=UTC)
    semantics = _semantics(now)
    evidence = tuple(
        item
        for item in _evidence(now, semantics, include_post=False)
        if item.kind is not AssuranceEvidenceKind.EFFECT_PATH_CONFORMANCE
    )
    attestation = assess_agent_risk_attestation(
        profile=_profile(now),
        authority_semantics=semantics,
        evidence=evidence,
        stage=AttestationStage.PRE_COMMIT,
        execution_ref="execution:po:1001",
        evaluated_at=now + timedelta(seconds=1),
    )
    assert attestation.disposition is AttestationDisposition.NOT_ATTESTED
    assert "MISSING_REQUIRED_EVIDENCE:EFFECT_PATH_CONFORMANCE" in (
        attestation.failure_reasons
    )
    assert attestation.valid_until is None


def test_deny_outcome_is_not_attested():
    now = datetime(2026, 8, 16, 10, 0, tzinfo=UTC)
    semantics = _semantics(now)
    evidence = list(_evidence(now, semantics, include_post=False))
    racs = evidence[1]
    evidence[1] = seal_assurance_evidence_reference(
        evidence_id=racs.evidence_id,
        kind=racs.kind,
        action_id=racs.action_id,
        execution_ref=racs.execution_ref,
        authority_semantics_digest=racs.authority_semantics_digest,
        source_ref=racs.source_ref,
        evidence_digest=racs.evidence_digest,
        observed_at=racs.observed_at,
        valid_until=racs.valid_until,
        decision_outcome="DENY",
    )
    attestation = assess_agent_risk_attestation(
        profile=_profile(now),
        authority_semantics=semantics,
        evidence=tuple(evidence),
        stage=AttestationStage.PRE_COMMIT,
        execution_ref="execution:po:1001",
        evaluated_at=now + timedelta(seconds=1),
    )
    assert attestation.disposition is AttestationDisposition.NOT_ATTESTED
    assert "RACS_OUTCOME_NOT_ACCEPTED:DENY" in attestation.failure_reasons


def test_missing_no_direct_effect_path_assertion_fails_closed():
    now = datetime(2026, 8, 16, 10, 0, tzinfo=UTC)
    semantics = _semantics(now)
    evidence = list(_evidence(now, semantics, include_post=False))
    path = evidence[2]
    evidence[2] = seal_assurance_evidence_reference(
        evidence_id=path.evidence_id,
        kind=path.kind,
        action_id=path.action_id,
        execution_ref=path.execution_ref,
        authority_semantics_digest=path.authority_semantics_digest,
        source_ref=path.source_ref,
        evidence_digest=path.evidence_digest,
        observed_at=path.observed_at,
        valid_until=path.valid_until,
        assertions=(
            "FRESH_AUTHORITY_AT_COMMIT",
            "GOVERNED_EFFECT_PATH",
            "NULL_EFFECT_ON_DENY",
        ),
    )
    attestation = assess_agent_risk_attestation(
        profile=_profile(now),
        authority_semantics=semantics,
        evidence=tuple(evidence),
        stage=AttestationStage.PRE_COMMIT,
        execution_ref="execution:po:1001",
        evaluated_at=now + timedelta(seconds=1),
    )
    assert "MISSING_PATH_ASSERTION:NO_DIRECT_EFFECT_PATH" in (
        attestation.failure_reasons
    )


def test_stale_evidence_fails_closed_even_when_authority_semantics_are_fresh():
    now = datetime(2026, 8, 16, 10, 0, tzinfo=UTC)
    semantics = _semantics(now)
    evidence = list(_evidence(now, semantics, include_post=False))
    reht = evidence[0]
    evidence[0] = seal_assurance_evidence_reference(
        evidence_id=reht.evidence_id,
        kind=reht.kind,
        action_id=reht.action_id,
        execution_ref=reht.execution_ref,
        authority_semantics_digest=reht.authority_semantics_digest,
        source_ref=reht.source_ref,
        evidence_digest=reht.evidence_digest,
        observed_at=now - timedelta(minutes=2),
        valid_until=now - timedelta(seconds=1),
    )
    attestation = assess_agent_risk_attestation(
        profile=_profile(now),
        authority_semantics=semantics,
        evidence=tuple(evidence),
        stage=AttestationStage.PRE_COMMIT,
        execution_ref="execution:po:1001",
        evaluated_at=now + timedelta(seconds=1),
    )
    assert f"EVIDENCE_NOT_FRESH:{reht.evidence_id}" in attestation.failure_reasons


def test_authority_action_and_execution_bindings_cannot_drift():
    now = datetime(2026, 8, 16, 10, 0, tzinfo=UTC)
    semantics = _semantics(now)
    evidence = list(_evidence(now, semantics, include_post=False))
    reht = evidence[0]
    evidence[0] = seal_assurance_evidence_reference(
        evidence_id=reht.evidence_id,
        kind=reht.kind,
        action_id="po:9999",
        execution_ref="execution:other",
        authority_semantics_digest="0" * 64,
        source_ref=reht.source_ref,
        evidence_digest=reht.evidence_digest,
        observed_at=reht.observed_at,
        valid_until=reht.valid_until,
    )
    attestation = assess_agent_risk_attestation(
        profile=_profile(now),
        authority_semantics=semantics,
        evidence=tuple(evidence),
        stage=AttestationStage.PRE_COMMIT,
        execution_ref="execution:po:1001",
        evaluated_at=now + timedelta(seconds=1),
    )
    assert f"ACTION_MISMATCH:{reht.evidence_id}" in attestation.failure_reasons
    assert f"EXECUTION_MISMATCH:{reht.evidence_id}" in attestation.failure_reasons
    assert f"AUTHORITY_BINDING_MISMATCH:{reht.evidence_id}" in (
        attestation.failure_reasons
    )


def test_post_effect_receipt_and_outcome_must_bind_same_effect():
    now = datetime(2026, 8, 16, 10, 0, tzinfo=UTC)
    semantics = _semantics(now)
    evidence = list(_evidence(now, semantics))
    outcome = evidence[-1]
    evidence[-1] = seal_assurance_evidence_reference(
        evidence_id=outcome.evidence_id,
        kind=outcome.kind,
        action_id=outcome.action_id,
        execution_ref=outcome.execution_ref,
        authority_semantics_digest=outcome.authority_semantics_digest,
        source_ref=outcome.source_ref,
        evidence_digest=outcome.evidence_digest,
        observed_at=outcome.observed_at,
        valid_until=outcome.valid_until,
        effect_ref="effect:other",
    )
    attestation = assess_agent_risk_attestation(
        profile=_profile(now),
        authority_semantics=semantics,
        evidence=tuple(evidence),
        stage=AttestationStage.POST_EFFECT,
        execution_ref="execution:po:1001",
        evaluated_at=now + timedelta(seconds=1),
    )
    assert "EFFECT_CORRELATION_MISMATCH" in attestation.failure_reasons


def test_tampered_evidence_reference_fails_closed():
    now = datetime(2026, 8, 16, 10, 0, tzinfo=UTC)
    semantics = _semantics(now)
    evidence = list(_evidence(now, semantics, include_post=False))
    evidence[0] = evidence[0].model_copy(update={"reference_digest": "0" * 64})
    attestation = assess_agent_risk_attestation(
        profile=_profile(now),
        authority_semantics=semantics,
        evidence=tuple(evidence),
        stage=AttestationStage.PRE_COMMIT,
        execution_ref="execution:po:1001",
        evaluated_at=now + timedelta(seconds=1),
    )
    assert "EVIDENCE_REFERENCE_TAMPERED:evidence:reht" in (
        attestation.failure_reasons
    )


def test_attestation_tampering_is_rejected():
    now = datetime(2026, 8, 16, 10, 0, tzinfo=UTC)
    semantics = _semantics(now)
    attestation = assess_agent_risk_attestation(
        profile=_profile(now),
        authority_semantics=semantics,
        evidence=_evidence(now, semantics, include_post=False),
        stage=AttestationStage.PRE_COMMIT,
        execution_ref="execution:po:1001",
        evaluated_at=now + timedelta(seconds=1),
    )
    with pytest.raises(ValidationError, match="attestation digest mismatch"):
        AgentRiskAttestation.model_validate(
            {
                **attestation.model_dump(mode="python"),
                "attestation_digest": "0" * 64,
            }
        )


def test_attestation_validity_is_bounded_by_shortest_dependency():
    now = datetime(2026, 8, 16, 10, 0, tzinfo=UTC)
    semantics = _semantics(now)
    evidence = _evidence(now, semantics, include_post=False)
    attestation = assess_agent_risk_attestation(
        profile=_profile(now),
        authority_semantics=semantics,
        evidence=evidence,
        stage=AttestationStage.PRE_COMMIT,
        execution_ref="execution:po:1001",
        evaluated_at=now + timedelta(seconds=1),
    )
    expected = min(
        semantics.valid_until,
        _profile(now).valid_until,
        *(item.valid_until for item in evidence),
        *(item.observed_at + timedelta(seconds=600) for item in evidence),
    )
    assert attestation.valid_until == expected
