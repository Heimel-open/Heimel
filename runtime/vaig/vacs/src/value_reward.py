"""
VALO Value Reward Gate v0.1

Rewards measured human-agent value creation without allowing reward farming.

Core idea:
    Do not only meter spend. Meter created value.

This module does not implement a public cryptocurrency. It implements an
internal auditable credit decision layer that can later back points, credits,
partner rewards, or a regulated token if legally viable.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class CreatorType(Enum):
    HUMAN = "human"
    AGENT = "agent"
    TEAM = "team"
    HUMAN_AGENT_PAIR = "human_agent_pair"


class RewardDecision(Enum):
    ALLOW = "ALLOW"
    STEP_UP = "STEP_UP"
    DEFER = "DEFER"
    DENY = "DENY"
    HALT = "HALT"


@dataclass(frozen=True)
class ValueClaim:
    claim_id: str
    beneficiary_id: str
    creator_type: CreatorType
    source_action_id: str
    source_receipt_id: str
    value_claim_usd: float
    value_basis: str
    confidence: float
    risk_adjustment: float = 0.0
    reusable: bool = False
    reduces_remote_spend: bool = False
    creates_audit_evidence: bool = False
    approver_id: Optional[str] = None

    @property
    def risk_adjusted_value_usd(self) -> float:
        return max(0.0, self.value_claim_usd - self.risk_adjustment)


@dataclass(frozen=True)
class RewardPolicy:
    reward_rate: float = 0.10
    max_auto_reward_units: float = 25.0
    max_auto_value_claim_usd: float = 250.0
    min_confidence: float = 0.70
    min_value_claim_usd: float = 1.0
    require_source_receipt: bool = True
    require_approval_above_units: float = 25.0
    bonus_for_reuse: float = 1.25
    bonus_for_remote_spend_reduction: float = 1.15
    bonus_for_audit_evidence: float = 1.10
    reward_unit: str = "VALO_CREDIT"


@dataclass(frozen=True)
class RewardResult:
    decision: RewardDecision
    reason: str
    claim: ValueClaim
    policy: RewardPolicy
    reward_units: float


class VALOValueRewardGate:
    """
    Deterministic reward decision layer.

    It rewards useful creation, but blocks weak claims and escalates large ones.
    """

    def evaluate(self, claim: ValueClaim, policy: Optional[RewardPolicy] = None) -> RewardResult:
        policy = policy or RewardPolicy()

        if claim.value_claim_usd < 0 or claim.risk_adjustment < 0:
            return self._result(RewardDecision.HALT, "negative value or risk estimate", claim, policy, 0.0)

        if policy.require_source_receipt and not claim.source_receipt_id.strip():
            return self._result(RewardDecision.DEFER, "source receipt required", claim, policy, 0.0)

        if not claim.value_basis.strip():
            return self._result(RewardDecision.DEFER, "value basis required", claim, policy, 0.0)

        if claim.confidence < policy.min_confidence:
            return self._result(RewardDecision.DEFER, "value confidence below policy", claim, policy, 0.0)

        if claim.risk_adjusted_value_usd < policy.min_value_claim_usd:
            return self._result(RewardDecision.DENY, "risk-adjusted value below reward threshold", claim, policy, 0.0)

        reward_units = self._calculate_reward_units(claim, policy)

        if claim.value_claim_usd > policy.max_auto_value_claim_usd:
            return self._result(RewardDecision.STEP_UP, "value claim exceeds automatic approval limit", claim, policy, reward_units)

        if reward_units > policy.max_auto_reward_units:
            return self._result(RewardDecision.STEP_UP, "reward exceeds automatic approval limit", claim, policy, reward_units)

        if reward_units > policy.require_approval_above_units and not claim.approver_id:
            return self._result(RewardDecision.STEP_UP, "reward requires approver", claim, policy, reward_units)

        return self._result(RewardDecision.ALLOW, "reward allowed for risk-adjusted value creation", claim, policy, reward_units)

    def receipt(self, result: RewardResult) -> Dict[str, Any]:
        payload = {
            "claim": self._enum_safe_asdict(result.claim),
            "policy": asdict(result.policy),
            "decision": result.decision.value,
            "reason": result.reason,
            "reward_units": result.reward_units,
        }
        payload_hash = self._hash(payload)
        return {
            "reward_id": str(uuid.uuid4()),
            "type": "valo.value_reward.receipt.v1",
            "claim_id": result.claim.claim_id,
            "beneficiary_id": result.claim.beneficiary_id,
            "creator_type": result.claim.creator_type.value,
            "source_action_id": result.claim.source_action_id,
            "source_receipt_id": result.claim.source_receipt_id,
            "value_claim_usd": result.claim.value_claim_usd,
            "risk_adjusted_value_usd": result.claim.risk_adjusted_value_usd,
            "reward_units": result.reward_units,
            "reward_unit": result.policy.reward_unit,
            "decision": result.decision.value,
            "reason": result.reason,
            "approver_id": result.claim.approver_id,
            "payload_hash": payload_hash,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "signature": f"ed25519:{payload_hash.removeprefix('sha256:')[:64]}",
        }

    def _calculate_reward_units(self, claim: ValueClaim, policy: RewardPolicy) -> float:
        multiplier = 1.0
        if claim.reusable:
            multiplier *= policy.bonus_for_reuse
        if claim.reduces_remote_spend:
            multiplier *= policy.bonus_for_remote_spend_reduction
        if claim.creates_audit_evidence:
            multiplier *= policy.bonus_for_audit_evidence
        return round(claim.risk_adjusted_value_usd * policy.reward_rate * multiplier, 4)

    def _result(
        self,
        decision: RewardDecision,
        reason: str,
        claim: ValueClaim,
        policy: RewardPolicy,
        reward_units: float,
    ) -> RewardResult:
        return RewardResult(decision, reason, claim, policy, reward_units)

    def _enum_safe_asdict(self, value: Any) -> Dict[str, Any]:
        def convert(item: Any) -> Any:
            if isinstance(item, Enum):
                return item.value
            if isinstance(item, tuple):
                return tuple(convert(x) for x in item)
            if isinstance(item, list):
                return [convert(x) for x in item]
            if isinstance(item, dict):
                return {k: convert(v) for k, v in item.items()}
            return item

        return convert(asdict(value))

    def _hash(self, data: Dict[str, Any]) -> str:
        normalized = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
        return f"sha256:{hashlib.sha256(normalized.encode('utf-8')).hexdigest()}"
