"""
VAIG Agent Loop Boundary — Execution Boundary Controller

Sits at the boundary of every agent loop iteration.
Not a post-hoc filter. The gate through which all actions
must pass BEFORE execution.

Integrates with VAIG core via:
- Shared WORM audit log (append-only, hash-chained)
- Compatible receipt format with VAIG L5 receipts
- AARM decision mapping (ALLOW→PASS, STEP_UP→DEFER, etc.)

Every iteration produces:
1. Risk assessment (composite score)
2. Drift signals (gradual degradation detection)
3. Boundary decision (PASS/DEFER/HALT/DEGRADE)
4. Attestation receipt (WORM-compatible)

Receipts are pushed to VAIG WORM log for unified audit.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import uuid
from datetime import datetime, timezone

from .risk_engine import RiskEngine, RiskLevel, RiskAssessment
from .drift_detector import DriftDetector, DriftSignal, DriftSeverity
from .evidence_gap import EvidenceGapAnalyzer
from .authority import AuthorityChecker


class BoundaryDecision(Enum):
    """Execution boundary decisions."""
    PASS = "PASS"           # Continue execution
    DEFER = "DEFER"         # Pause, gather more evidence
    HALT = "HALT"           # Stop immediately
    DEGRADE = "DEGRADE"     # Continue with reduced capability


@dataclass
class BoundaryReceipt:
    """WORM-compatible receipt for boundary decision."""
    receipt_id: str
    timestamp: str
    iteration: int
    intent_hash: str
    evidence_hash: str
    risk_level: str
    risk_score: float
    drift_signals: List[Dict[str, Any]]
    evidence_gap: float
    authority_valid: bool
    decision: str
    reason: str
    prior_hash: Optional[str] = None
    receipt_hash: Optional[str] = None

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of receipt contents."""
        data = {
            "receipt_id": self.receipt_id,
            "timestamp": self.timestamp,
            "iteration": self.iteration,
            "intent_hash": self.intent_hash,
            "evidence_hash": self.evidence_hash,
            "risk_level": self.risk_level,
            "risk_score": self.risk_score,
            "drift_signals": self.drift_signals,
            "evidence_gap": self.evidence_gap,
            "authority_valid": self.authority_valid,
            "decision": self.decision,
            "reason": self.reason,
            "prior_hash": self.prior_hash,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "timestamp": self.timestamp,
            "iteration": self.iteration,
            "intent_hash": self.intent_hash,
            "evidence_hash": self.evidence_hash,
            "risk_level": self.risk_level,
            "risk_score": self.risk_score,
            "drift_signals": self.drift_signals,
            "evidence_gap": self.evidence_gap,
            "authority_valid": self.authority_valid,
            "decision": self.decision,
            "reason": self.reason,
            "prior_hash": self.prior_hash,
            "receipt_hash": self.receipt_hash,
        }


@dataclass
class BoundaryResult:
    """Result of boundary check."""
    decision: BoundaryDecision
    reason: str
    receipt: BoundaryReceipt
    risk_assessment: RiskAssessment
    drift_signals: List[DriftSignal]
    evidence_gap: float
    authority_valid: bool

    @property
    def allowed(self) -> bool:
        return self.decision in (BoundaryDecision.PASS, BoundaryDecision.DEGRADE)

    @property
    def requires_human(self) -> bool:
        return self.decision == BoundaryDecision.DEFER

    @property
    def halted(self) -> bool:
        return self.decision == BoundaryDecision.HALT


class ExecutionBoundary:
    """
    VAIG Agent Loop Execution Boundary.

    Checks every agent loop iteration before execution:
    - Risk assessment
    - Drift detection
    - Evidence gap
    - Authority mismatch

    Produces WORM-compatible receipts.
    """

    def __init__(
        self,
        risk_config: Optional[Dict[str, Any]] = None,
        drift_config: Optional[Dict[str, Any]] = None,
        authority_config: Optional[Dict[str, Any]] = None,
        worm_log: Optional[Any] = None,
    ):
        self.risk_engine = RiskEngine(risk_config or {})
        self.drift_detector = DriftDetector(drift_config or {})
        self.evidence_gap = EvidenceGapAnalyzer()
        self.authority = AuthorityChecker(authority_config or {})
        self.worm_log = worm_log
        self.iteration_count = 0
        self.prior_receipt_hash: Optional[str] = None
        self.history: List[Dict[str, Any]] = []

    def check(
        self,
        intent: Dict[str, Any],
        evidence: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> BoundaryResult:
        """
        Check if agent action should proceed.

        Args:
            intent: What the agent intends to do
            evidence: Evidence supporting the action
            context: Current loop context

        Returns:
            BoundaryResult with decision and receipt
        """
        context = context or {}
        self.iteration_count += 1

        risk = self.risk_engine.assess(intent, evidence, context)
        drift_signals = self.drift_detector.detect(intent, evidence, context, self.history)
        gap = self.evidence_gap.calculate(intent, evidence)
        authority_valid, authority_reason = self.authority.check(intent, context)

        decision, reason = self._decide(risk, drift_signals, gap, authority_valid, authority_reason)

        receipt = self._create_receipt(
            intent=intent,
            evidence=evidence,
            risk=risk,
            drift_signals=drift_signals,
            evidence_gap=gap,
            authority_valid=authority_valid,
            decision=decision,
            reason=reason,
        )

        self.history.append({
            "iteration": self.iteration_count,
            "intent": intent,
            "evidence": evidence,
            "risk_level": risk.level.value,
            "decision": decision.value,
            "receipt_hash": receipt.receipt_hash,
        })

        if self.worm_log is not None:
            self._write_to_worm(receipt)

        return BoundaryResult(
            decision=decision,
            reason=reason,
            receipt=receipt,
            risk_assessment=risk,
            drift_signals=drift_signals,
            evidence_gap=gap,
            authority_valid=authority_valid,
        )

    def _decide(
        self,
        risk: RiskAssessment,
        drift_signals: List[DriftSignal],
        evidence_gap: float,
        authority_valid: bool,
        authority_reason: str,
    ) -> tuple[BoundaryDecision, str]:
        """Decision logic."""

        if not authority_valid:
            return BoundaryDecision.HALT, f"Authority mismatch: {authority_reason}"

        critical_drifts = [s for s in drift_signals if s.severity == DriftSeverity.CRITICAL]
        if critical_drifts:
            return BoundaryDecision.HALT, f"Critical drift detected: {critical_drifts[0].reason}"

        if risk.level == RiskLevel.CRITICAL:
            return BoundaryDecision.HALT, f"Critical risk: {risk.reason}"

        if evidence_gap > 0.7:
            return BoundaryDecision.DEFER, f"Evidence gap too high: {evidence_gap:.2f}"

        if risk.level == RiskLevel.HIGH:
            return BoundaryDecision.DEFER, f"High risk requires review: {risk.reason}"

        warning_drifts = [s for s in drift_signals if s.severity == DriftSeverity.WARNING]
        if warning_drifts:
            return BoundaryDecision.DEFER, f"Drift warning: {warning_drifts[0].reason}"

        if 0.4 < evidence_gap <= 0.7:
            return BoundaryDecision.DEGRADE, f"Moderate evidence gap: {evidence_gap:.2f}"

        return BoundaryDecision.PASS, "Boundary check passed"

    def _create_receipt(
        self,
        intent: Dict[str, Any],
        evidence: Dict[str, Any],
        risk: RiskAssessment,
        drift_signals: List[DriftSignal],
        evidence_gap: float,
        authority_valid: bool,
        decision: BoundaryDecision,
        reason: str,
    ) -> BoundaryReceipt:
        """Create WORM-compatible receipt."""
        intent_hash = hashlib.sha256(json.dumps(intent, sort_keys=True).encode()).hexdigest()
        evidence_hash = hashlib.sha256(json.dumps(evidence, sort_keys=True).encode()).hexdigest()

        receipt = BoundaryReceipt(
            receipt_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            iteration=self.iteration_count,
            intent_hash=intent_hash,
            evidence_hash=evidence_hash,
            risk_level=risk.level.value,
            risk_score=risk.score,
            drift_signals=[s.to_dict() for s in drift_signals],
            evidence_gap=evidence_gap,
            authority_valid=authority_valid,
            decision=decision.value,
            reason=reason,
            prior_hash=self.prior_receipt_hash,
        )
        receipt.receipt_hash = receipt.compute_hash()
        self.prior_receipt_hash = receipt.receipt_hash
        return receipt

    def _write_to_worm(self, receipt: BoundaryReceipt) -> None:
        """Write receipt to WORM log if available."""
        if hasattr(self.worm_log, "append"):
            self.worm_log.append(receipt.to_dict())
        elif hasattr(self.worm_log, "write"):
            self.worm_log.write(receipt.to_dict())

    def reset(self) -> None:
        """Reset boundary state."""
        self.iteration_count = 0
        self.prior_receipt_hash = None
        self.history = []
        self.drift_detector.reset()
