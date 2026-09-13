from dataclasses import dataclass
from enum import Enum


class ModelTier(str, Enum):
    SMALL = "small"       # formatting, classification, extraction, low-risk summaries
    MEDIUM = "medium"     # normal reasoning, code review, planning
    LARGE = "large"       # high consequence, governance boundary, error cost > model cost


@dataclass(frozen=True)
class RoutingContext:
    risk_level: float         # 0.0–1.0
    consequence_level: float  # 0.0–1.0; ≥0.6 → never downgrade
    cost_pressure: float      # 0.0–1.0; 1.0 = critically over budget


_CONSEQUENCE_LOCK = 0.6
_LOW = 0.35
_HIGH_COST = 0.6


def route_model(ctx: RoutingContext) -> ModelTier:
    # High-consequence tasks are never downgraded regardless of cost pressure.
    if ctx.consequence_level >= _CONSEQUENCE_LOCK:
        return ModelTier.LARGE

    # Low risk + low consequence → small model
    if ctx.risk_level < _LOW and ctx.consequence_level < _LOW:
        return ModelTier.SMALL

    # Cost pressure with sub-high risk → medium model
    if ctx.cost_pressure >= _HIGH_COST and ctx.risk_level < _CONSEQUENCE_LOCK:
        return ModelTier.MEDIUM

    return ModelTier.LARGE
