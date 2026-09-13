"""
VΛLΦ ROI Gate v0.1

Pre-execution value gate: "Is this action worth doing before the agent does it?"
Blocks bad ideas early by comparing estimated cost vs. expected value.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, List
from decimal import Decimal
import hashlib
from datetime import datetime, timezone


def _utcnow() -> datetime:
    """Return naive UTC for compatibility with persisted legacy timestamps."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ROIDecision(str, Enum):
    """Standard decision vocabulary (shared with ACS/VACS)."""
    ALLOW = "ALLOW"
    STEP_UP = "STEP_UP"  # Requires human review before execution
    DEFER = "DEFER"  # Wait for better conditions
    DENY = "DENY"  # Block this action
    HALT = "HALT"  # Emergency stop (override, system failure)


@dataclass
class CostEstimate:
    """Pre-execution cost breakdown."""
    tokens_prompt: int = 0
    tokens_completion: int = 0
    compute_seconds: float = 0.0
    api_calls: int = 0
    human_review_minutes: float = 0.0

    @property
    def compute_cost(self) -> Decimal:
        """Estimated compute cost in USD."""
        # Token costs: $0.003/1k prompt, $0.006/1k completion
        # Compute: $0.10/GPU-hour
        token_cost = (self.tokens_prompt * 0.000003) + (self.tokens_completion * 0.000006)
        compute = self.compute_seconds * (0.10 / 3600)  # Per-second rate
        return Decimal(str(token_cost + compute))

    @property
    def human_cost(self) -> Decimal:
        """Estimated human review cost in USD."""
        # $100/hour for professional review
        return Decimal(str(self.human_review_minutes * (100 / 60)))

    @property
    def total_cost(self) -> Decimal:
        return self.compute_cost + self.human_cost

    def to_dict(self) -> Dict:
        return {
            "tokens_prompt": self.tokens_prompt,
            "tokens_completion": self.tokens_completion,
            "compute_seconds": self.compute_seconds,
            "api_calls": self.api_calls,
            "human_review_minutes": self.human_review_minutes,
            "compute_cost_usd": float(self.compute_cost),
            "human_cost_usd": float(self.human_cost),
            "total_cost_usd": float(self.total_cost),
        }


@dataclass
class ValueEstimate:
    """Post-execution expected value."""
    revenue: Decimal = Decimal("0")  # Direct revenue from this action
    saved_labor_hours: float = 0.0  # Labor hours saved
    risk_reduction: Decimal = Decimal("0")  # Avoided risk/loss
    strategic_value: Decimal = Decimal("0")  # Long-term strategic value

    @property
    def saved_labor_cost(self) -> Decimal:
        """Monetary value of labor saved."""
        return Decimal(str(self.saved_labor_hours * 100))  # $100/hour rate

    @property
    def total_value(self) -> Decimal:
        return self.revenue + self.saved_labor_cost + self.risk_reduction + self.strategic_value

    def to_dict(self) -> Dict:
        return {
            "revenue": float(self.revenue),
            "saved_labor_hours": self.saved_labor_hours,
            "saved_labor_cost": float(self.saved_labor_cost),
            "risk_reduction": float(self.risk_reduction),
            "strategic_value": float(self.strategic_value),
            "total_value": float(self.total_value),
        }


@dataclass
class ROIPolicy:
    """Policy constraints for ROI Gate decisions."""
    min_roi_ratio: Decimal = Decimal("2.0")  # Minimum expected value / cost ratio
    max_cost: Decimal = Decimal("100.0")  # Max cost allowed without escalation
    risk_adjustment_factor: Decimal = Decimal("1.0")  # Multiply expected value by this if risk high
    require_human_review_if_roi_below: Decimal = Decimal("5.0")  # Require review if ROI < 5x
    categories: Dict[str, Dict] = None  # Category-specific policies

    def __post_init__(self):
        if self.categories is None:
            self.categories = {
                "routine": {"min_roi": Decimal("1.5"), "max_cost": Decimal("50")},
                "experimental": {"min_roi": Decimal("3.0"), "max_cost": Decimal("200")},
                "critical": {"min_roi": Decimal("5.0"), "max_cost": Decimal("10")},
            }

    def get_category_policy(self, category: str) -> Dict:
        return self.categories.get(category, self.categories["routine"])


@dataclass
class ROIRequest:
    """Request to evaluate ROI before execution."""
    action_id: str
    category: str = "routine"  # routine, experimental, critical
    cost_estimate: CostEstimate = None
    value_estimate: ValueEstimate = None
    risk_level: str = "low"  # low, medium, high
    decision_deadline: Optional[datetime] = None

    def __post_init__(self):
        if self.cost_estimate is None:
            self.cost_estimate = CostEstimate()
        if self.value_estimate is None:
            self.value_estimate = ValueEstimate()


@dataclass
class ROIEstimate:
    """ROI calculation result."""
    decision: ROIDecision
    roi_ratio: Decimal
    confidence: str  # "claimed", "estimated", "observed"
    rationale: str
    estimated_value: Decimal
    estimated_cost: Decimal
    risk_adjustment: Decimal
    net_expected_value: Decimal
    requires_escalation: bool = False
    policy_violated: Optional[str] = None
    hash: str = ""  # SHA256 of this estimate
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = _utcnow()
        if not self.hash:
            self.hash = self.compute_hash()

    def compute_hash(self) -> str:
        """Compute SHA256 of this estimate for audit trail."""
        data = f"{self.decision.value}{self.roi_ratio}{self.estimated_value}{self.timestamp.isoformat()}".encode()
        return hashlib.sha256(data).hexdigest()

    def to_dict(self) -> Dict:
        return {
            "decision": self.decision.value,
            "roi_ratio": float(self.roi_ratio),
            "confidence": self.confidence,
            "rationale": self.rationale,
            "estimated_value": float(self.estimated_value),
            "estimated_cost": float(self.estimated_cost),
            "risk_adjustment": float(self.risk_adjustment),
            "net_expected_value": float(self.net_expected_value),
            "requires_escalation": self.requires_escalation,
            "policy_violated": self.policy_violated,
            "hash": self.hash,
            "timestamp": self.timestamp.isoformat(),
        }


class ROIGate:
    """VΛLΦ ROI Gate: Pre-execution value verification."""

    def __init__(self, policy: ROIPolicy = None):
        self.policy = policy or ROIPolicy()
        self.decision_log: List[ROIEstimate] = []

    def evaluate(self, request: ROIRequest) -> ROIEstimate:
        """
        Evaluate whether an action is worth executing based on ROI.

        Returns:
            ROIEstimate with decision and rationale
        """
        cost = request.cost_estimate.total_cost
        value = request.value_estimate.total_value

        # Apply risk adjustment
        risk_multiplier = self._get_risk_multiplier(request.risk_level)
        adjusted_value = value * Decimal(str(risk_multiplier))

        # Calculate ROI ratio
        if cost == 0:
            roi_ratio = Decimal("999")  # Cost-free actions get max ROI
        else:
            roi_ratio = adjusted_value / cost

        net_value = adjusted_value - cost

        # Get category policy
        category_policy = self.policy.get_category_policy(request.category)

        # Determine decision
        decision, policy_violated, rationale = self._decide(
            roi_ratio=roi_ratio,
            cost=cost,
            net_value=net_value,
            category_policy=category_policy,
            request=request
        )

        # Determine if escalation needed
        escalate = (
            decision == ROIDecision.STEP_UP or
            roi_ratio < self.policy.require_human_review_if_roi_below or
            cost > self.policy.max_cost
        )

        # Build result
        estimate = ROIEstimate(
            decision=decision,
            roi_ratio=roi_ratio,
            confidence="estimated",  # Will become "observed" after execution
            rationale=rationale,
            estimated_value=adjusted_value,
            estimated_cost=cost,
            risk_adjustment=Decimal(str(risk_multiplier)),
            net_expected_value=net_value,
            requires_escalation=escalate,
            policy_violated=policy_violated,
        )

        # Log for audit trail
        self.decision_log.append(estimate)

        return estimate

    def _get_risk_multiplier(self, risk_level: str) -> float:
        """Risk adjustment multiplier (lower risk = higher expected value)."""
        multipliers = {
            "low": 1.0,
            "medium": 0.7,
            "high": 0.4,
        }
        return multipliers.get(risk_level, 1.0)

    def _decide(self, roi_ratio: Decimal, cost: Decimal, net_value: Decimal,
                category_policy: Dict, request: ROIRequest) -> tuple:
        """Decide action based on ROI ratio and policy."""

        min_roi = Decimal(str(category_policy["min_roi"]))
        max_cost = Decimal(str(category_policy["max_cost"]))

        # Check minimum ROI
        if roi_ratio < min_roi:
            return (
                ROIDecision.DENY,
                f"ROI {roi_ratio:.2f}x below minimum {min_roi:.2f}x",
                f"Expected value ${net_value:.2f} does not justify cost"
            )

        # Check max cost without escalation
        if cost > max_cost:
            return (
                ROIDecision.STEP_UP,
                f"Cost ${cost:.2f} exceeds category max ${max_cost:.2f}",
                f"Requires human approval for high-cost action"
            )

        # Check if escalation needed for borderline ROI
        if roi_ratio < self.policy.require_human_review_if_roi_below:
            return (
                ROIDecision.STEP_UP,
                f"ROI {roi_ratio:.2f}x below escalation threshold",
                f"Close call: requires human judgment (net value: ${net_value:.2f})"
            )

        # All checks pass
        return (
            ROIDecision.ALLOW,
            None,
            f"ROI {roi_ratio:.2f}x exceeds minimum {min_roi:.2f}x (net value: ${net_value:.2f})"
        )

    def get_decision_log(self) -> List[Dict]:
        """Retrieve audit log of all ROI decisions."""
        return [e.to_dict() for e in self.decision_log]


# Example usage
if __name__ == "__main__":
    policy = ROIPolicy(
        min_roi_ratio=Decimal("2.0"),
        require_human_review_if_roi_below=Decimal("5.0"),
    )
    gate = ROIGate(policy)

    # Scenario: Should we run a customer support chatbot?
    request = ROIRequest(
        action_id="support-chatbot-run",
        category="routine",
        cost_estimate=CostEstimate(
            tokens_prompt=10000,
            tokens_completion=5000,
            compute_seconds=30,
            human_review_minutes=0,
        ),
        value_estimate=ValueEstimate(
            revenue=Decimal("500"),  # $500 in subscriptions
            saved_labor_hours=8,  # 8 hours of support time
            risk_reduction=Decimal("200"),  # Avoid 2 escalations worth $200
        ),
        risk_level="low"
    )

    result = gate.evaluate(request)
    print(f"Decision: {result.decision.value}")
    print(f"ROI: {result.roi_ratio:.2f}x")
    print(f"Net Expected Value: ${result.net_expected_value:.2f}")
    print(f"Rationale: {result.rationale}")
    print(f"Requires Escalation: {result.requires_escalation}")
