from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Mapping, Sequence


class Decision(str, Enum):
    SCALE = "scale"
    KEEP_TESTING = "keep_testing"
    KILL = "kill"
    NEW_DIRECTION = "new_direction"


@dataclass(frozen=True)
class IdeaCandidate:
    idea_id: str
    mission_ref: str
    hypothesis: str
    channel: str
    estimated_cost: float
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.idea_id or not self.mission_ref or not self.hypothesis or not self.channel:
            raise ValueError("idea candidate requires identity, mission, hypothesis and channel")
        if self.estimated_cost < 0:
            raise ValueError("estimated_cost must be >= 0")


@dataclass(frozen=True)
class OutcomeEvent:
    idea_id: str
    verified_gcu: float
    cost: float
    observations: int
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.idea_id:
            raise ValueError("outcome requires idea_id")
        if self.verified_gcu < 0 or self.cost < 0 or self.observations < 0:
            raise ValueError("outcome values must be >= 0")
        if self.verified_gcu > 0 and not self.evidence_refs:
            raise ValueError("positive GCU requires outcome evidence")

    @property
    def gcu_per_cost(self) -> float:
        if self.cost == 0:
            return self.verified_gcu
        return self.verified_gcu / self.cost


@dataclass(frozen=True)
class SelectionPolicy:
    min_observations: int = 3
    scale_gcu_per_cost: float = 1.0
    kill_gcu_per_cost: float = 0.15
    exploration_share: float = 0.20

    def __post_init__(self) -> None:
        if self.min_observations < 1:
            raise ValueError("min_observations must be >= 1")
        if self.kill_gcu_per_cost < 0 or self.scale_gcu_per_cost <= self.kill_gcu_per_cost:
            raise ValueError("scale threshold must exceed kill threshold")
        if not 0 <= self.exploration_share <= 1:
            raise ValueError("exploration_share must be between 0 and 1")


@dataclass(frozen=True)
class PortfolioDecision:
    idea_id: str
    decision: Decision
    score: float
    reason: str
    allocation: float = 0.0


@dataclass(frozen=True)
class PortfolioPlan:
    decisions: tuple[PortfolioDecision, ...]
    unallocated_budget: float
    feedback_to_idebank: tuple[dict[str, object], ...] = field(default_factory=tuple)
    direct_effect_path: bool = False


class AttentionPortfolioEngine:
    """Pure selection/allocation loop. It never publishes or spends directly."""

    def __init__(self, policy: SelectionPolicy | None = None) -> None:
        self.policy = policy or SelectionPolicy()

    def decide(self, outcome: OutcomeEvent) -> PortfolioDecision:
        score = outcome.gcu_per_cost
        if outcome.observations < self.policy.min_observations:
            return PortfolioDecision(outcome.idea_id, Decision.KEEP_TESTING, score, "insufficient observations")
        if score >= self.policy.scale_gcu_per_cost:
            return PortfolioDecision(outcome.idea_id, Decision.SCALE, score, "verified return above scale threshold")
        if score <= self.policy.kill_gcu_per_cost:
            return PortfolioDecision(outcome.idea_id, Decision.KILL, score, "verified return at or below kill threshold")
        return PortfolioDecision(outcome.idea_id, Decision.KEEP_TESTING, score, "signal is between kill and scale thresholds")

    def plan(
        self,
        candidates: Sequence[IdeaCandidate],
        outcomes: Iterable[OutcomeEvent],
        budget: float,
    ) -> PortfolioPlan:
        if budget < 0:
            raise ValueError("budget must be >= 0")
        by_id: Mapping[str, IdeaCandidate] = {candidate.idea_id: candidate for candidate in candidates}
        base = [self.decide(outcome) for outcome in outcomes]
        feedback: list[dict[str, object]] = []

        for decision in base:
            if decision.decision is Decision.KILL and decision.idea_id in by_id:
                candidate = by_id[decision.idea_id]
                feedback.append({
                    "type": "new_direction_request",
                    "source": "valo-factory",
                    "idea_id": candidate.idea_id,
                    "mission_ref": candidate.mission_ref,
                    "failed_hypothesis": candidate.hypothesis,
                    "channel": candidate.channel,
                    "score": decision.score,
                    "instruction": "generate a materially different direction; do not merely rewrite the failed artifact",
                })

        exploration_budget = budget * self.policy.exploration_share
        scale_budget = budget - exploration_budget
        scalable = sorted((d for d in base if d.decision is Decision.SCALE), key=lambda d: (-d.score, d.idea_id))
        testing = sorted((d for d in base if d.decision is Decision.KEEP_TESTING), key=lambda d: (-d.score, d.idea_id))
        allocations: dict[str, float] = {}

        if scalable:
            total = sum(d.score for d in scalable)
            for decision in scalable:
                allocations[decision.idea_id] = scale_budget * (decision.score / total)
        else:
            exploration_budget = budget

        if testing:
            per_test = exploration_budget / len(testing)
            for decision in testing:
                allocations[decision.idea_id] = allocations.get(decision.idea_id, 0.0) + per_test
        else:
            scale_budget += exploration_budget

        planned = tuple(
            PortfolioDecision(d.idea_id, d.decision, d.score, d.reason, allocations.get(d.idea_id, 0.0))
            for d in base
        )
        used = sum(d.allocation for d in planned)
        return PortfolioPlan(
            decisions=planned,
            unallocated_budget=max(0.0, budget - used),
            feedback_to_idebank=tuple(feedback),
            direct_effect_path=False,
        )
