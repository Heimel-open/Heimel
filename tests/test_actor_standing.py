from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from valo_kernel.actor_standing import evaluate_actor_decision_standing
from valo_kernel.authority_projection import AuthorityStateReference
from valo_kernel.authority_projection_v2 import seal_principal_authority_semantics_v2
from valo_kernel.contracts.actor_standing import (
    ActiveRoleBinding,
    AttentionDisposition,
    AttentionState,
    AuthorityConflictAssessment,
    AuthorityConflictDisposition,
    AuthorityOriginationState,
    CalibratedCompetence,
    CompetenceDisposition,
    DecisionFunction,
    EligibilityDisposition,
    EligibilityState,
    StandingDecision,
)
from valo_kernel.contracts.authority import Authority, Delegation
from valo_kernel.contracts.purpose import Purpose
from valo_kernel.contracts.time import TimeWindow
from valo_kernel.contracts.workspace import ProposedAction


def _fixture(now: datetime):
    action = ProposedAction(
        action_id="change:cyber:42",
        capability="APPROVE_CYBER_CHANGE",
        target="system:payments",
        purpose_id="purpose:secure-change",
        parameters={"change_ref": "chg-42"},
        declared_effects=("CHANGE_PRODUCTION_SECURITY",),
    )
    purpose = Purpose(
        purpose_id="purpose:secure-change",
        purpose_type="cyber_change",
        scope=["system:payments"],
        basis="change-policy:v3",
        permitted_data=["change:42"],
        permitted_actions=["APPROVE_CYBER_CHANGE"],
        validity=TimeWindow(
            valid_from=now - timedelta(hours=1),
            valid_until=now + timedelta(hours=2),
        ),
    )
    authority = Authority(
        authority_id="authority:ceo-office:approve-cyber",
        principal="office:ceo:acme",
        capability="APPROVE_CYBER_CHANGE",
        scope=["system:payments"],
        constraints={"risk_ceiling": "HIGH"},
        basis="board-mandate:2026",
        validity=TimeWindow(
            valid_from=now - timedelta(days=1),
            valid_until=now + timedelta(days=30),
        ),
        delegable=True,
    )
    origination = AuthorityOriginationState(
        origination_id="origination:ceo-office:approve-cyber",
        authority_id=authority.authority_id,
        authority_principal_id="office:ceo:acme",
        represented_principal_id="company:acme",
        grantor_id="board:acme",
        grantor_standing_ref="standing:board:2026",
        evidence_refs=("evidence:board-resolution",),
        evaluated_at=now - timedelta(seconds=5),
        valid_until=now + timedelta(minutes=30),
        max_delegation_depth=1,
        revocation_registry_ref="revocations:acme",
    )
    delegation = Delegation(
        delegation_id="delegation:ceo-office:person",
        delegator="office:ceo:acme",
        delegate="person:ceo",
        authority_ref=authority.authority_id,
        scope_reduction=["system:payments"],
        purpose_restriction=[purpose.purpose_id],
        validity=TimeWindow(
            valid_from=now - timedelta(hours=1),
            valid_until=now + timedelta(hours=1),
        ),
    )
    role = ActiveRoleBinding(
        role_binding_id="role-binding:ceo:acme",
        actor_id="person:ceo",
        role_id="role:ceo",
        principal_id="company:acme",
        decision_functions=(DecisionFunction.APPROVE, DecisionFunction.ACCEPT_RISK),
        capability_scope=("APPROVE_CYBER_CHANGE",),
        resource_scope=("system:payments",),
        jurisdiction_refs=("NO",),
        basis_ref="appointment:ceo",
        evidence_refs=("evidence:appointment",),
        validity=TimeWindow(
            valid_from=now - timedelta(days=30),
            valid_until=now + timedelta(days=30),
        ),
    )
    competence = CalibratedCompetence(
        competence_id="competence:ceo:cyber-approval",
        actor_id="person:ceo",
        role_binding_ref=role.role_binding_id,
        decision_function=DecisionFunction.APPROVE,
        capability="APPROVE_CYBER_CHANGE",
        domain="cybersecurity",
        system_refs=("system:payments",),
        context_refs=("production",),
        risk_ceiling="HIGH",
        credential_refs=("credential:board-training",),
        demonstrated_capability_refs=("assessment:ceo:2026-q3",),
        evidence_refs=("evidence:calibration",),
        calibration_basis="calibration:cyber-approval:v1",
        evaluated_at=now - timedelta(days=7),
        validity=TimeWindow(
            valid_from=now - timedelta(days=7),
            valid_until=now + timedelta(days=30),
        ),
        disposition=CompetenceDisposition.CALIBRATED,
        confidence=0.9,
        revalidation_triggers=("material_system_change", "major_incident"),
    )
    attention = AttentionState(
        attention_id="attention:ceo:42",
        actor_id="person:ceo",
        role_binding_ref=role.role_binding_id,
        observed_at=now - timedelta(seconds=10),
        valid_until=now + timedelta(minutes=5),
        disposition=AttentionDisposition.READY,
        evidence_refs=("evidence:active-review-session",),
    )
    eligibility = EligibilityState(
        eligibility_id="eligibility:ceo:42",
        actor_id="person:ceo",
        role_binding_ref=role.role_binding_id,
        principal_id="company:acme",
        jurisdiction_ref="NO",
        disposition=EligibilityDisposition.ELIGIBLE,
        evaluated_at=now - timedelta(seconds=5),
        valid_until=now + timedelta(minutes=10),
        evidence_refs=("evidence:no-conflict",),
    )
    conflict = AuthorityConflictAssessment(
        assessment_id="authority-conflict:42",
        authority_principal_id="office:ceo:acme",
        capability="APPROVE_CYBER_CHANGE",
        target_ref="system:payments",
        disposition=AuthorityConflictDisposition.CLEAR,
        evaluated_at=now - timedelta(seconds=5),
        valid_until=now + timedelta(minutes=10),
        evidence_refs=("evidence:authority-registry",),
    )
    return (
        action,
        purpose,
        authority,
        origination,
        delegation,
        role,
        competence,
        attention,
        eligibility,
        conflict,
    )


def _standing(now: datetime, **overrides):
    (
        action,
        purpose,
        authority,
        origination,
        delegation,
        role,
        competence,
        attention,
        eligibility,
        conflict,
    ) = _fixture(now)
    values = {
        "actor_id": "person:ceo",
        "decision_function": DecisionFunction.APPROVE,
        "domain": "cybersecurity",
        "jurisdiction_ref": "NO",
        "role": role,
        "competence": competence,
        "eligibility": eligibility,
        "authority": authority,
        "authority_origination": origination,
        "purpose": purpose,
        "action": action,
        "authority_conflict": conflict,
        "evaluated_at": now,
        "attention": attention,
        "require_attention": True,
    }
    values.update(overrides)
    standing = evaluate_actor_decision_standing(**values)
    return standing, (action, purpose, authority, origination, delegation)


def test_right_actor_role_whose_time_attention_and_calibrated_competence_pass():
    now = datetime(2026, 8, 18, 9, 0, tzinfo=UTC)
    standing, _ = _standing(now)
    assert standing.decision is StandingDecision.PASS
    assert standing.reason_codes == ()
    assert standing.principal_id == "company:acme"
    assert standing.authority_principal_id == "office:ceo:acme"
    assert standing.valid_until == now + timedelta(minutes=5)
    assert standing.authority_effect == "NO_AUTHORITY_CREATION"
    assert standing.can_issue_clearance is False


def test_represented_principal_is_not_authority_holder():
    now = datetime(2026, 8, 18, 9, 0, tzinfo=UTC)
    origination = _fixture(now)[3]
    wrong = origination.model_copy(update={"represented_principal_id": "company:other"})
    standing, _ = _standing(now, authority_origination=wrong)
    assert standing.decision is StandingDecision.DENY
    assert "REPRESENTED_PRINCIPAL_MISMATCH" in standing.reason_codes


def test_role_does_not_imply_decision_function_or_competence():
    now = datetime(2026, 8, 18, 9, 0, tzinfo=UTC)
    standing, _ = _standing(now, decision_function=DecisionFunction.ASSESS)
    assert standing.decision is StandingDecision.DENY
    assert "DECISION_FUNCTION_OUTSIDE_ROLE" in standing.reason_codes
    assert "COMPETENCE_FUNCTION_MISMATCH" in standing.reason_codes


def test_formal_credential_does_not_save_expired_calibrated_competence():
    now = datetime(2026, 8, 18, 9, 0, tzinfo=UTC)
    competence = _fixture(now)[6]
    expired = competence.model_copy(
        update={
            "validity": TimeWindow(
                valid_from=now - timedelta(days=30),
                valid_until=now - timedelta(seconds=1),
            )
        }
    )
    standing, _ = _standing(now, competence=expired)
    assert standing.decision is StandingDecision.DENY
    assert "COMPETENCE_STALE" in standing.reason_codes
    assert expired.credential_refs


def test_degraded_attention_requires_step_up_not_silent_human_in_loop():
    now = datetime(2026, 8, 18, 9, 0, tzinfo=UTC)
    attention = _fixture(now)[7]
    degraded = attention.model_copy(update={"disposition": AttentionDisposition.DEGRADED})
    standing, _ = _standing(now, attention=degraded)
    assert standing.decision is StandingDecision.STEP_UP
    assert "ATTENTION_DEGRADED" in standing.reason_codes


def test_unresolved_authority_origination_cannot_pass():
    now = datetime(2026, 8, 18, 9, 0, tzinfo=UTC)
    standing, _ = _standing(now, authority_origination=None)
    assert standing.decision is StandingDecision.STEP_UP
    assert "AUTHORITY_GRANTOR_NOT_ESTABLISHED" in standing.reason_codes
    assert "AUTHORITY_STANDING_NOT_ESTABLISHED" in standing.reason_codes
    assert "AUTHORITY_ORIGINATION_EVIDENCE_MISSING" in standing.reason_codes


def test_authority_semantics_v2_requires_pass_standing_and_bounded_delegation():
    now = datetime(2026, 8, 18, 9, 0, tzinfo=UTC)
    standing, (action, purpose, authority, origination, delegation) = _standing(now)
    state = AuthorityStateReference(
        tenant_id="acme",
        state_root="a" * 64,
        dependency_digest="b" * 64,
        observed_at=now - timedelta(seconds=2),
        valid_until=now + timedelta(minutes=20),
    )
    semantics = seal_principal_authority_semantics_v2(
        executor_id="person:ceo",
        authority=authority,
        authority_origination=origination,
        delegations=(delegation,),
        purpose=purpose,
        proposed_action=action,
        actor_standing=standing,
        authority_state=state,
        evaluated_at=now,
    )
    assert semantics.actor_standing.standing_digest == standing.standing_digest
    assert semantics.actor_standing.principal_id == "company:acme"
    assert semantics.authority.principal == "office:ceo:acme"
    assert semantics.valid_until == standing.valid_until

    no_delegation = origination.model_copy(update={"max_delegation_depth": 0})
    standing_no_delegation, _ = _standing(
        now,
        authority_origination=no_delegation,
    )
    with pytest.raises(ValidationError, match="delegation chain exceeds maximum depth"):
        seal_principal_authority_semantics_v2(
            executor_id="person:ceo",
            authority=authority,
            authority_origination=no_delegation,
            delegations=(delegation,),
            purpose=purpose,
            proposed_action=action,
            actor_standing=standing_no_delegation,
            authority_state=state,
            evaluated_at=now,
        )
