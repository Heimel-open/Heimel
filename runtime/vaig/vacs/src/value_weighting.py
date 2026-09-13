"""
VALO Value Weighting v0.1

Turns raw value into weighted reward basis.

Core rule:
    Do not reward large claims.
    Reward hard evidence, repeatability, clear attribution, and strategic value.

Formula:
    weighted_value = value
        * evidence_weight
        * duration_weight
        * attribution_weight
        * strategic_weight
        - risk_cost
        - extra_cost
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class EvidenceLevel(Enum):
    CLAIMED = "claimed"
    ESTIMATED = "estimated"
    OBSERVED = "observed"
    VERIFIED = "verified"
    AUDITED = "audited"


class DurationLevel(Enum):
    ONE_TIME = "one_time"
    WEEKLY = "weekly"
    DAILY = "daily"
    CROSS_TEAM_REUSE = "cross_team_reuse"
    PLATFORM_EFFECT = "platform_effect"


class AttributionLevel(Enum):
    UNCLEAR = "unclear"
    TEAM = "team"
    DIRECT = "direct"
    SPLIT = "split"


class StrategicLevel(Enum):
    LOW = "low"
    NORMAL = "normal"
    CRITICAL_PROCESS = "critical_process"
    REGULATORY_RISK = "regulatory_risk"
    NEW_REVENUE = "new_revenue"


class WeightDecision(Enum):
    ACCEPT = "ACCEPT"
    OBSERVE = "OBSERVE"
    DEFER = "DEFER"
    DENY = "DENY"
    HALT = "HALT"


@dataclass(frozen=True)
class ValueWeightPolicy:
    min_weighted_value_usd: float = 1.0
    require_baseline_for_accept: bool = True
    evidence_weights: Dict[str, float] = None
    duration_weights: Dict[str, float] = None
    attribution_weights: Dict[str, float] = None
    strategic_weights: Dict[str, float] = None

    def __post_init__(self):
        object.__setattr__(self, "evidence_weights", self.evidence_weights or {
            "claimed": 0.10,
            "estimated": 0.30,
            "observed": 0.60,
            "verified": 1.00,
            "audited": 1.20,
        })
        object.__setattr__(self, "duration_weights", self.duration_weights or {
            "one_time": 0.30,
            "weekly": 0.70,
            "daily": 1.00,
            "cross_team_reuse": 1.50,
            "platform_effect": 2.00,
        })
        object.__setattr__(self, "attribution_weights", self.attribution_weights or {
            "unclear": 0.30,
            "team": 0.60,
            "direct": 1.00,
            "split": 0.80,
        })
        object.__setattr__(self, "strategic_weights", self.strategic_weights or {
            "low": 0.50,
            "normal": 1.00,
            "critical_process": 1.50,
            "regulatory_risk": 2.00,
            "new_revenue": 2.00,
        })


@dataclass(frozen=True)
class ValueWeightInput:
    value_id: str
    raw_value_usd: float
    evidence_level: EvidenceLevel
    duration_level: DurationLevel
    attribution_level: AttributionLevel
    strategic_level: StrategicLevel
    risk_cost_usd: float = 0.0
    extra_cost_usd: float = 0.0
    has_baseline: bool = False
    source_receipt_id: str = ""


@dataclass(frozen=True)
class ValueWeightResult:
    decision: WeightDecision
    reason: str
    input: ValueWeightInput
    policy: ValueWeightPolicy
    evidence_weight: float
    duration_weight: float
    attribution_weight: float
    strategic_weight: float
    weighted_value_usd: float


class VALOValueWeightingEngine:
    def evaluate(self, value: ValueWeightInput, policy: Optional[ValueWeightPolicy] = None) -> ValueWeightResult:
        policy = policy or ValueWeightPolicy()

        if value.raw_value_usd < 0 or value.risk_cost_usd < 0 or value.extra_cost_usd < 0:
            return self._result(WeightDecision.HALT, "negative value, risk, or cost", value, policy, 0.0, 0.0, 0.0, 0.0, 0.0)

        ew = policy.evidence_weights[value.evidence_level.value]
        dw = policy.duration_weights[value.duration_level.value]
        aw = policy.attribution_weights[value.attribution_level.value]
        sw = policy.strategic_weights[value.strategic_level.value]

        weighted = round(value.raw_value_usd * ew * dw * aw * sw - value.risk_cost_usd - value.extra_cost_usd, 4)

        if weighted <= 0:
            return self._result(WeightDecision.DENY, "weighted value is not positive", value, policy, ew, dw, aw, sw, weighted)

        if policy.require_baseline_for_accept and not value.has_baseline:
            return self._result(WeightDecision.DEFER, "baseline required before accepting weighted value", value, policy, ew, dw, aw, sw, weighted)

        if value.evidence_level in (EvidenceLevel.CLAIMED, EvidenceLevel.ESTIMATED):
            return self._result(WeightDecision.OBSERVE, "evidence is too weak for final value acceptance", value, policy, ew, dw, aw, sw, weighted)

        if weighted < policy.min_weighted_value_usd:
            return self._result(WeightDecision.DENY, "weighted value below threshold", value, policy, ew, dw, aw, sw, weighted)

        return self._result(WeightDecision.ACCEPT, "weighted value accepted", value, policy, ew, dw, aw, sw, weighted)

    def receipt(self, result: ValueWeightResult) -> Dict[str, Any]:
        payload = {
            "input": self._enum_safe_asdict(result.input),
            "policy": asdict(result.policy),
            "decision": result.decision.value,
            "reason": result.reason,
            "weighted_value_usd": result.weighted_value_usd,
        }
        payload_hash = self._hash(payload)
        return {
            "receipt_id": str(uuid.uuid4()),
            "type": "valo.value_weighting.receipt.v1",
            "value_id": result.input.value_id,
            "decision": result.decision.value,
            "raw_value_usd": result.input.raw_value_usd,
            "weighted_value_usd": result.weighted_value_usd,
            "evidence_weight": result.evidence_weight,
            "duration_weight": result.duration_weight,
            "attribution_weight": result.attribution_weight,
            "strategic_weight": result.strategic_weight,
            "reason": result.reason,
            "payload_hash": payload_hash,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "signature": f"ed25519:{payload_hash.removeprefix('sha256:')[:64]}",
        }

    def _result(self, decision: WeightDecision, reason: str, value: ValueWeightInput, policy: ValueWeightPolicy, ew: float, dw: float, aw: float, sw: float, weighted: float) -> ValueWeightResult:
        return ValueWeightResult(decision, reason, value, policy, ew, dw, aw, sw, weighted)

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
