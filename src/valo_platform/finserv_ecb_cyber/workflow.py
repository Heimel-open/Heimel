"""Workflow — ECB Cyber Action Plan approval / exception / clearance flow (#218).

Composes the governed evidence chain for the ECB Cyber profile:

    ThreatObservation / ControlAssessment gap
      -> VAIG evaluation  (CyberEvaluation — risk signal, NOT authority)
      -> REHT clearance    (canonical GovernanceClearance — sole admissibility)
      -> Approval          (human delegate signs off)
      -> Receipt           (canonical RACS-compatible Receipt, WORM-chained)

Authority boundary (per architecture, and enforced by the #422 repair):
- VAIG evaluates  -> CyberEvaluation
- REHT clears     -> action_envelope.models.GovernanceClearance (CANONICAL, reused)
- No second competing clearance contract exists here.

Design: Index DESIGN.md §3 / §6. Reuses, never redefines, the canonical
GovernanceClearance / Receipt / RehtAdmissibilityEngine.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.valo_platform.action_envelope.models import (
    ActionDecision,
    ClearanceState,
    GovernanceClearance,
)
from src.valo_platform.finserv.ecb_cyber.models import (
    Approval,
    ControlException,
    CyberEvaluation,
)
from src.valo_platform.models.core_receipt import (
    ExecutionDecision,
    Receipt,
    ReceiptType,
)
from src.valo_platform.reht_admissibility_engine import (
    AdmissibilityVerdict,
    GovernanceBundle,
    ObserverSignal,
    RehtAdmissibilityEngine,
    SignalDisposition,
)


# VAIG/REHT verdict -> canonical ActionDecision used by GovernanceClearance
_VERDICT_TO_DECISION = {
    AdmissibilityVerdict.ADMIT: ActionDecision.ALLOW,
    AdmissibilityVerdict.ADMIT_WITH_CONDITIONS: ActionDecision.ALLOW,
    AdmissibilityVerdict.DEFER: ActionDecision.DEFER,
    AdmissibilityVerdict.DENY: ActionDecision.HALT,
}


class EcbCyberWorkflow:
    """Drives approval / exception / clearance for the ECB Cyber profile."""

    def __init__(self, reht_engine: Optional[RehtAdmissibilityEngine] = None) -> None:
        self.reht = reht_engine or RehtAdmissibilityEngine()

    def evaluate_action(
        self,
        *,
        action_id: str,
        tenant_id: str,
        signals: List[Dict[str, Any]],
        risk_tier: str,
        authority: str,
        human_delegate: Optional[str] = None,
        policy_id: Optional[str] = None,
    ) -> CyberEvaluation:
        """VAIG side: synthesise a CyberEvaluation risk signal from evidence.

        This is a risk signal ONLY. It confers no authority.
        """
        conf = sum(float(s.get("confidence", 0.0)) for s in signals) / max(len(signals), 1)
        return CyberEvaluation(
            decision_id=f"eval-{action_id}",
            action_id=action_id,
            signal_summary={"signals": signals, "risk_tier": risk_tier},
            risk_tier=risk_tier,
            confidence=min(conf, 1.0),
            recommended_disposition="step_up" if risk_tier in ("HIGH", "CRITICAL") else "allow",
        )

    def clear_action(
        self,
        *,
        action_id: str,
        tenant_id: str,
        evaluation: CyberEvaluation,
        authority: str,
        evidence_refs: Optional[List[str]] = None,
        valid_until: Optional[datetime] = None,
        policy_id: Optional[str] = None,
        human_delegate: Optional[str] = None,
    ) -> GovernanceClearance:
        """REHT side: produce the canonical GovernanceClearance (sole authority).

        Fuses the VAIG CyberEvaluation into a GovernanceBundle and lets the
        RehtAdmissibilityEngine decide. The resulting verdict is mapped to the
        canonical ActionDecision and recorded in the canonical clearance.
        """
        # Map VAIG signal dicts into the REHT ObserverSignal contract
        observer_signals = [
            ObserverSignal(
                source=s.get("source", "vaig"),
                disposition=(
                    SignalDisposition.ESCALATE
                    if evaluation.risk_tier in ("HIGH", "CRITICAL")
                    else SignalDisposition.BLOCK
                ),
                confidence=float(s.get("confidence", 0.5)),
                severity=evaluation.risk_tier.lower(),
                detail=str(s),
                risk=float(s.get("confidence", 0.5)),
            )
            for s in evaluation.signal_summary.get("signals", [])
        ]

        bundle = GovernanceBundle(
            action_id=action_id,
            proposed_action={"type": "ecb_cyber_mitigation", "action_id": action_id},
            authority=authority,
            policy_id=policy_id,
            human_delegate=human_delegate,
            signals=observer_signals,
            risk_tier=evaluation.risk_tier,
        )
        adm = self.reht.decide(bundle)
        decision = _VERDICT_TO_DECISION.get(adm.verdict, ActionDecision.HALT)
        return GovernanceClearance(
            clearance_id=f"clr-{action_id}",
            action_id=action_id,
            tenant_id=tenant_id,
            decision=decision,
            state=ClearanceState.ACTIVE,
            authority_refs=[authority],
            evidence_refs=evidence_refs or [],
            valid_until=valid_until or datetime(2026, 10, 31, tzinfo=timezone.utc),
            evaluator_refs=["VAIG", "REHT"],
            receipt_ref=None,
        )

    def record_approval(self, approval: Approval, clearance: GovernanceClearance) -> Receipt:
        """Human delegate approval -> canonical Receipt (WORM-chained)."""
        return Receipt(
            request_id=approval.action_id,
            decision=ExecutionDecision(clearance.decision.value),
            actor_id=approval.approved_by,
            actor_role=approval.level.value if approval.level else "approver",
            action_id=approval.action_id,
            evidence_ids=clearance.evidence_refs,
            regulatory_frameworks=["dora", "ecb"],
            compliance_status="COMPLIANT",
            decision_context=f"ECB Cyber approval ({approval.level.value})",
        )

    def record_exception(self, exception: ControlException) -> Receipt:
        """Granted control exception -> canonical Receipt (audit trail)."""
        return Receipt(
            request_id=exception.control_id,
            decision=ExecutionDecision.MODIFY,
            actor_id=exception.approved_by,
            actor_role="control_owner",
            action_id=exception.control_id,
            evidence_ids=[exception.receipt_signature],
            regulatory_frameworks=["dora", "ecb"],
            compliance_status="ESCALATED",
            decision_context=f"ECB Cyber control exception ({exception.reason})",
            receipt_type=ReceiptType.POLICY_ENFORCEMENT,
        )
