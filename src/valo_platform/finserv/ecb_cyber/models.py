"""
ECB Cyber Action Plan — Core Data Model (#212)

Canonical types for the ECB AI Cyber Action Plan (E-CAP), per DESIGN.md §4.
Composed from existing VALO platform enums, models, and capabilities.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# ── Reused enums from the existing codebase ──────────────────────────────────
from src.valo_platform.action_envelope.models import ActionDecision, GovernanceClearance  # noqa: F401
from src.valo_platform.semantic_admissibility_observation import Severity  # noqa: F401
from src.valo_platform.execution_governance.regulatory_framework import (
    RegulatoryFramework,  # noqa: F401
)
from src.valo_platform.reht_admissibility_engine import AdmissibilityVerdict  # noqa: F401
from src.valo_platform.governance_audit.assessment import ApprovalLevel  # noqa: F401

# ── Reused model: canonical unified Receipt (RACS-compatible) ────────────────
from src.valo_platform.models.core_receipt import (
    Receipt,  # noqa: F401 — DO NOT REDEFINE, reuse as-is
    WORMEntry,  # noqa: F401
)

# =============================================================================
# 1. RegulatorySource
# =============================================================================


class RegulatorySource(BaseModel):
    """A source of regulatory content (e.g. ECB regulation, EBA guideline,
    national transposition)."""

    source_id: str = Field(..., description="Unique regulatory source identifier")
    name: str = Field(..., description="Human-readable source name")
    framework: RegulatoryFramework = Field(
        ..., description="Regulatory framework this source belongs to"
    )
    url: str = Field(..., description="URL to the original source document")
    fetched_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the source was last fetched",
    )
    content_hash: str = Field(..., description="SHA-256 hash of source content")


# =============================================================================
# 2. RegulatoryRequirement
# =============================================================================


class RegulatoryRequirement(BaseModel):
    """A specific binding requirement extracted from a regulatory source."""

    requirement_id: str = Field(..., description="Unique requirement identifier")
    source_id: str = Field(
        ..., description="Identifier of the RegulatorySource this came from"
    )
    framework: RegulatoryFramework = Field(
        ..., description="Regulatory framework this requirement belongs to"
    )
    article_ref: str = Field(
        ..., description="Article / section reference (e.g. 'Article 5(1)')"
    )
    text: str = Field(..., description="Full requirement text")
    control_ids: List[str] = Field(
        default_factory=list, description="Controls mapped to this requirement"
    )
    owner_role: str = Field(
        ..., description="Role responsible for this requirement"
    )
    deadline: Optional[datetime] = Field(
        None, description="Compliance deadline if applicable"
    )


# =============================================================================
# 3. ThreatObservation
# =============================================================================


class ThreatObservation(BaseModel):
    """An observed threat signal from Speider or external intelligence."""

    observation_id: str = Field(..., description="Unique observation identifier")
    source: str = Field(..., description="Source module or feed (e.g. 'speider', 'mitre')")
    observed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the observation was made",
    )
    threat_type: str = Field(..., description="Classification of the threat")
    mitre_ttp: Optional[str] = Field(
        None, description="MITRE ATT&CK technique ID"
    )
    cvss: Optional[float] = Field(None, ge=0.0, le=10.0, description="CVSS v3 score")
    affected_supplier: Optional[str] = Field(
        None, description="Supplier identifier if supplier-linked"
    )
    affected_system: Optional[str] = Field(
        None, description="System identifier if system-linked"
    )
    severity: Severity = Field(..., description="Severity classification")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in the observation (0-1)"
    )
    reality_package: Dict[str, Any] = Field(
        default_factory=dict,
        description="Speider/BARO reality package with evidence context",
    )


# =============================================================================
# 4. CriticalService
# =============================================================================


class CriticalService(BaseModel):
    """A business-critical service under ECB oversight."""

    service_id: str = Field(..., description="Unique service identifier")
    name: str = Field(..., description="Service name")
    criticality: int = Field(
        ..., ge=1, le=5, description="Criticality rating 1 (low) – 5 (critical)"
    )
    dependent_systems: List[str] = Field(
        default_factory=list, description="System asset IDs this service depends on"
    )
    dependent_suppliers: List[str] = Field(
        default_factory=list,
        description="Supplier IDs this service depends on",
    )


# =============================================================================
# 5. BusinessProcess
# =============================================================================


class BusinessProcess(BaseModel):
    """A business process mapped to critical services."""

    process_id: str = Field(..., description="Unique process identifier")
    name: str = Field(..., description="Process name")
    critical_services: List[str] = Field(
        default_factory=list,
        description="CriticalService IDs underpinning this process",
    )
    owner: str = Field(..., description="Process owner identifier or name")


# =============================================================================
# 6. SystemAsset
# =============================================================================


class SystemAsset(BaseModel):
    """An ICT system or asset supporting critical functions."""

    asset_id: str = Field(..., description="Unique asset identifier")
    name: str = Field(..., description="Asset name")
    type: str = Field(
        ..., description="Asset type (e.g. 'database', 'application', 'network')"
    )
    criticality: int = Field(
        ..., ge=1, le=5, description="Criticality rating 1 (low) – 5 (critical)"
    )
    supplier_id: Optional[str] = Field(
        None, description="Supplier identifier if third-party"
    )
    controls: List[str] = Field(
        default_factory=list, description="Control IDs applied to this asset"
    )


# =============================================================================
# 7. Supplier
# =============================================================================


class Supplier(BaseModel):
    """A third-party supplier subject to ECB cyber risk assessment."""

    supplier_id: str = Field(..., description="Unique supplier identifier")
    name: str = Field(..., description="Supplier legal name")
    criticality: int = Field(
        ..., ge=1, le=5, description="Criticality rating 1 (low) – 5 (critical)"
    )
    risk_tier: str = Field(
        ...,
        description="Risk tier classification (e.g. 'tier_1', 'tier_2', 'tier_3')",
    )
    assessment_ref: Optional[str] = Field(
        None, description="Reference to latest supplier assessment"
    )


# =============================================================================
# 8. Control
# =============================================================================


class Control(BaseModel):
    """A security / compliance control mapped to regulatory requirements."""

    control_id: str = Field(..., description="Unique control identifier")
    name: str = Field(..., description="Control name")
    framework: RegulatoryFramework = Field(
        ..., description="Regulatory framework this control belongs to"
    )
    description: str = Field(..., description="Control description / implementation guidance")
    required_evidence: List[str] = Field(
        default_factory=list,
        description="Evidence kinds required to demonstrate control effectiveness",
    )


# =============================================================================
# 9. ControlAssessment
# =============================================================================


class ControlAssessment(BaseModel):
    """Assessment of a control's implementation state and effectiveness."""

    assessment_id: str = Field(..., description="Unique assessment identifier")
    control_id: str = Field(..., description="Control being assessed")
    state: str = Field(
        ...,
        description="Implementation state (e.g. 'implemented', 'partially', 'planned', 'not_applicable')",
    )
    evidence_ids: List[str] = Field(
        default_factory=list,
        description="Evidence IDs supporting this assessment",
    )
    assessed_by: str = Field(
        ..., description="Assessor identifier (person or tool)"
    )
    assessed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the assessment was performed",
    )
    effective: bool = Field(
        ..., description="Whether the control is deemed effective"
    )


# =============================================================================
# 10. AccountableOwner
# =============================================================================


class AccountableOwner(BaseModel):
    """A named owner accountable for controls and compliance."""

    owner_id: str = Field(..., description="Unique owner identifier")
    name: str = Field(..., description="Owner full name")
    role: str = Field(..., description="Owner role / title")
    department: str = Field(..., description="Department name")
    escalation_chain: List[str] = Field(
        default_factory=list,
        description="Escalation contact identifiers (ordered)",
    )
    control_responsibilities: List[str] = Field(
        default_factory=list,
        description="Control IDs this owner is responsible for",
    )


# =============================================================================
# 11. Evidence
# =============================================================================


class Evidence(BaseModel):
    """An evidence artefact used to demonstrate control effectiveness."""

    evidence_id: str = Field(..., description="Unique evidence identifier")
    kind: str = Field(
        ..., description="Evidence kind (e.g. 'audit_report', 'scan_result', 'attestation')"
    )
    ref: str = Field(
        ..., description="Reference / path to the evidence artefact"
    )
    valid_until: Optional[datetime] = Field(
        None, description="Expiration date for time-limited evidence"
    )
    owner_id: str = Field(
        ..., description="AccountableOwner identifier who provides this evidence"
    )
    content_hash: str = Field(
        ..., description="SHA-256 hash of evidence content for integrity"
    )


# =============================================================================
# 12. MitigationAction
# =============================================================================


class ResourceAllocation(BaseModel):
    """Resources allocated to a mitigation action."""

    fte: float = Field(
        ..., ge=0.0, description="Full-time equivalent headcount allocated"
    )
    budget_eur: float = Field(
        ..., ge=0.0, description="Budget allocated in EUR"
    )
    external_vendor: Optional[str] = Field(
        None, description="External vendor identifier if outsourced"
    )


class Milestone(BaseModel):
    """A milestone within a mitigation action plan."""

    milestone_id: str = Field(..., description="Unique milestone identifier")
    due: datetime = Field(..., description="Milestone due date")
    description: str = Field(..., description="Milestone description")
    status: str = Field(
        ...,
        description="Status (e.g. 'pending', 'in_progress', 'completed', 'overdue')",
    )


class MitigationAction(BaseModel):
    """A remediation or mitigation action addressing a regulatory requirement."""

    action_id: str = Field(..., description="Unique action identifier")
    requirement_id: str = Field(
        ..., description="RegulatoryRequirement this action addresses"
    )
    title: str = Field(..., description="Action title")
    description: str = Field(..., description="Detailed action description")
    owner_id: str = Field(
        ..., description="AccountableOwner identifier responsible"
    )
    resource_alloc: ResourceAllocation = Field(
        ..., description="Resource allocation for this action"
    )
    milestones: List[Milestone] = Field(
        default_factory=list, description="Milestones driving this action"
    )
    status: str = Field(
        ...,
        description="Action status (e.g. 'not_started', 'in_progress', 'completed', 'blocked')",
    )


# =============================================================================
# 15. Approval
# =============================================================================


class Approval(BaseModel):
    """An approval decision for a mitigation action at a governance level."""

    approval_id: str = Field(..., description="Unique approval identifier")
    action_id: str = Field(
        ..., description="MitigationAction being approved"
    )
    approved_by: str = Field(
        ..., description="Identifier of the approving authority"
    )
    level: ApprovalLevel = Field(
        ..., description="Approval level (LEVEL_0=audit, LEVEL_1=manager, LEVEL_2=director/CISO/CRO, LEVEL_3=executive/board)"
    )
    decided: ActionDecision = Field(
        ..., description="The decision rendered (ALLOW, MODIFY, DEFER, DENY, etc.)"
    )
    at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the approval was issued",
    )
    conditions: List[str] = Field(
        default_factory=list,
        description="Conditions attached to the approval",
    )
    expiry: Optional[datetime] = Field(
        None, description="Expiration of the approval if time-limited"
    )


# =============================================================================
# 16. ControlException
# =============================================================================


class ControlException(BaseModel):
    """A granted exception from a control requirement."""

    exception_id: str = Field(..., description="Unique exception identifier")
    control_id: str = Field(
        ..., description="Control for which the exception is granted"
    )
    reason: str = Field(..., description="Reason for granting the exception")
    approved_by: str = Field(
        ..., description="Authority who approved the exception"
    )
    expires: datetime = Field(
        ..., description="When the exception expires"
    )
    receipt_signature: str = Field(
        ...,
        description="Cryptographic signature / receipt reference for audit",
    )


# =============================================================================
# 17. CyberEvaluation (VAIG output)
# =============================================================================


class CyberEvaluation(BaseModel):
    """VAIG evaluation output — the decision produced by the VAIG inference
    engine from fused evidence signals.

    Distinct from the canonical GovernanceClearance (REHT authority artifact in
    action_envelope.models). VAIG evaluates; REHT clears. Named CyberEvaluation to
    avoid implying a competing decision authority.
    """

    decision_id: str = Field(..., description="Unique decision identifier")
    action_id: str = Field(
        ..., description="Action this evaluation relates to"
    )
    signal_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Summary of fused signals feeding this decision",
    )
    risk_tier: str = Field(
        ...,
        description="Risk tier determined (e.g. 'low', 'medium', 'high', 'critical')",
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in the evaluation"
    )
    recommended_disposition: str = Field(
        ..., description="Recommended disposition label"
    )


# =============================================================================
# 18. GovernanceClearance — REUSED (not redefined)
#
# The canonical REHT authority artifact lives in action_envelope.models
# .GovernanceClearance and is imported above. It is the SOLE admissibility
# authority; the ECB Cyber profile fills it with decision/state/authority_refs/
# evidence_refs/valid_until/evaluator_refs/receipt_ref. Do NOT define a second
# competing clearance contract here.
# =============================================================================

#
# Imported from src.valo_platform.models.core_receipt above. The canonical
# Receipt is used as-is with optional ECB-specific extensions carried in
# the metadata field (ecb_submission_ref, cyber_alert_id,
# supervisory_receipt_id).
# =============================================================================


# =============================================================================
# 20. SubmissionPackage
# =============================================================================


class SubmissionPackage(BaseModel):
    """A complete submission package for ECB supervisory reporting."""

    package_id: str = Field(..., description="Unique package identifier")
    bank: str = Field(..., description="Bank / institution identifier")
    as_of: datetime = Field(
        ..., description="Reporting date for this submission"
    )
    readiness_score: float = Field(
        ..., ge=0.0, le=1.0, description="Overall readiness score (0-1)"
    )
    requirements: List[RegulatoryRequirement] = Field(
        default_factory=list,
        description="Regulatory requirements covered in this package",
    )
    controls: List[Control] = Field(
        default_factory=list,
        description="Controls mapped to requirements",
    )
    gaps: List[str] = Field(
        default_factory=list,
        description="Identified compliance gaps (free-text descriptions)",
    )
    actions: List[MitigationAction] = Field(
        default_factory=list,
        description="Mitigation actions in progress or planned",
    )
    assessments: List[ControlAssessment] = Field(
        default_factory=list,
        description="Control assessments referenced by this package",
    )
    evidence: List[Evidence] = Field(
        default_factory=list,
        description="Evidence pieces backing assessments in this package",
    )
    owners: List[AccountableOwner] = Field(
        default_factory=list,
        description="Accountable owners for controls in this package",
    )
    threats: List[ThreatObservation] = Field(
        default_factory=list,
        description="Threat observations considered in this package",
    )
    approvals: List[Approval] = Field(
        default_factory=list,
        description="Human approvals recorded for actions in this package",
    )
    exceptions: List[ControlException] = Field(
        default_factory=list,
        description="Granted control exceptions in this package",
    )
    receipts: List[Receipt] = Field(
        default_factory=list,
        description="Governance receipts for actions in this package",
    )
    export_format: str = Field(
        ..., pattern=r"^(pdf|xml)$", description="Export format: 'pdf' or 'xml'"
    )
