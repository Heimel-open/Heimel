from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import CommitActionType, ProcurementActionCase


PROFILE_VERSION = "0.1.0"


class ProcurementProfileId(str, Enum):
    CRITERIA_WEIGHTING = "criteria_weighting"
    ALGORITHMIC_SHORTLIST = "algorithmic_shortlist"
    EXCLUSION_REINSTATEMENT = "exclusion_reinstatement"
    AWARD = "award"
    CONTRACT_SIGNATURE = "contract_signature"
    CONTRACT_MODIFICATION = "contract_modification"
    SUPPLIER_CHANGE = "supplier_change"
    PAYMENT = "payment"
    TERMINATION_RENEWAL = "termination_renewal"
    EMERGENCY_PROCEDURE = "emergency_procedure"
    LIFECYCLE_PUBLICATION = "lifecycle_publication"


class AssessmentDisposition(str, Enum):
    READY_FOR_REHT = "ready_for_reht"
    GATHER_EVIDENCE = "gather_evidence"
    STEP_UP_RECOMMENDED = "step_up_recommended"
    FAIL_CLOSED = "fail_closed"


class EvidenceRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(min_length=1)
    accepted_evidence_types: tuple[str, ...]
    mandatory: bool = True

    @model_validator(mode="after")
    def require_types(self) -> "EvidenceRequirement":
        if not self.accepted_evidence_types:
            raise ValueError("accepted_evidence_types cannot be empty")
        return self


class MaterialChangeTrigger(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(min_length=1)
    changed_fields: tuple[str, ...]

    @model_validator(mode="after")
    def require_fields(self) -> "MaterialChangeTrigger":
        if not self.changed_fields:
            raise ValueError("changed_fields cannot be empty")
        return self


class ProcurementClearanceProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    profile_id: ProcurementProfileId
    profile_version: str = PROFILE_VERSION
    allowed_commit_types: tuple[CommitActionType, ...] = ()
    required_context: tuple[str, ...]
    evidence_requirements: tuple[EvidenceRequirement, ...] = ()
    material_change_triggers: tuple[MaterialChangeTrigger, ...] = ()
    reht_clearance_required: bool = True
    grants_authority: bool = False

    @model_validator(mode="after")
    def preserve_boundary(self) -> "ProcurementClearanceProfile":
        if not self.reht_clearance_required:
            raise ValueError("procurement consequence profiles must require REHT clearance")
        if self.grants_authority:
            raise ValueError("clearance profile cannot grant authority")
        return self


class ProcurementClearanceAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    profile_id: ProcurementProfileId
    profile_version: str
    case_id: str = Field(min_length=1)
    disposition: AssessmentDisposition
    missing_context: tuple[str, ...] = ()
    missing_evidence: tuple[str, ...] = ()
    stale_evidence: tuple[str, ...] = ()
    triggered_changes: tuple[str, ...] = ()
    commit_type_valid: bool
    reht_clearance_required: bool = True
    grants_authority: bool = False

    @model_validator(mode="after")
    def assessment_is_evidence_only(self) -> "ProcurementClearanceAssessment":
        if not self.reht_clearance_required:
            raise ValueError("assessment cannot bypass REHT")
        if self.grants_authority:
            raise ValueError("assessment cannot grant authority")
        return self


def _requirement(code: str, *accepted_types: str) -> EvidenceRequirement:
    return EvidenceRequirement(code=code, accepted_evidence_types=tuple(accepted_types))


def _trigger(code: str, *fields: str) -> MaterialChangeTrigger:
    return MaterialChangeTrigger(code=code, changed_fields=tuple(fields))


def default_clearance_profiles() -> Mapping[ProcurementProfileId, ProcurementClearanceProfile]:
    common_context = (
        "principal_id",
        "mandate_ref",
        "authority",
        "policy_version",
        "current_state_digest",
        "requested_commit",
        "consequence",
    )
    profiles = (
        ProcurementClearanceProfile(
            profile_id=ProcurementProfileId.CRITERIA_WEIGHTING,
            allowed_commit_types=(CommitActionType.APPROVE_CRITERIA,),
            required_context=common_context + ("criteria_versions",),
            evidence_requirements=(
                _requirement("approved_need", "needs_plan", "business_need"),
                _requirement("criteria_basis", "evaluation_criteria", "quality_weighting"),
            ),
            material_change_triggers=(
                _trigger("criteria_or_policy_changed", "criteria_versions", "policy_version"),
            ),
        ),
        ProcurementClearanceProfile(
            profile_id=ProcurementProfileId.ALGORITHMIC_SHORTLIST,
            allowed_commit_types=(CommitActionType.ACCEPT_SHORTLIST,),
            required_context=common_context + ("operator_ref",),
            evidence_requirements=(
                _requirement("eligibility", "eligibility_attestation", "digital_business_credential"),
                _requirement("selection_trace", "algorithmic_selection_trace", "shortlist_evaluation"),
            ),
            material_change_triggers=(
                _trigger("eligibility_changed", "eligibility", "exclusion_status"),
                _trigger("algorithm_changed", "algorithm_version", "selection_inputs"),
            ),
        ),
        ProcurementClearanceProfile(
            profile_id=ProcurementProfileId.EXCLUSION_REINSTATEMENT,
            allowed_commit_types=(
                CommitActionType.EXCLUDE_OPERATOR,
                CommitActionType.REINSTATE_OPERATOR,
            ),
            required_context=common_context + ("operator_ref",),
            evidence_requirements=(
                _requirement("exclusion_basis", "exclusion_evidence", "eligibility_attestation"),
            ),
            material_change_triggers=(
                _trigger("operator_status_changed", "eligibility", "exclusion_status", "operator_identity"),
            ),
        ),
        ProcurementClearanceProfile(
            profile_id=ProcurementProfileId.AWARD,
            allowed_commit_types=(CommitActionType.COMMIT_AWARD,),
            required_context=common_context + ("operator_ref", "criteria_versions"),
            evidence_requirements=(
                _requirement("evaluation", "tender_evaluation", "evaluation_report"),
                _requirement("eligibility", "eligibility_attestation", "digital_business_credential"),
                _requirement("authority_evidence", "delegation_attestation", "authority_attestation"),
            ),
            material_change_triggers=(
                _trigger("evaluation_changed", "evaluation", "criteria_versions", "policy_version"),
                _trigger("operator_changed", "eligibility", "ownership_control", "operator_identity"),
                _trigger("budget_changed", "budget_state", "funding_state"),
            ),
        ),
        ProcurementClearanceProfile(
            profile_id=ProcurementProfileId.CONTRACT_SIGNATURE,
            allowed_commit_types=(CommitActionType.SIGN_CONTRACT,),
            required_context=common_context + ("operator_ref", "contract_ref"),
            evidence_requirements=(
                _requirement("award_clearance", "award_clearance_receipt"),
                _requirement("contract_terms", "contract_terms"),
                _requirement("authority_evidence", "delegation_attestation", "authority_attestation"),
            ),
            material_change_triggers=(
                _trigger("terms_changed", "contract_terms", "contract_value", "contract_term"),
                _trigger("supplier_changed", "operator_identity", "ownership_control"),
            ),
        ),
        ProcurementClearanceProfile(
            profile_id=ProcurementProfileId.CONTRACT_MODIFICATION,
            allowed_commit_types=(CommitActionType.MODIFY_CONTRACT,),
            required_context=common_context + ("contract_ref",),
            evidence_requirements=(
                _requirement("modification_basis", "contract_modification_basis"),
                _requirement("current_contract", "contract_state"),
                _requirement("authority_evidence", "delegation_attestation", "authority_attestation"),
            ),
            material_change_triggers=(
                _trigger("modification_changed", "modification_scope", "contract_value", "contract_term"),
                _trigger("performance_changed", "performance_state"),
            ),
        ),
        ProcurementClearanceProfile(
            profile_id=ProcurementProfileId.SUPPLIER_CHANGE,
            allowed_commit_types=(CommitActionType.CHANGE_SUPPLIER,),
            required_context=common_context + ("contract_ref", "operator_ref"),
            evidence_requirements=(
                _requirement("supplier_identity", "supplier_identity", "digital_business_credential"),
                _requirement("change_verification", "supplier_change_verification", "callback_verification"),
            ),
            material_change_triggers=(
                _trigger(
                    "supplier_state_changed",
                    "supplier_master",
                    "bank_details",
                    "subcontractors",
                    "ownership_control",
                    "data_location",
                ),
            ),
        ),
        ProcurementClearanceProfile(
            profile_id=ProcurementProfileId.PAYMENT,
            allowed_commit_types=(
                CommitActionType.APPROVE_PAYMENT,
                CommitActionType.HOLD_PAYMENT,
                CommitActionType.RELEASE_PAYMENT,
                CommitActionType.REJECT_PAYMENT,
                CommitActionType.EXECUTE_PAYMENT,
            ),
            required_context=common_context + ("contract_ref", "operator_ref"),
            evidence_requirements=(
                _requirement("invoice", "invoice"),
                _requirement("delivery", "delivery_attestation", "performance_evidence"),
                _requirement("bank_verification", "bank_account_verification", "callback_verification"),
            ),
            material_change_triggers=(
                _trigger("payment_state_changed", "invoice_state", "budget_state", "payment_status"),
                _trigger("bank_changed", "bank_details", "supplier_master"),
                _trigger("performance_changed", "performance_state"),
            ),
        ),
        ProcurementClearanceProfile(
            profile_id=ProcurementProfileId.TERMINATION_RENEWAL,
            allowed_commit_types=(
                CommitActionType.TERMINATE_CONTRACT,
                CommitActionType.RENEW_CONTRACT,
                CommitActionType.EXTEND_CONTRACT,
            ),
            required_context=common_context + ("contract_ref",),
            evidence_requirements=(
                _requirement("contract_state", "contract_state"),
                _requirement("performance", "performance_evidence", "breach_evidence"),
                _requirement("authority_evidence", "delegation_attestation", "authority_attestation"),
            ),
            material_change_triggers=(
                _trigger("performance_changed", "performance_state", "breach_state"),
                _trigger("remedy_changed", "remediation_state", "notice_period"),
            ),
        ),
        ProcurementClearanceProfile(
            profile_id=ProcurementProfileId.EMERGENCY_PROCEDURE,
            allowed_commit_types=(CommitActionType.INVOKE_EMERGENCY_PROCEDURE,),
            required_context=common_context,
            evidence_requirements=(
                _requirement("emergency_basis", "emergency_basis"),
                _requirement("proportionality", "proportionality_assessment"),
                _requirement("authority_evidence", "delegation_attestation", "authority_attestation"),
            ),
            material_change_triggers=(
                _trigger("emergency_basis_changed", "emergency_basis", "urgency", "available_alternatives"),
            ),
        ),
        ProcurementClearanceProfile(
            profile_id=ProcurementProfileId.LIFECYCLE_PUBLICATION,
            allowed_commit_types=(
                CommitActionType.PUBLISH_NEEDS_PLAN,
                CommitActionType.PUBLISH_LIFECYCLE_DATA,
            ),
            required_context=common_context,
            evidence_requirements=(
                _requirement("publication_payload", "publication_payload"),
                _requirement("source_receipts", "clearance_receipt", "execution_receipt", "outcome_receipt"),
            ),
            material_change_triggers=(
                _trigger("publication_changed", "publication_payload", "target_schema", "source_receipts"),
            ),
        ),
    )
    return {profile.profile_id: profile for profile in profiles}


def _is_present(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, (str, tuple, list, dict, set)):
        return bool(value)
    return True


def assess_procurement_action_case(
    *,
    action_case: ProcurementActionCase,
    profile: ProcurementClearanceProfile,
    observed_at: datetime,
    changed_fields: tuple[str, ...] = (),
) -> ProcurementClearanceAssessment:
    missing_context = tuple(
        field_name
        for field_name in profile.required_context
        if not _is_present(getattr(action_case, field_name, None))
    )

    evidence_by_type: dict[str, list[object]] = {}
    for evidence in action_case.evidence_refs:
        evidence_by_type.setdefault(evidence.evidence_type, []).append(evidence)

    missing_evidence: list[str] = []
    stale_ids: set[str] = set()
    for requirement in profile.evidence_requirements:
        matching = [
            evidence
            for evidence_type in requirement.accepted_evidence_types
            for evidence in evidence_by_type.get(evidence_type, ())
        ]
        if requirement.mandatory and not matching:
            missing_evidence.append(requirement.code)
        for evidence in matching:
            if evidence.expires_at is not None and evidence.expires_at <= observed_at:
                stale_ids.add(evidence.evidence_id)

    changed = set(changed_fields)
    triggered_changes = tuple(
        trigger.code
        for trigger in profile.material_change_triggers
        if changed.intersection(trigger.changed_fields)
    )

    commit_type_valid = (
        not profile.allowed_commit_types
        or action_case.requested_commit.action_type in profile.allowed_commit_types
    )

    if not commit_type_valid:
        disposition = AssessmentDisposition.FAIL_CLOSED
    elif missing_context or missing_evidence:
        disposition = AssessmentDisposition.GATHER_EVIDENCE
    elif stale_ids or triggered_changes:
        disposition = AssessmentDisposition.STEP_UP_RECOMMENDED
    else:
        disposition = AssessmentDisposition.READY_FOR_REHT

    return ProcurementClearanceAssessment(
        profile_id=profile.profile_id,
        profile_version=profile.profile_version,
        case_id=action_case.case_id,
        disposition=disposition,
        missing_context=tuple(sorted(missing_context)),
        missing_evidence=tuple(sorted(missing_evidence)),
        stale_evidence=tuple(sorted(stale_ids)),
        triggered_changes=tuple(sorted(triggered_changes)),
        commit_type_valid=commit_type_valid,
    )
