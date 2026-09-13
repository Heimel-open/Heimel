"""
VΛLΦ Spend Gate v0.1

Budget enforcement: "Do we have budget remaining for this action?"
Prevents overspending by tracking allocation, usage, and forecasting.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List
from decimal import Decimal
import hashlib
from datetime import datetime, timedelta, timezone


def _utcnow() -> datetime:
    """Return naive UTC for compatibility with persisted legacy timestamps."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class SpendDecision(str, Enum):
    """Standard decision vocabulary (shared with ACS/VACS)."""
    ALLOW = "ALLOW"
    STEP_UP = "STEP_UP"  # Requires approval to exceed budget
    DEFER = "DEFER"  # Wait for budget refresh
    DENY = "DENY"  # Budget exhausted
    HALT = "HALT"  # Spend system failure


class BudgetPeriod(str, Enum):
    """Budget cycle types."""
    HOURLY = "HOURLY"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    ANNUAL = "ANNUAL"
    UNLIMITED = "UNLIMITED"


@dataclass
class BudgetAllocation:
    """Budget allocation for a principal."""
    principal_id: str  # User, team, or agent identifier
    period: BudgetPeriod
    total_usd: Decimal
    start_date: datetime
    end_date: Optional[datetime] = None  # None if recurring

    @property
    def is_active(self) -> bool:
        now = _utcnow()
        return self.start_date <= now and (self.end_date is None or now < self.end_date)

    @property
    def days_remaining(self) -> int:
        if self.end_date is None:
            return 999
        delta = self.end_date - _utcnow()
        return max(0, delta.days)

    def to_dict(self) -> Dict:
        return {
            "principal_id": self.principal_id,
            "period": self.period.value,
            "total_usd": float(self.total_usd),
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "is_active": self.is_active,
            "days_remaining": self.days_remaining,
        }


@dataclass
class SpendRecord:
    """Individual spend transaction."""
    transaction_id: str
    principal_id: str
    amount_usd: Decimal
    category: str  # "compute", "api_calls", "human_review", etc
    reason: str  # Action/request that triggered spend
    timestamp: datetime = field(default_factory=_utcnow)
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "transaction_id": self.transaction_id,
            "principal_id": self.principal_id,
            "amount_usd": float(self.amount_usd),
            "category": self.category,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class BudgetState:
    """Current budget state for a principal."""
    allocation: BudgetAllocation
    spent: Decimal = Decimal("0")
    committed: Decimal = Decimal("0")  # Pre-authorized but not yet spent
    available: Decimal = Decimal("0")
    forecast_30d: Decimal = Decimal("0")  # Projected spend in next 30 days
    utilization_pct: float = 0.0  # Percentage of budget used

    def recalculate(self):
        """Recalculate available budget."""
        self.available = self.allocation.total_usd - self.spent - self.committed
        total = float(self.allocation.total_usd)
        if total > 0:
            self.utilization_pct = float((self.spent / self.allocation.total_usd) * 100)

    def to_dict(self) -> Dict:
        return {
            "allocation": self.allocation.to_dict(),
            "spent_usd": float(self.spent),
            "committed_usd": float(self.committed),
            "available_usd": float(self.available),
            "forecast_30d_usd": float(self.forecast_30d),
            "utilization_pct": self.utilization_pct,
        }


@dataclass
class SpendPolicy:
    """Policy for spend gating."""
    allow_under_pct: float = 0.80  # Allow all spend if under 80% utilization
    warn_at_pct: float = 0.85  # Warn user at 85%
    step_up_at_pct: float = 0.90  # Require approval at 90%
    deny_at_pct: float = 0.95  # Deny new spend at 95%
    emergency_reserve_pct: float = 0.05  # Always keep 5% as emergency buffer

    forecast_multiplier: float = 1.2  # Assume 20% variance in spending forecast
    allow_overage: bool = False  # If True, allow exceeding budget with approval
    max_overage_pct: float = 0.10  # Max 10% overage if allowed


@dataclass
class SpendRequest:
    """Request to authorize spend."""
    principal_id: str
    amount_usd: Decimal
    category: str = "general"  # compute, api_calls, human_review, storage, etc
    reason: str = ""
    metadata: Dict = field(default_factory=dict)


@dataclass
class SpendGateResult:
    """Spend gating decision result."""
    decision: SpendDecision
    approved_amount: Decimal = Decimal("0")
    denied_amount: Decimal = Decimal("0")
    available_after: Decimal = Decimal("0")
    utilization_pct: float = 0.0
    rationale: str = ""
    recommended_action: str = ""
    requires_escalation: bool = False
    hash: str = ""
    timestamp: datetime = field(default_factory=_utcnow)

    def compute_hash(self) -> str:
        """Compute SHA256 for audit trail."""
        data = f"{self.decision.value}{self.approved_amount}{self.timestamp.isoformat()}".encode()
        return hashlib.sha256(data).hexdigest()

    def __post_init__(self):
        if not self.hash:
            self.hash = self.compute_hash()

    def to_dict(self) -> Dict:
        return {
            "decision": self.decision.value,
            "approved_amount_usd": float(self.approved_amount),
            "denied_amount_usd": float(self.denied_amount),
            "available_after_usd": float(self.available_after),
            "utilization_pct": self.utilization_pct,
            "rationale": self.rationale,
            "requires_escalation": self.requires_escalation,
            "hash": self.hash,
            "timestamp": self.timestamp.isoformat(),
        }


class SpendGate:
    """VΛLΦ Spend Gate: Budget enforcement."""

    def __init__(self, policy: SpendPolicy = None):
        self.policy = policy or SpendPolicy()
        self.allocations: Dict[str, BudgetAllocation] = {}
        self.spend_records: List[SpendRecord] = []
        self.decision_log: List[SpendGateResult] = []

    def authorize(self, request: SpendRequest) -> SpendGateResult:
        """
        Authorize or deny spend based on budget.

        Returns:
            SpendGateResult with decision and available budget
        """
        # Get or create allocation
        if request.principal_id not in self.allocations:
            return SpendGateResult(
                decision=SpendDecision.DENY,
                rationale=f"No budget allocation for {request.principal_id}",
            )

        allocation = self.allocations[request.principal_id]
        if not allocation.is_active:
            return SpendGateResult(
                decision=SpendDecision.DENY,
                rationale=f"Budget allocation expired for {request.principal_id}",
            )

        # Calculate current state
        state = self._get_budget_state(request.principal_id)

        # Determine decision
        decision, rationale, recommended = self._decide(state, request)

        # Calculate available after decision
        available_after = state.available - (request.amount_usd if decision == SpendDecision.ALLOW else Decimal("0"))

        # Build result
        result = SpendGateResult(
            decision=decision,
            approved_amount=request.amount_usd if decision == SpendDecision.ALLOW else Decimal("0"),
            denied_amount=request.amount_usd if decision in [SpendDecision.DENY, SpendDecision.DEFER] else Decimal("0"),
            available_after=max(Decimal("0"), available_after),
            utilization_pct=state.utilization_pct,
            rationale=rationale,
            recommended_action=recommended,
            requires_escalation=(decision in [SpendDecision.STEP_UP, SpendDecision.HALT]),
        )

        # Record if approved
        if decision == SpendDecision.ALLOW:
            record = SpendRecord(
                transaction_id=self._generate_txn_id(),
                principal_id=request.principal_id,
                amount_usd=request.amount_usd,
                category=request.category,
                reason=request.reason,
                metadata=request.metadata,
            )
            self.spend_records.append(record)

        self.decision_log.append(result)
        return result

    def allocate_budget(self, allocation: BudgetAllocation):
        """Register new budget allocation."""
        self.allocations[allocation.principal_id] = allocation

    def refund(self, transaction_id: str):
        """Refund a transaction."""
        for record in self.spend_records:
            if record.transaction_id == transaction_id:
                # Create reverse record
                refund = SpendRecord(
                    transaction_id=f"REFUND_{transaction_id}",
                    principal_id=record.principal_id,
                    amount_usd=-record.amount_usd,
                    category=record.category,
                    reason=f"Refund of {transaction_id}",
                )
                self.spend_records.append(refund)
                return True
        return False

    def _get_budget_state(self, principal_id: str) -> BudgetState:
        """Calculate current budget state."""
        allocation = self.allocations.get(principal_id)
        if not allocation:
            return BudgetState(allocation=None)

        # Sum spending by principal
        spent = sum(
            r.amount_usd for r in self.spend_records
            if r.principal_id == principal_id
        )

        # Calculate forecast (last 7 days × average daily rate)
        seven_days_ago = _utcnow() - timedelta(days=7)
        recent_spend = sum(
            r.amount_usd for r in self.spend_records
            if r.principal_id == principal_id and r.timestamp > seven_days_ago
        )
        daily_avg = recent_spend / Decimal("7") if recent_spend > 0 else Decimal("0")
        forecast = daily_avg * Decimal("30") * Decimal(str(self.policy.forecast_multiplier))

        state = BudgetState(
            allocation=allocation,
            spent=spent,
            forecast_30d=forecast,
        )
        state.recalculate()
        return state

    def _decide(self, state: BudgetState, request: SpendRequest) -> tuple:
        """Decide whether to approve spend."""
        utilization = state.utilization_pct
        emergency_reserve = state.allocation.total_usd * Decimal(str(self.policy.emergency_reserve_pct))
        available_after_spend = state.available - request.amount_usd

        # Check hard deny: no budget
        if state.available <= Decimal("0"):
            return (
                SpendDecision.DENY,
                f"Budget exhausted ({utilization:.1f}% used)",
                "Request budget increase or defer until next period"
            )

        # Check emergency reserve
        if available_after_spend < emergency_reserve:
            return (
                SpendDecision.STEP_UP,
                f"Spend would breach emergency reserve (${emergency_reserve})",
                "Approve only if critical"
            )

        # Check utilization-based thresholds
        if utilization >= self.policy.deny_at_pct * 100:
            return (
                SpendDecision.DENY,
                f"Budget utilization {utilization:.1f}% ≥ {self.policy.deny_at_pct*100:.0f}% hard limit",
                "Request budget increase"
            )

        if utilization >= self.policy.step_up_at_pct * 100:
            return (
                SpendDecision.STEP_UP,
                f"Budget utilization {utilization:.1f}% ≥ {self.policy.step_up_at_pct*100:.0f}% threshold",
                "Requires human approval"
            )

        if utilization >= self.policy.warn_at_pct * 100:
            return (
                SpendDecision.ALLOW,
                f"Warning: Budget utilization {utilization:.1f}% ≥ {self.policy.warn_at_pct*100:.0f}%",
                "Monitor closely"
            )

        # Default allow
        return (
            SpendDecision.ALLOW,
            f"Budget available: ${state.available:.2f} ({100-utilization:.1f}% remaining)",
            ""
        )

    def _generate_txn_id(self) -> str:
        """Generate unique transaction ID."""
        timestamp = _utcnow().isoformat()
        data = f"spend_{timestamp}".encode()
        return hashlib.sha256(data).hexdigest()[:16]

    def get_spend_log(self, principal_id: str) -> List[Dict]:
        """Get spend history for principal."""
        return [
            r.to_dict() for r in self.spend_records
            if r.principal_id == principal_id
        ]

    def get_decision_log(self) -> List[Dict]:
        """Return all decisions as dicts."""
        return [d.to_dict() for d in self.decision_log]
