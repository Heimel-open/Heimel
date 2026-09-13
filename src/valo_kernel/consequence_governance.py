from __future__ import annotations

from datetime import datetime

from .contracts.actor_standing import (
    ActiveRoleBinding,
    AttentionDisposition,
    AttentionState,
    CalibratedCompetence,
    CompetenceDisposition,
    DecisionFunction,
    EligibilityDisposition,
    EligibilityState,
    StandingDecision,
)
from .contracts.common import canonical_digest
from .contracts.consequence_governance import (
    ConsequenceProfile,
    DecisionContribution,
    DecisionContributionChain,
    EmergencyActivation,
    EmergencyConditionEvidence,
    EmergencyDecision,
    EmergencyExecutorReadiness,
    EmergencyMandate,
    MinimumSafeResponseAssessment,
    NormalPathAssessment,
    NormalPathAvailability,
    OmissionConsequenceAssessment,
    OmissionSeverity,
)
from .contracts.workspace import ProposedAction


def _digest(value: object) -> str:
    if hasattr(value, "model_dump"):
        return canonical_digest(value.model_dump(mode="json"))
    return canonical_digest(value)


def seal_consequence_profile(profile: ConsequenceProfile) -> ConsequenceProfile:
    return ConsequenceProfile.model_validate(
        {
            **profile.model_dump(mode="python"),
            "profile_digest": profile.computed_digest,
        }
    )


def seal_decision_contribution(
    contribution: DecisionContribution,
) -> DecisionContribution:
    return DecisionContribution.model_validate(
        {
            **contribution.model_dump(mode="python"),
            "contribution_digest": contribution.computed_digest,
        }
    )


def seal_decision_contribution_chain(
    chain: DecisionContributionChain,
) -> DecisionContributionChain:
    return DecisionContributionChain.model_validate(
        {
            **chain.model_dump(mode="python"),
            "chain_digest": chain.computed_digest,
        }
    )


def seal_omission_assessment(
    assessment: OmissionConsequenceAssessment,
) -> OmissionConsequenceAssessment:
    return OmissionConsequenceAssessment.model_validate(
        {
            **assessment.model_dump(mode="python"),
            "assessment_digest": assessment.computed_digest,
        }
    )


def seal_normal_path_assessment(
    assessment: NormalPathAssessment,
) -> NormalPathAssessment:
    return NormalPathAssessment.model_validate(
        {
            **assessment.model_dump(mode="python"),
            "assessment_digest": assessment.computed_digest,
        }
    )


def seal_minimum_safe_response(
    assessment: MinimumSafeResponseAssessment,
) -> MinimumSafeResponseAssessment:
    return MinimumSafeResponseAssessment.model_validate(
        {
            **assessment.model_dump(mode="python"),
            "assessment_digest": assessment.computed_digest,
        }
    )


def seal_emergency_condition(
    condition: EmergencyConditionEvidence,
) -> EmergencyConditionEvidence:
    return EmergencyConditionEvidence.model_validate(
        {
            **condition.model_dump(mode="python"),
            "condition_digest": condition.computed_digest,
        }
    )


def seal_emergency_mandate(mandate: EmergencyMandate) -> EmergencyMandate:
    return EmergencyMandate.model_validate(
        {
            **mandate.model_dump(mode="python"),
            "mandate_digest": mandate.computed_digest,
        }
    )


def evaluate_emergency_executor_readiness(
    *,
    actor_id: str,
    domain: str,
    jurisdiction_ref: str,
    role: ActiveRoleBinding,
    competence: CalibratedCompetence,
    eligibility: EligibilityState,
    action: ProposedAction,
    evaluated_at: datetime,
    attention: AttentionState | None = None,
    require_attention: bool = True,
) -> EmergencyExecutorReadiness:
    """Evaluate actor readiness without importing normal-path authority.

    Emergency authority comes only from a pre-existing EmergencyMandate. This
    readiness check proves role, calibrated competence, attention and
    eligibility; it cannot itself create authority or clearance.
    """

    deny: list[str] = []
    step_up: list[str] = []
    validity_bounds: list[datetime] = []

    if role.actor_id != actor_id:
        deny.append("ROLE_ACTOR_MISMATCH")
    if not role.is_active(evaluated_at):
        deny.append("ROLE_NOT_ACTIVE")
    else:
        validity_bounds.append(role.validity.valid_until)
    if DecisionFunction.EXECUTE not in role.decision_functions:
        deny.append("EXECUTE_FUNCTION_OUTSIDE_ROLE")
    if role.capability_scope and action.capability not in role.capability_scope:
        deny.append("CAPABILITY_OUTSIDE_ROLE")
    if role.resource_scope and action.target not in role.resource_scope:
        deny.append("TARGET_OUTSIDE_ROLE")
    if role.jurisdiction_refs and jurisdiction_ref not in role.jurisdiction_refs:
        deny.append("JURISDICTION_OUTSIDE_ROLE")

    if competence.actor_id != actor_id:
        deny.append("COMPETENCE_ACTOR_MISMATCH")
    if competence.role_binding_ref != role.role_binding_id:
        deny.append("COMPETENCE_ROLE_MISMATCH")
    if competence.decision_function is not DecisionFunction.EXECUTE:
        deny.append("COMPETENCE_FUNCTION_MISMATCH")
    if competence.capability != action.capability:
        deny.append("COMPETENCE_CAPABILITY_MISMATCH")
    if competence.domain != domain:
        deny.append("COMPETENCE_DOMAIN_MISMATCH")
    if not competence.is_current(evaluated_at):
        deny.append("COMPETENCE_STALE")
    else:
        validity_bounds.append(competence.validity.valid_until)
    if competence.disposition is CompetenceDisposition.CALIBRATED:
        pass
    elif competence.disposition in {
        CompetenceDisposition.CONDITIONAL,
        CompetenceDisposition.STEP_UP_REQUIRED,
        CompetenceDisposition.UNKNOWN,
    }:
        step_up.append(f"COMPETENCE_{competence.disposition.value}")
    else:
        deny.append("COMPETENCE_NOT_CALIBRATED")

    if eligibility.actor_id != actor_id:
        deny.append("ELIGIBILITY_ACTOR_MISMATCH")
    if eligibility.role_binding_ref != role.role_binding_id:
        deny.append("ELIGIBILITY_ROLE_MISMATCH")
    if eligibility.principal_id != role.principal_id:
        deny.append("ELIGIBILITY_PRINCIPAL_MISMATCH")
    if eligibility.jurisdiction_ref != jurisdiction_ref:
        deny.append("ELIGIBILITY_JURISDICTION_MISMATCH")
    if not eligibility.is_current(evaluated_at):
        deny.append("ELIGIBILITY_STALE")
    else:
        validity_bounds.append(eligibility.valid_until)
    if eligibility.disposition is EligibilityDisposition.ELIGIBLE:
        pass
    elif eligibility.disposition is EligibilityDisposition.UNKNOWN:
        step_up.append("ELIGIBILITY_UNKNOWN")
    else:
        deny.append(f"ELIGIBILITY_{eligibility.disposition.value}")

    if require_attention:
        if attention is None:
            step_up.append("ATTENTION_MISSING")
        else:
            if attention.actor_id != actor_id:
                deny.append("ATTENTION_ACTOR_MISMATCH")
            if attention.role_binding_ref != role.role_binding_id:
                deny.append("ATTENTION_ROLE_MISMATCH")
            if not attention.is_current(evaluated_at):
                deny.append("ATTENTION_STALE")
            else:
                validity_bounds.append(attention.valid_until)
            if attention.disposition is AttentionDisposition.READY:
                pass
            elif attention.disposition in {
                AttentionDisposition.DEGRADED,
                AttentionDisposition.UNKNOWN,
            }:
                step_up.append(f"ATTENTION_{attention.disposition.value}")
            else:
                deny.append("ATTENTION_UNAVAILABLE")

    if not validity_bounds:
        raise ValueError("emergency readiness has no bounded dependency")

    if deny:
        decision = StandingDecision.DENY
        reasons = tuple(sorted(set(deny)))
    elif step_up:
        decision = StandingDecision.STEP_UP
        reasons = tuple(sorted(set(step_up)))
    else:
        decision = StandingDecision.PASS
        reasons = ()

    action_digest = _digest(action)
    provisional = EmergencyExecutorReadiness(
        readiness_id=canonical_digest(
            {
                "actor_id": actor_id,
                "role_binding_id": role.role_binding_id,
                "action_digest": action_digest,
                "evaluated_at": evaluated_at.isoformat(),
            }
        ),
        actor_id=actor_id,
        role_binding_id=role.role_binding_id,
        represented_principal_id=role.principal_id,
        decision_function=DecisionFunction.EXECUTE,
        capability=action.capability,
        jurisdiction_ref=jurisdiction_ref,
        action_id=action.action_id,
        action_digest=action_digest,
        role_digest=_digest(role),
        competence_digest=_digest(competence),
        attention_digest=_digest(attention) if attention is not None else None,
        eligibility_digest=_digest(eligibility),
        evaluated_at=evaluated_at,
        valid_until=min(validity_bounds),
        decision=decision,
        reason_codes=reasons,
    )
    return EmergencyExecutorReadiness.model_validate(
        {
            **provisional.model_dump(mode="python"),
            "readiness_digest": provisional.computed_digest,
        }
    )


def evaluate_emergency_activation(
    *,
    mandate: EmergencyMandate,
    readiness: EmergencyExecutorReadiness,
    omission_assessment: OmissionConsequenceAssessment,
    normal_path_assessment: NormalPathAssessment,
    minimum_safe_response: MinimumSafeResponseAssessment,
    conditions: tuple[EmergencyConditionEvidence, ...],
    action: ProposedAction,
    evaluated_at: datetime,
) -> EmergencyActivation:
    """Activate only pre-authorized emergency scope under independent evidence.

    A normal-path DENY is never an emergency trigger. The activation cannot
    widen scope, delegate, create clearance, or replace fresh REHT evaluation.
    """

    deny: list[str] = []
    step_up: list[str] = []
    validity_bounds: list[datetime] = []
    action_digest = _digest(action)

    if mandate.mandate_digest != mandate.computed_digest:
        deny.append("EMERGENCY_MANDATE_UNSEALED")
    if not mandate.is_current(evaluated_at):
        deny.append("EMERGENCY_MANDATE_NOT_CURRENT")
    else:
        validity_bounds.append(mandate.validity.valid_until)

    if readiness.readiness_digest != readiness.computed_digest:
        deny.append("EMERGENCY_READINESS_UNSEALED")
    if readiness.decision is not StandingDecision.PASS:
        deny.append("EMERGENCY_EXECUTOR_NOT_READY")
    if not (readiness.evaluated_at <= evaluated_at < readiness.valid_until):
        deny.append("EMERGENCY_READINESS_STALE")
    else:
        validity_bounds.append(readiness.valid_until)
    if readiness.actor_id not in mandate.executor_refs:
        deny.append("EXECUTOR_OUTSIDE_EMERGENCY_MANDATE")
    if readiness.represented_principal_id != mandate.represented_principal_id:
        deny.append("EMERGENCY_PRINCIPAL_MISMATCH")
    if readiness.action_id != action.action_id or readiness.action_digest != action_digest:
        deny.append("EMERGENCY_READINESS_ACTION_MISMATCH")

    if action.capability not in mandate.allowed_capabilities:
        deny.append("EMERGENCY_CAPABILITY_OUTSIDE_MANDATE")
    if action.target not in mandate.target_refs:
        deny.append("EMERGENCY_TARGET_OUTSIDE_MANDATE")
    if action.purpose_id not in mandate.purpose_refs:
        deny.append("EMERGENCY_PURPOSE_OUTSIDE_MANDATE")
    if not set(action.declared_effects).issubset(set(mandate.allowed_effects)):
        deny.append("EMERGENCY_EFFECT_OUTSIDE_MANDATE")

    if omission_assessment.assessment_digest != omission_assessment.computed_digest:
        deny.append("OMISSION_ASSESSMENT_UNSEALED")
    if omission_assessment.action_id != action.action_id:
        deny.append("OMISSION_ACTION_MISMATCH")
    if not omission_assessment.is_current(evaluated_at):
        deny.append("OMISSION_ASSESSMENT_STALE")
    else:
        validity_bounds.append(omission_assessment.valid_until)
    if omission_assessment.severity not in {
        OmissionSeverity.MATERIAL,
        OmissionSeverity.CRITICAL,
    }:
        deny.append("OMISSION_HAZARD_NOT_MATERIAL")
    if omission_assessment.safe_null_effect:
        deny.append("NULL_EFFECT_ALREADY_SAFE")

    if normal_path_assessment.assessment_digest != normal_path_assessment.computed_digest:
        deny.append("NORMAL_PATH_ASSESSMENT_UNSEALED")
    if normal_path_assessment.action_id != action.action_id:
        deny.append("NORMAL_PATH_ACTION_MISMATCH")
    if not normal_path_assessment.is_current(evaluated_at):
        deny.append("NORMAL_PATH_ASSESSMENT_STALE")
    else:
        validity_bounds.append(normal_path_assessment.valid_until)
    if normal_path_assessment.availability is NormalPathAvailability.AVAILABLE:
        deny.append("NORMAL_PATH_AVAILABLE")
    elif normal_path_assessment.availability is NormalPathAvailability.DENIED:
        deny.append("NORMAL_DENIAL_NOT_EMERGENCY_TRIGGER")
    elif normal_path_assessment.availability is NormalPathAvailability.UNKNOWN:
        step_up.append("NORMAL_PATH_AVAILABILITY_UNKNOWN")
    elif normal_path_assessment.availability not in {
        NormalPathAvailability.UNAVAILABLE,
        NormalPathAvailability.INSUFFICIENT_TIME,
    }:
        deny.append("NORMAL_PATH_NOT_EMERGENCY_ELIGIBLE")

    if minimum_safe_response.assessment_digest != minimum_safe_response.computed_digest:
        deny.append("MINIMUM_SAFE_RESPONSE_UNSEALED")
    if minimum_safe_response.action_id != action.action_id:
        deny.append("MINIMUM_SAFE_RESPONSE_ACTION_MISMATCH")
    if minimum_safe_response.action_digest != action_digest:
        deny.append("MINIMUM_SAFE_RESPONSE_DIGEST_MISMATCH")
    if not minimum_safe_response.is_current(evaluated_at):
        deny.append("MINIMUM_SAFE_RESPONSE_STALE")
    else:
        validity_bounds.append(minimum_safe_response.valid_until)
    if not minimum_safe_response.sufficient_to_control_hazard:
        deny.append("EMERGENCY_ACTION_NOT_SUFFICIENT")
    if not minimum_safe_response.no_lower_impact_sufficient_action:
        deny.append("LOWER_IMPACT_SAFE_ACTION_EXISTS")

    by_ref = {item.condition_ref: item for item in conditions}
    for trigger_ref in mandate.trigger_refs:
        condition = by_ref.get(trigger_ref)
        if condition is None:
            step_up.append(f"EMERGENCY_TRIGGER_MISSING:{trigger_ref}")
            continue
        if condition.mandate_id != mandate.mandate_id:
            deny.append(f"EMERGENCY_TRIGGER_MANDATE_MISMATCH:{trigger_ref}")
        if condition.condition_digest != condition.computed_digest:
            deny.append(f"EMERGENCY_TRIGGER_UNSEALED:{trigger_ref}")
        if not condition.is_current(evaluated_at):
            deny.append(f"EMERGENCY_TRIGGER_STALE:{trigger_ref}")
        else:
            validity_bounds.append(condition.valid_until)
        if not condition.satisfied:
            deny.append(f"EMERGENCY_TRIGGER_NOT_SATISFIED:{trigger_ref}")

    if not validity_bounds:
        raise ValueError("emergency activation has no bounded dependency")

    if deny:
        decision = EmergencyDecision.DENY
        reasons = tuple(sorted(set(deny)))
    elif step_up:
        decision = EmergencyDecision.STEP_UP
        reasons = tuple(sorted(set(step_up)))
    else:
        decision = EmergencyDecision.PASS
        reasons = ()

    provisional = EmergencyActivation(
        activation_id=canonical_digest(
            {
                "mandate_digest": mandate.mandate_digest,
                "readiness_digest": readiness.readiness_digest,
                "action_digest": action_digest,
                "evaluated_at": evaluated_at.isoformat(),
            }
        ),
        action_id=action.action_id,
        action_digest=action_digest,
        mandate=mandate,
        readiness=readiness,
        omission_assessment=omission_assessment,
        normal_path_assessment=normal_path_assessment,
        minimum_safe_response=minimum_safe_response,
        conditions=conditions,
        evaluated_at=evaluated_at,
        valid_until=min(validity_bounds),
        decision=decision,
        reason_codes=reasons,
    )
    return EmergencyActivation.model_validate(
        {
            **provisional.model_dump(mode="python"),
            "activation_digest": provisional.computed_digest,
        }
    )
