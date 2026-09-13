"""
Supervisory Export — ECB Cyber Action Plan (#220).

Presentation + packaging layer ONLY. Consumes an existing SubmissionPackage
(and optionally an EcbCyberContext for dashboard-derived readiness data) and
produces regulator-ready artefacts:

    - deterministic machine-readable XML
    - regulator-readable HTML (Jinja2; usable without PDF dependency)
    - PDF (WeasyPrint, OPTIONAL [ecb] extra; fails clearly if absent)
    - proof-of-evidence manifest (controls / assessments / owners / actions /
      approvals / exceptions / clearance refs / canonical Receipt refs /
      evidence / exposure-graph refs)

Architectural invariant (reporting never becomes an authority layer):
    BARO observes -> VAIG evaluates -> REHT decides -> Core enforces
    -> RACS records -> Reporting packages existing evidence

This module MUST NOT:
    - evaluate risk
    - decide admissibility
    - issue GovernanceClearance
    - create a second receipt type
    - modify VAIG or REHT decisions
    - claim regulatory approval / ECB submission acceptance

Fail-closed: when required evidence is missing, receipt references are broken,
owners are absent, required fields are incomplete, or the package schema is
invalid, export generation returns a structured ValidationResult (no export,
no REHT verdict).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as ET

from src.valo_platform.finserv.ecb_cyber.models import (
    AccountableOwner,
    Approval,
    Control,
    ControlAssessment,
    ControlException,
    Evidence,
    GovernanceClearance,
    MitigationAction,
    RegulatoryRequirement,
    SubmissionPackage,
    ThreatObservation,
)
from src.valo_platform.finserv.ecb_cyber.exposure_graph import ExposureGraph
from src.valo_platform.models.core_receipt import Receipt

SCHEMA_VERSION = "ecb-cyber-export/1.0"
POLICY_VERSION = "ecb-cyber-action-plan/2026"

# Exposure-graph reference is linked by id when present on the package context.
# The package itself does not carry the graph; the builder accepts an optional
# graph whose node ids are referenced from controls/assets.


@dataclass
class ValidationIssue:
    code: str
    severity: str  # "error" | "warning"
    detail: str


@dataclass
class ValidationResult:
    ok: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    submission_id: Optional[str] = None

    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    def add(self, code: str, severity: str, detail: str) -> None:
        self.issues.append(ValidationIssue(code, severity, detail))


@dataclass
class ExportManifest:
    submission_id: str
    generated_at: str
    schema_version: str
    policy_version: str
    source_snapshot_ids: List[str]
    receipt_chain_refs: List[str]
    clearance_refs: List[str] = field(default_factory=list)
    content_hash: str = ""
    evidence_count: int = 0
    unresolved_gap_count: int = 0
    stale_assessment_count: int = 0
    sections: Dict[str, int] = field(default_factory=dict)


class SupervisoryExportBuilder:
    """Builds regulator-ready exports from an existing SubmissionPackage."""

    def __init__(self, package: SubmissionPackage,
                 context: Optional[Any] = None,
                 exposure_graph: Optional[ExposureGraph] = None) -> None:
        self.pkg = package
        self.ctx = context
        self.graph = exposure_graph

    # -- fail-closed validation --------------------------------------------
    def validate(self) -> ValidationResult:
        pkg = self.pkg
        res = ValidationResult(ok=True, submission_id=pkg.package_id)
        # 1. schema-required fields
        for fld in ("package_id", "bank", "as_of", "readiness_score", "export_format"):
            if getattr(pkg, fld, None) in (None, ""):
                res.add("missing_field", "error", f"SubmissionPackage.{fld} is empty")
        if pkg.export_format not in ("pdf", "xml"):
            res.add("invalid_schema", "error",
                    f"export_format must be 'pdf' or 'xml', got {pkg.export_format!r}")
        # 2. required evidence present for every assessment's evidence_ids
        ev_ids = {e.evidence_id for e in getattr(pkg, "evidence", []) or []}
        for a in getattr(pkg, "assessments", []) or []:
            for eid in a.evidence_ids:
                if eid not in ev_ids:
                    res.add("missing_evidence", "error",
                            f"assessment {a.assessment_id} references "
                            f"missing evidence {eid}")
        # 3. broken receipt references (receipt must have receipt_id)
        receipt_ids = set()
        for r in pkg.receipts:
            rid = getattr(r, "receipt_id", None)
            if not rid:
                res.add("broken_receipt", "error",
                        "receipt without receipt_id in package")
            else:
                receipt_ids.add(rid)
        # 4. owners present for controls requiring them
        owner_ids = {o.owner_id for o in getattr(pkg, "owners", []) or []}
        ctrl_owner_refs: set = set()
        for c in pkg.controls:
            for req in pkg.requirements:
                if c.control_id in req.control_ids:
                    if getattr(req, "owner_role", None):
                        ctrl_owner_refs.add(req.owner_role)
        if getattr(pkg, "controls", None) and not owner_ids:
            res.add("missing_owner", "error",
                    "controls present but no accountable owners supplied")
        # aggregate
        res.ok = len(res.errors) == 0
        return res

    # -- helpers -----------------------------------------------------------
    def _content_hash(self, payload: str) -> str:
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _receipt_refs(self) -> List[str]:
        return [getattr(r, "receipt_id", "") for r in self.pkg.receipts
                if getattr(r, "receipt_id", "")]

    def _clearance_refs(self) -> List[str]:
        refs: List[str] = []
        for r in self.pkg.receipts:
            meta = getattr(r, "metadata", None) or {}
            cr = meta.get("clearance_ref") if isinstance(meta, dict) else None
            if cr:
                refs.append(str(cr))
        return refs

    def _stale_assessment_count(self, as_of) -> int:
        cnt = 0
        for a in getattr(self.pkg, "assessments", []) or []:
            try:
                age = (as_of - a.assessed_at.date()).days
            except Exception:
                age = 0
            if age > 180:
                cnt += 1
        return cnt

    # -- XML ---------------------------------------------------------------
    def build_xml(self) -> str:
        """Deterministic, sorted XML export. Stable element ordering."""
        pkg = self.pkg
        root = ET.Element("ecbSupervisorySubmission")
        root.set("schemaVersion", SCHEMA_VERSION)
        root.set("policyVersion", POLICY_VERSION)
        root.set("submissionId", pkg.package_id)
        root.set("bank", pkg.bank)
        root.set("asOf", pkg.as_of.isoformat())
        root.set("generatedAt", pkg.as_of.isoformat())
        root.set("readinessScore", f"{pkg.readiness_score:.4f}")

        # Evidence manifest (counts + refs) — deterministic
        manifest = ET.SubElement(root, "evidenceManifest")
        ET.SubElement(manifest, "evidenceCount").text = str(
            len(getattr(pkg, "evidence", []) or []))
        ET.SubElement(manifest, "unresolvedGapCount").text = str(len(pkg.gaps))
        ET.SubElement(manifest, "staleAssessmentCount").text = str(
            self._stale_assessment_count(pkg.as_of))
        rc = ET.SubElement(manifest, "receiptChainRefs")
        for rid in sorted(self._receipt_refs()):
            e = ET.SubElement(rc, "receiptRef")
            e.text = rid
        cc = ET.SubElement(manifest, "governanceClearanceRefs")
        for cref in sorted(self._clearance_refs()):
            e = ET.SubElement(cc, "clearanceRef")
            e.text = cref

        # Regulatory scope
        scope = ET.SubElement(root, "regulatoryScope")
        for req in sorted(pkg.requirements, key=lambda r: r.requirement_id):
            re = ET.SubElement(scope, "requirement")
            re.set("id", req.requirement_id)
            re.set("framework", req.framework.value if hasattr(req.framework, "value") else str(req.framework))
            re.set("article", req.article_ref)
            re.set("ownerRole", req.owner_role)
            ET.SubElement(re, "text").text = req.text

        # Controls + assessments
        ctrls = ET.SubElement(root, "controls")
        assess_map = {a.control_id: a for a in getattr(pkg, "assessments", []) or []}
        for c in sorted(pkg.controls, key=lambda c: c.control_id):
            ce = ET.SubElement(ctrls, "control")
            ce.set("id", c.control_id)
            ce.set("framework", c.framework.value if hasattr(c.framework, "value") else str(c.framework))
            ET.SubElement(ce, "name").text = c.name
            ET.SubElement(ce, "description").text = c.description
            a = assess_map.get(c.control_id)
            if a is not None:
                ae = ET.SubElement(ce, "assessment")
                ae.set("state", a.state)
                ae.set("effective", "true" if a.effective else "false")
                ae.set("assessedAt", a.assessed_at.isoformat())
                for eid in sorted(a.evidence_ids):
                    ve = ET.SubElement(ae, "evidenceRef")
                    ve.text = eid

        # Owners
        owners = ET.SubElement(root, "owners")
        for o in sorted(getattr(pkg, "owners", []) or [], key=lambda o: o.owner_id):
            oe = ET.SubElement(owners, "owner")
            oe.set("id", o.owner_id)
            oe.set("name", o.name)
            oe.set("role", o.role)
            oe.set("department", o.department)

        # Mitigation actions
        actions = ET.SubElement(root, "mitigationActions")
        for m in sorted(pkg.actions, key=lambda m: m.action_id):
            me = ET.SubElement(actions, "action")
            me.set("id", m.action_id)
            me.set("status", m.status)
            ET.SubElement(me, "title").text = m.title
            ET.SubElement(me, "description").text = m.description
            for ms in sorted(m.milestones, key=lambda x: x.due.isoformat()):
                mse = ET.SubElement(me, "milestone")
                mse.set("due", ms.due.isoformat())
                mse.set("status", ms.status)
                mse.text = ms.description

        # Threat observations
        threats = ET.SubElement(root, "threatObservations")
        for t in sorted(getattr(pkg, "threats", []) or [], key=lambda t: t.observation_id):
            te = ET.SubElement(threats, "threat")
            te.set("id", t.observation_id)
            te.set("type", t.threat_type)
            te.set("severity", t.severity.value if hasattr(t.severity, "value") else str(t.severity))
            te.set("cvss", str(t.cvss) if t.cvss is not None else "")
            te.set("observedAt", t.observed_at.isoformat())

        # Approvals
        approvals = ET.SubElement(root, "approvals")
        for ap in sorted(getattr(pkg, "approvals", []) or [], key=lambda a: a.approval_id):
            ae = ET.SubElement(approvals, "approval")
            ae.set("id", ap.approval_id)
            ae.set("actionId", ap.action_id)
            ae.set("level", ap.level.value if hasattr(ap.level, "value") else str(ap.level))
            ae.set("decision", ap.decided.value if hasattr(ap.decided, "value") else str(ap.decided))
            ae.set("at", ap.at.isoformat())

        # Exceptions
        exceptions = ET.SubElement(root, "exceptions")
        for ex in sorted(getattr(pkg, "exceptions", []) or [], key=lambda x: x.exception_id):
            xe = ET.SubElement(exceptions, "exception")
            xe.set("id", ex.exception_id)
            xe.set("controlId", ex.control_id)
            xe.set("reason", ex.reason)
            xe.set("expires", ex.expires.isoformat())

        # Unresolved gaps
        gaps = ET.SubElement(root, "unresolvedGaps")
        for g in sorted(pkg.gaps):
            ge = ET.SubElement(gaps, "gap")
            ge.text = g

        # Receipts (canonical, referenced)
        receipts = ET.SubElement(root, "receipts")
        for r in sorted(pkg.receipts, key=lambda r: getattr(r, "receipt_id", "")):
            re = ET.SubElement(receipts, "receipt")
            re.set("id", getattr(r, "receipt_id", ""))
            re.set("requestId", getattr(r, "request_id", ""))

        # Exposure-graph references
        if self.graph is not None:
            eg = ET.SubElement(root, "exposureGraphRefs")
            for nid in sorted(getattr(self.graph, "nodes", {}).keys()):
                ne = ET.SubElement(eg, "nodeRef")
                ne.text = str(nid)

        # Limitations / disclaimer
        lim = ET.SubElement(root, "limitations")
        ET.SubElement(lim, "disclaimer").text = (
            "Generated from existing governed evidence. This artefact is a "
            "packaging of records already produced by VAIG/REHT/RACS. It asserts "
            "no regulatory approval and no acceptance by the ECB. Submission "
            "acceptance is determined solely by the competent authority."
        )

        ET.indent(root)
        return ET.tostring(root, encoding="unicode")

    # -- HTML (Jinja2; usable without PDF) --------------------------------
    def build_html(self) -> str:
        from jinja2 import Template
        pkg = self.pkg
        assess_map = {a.control_id: a for a in getattr(pkg, "assessments", []) or []}
        tpl = Template(_HTML_TEMPLATE)
        return tpl.render(
            schema_version=SCHEMA_VERSION,
            policy_version=POLICY_VERSION,
            submission_id=pkg.package_id,
            bank=pkg.bank,
            as_of=pkg.as_of.isoformat(),
            generated_at=pkg.as_of.isoformat(),
            readiness_score=f"{pkg.readiness_score:.4f}",
            requirements=sorted(pkg.requirements, key=lambda r: r.requirement_id),
            controls=sorted(pkg.controls, key=lambda c: c.control_id),
            assessments_map=assess_map,
            owners=sorted(getattr(pkg, "owners", []) or [], key=lambda o: o.owner_id),
            actions=sorted(pkg.actions, key=lambda m: m.action_id),
            threats=sorted(getattr(pkg, "threats", []) or [], key=lambda t: t.observation_id),
            approvals=sorted(getattr(pkg, "approvals", []) or [], key=lambda a: a.approval_id),
            exceptions=sorted(getattr(pkg, "exceptions", []) or [], key=lambda x: x.exception_id),
            gaps=sorted(pkg.gaps),
            receipt_refs=sorted(self._receipt_refs()),
            clearance_refs=sorted(self._clearance_refs()),
            evidence_count=len(getattr(pkg, "evidence", []) or []),
            unresolved_gap_count=len(pkg.gaps),
            stale_assessment_count=self._stale_assessment_count(pkg.as_of),
        )

    # -- PDF (optional WeasyPrint) ---------------------------------------
    def build_pdf(self) -> bytes:
        try:
            import weasyprint  # type: ignore
        except Exception:
            raise RuntimeError(
                "PDF rendering requires the optional 'ecb' dependency extra "
                "(WeasyPrint). Install with: pip install 'valo-platform[ecb]'. "
                "HTML export is available without it."
            )
        html = self.build_html()
        return weasyprint.HTML(string=html).write_pdf()

    # -- manifest ----------------------------------------------------------
    def build_manifest(self, xml: str) -> ExportManifest:
        pkg = self.pkg
        snap = []
        for r in pkg.receipts:
            meta = getattr(r, "metadata", None) or {}
            if isinstance(meta, dict) and meta.get("snapshot_id"):
                snap.append(meta["snapshot_id"])
        return ExportManifest(
            submission_id=pkg.package_id,
            generated_at=pkg.as_of.isoformat(),
            schema_version=SCHEMA_VERSION,
            policy_version=POLICY_VERSION,
            source_snapshot_ids=sorted(set(snap)),
            receipt_chain_refs=sorted(self._receipt_refs()),
            clearance_refs=sorted(self._clearance_refs()),
            content_hash=self._content_hash(xml),
            evidence_count=len(getattr(pkg, "evidence", []) or []),
            unresolved_gap_count=len(pkg.gaps),
            stale_assessment_count=self._stale_assessment_count(pkg.as_of),
            sections={
                "requirements": len(pkg.requirements),
                "controls": len(pkg.controls),
                "owners": len(getattr(pkg, "owners", []) or []),
                "actions": len(pkg.actions),
                "threats": len(getattr(pkg, "threats", []) or []),
                "approvals": len(getattr(pkg, "approvals", []) or []),
                "exceptions": len(getattr(pkg, "exceptions", []) or []),
                "gaps": len(pkg.gaps),
                "receipts": len(pkg.receipts),
            },
        )

    # -- orchestrator ------------------------------------------------------
    def build(self, with_pdf: bool = False) -> Dict[str, Any]:
        """Build the full export bundle. Fail-closed on validation."""
        vres = self.validate()
        if not vres.ok:
            return {"ok": False, "validation": vres}
        xml = self.build_xml()
        html = self.build_html()
        manifest = self.build_manifest(xml)
        out: Dict[str, Any] = {
            "ok": True,
            "xml": xml,
            "html": html,
            "manifest": manifest,
            "validation": vres,
        }
        if with_pdf:
            out["pdf"] = self.build_pdf()
        return out


_HTML_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>ECB Cyber Supervisory Submission — {{ bank }}</title>
<style>
 body{font-family:Helvetica,Arial,sans-serif;margin:2rem;color:#1a1a1a}
 h1{border-bottom:2px solid #003;padding-bottom:.3rem}
 h2{margin-top:1.6rem;color:#003}
 table{border-collapse:collapse;width:100%;font-size:.85rem}
 td,th{border:1px solid #ccc;padding:.3rem .5rem;text-align:left}
 .meta{color:#555;font-size:.8rem}
 .warn{color:#a33}
</style></head><body>
<h1>ECB Cyber Action Plan — Supervisory Submission</h1>
<p class="meta">Submission ID: {{ submission_id }} | Institution: {{ bank }}
 | As of: {{ as_of }} | Generated: {{ generated_at }}</p>
<p class="meta">Schema: {{ schema_version }} | Policy: {{ policy_version }}
 | Readiness score: {{ readiness_score }}</p>

<h2>1. Executive Summary</h2>
<p>This artefact packages existing governed evidence (VAIG evaluations, REHT
clearances, RACS receipts). It asserts no regulatory approval and no
acceptance by the ECB.</p>

<h2>2. Institution &amp; Submission Metadata</h2>
<table><tr><th>Field</th><th>Value</th></tr>
<tr><td>Bank</td><td>{{ bank }}</td></tr>
<tr><td>As of</td><td>{{ as_of }}</td></tr>
<tr><td>Readiness score</td><td>{{ readiness_score }}</td></tr>
<tr><td>Evidence count</td><td>{{ evidence_count }}</td></tr>
<tr><td>Unresolved gaps</td><td>{{ unresolved_gap_count }}</td></tr>
<tr><td>Stale assessments (&gt;180d)</td><td>{{ stale_assessment_count }}</td></tr>
</table>

<h2>3. Submission Readiness</h2>
<p>Readiness score {{ readiness_score }} (derived from effective controls).</p>

<h2>4. Regulatory Scope</h2>
<table><tr><th>ID</th><th>Framework</th><th>Article</th><th>Owner</th><th>Text</th></tr>
{% for r in requirements %}<tr><td>{{ r.requirement_id }}</td><td>{{ r.framework.value if r.framework.value is defined else r.framework }}</td><td>{{ r.article_ref }}</td><td>{{ r.owner_role }}</td><td>{{ r.text }}</td></tr>{% endfor %}
</table>

<h2>5. Controls &amp; Assessments</h2>
<table><tr><th>Control</th><th>Name</th><th>State</th><th>Effective</th></tr>
{% for c in controls %}<tr><td>{{ c.control_id }}</td><td>{{ c.name }}</td>
<td>{{ (assessments_map.get(c.control_id).state) if assessments_map.get(c.control_id) else 'n/a' }}</td>
<td>{{ (assessments_map.get(c.control_id).effective) if assessments_map.get(c.control_id) else 'n/a' }}</td></tr>{% endfor %}
</table>

<h2>6. Accountable Owners</h2>
<table><tr><th>ID</th><th>Name</th><th>Role</th><th>Dept</th></tr>
{% for o in owners %}<tr><td>{{ o.owner_id }}</td><td>{{ o.name }}</td><td>{{ o.role }}</td><td>{{ o.department }}</td></tr>{% endfor %}
</table>

<h2>7. Mitigation Actions &amp; Milestones</h2>
<table><tr><th>ID</th><th>Title</th><th>Status</th><th>Milestones</th></tr>
{% for m in actions %}<tr><td>{{ m.action_id }}</td><td>{{ m.title }}</td><td>{{ m.status }}</td>
<td>{% for ms in m.milestones %}{{ ms.due.isoformat() }} [{{ ms.status }}]; {% endfor %}</td></tr>{% endfor %}
</table>

<h2>8. Threat Observations</h2>
<table><tr><th>ID</th><th>Type</th><th>Severity</th><th>CVSS</th></tr>
{% for t in threats %}<tr><td>{{ t.observation_id }}</td><td>{{ t.threat_type }}</td>
<td>{{ t.severity.value if t.severity.value is defined else t.severity }}</td><td>{{ t.cvss or '' }}</td></tr>{% endfor %}
</table>

<h2>9. Approvals</h2>
<table><tr><th>ID</th><th>Action</th><th>Level</th><th>Decision</th></tr>
{% for a in approvals %}<tr><td>{{ a.approval_id }}</td><td>{{ a.action_id }}</td>
<td>{{ a.level.value if a.level.value is defined else a.level }}</td>
<td>{{ a.decided.value if a.decided.value is defined else a.decided }}</td></tr>{% endfor %}
</table>

<h2>10. Exceptions</h2>
<table><tr><th>ID</th><th>Control</th><th>Reason</th><th>Expires</th></tr>
{% for x in exceptions %}<tr><td>{{ x.exception_id }}</td><td>{{ x.control_id }}</td><td>{{ x.reason }}</td><td>{{ x.expires.isoformat() }}</td></tr>{% endfor %}
</table>

<h2>11. Unresolved Gaps</h2>
<ul>{% for g in gaps %}<li>{{ g }}</li>{% endfor %}</ul>

<h2>12. Governance Clearance &amp; Receipt References</h2>
<p>Receipts: {{ receipt_refs|join(', ') or 'none' }}</p>
<p>Clearance refs: {{ clearance_refs|join(', ') or 'none' }}</p>

<h2>13. Limitations &amp; Declarations</h2>
<p class="warn">Generated from existing governed evidence. This artefact is a
packaging of records already produced by VAIG/REHT/RACS. It asserts no
regulatory approval and no acceptance by the ECB. Submission acceptance is
determined solely by the competent authority.</p>
</body></html>"""
