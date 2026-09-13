"""
VΛLΦ Reward Economy v0.1

EXPERIMENTAL — outside VAIG Core scope; see EXPERIMENTAL.md. Not covered
by TEST_EVIDENCE.md; must not be claimed externally as a VAIG capability.

Learning incentives & token model: "How do we reward efficient execution?"
Allocates VALO Credits based on demonstrated value creation and efficiency.
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


class RewardType(str, Enum):
    """Types of rewards."""
    TOKEN_GRANT = "TOKEN_GRANT"  # VALO Credits earned
    EFFICIENCY_BONUS = "EFFICIENCY_BONUS"  # Bonus for beating expected value
    CONSISTENCY_BONUS = "CONSISTENCY_BONUS"  # Bonus for repeated success
    RISK_REDUCTION = "RISK_REDUCTION"  # Bonus for reducing risk
    COMPLIANCE_BONUS = "COMPLIANCE_BONUS"  # Bonus for meeting governance


class RewardStatus(str, Enum):
    """Reward lifecycle status."""
    PENDING = "PENDING"  # Waiting for confirmation
    GRANTED = "GRANTED"  # Tokens allocated
    VESTED = "VESTED"  # Fully claimed
    REVOKED = "REVOKED"  # Revoked due to negative outcome


@dataclass
class TokenGrant:
    """VALO Credit allocation."""
    grant_id: str
    principal_id: str  # User, team, or agent
    amount_tokens: Decimal
    reward_type: RewardType
    earned_from: str  # Action ID that generated reward
    basis: str  # Description of why earned
    vesting_period_days: int = 30
    grant_date: datetime = field(default_factory=_utcnow)
    vested_date: Optional[datetime] = None
    status: RewardStatus = RewardStatus.PENDING
    metadata: Dict = field(default_factory=dict)

    @property
    def is_vested(self) -> bool:
        if self.status == RewardStatus.VESTED:
            return True
        if self.vesting_period_days == 0:
            return True
        elapsed_days = (_utcnow() - self.grant_date).days
        return elapsed_days >= self.vesting_period_days

    def to_dict(self) -> Dict:
        return {
            "grant_id": self.grant_id,
            "principal_id": self.principal_id,
            "amount_tokens": float(self.amount_tokens),
            "reward_type": self.reward_type.value,
            "earned_from": self.earned_from,
            "basis": self.basis,
            "vesting_period_days": self.vesting_period_days,
            "grant_date": self.grant_date.isoformat(),
            "vested_date": self.vested_date.isoformat() if self.vested_date else None,
            "status": self.status.value,
            "is_vested": self.is_vested,
            "metadata": self.metadata,
        }


@dataclass
class RewardPolicy:
    """Policy for reward allocation."""
    # Base reward multipliers
    base_ves_to_tokens: Decimal = Decimal("100")  # 100 tokens per 1.0x VES
    efficiency_bonus_multiplier: float = 2.0  # 2x tokens if VES > expected
    consistency_bonus_threshold: int = 5  # Grant after N successful actions
    consistency_bonus_amount: Decimal = Decimal("50")

    risk_reduction_value_per_usd: Decimal = Decimal("1.0")  # 1 token per $1 risk prevented
    compliance_bonus_per_check: Decimal = Decimal("10")

    # Token vesting
    default_vesting_days: int = 30
    max_grant_per_action: Decimal = Decimal("1000")  # Cap per action
    daily_grant_limit: Decimal = Decimal("5000")  # Org-wide daily cap

    # Token utility
    tokens_per_usd_cost: Decimal = Decimal("1.0")  # Can spend 1 token per $1 of compute


@dataclass
class RewardCalculation:
    """Reward calculation for an action."""
    action_id: str
    principal_id: str
    ves_ratio: Decimal  # Value / Cost ratio from Efficiency Engine
    expected_ves: Decimal
    actual_value_usd: Decimal
    base_tokens: Decimal
    efficiency_bonus_tokens: Decimal = Decimal("0")
    consistency_bonus_tokens: Decimal = Decimal("0")
    risk_bonus_tokens: Decimal = Decimal("0")
    compliance_bonus_tokens: Decimal = Decimal("0")
    total_tokens: Decimal = field(default_factory=Decimal)
    rationale: str = ""
    vesting_days: int = 30

    def __post_init__(self):
        self.total_tokens = (
            self.base_tokens +
            self.efficiency_bonus_tokens +
            self.consistency_bonus_tokens +
            self.risk_bonus_tokens +
            self.compliance_bonus_tokens
        )

    def to_dict(self) -> Dict:
        return {
            "action_id": self.action_id,
            "principal_id": self.principal_id,
            "ves_ratio": float(self.ves_ratio),
            "expected_ves": float(self.expected_ves),
            "actual_value_usd": float(self.actual_value_usd),
            "base_tokens": float(self.base_tokens),
            "efficiency_bonus_tokens": float(self.efficiency_bonus_tokens),
            "consistency_bonus_tokens": float(self.consistency_bonus_tokens),
            "risk_bonus_tokens": float(self.risk_bonus_tokens),
            "compliance_bonus_tokens": float(self.compliance_bonus_tokens),
            "total_tokens": float(self.total_tokens),
            "rationale": self.rationale,
            "vesting_days": self.vesting_days,
        }


class RewardEconomy:
    """VΛLΦ Reward Economy: Learning incentives & token allocation."""

    def __init__(self, policy: RewardPolicy = None):
        self.policy = policy or RewardPolicy()
        self.grants: Dict[str, TokenGrant] = {}
        self.calculations: List[RewardCalculation] = []
        self.principal_history: Dict[str, List[str]] = {}  # Track action history per principal
        self.daily_granted: Dict[str, Decimal] = {}  # Track daily grant totals
        self.principal_balances: Dict[str, Decimal] = {}  # Token balances

    def calculate_reward(self, action_id: str, principal_id: str,
                        ves_ratio: Decimal, expected_ves: Decimal,
                        actual_value_usd: Decimal,
                        risk_reduced_usd: Decimal = Decimal("0")) -> RewardCalculation:
        """
        Calculate reward tokens for an action.

        Returns:
            RewardCalculation with token amounts and rationale
        """
        # Base reward from VES ratio
        base_tokens = self.policy.base_ves_to_tokens * ves_ratio

        # Efficiency bonus if beat expected
        efficiency_bonus = Decimal("0")
        if ves_ratio > expected_ves:
            efficiency_bonus = base_tokens * Decimal(str(self.policy.efficiency_bonus_multiplier - 1.0))

        # Consistency bonus (after N successful actions)
        consistency_bonus = Decimal("0")
        action_count = len(self.principal_history.get(principal_id, []))
        if action_count >= self.policy.consistency_bonus_threshold:
            consistency_bonus = self.policy.consistency_bonus_amount

        # Risk reduction bonus
        risk_bonus = risk_reduced_usd * self.policy.risk_reduction_value_per_usd

        # Compliance bonus (if applicable)
        compliance_bonus = Decimal("0")
        if "compliance" in str(action_id).lower():
            compliance_bonus = self.policy.compliance_bonus_per_check

        # Calculate total, respecting caps
        total = base_tokens + efficiency_bonus + consistency_bonus + risk_bonus + compliance_bonus
        total = min(total, self.policy.max_grant_per_action)

        # Build calculation record
        calc = RewardCalculation(
            action_id=action_id,
            principal_id=principal_id,
            ves_ratio=ves_ratio,
            expected_ves=expected_ves,
            actual_value_usd=actual_value_usd,
            base_tokens=base_tokens,
            efficiency_bonus_tokens=efficiency_bonus,
            consistency_bonus_tokens=consistency_bonus,
            risk_bonus_tokens=risk_bonus,
            compliance_bonus_tokens=compliance_bonus,
            vesting_days=self.policy.default_vesting_days,
        )

        # Build rationale
        rationale_parts = [f"VES {ves_ratio:.2f}x → {base_tokens:.0f} base tokens"]
        if efficiency_bonus > 0:
            rationale_parts.append(f"beat expected VES by {((ves_ratio/expected_ves - 1)*100):.0f}% → +{efficiency_bonus:.0f} bonus")
        if consistency_bonus > 0:
            rationale_parts.append(f"consistency ({action_count} actions) → +{consistency_bonus:.0f}")
        if risk_bonus > 0:
            rationale_parts.append(f"risk reduction ${risk_reduced_usd} → +{risk_bonus:.0f}")
        calc.rationale = " | ".join(rationale_parts)

        self.calculations.append(calc)
        return calc

    def grant_tokens(self, calculation: RewardCalculation) -> TokenGrant:
        """
        Convert calculation into actual token grant.

        Returns:
            TokenGrant record
        """
        grant_id = self._generate_grant_id()

        # Check daily limit
        today = _utcnow().date().isoformat()
        daily_total = self.daily_granted.get(today, Decimal("0"))
        if daily_total + calculation.total_tokens > self.policy.daily_grant_limit:
            # Defer excess to tomorrow
            calculation.total_tokens = self.policy.daily_grant_limit - daily_total

        # Create grant
        grant = TokenGrant(
            grant_id=grant_id,
            principal_id=calculation.principal_id,
            amount_tokens=calculation.total_tokens,
            reward_type=RewardType.TOKEN_GRANT,
            earned_from=calculation.action_id,
            basis=calculation.rationale,
            vesting_period_days=calculation.vesting_days,
            status=RewardStatus.GRANTED,
        )

        self.grants[grant_id] = grant

        # Update tracking
        if calculation.principal_id not in self.principal_history:
            self.principal_history[calculation.principal_id] = []
        self.principal_history[calculation.principal_id].append(calculation.action_id)

        # Update daily limit
        self.daily_granted[today] = daily_total + calculation.total_tokens

        # Update balance
        if calculation.principal_id not in self.principal_balances:
            self.principal_balances[calculation.principal_id] = Decimal("0")
        self.principal_balances[calculation.principal_id] += calculation.total_tokens

        return grant

    def claim_vested_tokens(self, principal_id: str) -> Decimal:
        """
        Claim all vested tokens for principal.

        Returns:
            Total tokens claimed
        """
        total_claimed = Decimal("0")

        for grant_id, grant in self.grants.items():
            if (grant.principal_id == principal_id and
                grant.status == RewardStatus.GRANTED and
                grant.is_vested):

                grant.status = RewardStatus.VESTED
                grant.vested_date = _utcnow()
                total_claimed += grant.amount_tokens

        return total_claimed

    def spend_tokens(self, principal_id: str, cost_usd: Decimal) -> bool:
        """
        Spend tokens to pay for compute.

        Returns:
            True if successful, False if insufficient balance
        """
        tokens_needed = cost_usd * self.policy.tokens_per_usd_cost
        balance = self.principal_balances.get(principal_id, Decimal("0"))

        if balance < tokens_needed:
            return False

        self.principal_balances[principal_id] -= tokens_needed
        return True

    def get_principal_balance(self, principal_id: str) -> Dict:
        """Get token balance and vest status for principal."""
        balance = self.principal_balances.get(principal_id, Decimal("0"))
        principal_grants = [g for g in self.grants.values() if g.principal_id == principal_id]

        vested_total = sum(
            g.amount_tokens for g in principal_grants
            if g.status == RewardStatus.VESTED
        )
        pending_total = sum(
            g.amount_tokens for g in principal_grants
            if g.status == RewardStatus.GRANTED and not g.is_vested
        )

        return {
            "principal_id": principal_id,
            "total_balance": float(balance),
            "vested_tokens": float(vested_total),
            "pending_tokens": float(pending_total),
            "grant_count": len(principal_grants),
        }

    def _generate_grant_id(self) -> str:
        """Generate unique grant ID."""
        timestamp = _utcnow().isoformat()
        data = f"grant_{timestamp}".encode()
        return hashlib.sha256(data).hexdigest()[:16]

    def get_grant_log(self, principal_id: str) -> List[Dict]:
        """Get all grants for principal."""
        return [
            g.to_dict() for g in self.grants.values()
            if g.principal_id == principal_id
        ]

    def get_calculation_log(self) -> List[Dict]:
        """Return all calculations as dicts."""
        return [c.to_dict() for c in self.calculations]
