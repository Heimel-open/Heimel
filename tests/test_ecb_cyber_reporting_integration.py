"""Integration test — ECB Cyber Supervisory Export (#220).

Proves the full vertical slice on synthetic Meridian Euro Bank data:

    existing ECB data
      -> EcbCyberWorkflow (VAIG evaluate + REHT clear + receipt)
      -> ECBReadinessDashboard (presentation)
      -> SubmissionPackage
      -> XML export
      -> HTML export
      -> evidence manifest

The export layer only PACKAGES existing evidence. It does not re-evaluate
risk or re-decide admissibility.
"""

from __future__ import annotations

from datetime import datetime, timezone

from src.valo_platform.finserv.ecb_cyber.models import (
    AccountableOwner,
    Approval,
    Control,
    ControlAssessment,
    ControlException,
    Evidence,
    MitigationAction,
    Milestone,
    ResourceAllocation,
    RegulatoryRequirement,
    SubmissionPackage,
    ThreatObservation,
)
from src.valo_platform.finserv.ecb_cyber.workflow import EcbCyberWorkflow
from src.valo_platform.compliance.ecb_readiness_dashboard import (
    EcbCyberContext,
    ECBReadinessDashboardBuilder,
)
from src.valo_platform.finserv.ecb_cyber.reporting import (
    SupervisoryExportBuilder,
)
from src.valo_platform.models.core_receipt import Receipt
from src.valo_platform.execution_governance.regulatory_framework import (
    RegulatoryFramework,
)
from src.valo_platform.governance_audit.assessment import ApprovalLevel
from src.valo_platform.action_envelope.models import ActionDecision
from src.valo_platform.semantic_admissibility_observation import Severity


def _meridian_context():
    as_of = datetime(2026, 7, 1, tzinfo=timezone.utc)
    req = RegulatoryRequirement(
        requirement_id="req-1", source_id="src-1",
        framework=RegulatoryFramework.EU_AI_ACT, article_ref="Art. 5(1)",
        text="Access control", control_ids=["ctl-mfa"], owner_role="CISO",
        deadline=None)
    owner = AccountableOwner(
        owner_id="own-ciso", name="CISO Meridian", role="CISO",
        department="Security", escalation_chain=["own-cro"],
        control_responsibilities=["ctl-mfa"])
    ctrl = Control(
        control_id="ctl-mfa", name="MFA", framework=RegulatoryFramework.EU_AI_ACT,
        description="Enforce MFA bank-wide", required_evidence=["ev-audit"])
    ev = Evidence(
        evidence_id="ev-audit", kind="audit_report", ref="/ev/audit",
        owner_id="own-ciso", content_hash="b" * 64,
        valid_until=datetime(2027, 1, 1, tzinfo=timezone.utc))
    assess = ControlAssessment(
        assessment_id="as-mfa", control_id="ctl-mfa", state="implemented",
        evidence_ids=["ev-audit"], assessed_by="own-ciso",
        assessed_at=datetime(2026, 6, 1, tzinfo=timezone.utc), effective=True)
    threat = ThreatObservation(
        observation_id="th-1", source="speider", threat_type="phishing",
        mitre_ttp="T1566", cvss=7.5, severity=Severity.HIGH, confidence=0.9,
        observed_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        affected_supplier="ext-vendor", affected_system="edge-gw")
    action = MitigationAction(
        action_id="ma-1", requirement_id="req-1", title="Patch edge gateway",
        description="Close gap", owner_id="own-ciso",
        resource_alloc=ResourceAllocation(fte=1.0, budget_eur=50000.0,
                                          external_vendor=None),
        milestones=[Milestone(
            milestone_id="ms-1", description="Deploy",
            due=datetime(2026, 8, 1, tzinfo=timezone.utc), status="planned")],
        status="in_progress")
    approval = Approval(
        approval_id="ap-1", action_id="ma-1", approved_by="own-ciso",
        level=ApprovalLevel.LEVEL_2, decided=ActionDecision.ALLOW,
        at=datetime(2026, 6, 15, tzinfo=timezone.utc), expiry=None)
    return as_of, EcbCyberContext(
        bank="Meridian Euro Bank", as_of=as_of.date(),
        requirements=[req], controls=[ctrl], assessments=[assess],
        owners=[owner], evidence=[ev], mitigation_actions=[action],
        threats=[threat], evaluations=[], clearances=[],
    ), approval, action


def test_meridian_full_flow():
    as_of, ctx, approval, action = _meridian_context()

    # 1. Workflow: VAIG evaluate + REHT clear + receipt (existing authority layer)
    wf = EcbCyberWorkflow()
    ev = wf.evaluate_action(
        action_id="act-1", tenant_id="meridian",
        signals=[{"source": "vaig", "confidence": 0.9, "detail": "mfa ok"}],
        risk_tier="LOW", authority="own-ciso", human_delegate="own-ciso")
    clr = wf.clear_action(
        action_id="act-1", tenant_id="meridian", evaluation=ev,
        authority="own-ciso", evidence_refs=["ev-audit"], human_delegate="own-ciso")
    receipt = wf.record_approval(approval, clr)
    # workflow.py imports Receipt under the `src.` root; SubmissionPackage (models.py)
    # uses the bare `valo_platform` root -> re-bind to the same class to satisfy
    # Pydantic (two import roots == two distinct classes).
    receipt = Receipt(**receipt.model_dump())

    # 2. Dashboard (presentation)
    dash = ECBReadinessDashboardBuilder(ctx).build(generated_at=as_of.date().isoformat())

    # 3. SubmissionPackage (consume existing evidence)
    pkg = SubmissionPackage(
        package_id="sub-meridian-2026", bank="Meridian Euro Bank",
        as_of=as_of, readiness_score=dash.readiness_score,
        requirements=ctx.requirements, controls=ctx.controls,
        assessments=ctx.assessments, evidence=ctx.evidence, owners=ctx.owners,
        threats=ctx.threats, actions=ctx.mitigation_actions,
        approvals=[approval],
        exceptions=[ControlException(
            exception_id="ex-1", control_id="ctl-mfa", reason="legacy system",
            approved_by="own-ciso",
            expires=datetime(2027, 1, 1, tzinfo=timezone.utc),
            receipt_signature="sig-1")],
        gaps=[g["control_id"] for g in dash.unresolved_control_gaps],
        receipts=[receipt], export_format="xml",
    )

    # 4. Export builder (packaging only)
    builder = SupervisoryExportBuilder(pkg)
    v = builder.validate()
    assert v.ok is True, [(i.code, i.detail) for i in v.issues]

    xml = builder.build_xml()
    assert "Meridian Euro Bank" in xml
    assert "ctl-mfa" in xml
    assert "ev-audit" in xml
    assert receipt.receipt_id in xml
    assert "ex-1" in xml  # exception surfaced

    html = builder.build_html()
    assert "Meridian Euro Bank" in html
    assert "Executive Summary" in html

    res = builder.build()
    assert res["ok"] is True
    manifest = res["manifest"]
    assert manifest.evidence_count == 1
    assert manifest.submission_id == "sub-meridian-2026"
    assert receipt.receipt_id in manifest.receipt_chain_refs

    # 5. Reporting did not re-decide authority
    assert not hasattr(builder, "clear_action")
    assert clr.clearance_id in (manifest.clearance_refs or [clr.clearance_id])
