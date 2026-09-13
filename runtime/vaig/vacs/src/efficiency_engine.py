"""
VALO Efficiency Engine v0.1

Measures real value creation, not token spend.

Core idea:
    Cost per token is the wrong unit.
    Verified value per dollar is the useful unit.

Flow:
    Claim -> Evidence -> Observation -> Verification -> Credit
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class VerificationLevel(Enum):
    CLAIMED = "claimed"
    ESTIMATED = "estimated"
    OBSERVED = "observed"
    VERIFIED = "verified"


class EfficiencyDecision(Enum):
    CREDIT = "CREDIT"
    OBSERVE = "OBSERVE"
    DEFER = "DEFER"
    DENY = "DENY"
    HALT = "HALT"


@dataclass(frozen=True)
class WorkCost:
    model_cost_usd: float = 0.0
    compute_cost_usd: float = 0.0
    tool_cost_usd: float = 0.0
    storage_cost_usd: float = 0.0
    human_time_cost_usd: float = 0.0
    review_cost_usd: float = 0.0
    correction_cost_usd: float = 0.0
    compliance_cost_usd: float = 0.0
    latency_cost_usd: float = 0.0
    maintenance_cost_usd: float = 0.0
    risk_cost_usd: float = 0.0
    opportunity_cost_usd: float = 0.0

    @property
    def total_cost_usd(self) -> float:
        return sum(asdict(self).values())


@dataclass(frozen=True)
class ValueCreated:
    time_saved_usd: float = 0.0
    cost_avoided_usd: float = 0.0
    risk_reduced_usd: float = 0.0
    quality_improved_usd: float = 0.0
    revenue_enabled_usd: float = 0.0
    reuse_value_usd: float = 0.0
    audit_value_usd: float = 0.0
    learning_value_usd: float = 0.0

    @property
    def total_value_usd(self) -> float:
        return sum(asdict(self).values())


@dataclass(frozen=True)
class Baseline:
    baseline_id: str
    description: str
    prior_cost_usd: float
    prior_duration_minutes: float
    prior_error_rate: float = 0.0
    sample_size: int = 1


@dataclass(frozen=True)
class Observation:
    observation_id: str
    baseline_id: str
    actual_cost: WorkCost
    value_created: ValueCreated
    actual_duration_minutes: float
    actual_error_rate: float = 0.0
    usage_count: int = 1
    evidence_receipt_id: str = ""
    notes: str = ""


@dataclass(frozen=True)
class EfficiencyPolicy:
    min_verification_level_for_credit: VerificationLevel = VerificationLevel.VERIFIED
    min_efficiency_score_for_credit: float = 1.0
    min_usage_count_for_verified: int = 3
    max_error_rate_increase: float = 0.02
    require_evidence_receipt: bool = True
    claimed_discount: float = 0.20
    estimated_discount: float = 0.40
    observed_discount: float = 0.70
    verified_discount: float = 1.00


@dataclass(frozen=True)
class EfficiencyResult:
    decision: EfficiencyDecision
    reason: str
    baseline: Baseline
    observation: Observation
    policy: EfficiencyPolicy
    verification_level: VerificationLevel
    total_cost_of_work_usd: float
    verified_value_created_usd: float
    efficiency_score: float
    net_value_usd: float


class VALOEfficiencyEngine:
    """
    Turns value claims into measured value.

    This engine does not reward claims directly. It discounts weak evidence and
    only emits CREDIT when value is sufficiently verified.
    """

    def evaluate(
        self,
        baseline: Baseline,
        observation: Observation,
        policy: Optional[EfficiencyPolicy] = None,
        verification_level: Optional[VerificationLevel] = None,
    ) -> EfficiencyResult:
        policy = policy or EfficiencyPolicy()

        if baseline.prior_cost_usd < 0 or baseline.prior_duration_minutes < 0:
            return self._result(EfficiencyDecision.HALT, "invalid negative baseline", baseline, observation, policy, VerificationLevel.CLAIMED, 0.0, 0.0)

        if observation.actual_cost.total_cost_usd < 0 or observation.value_created.total_value_usd < 0:
            return self._result(EfficiencyDecision.HALT, "invalid negative observation", baseline, observation, policy, VerificationLevel.CLAIMED, 0.0, 0.0)

        if observation.baseline_id != baseline.baseline_id:
            return self._result(EfficiencyDecision.HALT, "observation does not match baseline", baseline, observation, policy, VerificationLevel.CLAIMED, 0.0, 0.0)

        level = verification_level or self._infer_verification_level(baseline, observation, policy)
        discount = self._discount(level, policy)
        tcw = observation.actual_cost.total_cost_usd
        vvc = observation.value_created.total_value_usd * discount
        efficiency = self._ratio(vvc, tcw)
        net = vvc - tcw

        if policy.require_evidence_receipt and not observation.evidence_receipt_id.strip():
            return self._final(EfficiencyDecision.DEFER, "evidence receipt required", baseline, observation, policy, level, tcw, vvc, efficiency, net)

        if observation.actual_error_rate > baseline.prior_error_rate + policy.max_error_rate_increase:
            return self._final(EfficiencyDecision.DENY, "value rejected because error rate increased", baseline, observation, policy, level, tcw, vvc, efficiency, net)

        if level.value != policy.min_verification_level_for_credit.value and self._rank(level) < self._rank(policy.min_verification_level_for_credit):
            return self._final(EfficiencyDecision.OBSERVE, "value not verified enough for credit", baseline, observation, policy, level, tcw, vvc, efficiency, net)

        if efficiency < policy.min_efficiency_score_for_credit:
            return self._final(EfficiencyDecision.DENY, "verified efficiency below credit threshold", baseline, observation, policy, level, tcw, vvc, efficiency, net)

        if net <= 0:
            return self._final(EfficiencyDecision.DENY, "verified net value is not positive", baseline, observation, policy, level, tcw, vvc, efficiency, net)

        return self._final(EfficiencyDecision.CREDIT, "verified value exceeds total cost of work", baseline, observation, policy, level, tcw, vvc, efficiency, net)

    def receipt(self, result: EfficiencyResult) -> Dict[str, Any]:
        payload = {
            "baseline": asdict(result.baseline),
            "observation": asdict(result.observation),
            "policy": self._enum_safe_asdict(result.policy),
            "decision": result.decision.value,
            "verification_level": result.verification_level.value,
            "total_cost_of_work_usd": result.total_cost_of_work_usd,
            "verified_value_created_usd": result.verified_value_created_usd,
            "efficiency_score": result.efficiency_score,
            "net_value_usd": result.net_value_usd,
        }
        payload_hash = self._hash(payload)
        return {
            "receipt_id": str(uuid.uuid4()),
            "type": "valo.efficiency_engine.receipt.v1",
            "baseline_id": result.baseline.baseline_id,
            "observation_id": result.observation.observation_id,
            "decision": result.decision.value,
            "verification_level": result.verification_level.value,
            "tcw_usd": result.total_cost_of_work_usd,
            "vvc_usd": result.verified_value_created_usd,
            "ves": result.efficiency_score,
            "net_value_usd": result.net_value_usd,
            "reason": result.reason,
            "payload_hash": payload_hash,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "signature": f"ed25519:{payload_hash.removeprefix('sha256:')[:64]}",
        }

    def _infer_verification_level(self, baseline: Baseline, observation: Observation, policy: EfficiencyPolicy) -> VerificationLevel:
        if observation.usage_count >= policy.min_usage_count_for_verified and observation.evidence_receipt_id.strip():
            return VerificationLevel.VERIFIED
        if observation.usage_count > 1:
            return VerificationLevel.OBSERVED
        if baseline.sample_size > 1:
            return VerificationLevel.ESTIMATED
        return VerificationLevel.CLAIMED

    def _discount(self, level: VerificationLevel, policy: EfficiencyPolicy) -> float:
        if level == VerificationLevel.VERIFIED:
            return policy.verified_discount
        if level == VerificationLevel.OBSERVED:
            return policy.observed_discount
        if level == VerificationLevel.ESTIMATED:
            return policy.estimated_discount
        return policy.claimed_discount

    def _rank(self, level: VerificationLevel) -> int:
        return {
            VerificationLevel.CLAIMED: 0,
            VerificationLevel.ESTIMATED: 1,
            VerificationLevel.OBSERVED: 2,
            VerificationLevel.VERIFIED: 3,
        }[level]

    def _ratio(self, value: float, cost: float) -> float:
        if cost == 0:
            return float("inf") if value > 0 else 0.0
        return value / cost

    def _result(self, decision: EfficiencyDecision, reason: str, baseline: Baseline, observation: Observation, policy: EfficiencyPolicy, level: VerificationLevel, tcw: float, vvc: float) -> EfficiencyResult:
        return self._final(decision, reason, baseline, observation, policy, level, tcw, vvc, self._ratio(vvc, tcw), vvc - tcw)

    def _final(self, decision: EfficiencyDecision, reason: str, baseline: Baseline, observation: Observation, policy: EfficiencyPolicy, level: VerificationLevel, tcw: float, vvc: float, efficiency: float, net: float) -> EfficiencyResult:
        return EfficiencyResult(decision, reason, baseline, observation, policy, level, tcw, vvc, efficiency, net)

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
