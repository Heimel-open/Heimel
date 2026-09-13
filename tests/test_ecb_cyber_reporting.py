"""Unit tests — ECB Cyber Supervisory Export (#220).

Verifies packaging-only behaviour:
- deterministic, stable-ordered XML
- valid evidence references pass validation
- missing evidence -> fail-closed validation error
- broken receipt reference -> fail-closed validation error
- stale assessment (>180d) counted + represented
- unresolved gap represented
- HTML renders with all required sections
- PDF adapter fails clearly when WeasyPrint absent (no crash)
- reporting layer holds NO governance authority (no clearance issued,
  no admissibility decision, no VAIG/REHT mutation)
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from src.valo_platform.finserv.ecb_cyber.models import (
    AccountableOwner,
    Approval,
    Control,
    ControlAssessment,
    Evidence,
    MitigationAction,
    Milestone,
    RegulatoryRequirement,
    SubmissionPackage,
    ThreatObservation,
)
from src.valo_platform.finserv.ecb_cyber.reporting import (
    SupervisoryExportBuilder,
)
from src.valo_platform.models.core_receipt import (
    ExecutionDecision,
    Receipt,
    ReceiptType,
)
from src.valo_platform.action_envelope.models import ActionDecision
from src.valo_platform.execution_governance.regulatory_framework import (
    RegulatoryFramework,
)
from src.valo_platform.governance_audit.assessment import ApprovalLevel
from src.valo_platform.semantic_admissibility_observation import Severity


def _owner():
    return AccountableOwner(
        owner_id="own-1", name="Jane Doe", role="CISO",
        department="Security", escalation_chain=["own-2"])


def _control():
    return Control(
        control_id="ctl-1", name="MFA", framework=RegulatoryFramework.EU_AI_ACT,
        description="Enforce MFA", required_evidence=["ev-audit"])


def _requirement():
    return RegulatoryRequirement(
        requirement_id="req-1", source_id="src-1",
        framework=RegulatoryFramework.EU_AI_ACT,
        article_ref="Art. 5(1)", text="Access control",
        control_ids=["ctl-1"], owner_role="CISO", deadline=None)


def _evidence(ev_id="ev-audit"):
    return Evidence(
        evidence_id=ev_id, kind="audit_report", ref=f"/ev/{ev_id}",
        owner_id="own-1",
        content_hash="a" * 64,
        valid_until=datetime(2027, 1, 1, tzinfo=timezone.utc))


def _assessment(ev_id="ev-audit", assessed_at=None):
    return ControlAssessment(
        assessment_id="as-1", control_id="ctl-1", state="implemented",
        evidence_ids=[ev_id], assessed_by="own-1",
        assessed_at=assessed_at or datetime(2026, 6, 1, tzinfo=timezone.utc),
        effective=True)


def _receipt(rid="rcpt-1"):
    return Receipt(
        receipt_id=rid,
        request_id="req-x", decision=ExecutionDecision.ALLOW,
        actor_id="own-1", actor_role="approver", action_id="act-1",
        evidence_ids=["ev-audit"], regulatory_frameworks=["dora", "ecb"],
        compliance_status="COMPLIANT", receipt_type=ReceiptType.POLICY_ENFORCEMENT,
        metadata={"clearance_ref": "clr-1", "snapshot_id": "snap-1"})


def _approval():
    return Approval(
        approval_id="ap-1", action_id="act-1", approved_by="own-1",
        level=ApprovalLevel.LEVEL_2, decided=ActionDecision.ALLOW,
        at=datetime(2026, 6, 15, tzinfo=timezone.utc))


def _threat():
    return ThreatObservation(
        observation_id="th-1", source="speider", threat_type="phishing",
        mitre_ttp="T1566", cvss=7.5, severity=Severity.HIGH, confidence=0.9,
        observed_at=datetime(2026, 6, 1, tzinfo=timezone.utc))


def _base_package(**over):
    kw = dict(
        package_id="sub-1", bank="Meridian Euro Bank",
        as_of=date(2026, 7, 1), readiness_score=0.8,
        requirements=[_requirement()], controls=[_control()],
        assessments=[_assessment()], owners=[_owner()],
        evidence=[_evidence()], actions=[], approvals=[], exceptions=[],
        threats=[], gaps=[], receipts=[_receipt()],
        export_format="xml",
    )
    kw.update(over)
    return SubmissionPackage(**kw)


# --- deterministic + stable ordering ----------------------------------------
def test_xml_is_deterministic():
    out1 = SupervisoryExportBuilder(_base_package()).build_xml()
    out2 = SupervisoryExportBuilder(_base_package()).build_xml()
    assert out1 == out2


def test_xml_stable_ordering():
    c2 = Control(control_id="ctl-2", name="Logging",
                 framework=RegulatoryFramework.EU_AI_ACT,
                 description="x", required_evidence=[])
    pkg = _base_package(controls=[c2, _control()])
    xml = SupervisoryExportBuilder(pkg).build_xml()
    assert xml.index("ctl-1") < xml.index("ctl-2")


# --- validation ------------------------------------------------------------
def test_valid_package_passes():
    v = SupervisoryExportBuilder(_base_package()).validate()
    assert v.ok is True
    assert v.errors == []


def test_missing_evidence_fails_closed():
    pkg = _base_package(assessments=[_assessment(ev_id="ev-missing")],
                         evidence=[])
    v = SupervisoryExportBuilder(pkg).validate()
    assert v.ok is False
    assert any(i.code == "missing_evidence" for i in v.errors)


def test_broken_receipt_reference_fails_closed():
    bad = _receipt()
    bad.receipt_id = ""
    pkg = _base_package(receipts=[bad])
    v = SupervisoryExportBuilder(pkg).validate()
    assert v.ok is False
    assert any(i.code == "broken_receipt" for i in v.errors)


def test_stale_assessment_represented():
    stale = _assessment(assessed_at=datetime(2025, 1, 1, tzinfo=timezone.utc))
    pkg = _base_package(assessments=[stale])
    b = SupervisoryExportBuilder(pkg)
    assert b._stale_assessment_count(date(2026, 7, 1)) == 1
    xml = b.build_xml()
    assert "staleAssessmentCount" in xml


def test_unresolved_gap_represented():
    pkg = _base_package(gaps=["Control ctl-9 not implemented"])
    xml = SupervisoryExportBuilder(pkg).build_xml()
    assert "Control ctl-9 not implemented" in xml


def test_build_returns_manifest_on_success():
    res = SupervisoryExportBuilder(_base_package()).build()
    assert res["ok"] is True
    assert res["manifest"].evidence_count == 1
    assert res["manifest"].unresolved_gap_count == 0
    assert "rcpt-1" in res["manifest"].receipt_chain_refs


def test_build_fail_closed_on_missing_evidence():
    pkg = _base_package(assessments=[_assessment(ev_id="ev-x")], evidence=[])
    res = SupervisoryExportBuilder(pkg).build()
    assert res["ok"] is False
    assert res.get("xml") is None


# --- HTML + PDF adapter -----------------------------------------------------
def test_html_renders_all_sections():
    html = SupervisoryExportBuilder(
        _base_package(approvals=[_approval()], threats=[_threat()])
    ).build_html()
    for sec in ("Executive Summary", "Regulatory Scope", "Controls",
                "Accountable Owners", "Mitigation Actions", "Threat Observations",
                "Approvals", "Unresolved Gaps", "Receipt References",
                "Limitations"):
        assert sec in html


def test_pdf_adapter_fails_without_weasyprint():
    import importlib.util
    if importlib.util.find_spec("weasyprint") is None:
        try:
            SupervisoryExportBuilder(_base_package()).build_pdf()
            assert False, "expected RuntimeError when WeasyPrint absent"
        except RuntimeError as e:
            assert "ecb" in str(e)
    else:
        pdf = SupervisoryExportBuilder(_base_package()).build_pdf()
        assert isinstance(pdf, (bytes, bytearray))


# --- authority boundary ----------------------------------------------------
def test_reporting_layer_holds_no_authority():
    b = SupervisoryExportBuilder(_base_package())
    assert not hasattr(b, "decide")
    assert not hasattr(b, "clear_action")
    assert not hasattr(b, "issue_clearance")
    pkg = _base_package()
    b2 = SupervisoryExportBuilder(pkg)
    _ = b2.build_xml()
    assert pkg.readiness_score == 0.8  # unchanged
