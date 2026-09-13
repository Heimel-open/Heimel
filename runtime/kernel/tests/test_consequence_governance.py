from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from valo_kernel.consequence_governance import (
    evaluate_emergency_activation,
    evaluate_emergency_executor_readiness,
    seal_consequence_profile,
    seal_decision_contribution,
    seal_decision_contribution_chain,
    seal_emergency_condition,
    seal_emergency_mandate,
    seal_minimum_safe_response,
    seal_normal_path_assessment,
    seal_omission_assessment,
)
from valo_kernel.contracts.actor_standing import (
    ActiveRoleBinding,
    ActorDecisionStanding,
    AttentionDisposition,
    AttentionState,
    CalibratedCompetence,
    CompetenceDisposition,
    DecisionFunction,
    EligibilityDisposition,
    EligibilityState,
    StandingDecision,
)
from valo_kernel.contracts.common import canonical_digest
from valo_kernel.contracts.consequence_governance import (
    ConsequencePartyBinding,
    ConsequenceProfile,
    ConsequenceRelation,
    DecisionContribution,
    DecisionContributionChain,
    DecisionContributionRequirement,
    DecisionContributionType,
    EmergencyConditionEvidence,
    EmergencyDecision,
    EmergencyMandate,
    MinimumSafeResponseAssessment,
    NormalPathAssessment,
    NormalPathAvailability,
    OmissionConsequenceAssessment,
    OmissionSeverity,
    Reversibility,
)
from valo_kernel.contracts.time import TimeWindow
from valo_kernel.contracts.workspace import ProposedAction


def _sealed_standing(
    now: datetime,
    *,
    actor_id: str,
    function: DecisionFunction,
    action_id: str,
    capability: str,
) -> ActorDecisionStanding:
    provisional = ActorDecisionStanding(
        standing_id=f"standing:{actor_id}:{function.value}",
        actor_id=actor_id,
        role_binding_id=f"role-binding:{actor_id}",
        principal_id="company:acme",
        authority_principal_id=f"office:{actor_id}",
        decision_function=function,
        capability=capability,
        jurisdiction_ref="NO",
        action_id=action_id,
        action_digest="a" * 64,
        authority_id=f"authority:{actor_id}:{function.value}",
        purpose_id="purpose:incident",
        role_digest="b" * 64,
        competence_digest="c" * 64,
        attention_digest="d" * 64,
        eligibility_digest="e" * 64,
        authority_origination_digest="f" * 64,
        authority_conflict_digest="1" * 64,
        evaluated_at=now - timedelta(seconds=5),
        valid_until=now + timedelta(minutes=10),
        decision=StandingDecision.PASS,
        reason_codes=(),
    )
    return ActorDecisionStanding.model_validate(
        {
            **provisional.model_dump(mode="python"),
            "standing_digest": provisional.computed_digest,
        }
    )


def test_every_decision_contribution_requires_its_own_pass_standing():
    now = datetime(2026, 8, 18, 10, 0, tzinfo=UTC)
    approval_standing = _sealed_standing(
        now,
        actor_id="person:ciso",
        function=DecisionFunction.APPROVE,
        action_id="action:1",
        capability="ISOLATE_NETWORK",
    )
    contribution = seal_decision_contribution(
        DecisionContribution(
            contribution_id="contribution:approval:ciso",
            contribution_type=DecisionContributionType.APPROVAL,
            contribution_ref="approval:42",
            action_id="action:1",
            actor_id="person:ciso",
            actor_standing=approval_standing,
            issued_at=now,
            valid_until=now + timedelta(minutes=5),
        )
    )
    executor = _sealed_standing(
        now,
        actor_id="agent:soc",
        function=DecisionFunction.EXECUTE,
        action_id="action:1",
        capability="ISOLATE_NETWORK",
    )
    chain = seal_decision_contribution_chain(
        DecisionContributionChain(
            chain_id="chain:1",
            action_id="action:1",
            executor_standing=executor,
            contributions=(contribution,),
            requirements=(
                DecisionContributionRequirement(
                    contribution_type=DecisionContributionType.APPROVAL,
                    minimum_count=1,
                    prohibit_executor_as_contributor=True,
                ),
            ),
            evaluated_at=now,
            valid_until=now + timedelta(minutes=5),
        )
    )
    assert chain.chain_digest == chain.computed_digest

    stepped = approval_standing.model_copy(
        update={
            "decision": StandingDecision.STEP_UP,
            "reason_codes": ("ATTENTION_MISSING",),
            "standing_digest": "",
        }
    )
    stepped = ActorDecisionStanding.model_validate(
        {**stepped.model_dump(mode="python"), "standing_digest": stepped.computed_digest}
    )
    with pytest.raises(ValidationError, match="requires PASS actor standing"):
        DecisionContribution(
            contribution_id="contribution:bad",
            contribution_type=DecisionContributionType.APPROVAL,
            contribution_ref="approval:bad",
            action_id="action:1",
            actor_id="person:ciso",
            actor_standing=stepped,
            issued_at=now,
            valid_until=now + timedelta(minutes=1),
        )


def test_consequence_parties_are_not_collapsed_into_whose():
    now = datetime(2026, 8, 18, 10, 0, tzinfo=UTC)
    bindings = (
        ConsequencePartyBinding(
            binding_id="party:beneficiary",
            action_id="action:1",
            party_id="customer:7",
            relation=ConsequenceRelation.BENEFICIARY,
            basis_ref="contract:7",
            evidence_refs=("evidence:contract",),
            evaluated_at=now,
            valid_until=now + timedelta(minutes=10),
        ),
        ConsequencePartyBinding(
            binding_id="party:affected",
            action_id="action:1",
            party_id="employee:12",
            relation=ConsequenceRelation.AFFECTED_PARTY,
            basis_ref="impact:12",
            evidence_refs=("evidence:impact",),
            evaluated_at=now,
            valid_until=now + timedelta(minutes=10),
        ),
        ConsequencePartyBinding(
            binding_id="party:risk",
            action_id="action:1",
            party_id="company:acme",
            relation=ConsequenceRelation.RISK_BEARER,
            basis_ref="risk-register:1",
            evidence_refs=("evidence:risk",),
            evaluated_at=now,
            valid_until=now + timedelta(minutes=10),
        ),
    )
    profile = seal_consequence_profile(
        ConsequenceProfile(
            profile_id="consequence:action:1",
            action_id="action:1",
            bindings=bindings,
            evaluated_at=now,
            valid_until=now + timedelta(minutes=10),
        )
    )
    assert {item.party_id for item in profile.bindings} == {
        "customer:7",
        "employee:12",
        "company:acme",
    }


def test_material_omission_cannot_be_called_safe_null_effect():
    now = datetime(2026, 8, 18, 10, 0, tzinfo=UTC)
    with pytest.raises(ValidationError, match="cannot classify null effect as safe"):
        OmissionConsequenceAssessment(
            assessment_id="omission:1",
            action_id="action:1",
            severity=OmissionSeverity.CRITICAL,
            consequence_refs=("hazard:ransomware-spread",),
            safe_null_effect=True,
            evidence_refs=("evidence:hazard",),
            evaluated_at=now,
            valid_until=now + timedelta(minutes=2),
        )


def _emergency_fixture(now: datetime):
    action = ProposedAction(
        action_id="emergency:isolate:1",
        capability="ISOLATE_NETWORK",
        target="network:production",
        purpose_id="purpose:incident",
        parameters={"segment": "payments"},
        declared_effects=("NETWORK_ISOLATION",),
    )
    role = ActiveRoleBinding(
        role_binding_id="role-binding:soc-agent",
        actor_id="agent:soc",
        role_id="role:emergency-network-operator",
        principal_id="company:acme",
        decision_functions=(DecisionFunction.EXECUTE,),
        capability_scope=("ISOLATE_NETWORK",),
        resource_scope=("network:production",),
        jurisdiction_refs=("NO",),
        basis_ref="assignment:soc-agent",
        evidence_refs=("evidence:assignment",),
        validity=TimeWindow(
            valid_from=now - timedelta(days=1),
            valid_until=now + timedelta(days=1),
        ),
    )
    competence = CalibratedCompetence(
        competence_id="competence:soc-agent:isolation",
        actor_id="agent:soc",
        role_binding_ref=role.role_binding_id,
        decision_function=DecisionFunction.EXECUTE,
        capability="ISOLATE_NETWORK",
        domain="cybersecurity",
        system_refs=("network:production",),
        context_refs=("ransomware",),
        evidence_refs=("evidence:calibration",),
        calibration_basis="calibration:soc:v1",
        evaluated_at=now - timedelta(hours=1),
        validity=TimeWindow(
            valid_from=now - timedelta(hours=1),
            valid_until=now + timedelta(hours=8),
        ),
        disposition=CompetenceDisposition.CALIBRATED,
        confidence=0.97,
    )
    attention = AttentionState(
        attention_id="attention:soc-agent",
        actor_id="agent:soc",
        role_binding_ref=role.role_binding_id,
        observed_at=now - timedelta(seconds=5),
        valid_until=now + timedelta(minutes=2),
        disposition=AttentionDisposition.READY,
        evidence_refs=("evidence:runtime-readiness",),
    )
    eligibility = EligibilityState(
        eligibility_id="eligibility:soc-agent",
        actor_id="agent:soc",
        role_binding_ref=role.role_binding_id,
        principal_id="company:acme",
        jurisdiction_ref="NO",
        disposition=EligibilityDisposition.ELIGIBLE,
        evaluated_at=now - timedelta(seconds=5),
        valid_until=now + timedelta(minutes=5),
        evidence_refs=("evidence:eligibility",),
    )
    readiness = evaluate_emergency_executor_readiness(
        actor_id="agent:soc",
        domain="cybersecurity",
        jurisdiction_ref="NO",
        role=role,
        competence=competence,
        eligibility=eligibility,
        action=action,
        evaluated_at=now,
        attention=attention,
    )
    mandate = seal_emergency_mandate(
        EmergencyMandate(
            mandate_id="emergency-mandate:network-isolation",
            represented_principal_id="company:acme",
            grantor_id="person:ciso",
            grantor_standing_ref="standing:ciso:authorize-emergency",
            grantor_standing_digest="2" * 64,
            executor_refs=("agent:soc",),
            allowed_capabilities=("ISOLATE_NETWORK",),
            target_refs=("network:production",),
            allowed_effects=("NETWORK_ISOLATION",),
            purpose_refs=("purpose:incident",),
            trigger_refs=("trigger:ransomware", "trigger:human-unavailable"),
            max_risk_class="CRITICAL",
            evidence_refs=("evidence:board-emergency-policy",),
            validity=TimeWindow(
                valid_from=now - timedelta(days=30),
                valid_until=now + timedelta(days=30),
            ),
            revocation_registry_ref="revocations:emergency",
        )
    )
    omission = seal_omission_assessment(
        OmissionConsequenceAssessment(
            assessment_id="omission:ransomware",
            action_id=action.action_id,
            severity=OmissionSeverity.CRITICAL,
            consequence_refs=("hazard:lateral-spread",),
            affected_party_refs=("customer:payments",),
            trigger_deadline=now + timedelta(seconds=30),
            safe_null_effect=False,
            evidence_refs=("evidence:ransomware-detection",),
            evaluated_at=now - timedelta(seconds=2),
            valid_until=now + timedelta(minutes=1),
        )
    )
    normal = seal_normal_path_assessment(
        NormalPathAssessment(
            assessment_id="normal-path:1",
            action_id=action.action_id,
            availability=NormalPathAvailability.INSUFFICIENT_TIME,
            reason_refs=("deadline:30s",),
            evidence_refs=("evidence:oncall-latency",),
            evaluated_at=now - timedelta(seconds=2),
            valid_until=now + timedelta(seconds=30),
        )
    )
    safe = seal_minimum_safe_response(
        MinimumSafeResponseAssessment(
            assessment_id="minimum-safe:1",
            action_id=action.action_id,
            action_digest=canonical_digest(action.model_dump(mode="json")),
            candidate_set_digest="3" * 64,
            reversibility=Reversibility.REVERSIBLE,
            sufficient_to_control_hazard=True,
            no_lower_impact_sufficient_action=True,
            evidence_refs=("evidence:response-policy",),
            evaluated_at=now - timedelta(seconds=2),
            valid_until=now + timedelta(seconds=30),
        )
    )
    conditions = tuple(
        seal_emergency_condition(
            EmergencyConditionEvidence(
                condition_id=f"condition:{index}",
                mandate_id=mandate.mandate_id,
                condition_ref=trigger_ref,
                satisfied=True,
                observed_at=now - timedelta(seconds=2),
                valid_until=now + timedelta(seconds=20),
                evidence_refs=(f"evidence:{index}",),
            )
        )
        for index, trigger_ref in enumerate(mandate.trigger_refs, start=1)
    )
    return action, readiness, mandate, omission, normal, safe, conditions


def test_emergency_activation_is_pre_authorized_narrow_and_still_requires_reht():
    now = datetime(2026, 8, 18, 10, 0, tzinfo=UTC)
    action, readiness, mandate, omission, normal, safe, conditions = _emergency_fixture(now)
    activation = evaluate_emergency_activation(
        mandate=mandate,
        readiness=readiness,
        omission_assessment=omission,
        normal_path_assessment=normal,
        minimum_safe_response=safe,
        conditions=conditions,
        action=action,
        evaluated_at=now,
    )
    assert activation.decision is EmergencyDecision.PASS
    assert activation.scope_effect == "ACTIVATE_PREAUTHORIZED_SCOPE_ONLY"
    assert activation.authority_effect == "NO_AUTHORITY_CREATION"
    assert activation.can_issue_clearance is False
    assert activation.requires_fresh_reht is True
    assert activation.single_use_required is True
    assert activation.valid_until == now + timedelta(seconds=20)


def test_normal_denial_is_never_an_emergency_trigger():
    now = datetime(2026, 8, 18, 10, 0, tzinfo=UTC)
    action, readiness, mandate, omission, normal, safe, conditions = _emergency_fixture(now)
    denied = seal_normal_path_assessment(
        normal.model_copy(
            update={
                "availability": NormalPathAvailability.DENIED,
                "assessment_digest": "",
            }
        )
    )
    activation = evaluate_emergency_activation(
        mandate=mandate,
        readiness=readiness,
        omission_assessment=omission,
        normal_path_assessment=denied,
        minimum_safe_response=safe,
        conditions=conditions,
        action=action,
        evaluated_at=now,
    )
    assert activation.decision is EmergencyDecision.DENY
    assert "NORMAL_DENIAL_NOT_EMERGENCY_TRIGGER" in activation.reason_codes


def test_emergency_mandate_cannot_be_self_issued_or_wildcarded():
    now = datetime(2026, 8, 18, 10, 0, tzinfo=UTC)
    with pytest.raises(ValidationError, match="cannot issue its own mandate"):
        EmergencyMandate(
            mandate_id="mandate:self",
            represented_principal_id="company:acme",
            grantor_id="agent:soc",
            grantor_standing_ref="standing:bad",
            grantor_standing_digest="4" * 64,
            executor_refs=("agent:soc",),
            allowed_capabilities=("ISOLATE_NETWORK",),
            target_refs=("network:production",),
            allowed_effects=("NETWORK_ISOLATION",),
            purpose_refs=("purpose:incident",),
            trigger_refs=("trigger:ransomware",),
            evidence_refs=("evidence:bad",),
            validity=TimeWindow(
                valid_from=now - timedelta(days=1),
                valid_until=now + timedelta(days=1),
            ),
            revocation_registry_ref="revocations:1",
        )

    with pytest.raises(ValidationError, match="cannot contain wildcard scope"):
        EmergencyMandate(
            mandate_id="mandate:wildcard",
            represented_principal_id="company:acme",
            grantor_id="person:ciso",
            grantor_standing_ref="standing:ciso",
            grantor_standing_digest="5" * 64,
            executor_refs=("agent:soc",),
            allowed_capabilities=("*",),
            target_refs=("network:production",),
            allowed_effects=("NETWORK_ISOLATION",),
            purpose_refs=("purpose:incident",),
            trigger_refs=("trigger:ransomware",),
            evidence_refs=("evidence:policy",),
            validity=TimeWindow(
                valid_from=now - timedelta(days=1),
                valid_until=now + timedelta(days=1),
            ),
            revocation_registry_ref="revocations:1",
        )
