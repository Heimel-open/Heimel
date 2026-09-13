from dataclasses import dataclass
from enum import Enum
from typing import Optional

from vaig.economy.context_budget import ContextBudget
from vaig.economy.router import ModelTier, RoutingContext, route_model


class EconomyOutcome(str, Enum):
    ALLOW = "allow"
    COMPRESS = "compress"
    RETRIEVE = "retrieve"
    ROUTE_UP = "route_up"
    ROUTE_DOWN = "route_down"
    REORDER_CACHE = "reorder_cache"
    REQUIRE_HUMAN = "require_human"
    STOP = "stop"


@dataclass
class EconomyRequest:
    session_id: str
    current_tokens: int
    risk_level: float = 0.0
    consequence_level: float = 0.0
    cost_pressure: float = 0.0
    uncertainty: float = 0.0         # current estimate [0,1]
    prev_uncertainty: float = 0.0    # previous step estimate [0,1]; 0 = first step
    cost_trend: float = 0.0          # rate of cost increase per step (>0 = rising)
    human_cost_threshold: Optional[float] = None
    estimated_cost: Optional[float] = None


@dataclass
class EconomyDecision:
    outcome: EconomyOutcome
    reasoning: str
    model_tier: ModelTier
    token_cost: int = 0
    request: Optional[EconomyRequest] = None


class EconomyGate:
    def __init__(self, budget: Optional[ContextBudget] = None):
        self.budget = budget or ContextBudget()

    def decide(self, request: EconomyRequest) -> EconomyDecision:
        # 1. Rising cost with no uncertainty reduction → stop the loop
        if (request.cost_trend > 0
                and request.prev_uncertainty > 0
                and request.uncertainty >= request.prev_uncertainty):
            return EconomyDecision(
                outcome=EconomyOutcome.STOP,
                reasoning="Rising cost with no uncertainty reduction; loop has no value",
                model_tier=ModelTier.LARGE,
                token_cost=request.current_tokens,
                request=request,
            )

        # 2. Over budget → compress (low risk) or retrieve (higher risk)
        if self.budget.is_over_budget(request.current_tokens):
            outcome = (
                EconomyOutcome.RETRIEVE
                if request.risk_level >= 0.5
                else EconomyOutcome.COMPRESS
            )
            return EconomyDecision(
                outcome=outcome,
                reasoning=(
                    f"Context over budget ({request.current_tokens} > {self.budget.max_tokens})"
                ),
                model_tier=ModelTier.MEDIUM,
                token_cost=request.current_tokens,
                request=request,
            )

        # 3. Human approval required for cost
        if (request.human_cost_threshold is not None
                and request.estimated_cost is not None
                and request.estimated_cost > request.human_cost_threshold):
            return EconomyDecision(
                outcome=EconomyOutcome.REQUIRE_HUMAN,
                reasoning=(
                    f"Estimated cost {request.estimated_cost} exceeds "
                    f"approval threshold {request.human_cost_threshold}"
                ),
                model_tier=ModelTier.LARGE,
                token_cost=request.current_tokens,
                request=request,
            )

        # 4. Route to appropriate model tier
        tier = route_model(RoutingContext(
            risk_level=request.risk_level,
            consequence_level=request.consequence_level,
            cost_pressure=request.cost_pressure,
        ))
        return EconomyDecision(
            outcome=EconomyOutcome.ALLOW,
            reasoning="Within budget and policy constraints",
            model_tier=tier,
            token_cost=request.current_tokens,
            request=request,
        )
