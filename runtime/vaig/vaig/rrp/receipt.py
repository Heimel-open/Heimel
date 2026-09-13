"""
Receipt — Unified Chain-of-Custody with RiskContract trace.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class Receipt:
    receipt_id: str
    created_at: str

    evidence_condition_id: str
    evidence_condition_snapshot: Dict[str, Any]
    risk_contract_snapshot: Dict[str, Any]

    intent_id: str
    intent_snapshot: Dict[str, Any]

    vaig_outcome: str
    vaig_rule_triggered: Optional[str]
    vaig_rationale: Optional[str]

    refusal_id: Optional[str]
    refusal_snapshot: Optional[Dict[str, Any]]
    uncertainty_inventory_id: Optional[str]
    authority_assignment_id: Optional[str]

    accountability_thread_id: str
    thread_snapshot: Dict[str, Any]

    final_status: str
    closed_at: Optional[str] = None

    # --- end Receipts v4 fields ---

    # --- Reflection metadata (Reflective Inquiry) ---
    reflection_outcome: Optional[str] = None
    """Outcome of the reflective inquiry layer (STEP_UP, DEFER, HALT)."""

    reflection_trace: Optional[List[str]] = None
    """Sequential log of reasoning steps during reflection."""

    evidence_gaps: Optional[List[Dict[str, Any]]] = None
    """Evidence gaps identified during reflection."""

    policy_ambiguities: Optional[List[Dict[str, Any]]] = None
    """Policy ambiguities identified during reflection."""

    confidence_score: Optional[float] = None
    """Calibrated confidence score from reflection (0.0–1.0)."""

    epistemic_uncertainty: Optional[float] = None
    """Epistemic uncertainty assessed during reflection (0.0–1.0)."""

    sage_referral: Optional[Dict[str, Any]] = None
    """SAGE handoff metadata generated from policy ambiguity detection."""
    # --- end Reflection metadata ---

    def to_dict(self):
        return asdict(self)


class ReceiptFactory:
    @staticmethod
    def create(
        receipt_id: str,
        evidence_condition_id: str,
        evidence_condition_snapshot: Dict[str, Any],
        intent_id: str,
        intent_snapshot: Dict[str, Any],
        vaig_outcome: str,
        vaig_rule_triggered: Optional[str],
        vaig_rationale: Optional[str],
        accountability_thread_id: str,
        thread_snapshot: Dict[str, Any],
        refusal_id: Optional[str] = None,
        refusal_snapshot: Optional[Dict[str, Any]] = None,
        uncertainty_inventory_id: Optional[str] = None,
        authority_assignment_id: Optional[str] = None,
        final_status: str = "EXECUTED",
        risk_contract_snapshot: Optional[Dict[str, Any]] = None,
    ) -> Receipt:
        return Receipt(
            receipt_id=receipt_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            evidence_condition_id=evidence_condition_id,
            evidence_condition_snapshot=evidence_condition_snapshot,
            risk_contract_snapshot=risk_contract_snapshot or {},
            intent_id=intent_id,
            intent_snapshot=intent_snapshot,
            vaig_outcome=vaig_outcome,
            vaig_rule_triggered=vaig_rule_triggered,
            vaig_rationale=vaig_rationale,
            refusal_id=refusal_id,
            refusal_snapshot=refusal_snapshot,
            uncertainty_inventory_id=uncertainty_inventory_id,
            authority_assignment_id=authority_assignment_id,
            accountability_thread_id=accountability_thread_id,
            thread_snapshot=thread_snapshot,
            final_status=final_status,
        )
