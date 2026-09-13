from __future__ import annotations

from datetime import datetime

from .contracts.actor_standing import (
    ActiveRoleBinding,
    ActorDecisionStanding,
    ApprovalAttestation,
    ApprovalDisposition,
    ApprovalRequirement,
    AttentionDisposition,
    AttentionState,
    AuthorityConflictAssessment,
    AuthorityConflictDisposition,
    AuthorityOriginationState,
    CalibratedCompetence,
    CompetenceDisposition,
    ConsentDisposition,
    ConsentState,
    DecisionFunction,
    EligibilityDisposition,
    EligibilityState,
    RiskAcceptanceState,
    StandingDecision,
)
from .contracts.authority import Authority
from .contracts.common import canonical_digest
from .contracts.purpose import Purpose
from .contracts.workspace import ProposedAction


def _digest(value: object) -> str:
    if hasattr(value, "model_dump"):
        return canonical_digest(value.model_dump(mode="json"))
    return canonical_digest(value)


def evaluate_actor_decision_standing(
    *,
    actor_id: str,
    decision_function: DecisionFunction,
    domain: str,
    jurisdiction_ref: str,
    role: ActiveRoleBinding,
    competence: CalibratedCompetence,
    eligibility: EligibilityState,
    authority: Authority,
    purpose: Purpose,
    action: ProposedAction,
    authority_conflict: AuthorityConflictAssessment,
    evaluated_at: datetime,
    authority_origination: AuthorityOriginationState | None = None,
    attention: AttentionState | None = None,
    require_attention: bool = False,
    consents: tuple[ConsentState, ...] = (),
    required_consent_subjects: tuple[str, ...] = (),
    approvals: tuple[ApprovalAttestation, ...] = (),
    approval_requirement: ApprovalRequirement | None = None,
    risk_acceptance: RiskAcceptanceState | None = None,
    require_risk_acceptance: bool = False,
) -> ActorDecisionStanding:
    """Resolve whether one actor has standing for one decision function now.

    `role.principal_id` is the represented principal / whose. It is deliberately
    separate from `authority.principal`, which is the holder from which the
    execution authority chain originates.
    """

    deny: list[str] = []
    step_up: list[str] = []
    validity_bounds: list[datetime] = []

    if not actor_id:
        deny.append("ACTOR_ID_MISSING")

    if not role.is_active(evaluated_at):
        deny.append("ROLE_NOT_ACTIVE")
    else:
        validity_bounds.append(role.validity.valid_until)
    if role.actor_id != actor_id:
        deny.append("ROLE_ACTOR_MISMATCH")
    if decision_function not in role.decision_functions:
        deny.append("DECISION_FUNCTION_OUTSIDE_ROLE")
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
    if competence.decision_function is not decision_function:
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

    if not authority.is_active(evaluated_at):
        deny.append("AUTHORITY_NOT_ACTIVE")
    else:
        validity_bounds.append(authority.validity.valid_until)
    if authority.capability != action.capability:
        deny.append("AUTHORITY_CAPABILITY_MISMATCH")
    if authority.scope and action.target not in authority.scope:
        deny.append("AUTHORITY_SCOPE_MISMATCH")

    if authority_origination is None:
        step_up.extend(
            (
                "AUTHORITY_GRANTOR_NOT_ESTABLISHED",
                "AUTHORITY_STANDING_NOT_ESTABLISHED",
                "AUTHORITY_ORIGINATION_EVIDENCE_MISSING",
            )
        )
    else:
        if authority_origination.authority_id != authority.authority_id:
            deny.append("AUTHORITY_ORIGINATION_MISMATCH")
        if authority_origination.authority_principal_id != authority.principal:
            deny.append("AUTHORITY_PRINCIPAL_MISMATCH")
        if authority_origination.represented_principal_id != role.principal_id:
            deny.append("REPRESENTED_PRINCIPAL_MISMATCH")
        if not authority_origination.is_current(evaluated_at):
            deny.append("AUTHORITY_ORIGINATION_STALE")
        else:
            validity_bounds.append(authority_origination.valid_until)

    if not purpose.validity.is_active_at(evaluated_at):
        deny.append("PURPOSE_NOT_ACTIVE")
    else:
        validity_bounds.append(purpose.validity.valid_until)
    if action.purpose_id != purpose.purpose_id:
        deny.append("PURPOSE_MISMATCH")
    if purpose.permitted_actions and action.capability not in purpose.permitted_actions:
        deny.append("ACTION_OUTSIDE_PURPOSE")
    if purpose.scope and action.target not in purpose.scope:
        deny.append("TARGET_OUTSIDE_PURPOSE")

    if not authority_conflict.is_current(evaluated_at):
        deny.append("AUTHORITY_CONFLICT_STATE_STALE")
    else:
        validity_bounds.append(authority_conflict.valid_until)
    if authority_conflict.authority_principal_id != authority.principal:
        deny.append("AUTHORITY_CONFLICT_PRINCIPAL_MISMATCH")
    if authority_conflict.capability != action.capability:
        deny.append("AUTHORITY_CONFLICT_CAPABILITY_MISMATCH")
    if authority_conflict.target_ref != action.target:
        deny.append("AUTHORITY_CONFLICT_TARGET_MISMATCH")
    if authority_conflict.disposition is AuthorityConflictDisposition.UNKNOWN:
        step_up.append("AUTHORITY_CONFLICT_UNKNOWN")
    elif authority_conflict.disposition is AuthorityConflictDisposition.CONFLICTED:
        deny.append("AUTHORITY_CONFLICTED")

    consent_by_subject = {
        item.subject_id: item for item in consents if item.action_id == action.action_id
    }
    for subject_id in required_consent_subjects:
        consent = consent_by_subject.get(subject_id)
        if consent is None:
            step_up.append(f"CONSENT_MISSING:{subject_id}")
            continue
        if consent.purpose_id != purpose.purpose_id:
            deny.append(f"CONSENT_PURPOSE_MISMATCH:{subject_id}")
        if not consent.is_current(evaluated_at):
            deny.append(f"CONSENT_STALE:{subject_id}")
        else:
            validity_bounds.append(consent.valid_until)
        if consent.disposition is ConsentDisposition.SATISFIED:
            pass
        elif consent.disposition is ConsentDisposition.MISSING:
            step_up.append(f"CONSENT_MISSING:{subject_id}")
        else:
            deny.append(f"CONSENT_{consent.disposition.value}:{subject_id}")

    if approval_requirement is not None:
        relevant = [
            item
            for item in approvals
            if item.action_id == action.action_id
            and item.disposition is ApprovalDisposition.APPROVED
            and item.is_current(evaluated_at)
        ]
        if approval_requirement.prohibit_self_approval and any(
            item.approver_id == actor_id for item in relevant
        ):
            deny.append("SELF_APPROVAL_FORBIDDEN")
        if approval_requirement.require_distinct_approvers and len(
            {item.approver_id for item in relevant}
        ) != len(relevant):
            deny.append("APPROVERS_NOT_DISTINCT")
        roles = {item.approver_role_ref for item in relevant}
        missing_roles = set(approval_requirement.required_role_refs) - roles
        if missing_roles:
            step_up.append("REQUIRED_APPROVAL_ROLE_MISSING")
        if len(relevant) < approval_requirement.minimum_approvals:
            step_up.append("APPROVAL_QUORUM_NOT_MET")
        validity_bounds.extend(item.valid_until for item in relevant)
        if any(
            item.action_id == action.action_id
            and item.disposition
            in {ApprovalDisposition.DENIED, ApprovalDisposition.REVOKED}
            for item in approvals
        ):
            deny.append("APPROVAL_DENIED_OR_REVOKED")

    if require_risk_acceptance:
        if risk_acceptance is None:
            step_up.append("RISK_ACCEPTANCE_MISSING")
        else:
            if risk_acceptance.action_id != action.action_id:
                deny.append("RISK_ACCEPTANCE_ACTION_MISMATCH")
            if not risk_acceptance.is_current(evaluated_at):
                deny.append("RISK_ACCEPTANCE_STALE")
            else:
                validity_bounds.append(risk_acceptance.valid_until)
            if not risk_acceptance.accepted:
                deny.append("RISK_NOT_ACCEPTED")

    reason_codes = tuple(sorted(set(deny + step_up)))
    if deny:
        decision = StandingDecision.DENY
    elif step_up:
        decision = StandingDecision.STEP_UP
    else:
        decision = StandingDecision.PASS

    if not validity_bounds:
        raise ValueError("actor standing has no bounded authoritative dependency")

    consent_digests = tuple(sorted(_digest(item) for item in consents))
    approval_digests = tuple(sorted(_digest(item) for item in approvals))
    action_digest = _digest(action)
    authority_origination_digest = (
        _digest(authority_origination)
        if authority_origination is not None
        else canonical_digest({"authority_origination": "NOT_ESTABLISHED"})
    )

    provisional = ActorDecisionStanding(
        standing_id=canonical_digest(
            {
                "actor_id": actor_id,
                "role_binding_id": role.role_binding_id,
                "principal_id": role.principal_id,
                "authority_principal_id": authority.principal,
                "decision_function": decision_function.value,
                "action_digest": action_digest,
                "evaluated_at": evaluated_at.isoformat(),
            }
        ),
        actor_id=actor_id,
        role_binding_id=role.role_binding_id,
        principal_id=role.principal_id,
        authority_principal_id=authority.principal,
        decision_function=decision_function,
        capability=action.capability,
        jurisdiction_ref=jurisdiction_ref,
        action_id=action.action_id,
        action_digest=action_digest,
        authority_id=authority.authority_id,
        purpose_id=purpose.purpose_id,
        role_digest=_digest(role),
        competence_digest=_digest(competence),
        attention_digest=_digest(attention) if attention is not None else None,
        eligibility_digest=_digest(eligibility),
        consent_digests=consent_digests,
        approval_digests=approval_digests,
        risk_acceptance_digest=(
            _digest(risk_acceptance) if risk_acceptance is not None else None
        ),
        authority_origination_digest=authority_origination_digest,
        authority_conflict_digest=_digest(authority_conflict),
        evaluated_at=evaluated_at,
        valid_until=min(validity_bounds),
        decision=decision,
        reason_codes=reason_codes,
    )
    return ActorDecisionStanding.model_validate(
        {
            **provisional.model_dump(mode="python"),
            "standing_digest": provisional.computed_digest,
        }
    )
