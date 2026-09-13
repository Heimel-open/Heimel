"""REHT Procurement Verifier — REHT clearance validation for public procurement actions.

REHT is the sole clearance boundary. This module validates ProcurementActionCaseV1 evidence
against legal, policy, supplier, financial, containment, and mandate preconditions before REHT issues clearance.
RACS remains dumb immutable contract data.
"""
from enum import Enum
from typing import Tuple, Optional
from valo_platform.public_procurement.action_case import ProcurementActionCaseV1
from valo_platform.governance.containment_attestation import ContainmentAttestationV1
from valo_platform.mandate_os.mandate_context import MandateContextV1
from valo_platform.governance.reht_containment_verifier import verify_containment_attestation
from valo_platform.governance.reht_mandate_verifier import verify_mandate_context


class RehtClearanceOutcome(str, Enum):
    ALLOW = "ALLOW"
    MODIFY = "MODIFY"
    STEP_UP = "STEP_UP"
    DEFER = "DEFER"
    DENY = "DENY"
    HALT = "HALT"


MANDATORY_PROCUREMENT_ACTIONS = {
    "NEEDS_PLAN_PUBLISH",
    "PROCEDURE_CRITERIA_APPROVE",
    "SHORTLIST_SELECTION_ACCEPT",
    "OPERATOR_EXCLUDE_REINSTATE",
    "AWARD_RECOMMENDATION_APPROVE",
    "AWARD_DECISION_COMMIT",
    "CONTRACT_SIGNATURE",
    "CONTRACT_MODIFICATION_MATERIAL",
    "SUPPLIER_MASTERDATA_CHANGE",
    "INVOICE_PAYMENT_RELEASE",
    "CONTRACT_TERMINATE_RENEW",
    "EMERGENCY_PROCEDURE_INVOKE",
    "DATASPACE_DATA_PUBLISH",
}


def verify_procurement_clearance(
    action_case: Optional[ProcurementActionCaseV1],
    required_tenant_id: str,
    supplier_verified: bool = True,
    has_policy_evidence: bool = True,
    containment_attestation: Optional[ContainmentAttestationV1] = None,
    mandate_context: Optional[MandateContextV1] = None,
    required_runtime_instance_id: Optional[str] = None,
    required_agent_id: Optional[str] = None,
    now_iso: str = "2026-08-04T21:00:00Z",
) -> Tuple[RehtClearanceOutcome, Optional[str]]:
    """REHT clearance rule: Validate procurement action case evidence, containment, and mandate context before clearance."""
    if action_case is None:
        return (RehtClearanceOutcome.DENY, "MISSING_PROCUREMENT_ACTION_CASE")

    if action_case.tenant_id != required_tenant_id:
        return (RehtClearanceOutcome.DENY, "TENANT_ISOLATION_VIOLATION")

    if action_case.action_type not in MANDATORY_PROCUREMENT_ACTIONS:
        return (RehtClearanceOutcome.DENY, "UNSUPPORTED_PROCUREMENT_ACTION_TYPE")

    if not has_policy_evidence or not action_case.evidence_digests:
        return (RehtClearanceOutcome.DENY, "MISSING_EVIDENCE_DIGESTS")

    # High-consequence actions (award, signature, payment) require supplier identity verification
    if action_case.action_type in {"AWARD_DECISION_COMMIT", "CONTRACT_SIGNATURE", "INVOICE_PAYMENT_RELEASE", "SUPPLIER_MASTERDATA_CHANGE"}:
        if not action_case.supplier_id:
            return (RehtClearanceOutcome.DENY, "MISSING_SUPPLIER_IDENTITY")
        if not supplier_verified:
            return (RehtClearanceOutcome.DENY, "UNVERIFIED_SUPPLIER_IDENTITY")

    # High-consequence payment releases require positive amount
    if action_case.action_type == "INVOICE_PAYMENT_RELEASE":
        if action_case.amount_nok is None or action_case.amount_nok <= 0:
            return (RehtClearanceOutcome.DENY, "INVALID_PAYMENT_AMOUNT")

    # 1. Verify containment attestation if provided
    if containment_attestation is not None and required_runtime_instance_id is not None:
        c_state, c_err = verify_containment_attestation(
            attestation=containment_attestation,
            required_runtime_instance_id=required_runtime_instance_id,
            now_iso=now_iso,
        )
        if c_state != RehtClearanceOutcome.ALLOW:
            return (RehtClearanceOutcome(c_state.value), c_err)

    # 2. Verify mandate context if provided
    if mandate_context is not None and required_agent_id is not None:
        m_state, m_err = verify_mandate_context(
            mandate_context=mandate_context,
            required_tenant_id=required_tenant_id,
            required_agent_id=required_agent_id,
            requested_action_class=action_case.action_type,
            now_iso=now_iso,
        )
        if m_state != RehtClearanceOutcome.ALLOW:
            return (RehtClearanceOutcome(m_state.value), m_err)

    return (RehtClearanceOutcome.ALLOW, None)
