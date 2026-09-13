from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from vaig.aarm import AARMState

from .gate import GateDecision, GateEvent, vaig_gate
from .receipt import build_receipt


@dataclass(frozen=True)
class LoopStep:
    event_type: str
    current_frame: str
    proposed_action: str = ""
    tool: str = ""
    tool_authority: str = "none"
    task_authority: str = "read"
    reversibility: str = "reversible"
    domain_risk: str = "low"
    uncertainty: float = 0.0
    drift_score: float = 0.0
    observation_trust: float = 1.0
    claims_substantiated: bool = True
    # Cost-value gate fields
    estimated_tokens: int = 0
    model_tier: str = "standard"
    context_tokens: int = 0
    expected_latency_ms: int = 0
    human_time_minutes: float = 0.0
    expected_value: str = "medium"
    value_confidence: float = 1.0


@dataclass(frozen=True)
class LoopResult:
    run_id: str
    decisions: list[GateDecision]
    receipt: dict[str, Any]
    halted: bool


class AgentLoop:
    def __init__(self, original_intent: str, run_id: str | None = None) -> None:
        self.original_intent = original_intent
        self.run_id = run_id or str(uuid4())
        self._history: list[tuple[GateEvent, GateDecision]] = []
        self._aarm_state = AARMState()

    def run(self, steps: list[LoopStep]) -> LoopResult:
        halted = False
        for index, step in enumerate(steps, start=1):
            event = GateEvent(
                run_id=self.run_id,
                step_id=str(index),
                event_type=step.event_type,  # type: ignore[arg-type]
                original_intent=self.original_intent,
                current_frame=step.current_frame,
                proposed_action=step.proposed_action,
                tool=step.tool,
                tool_authority=step.tool_authority,  # type: ignore[arg-type]
                task_authority=step.task_authority,  # type: ignore[arg-type]
                reversibility=step.reversibility,  # type: ignore[arg-type]
                domain_risk=step.domain_risk,  # type: ignore[arg-type]
                uncertainty=step.uncertainty,
                drift_score=step.drift_score,
                observation_trust=step.observation_trust,
                claims_substantiated=step.claims_substantiated,
                prior_steps=[{"reason": decision.reason} for _, decision in self._history],
                estimated_tokens=step.estimated_tokens,
                model_tier=step.model_tier,  # type: ignore[arg-type]
                context_tokens=step.context_tokens,
                expected_latency_ms=step.expected_latency_ms,
                human_time_minutes=step.human_time_minutes,
                expected_value=step.expected_value,  # type: ignore[arg-type]
                value_confidence=step.value_confidence,
            )
            decision = vaig_gate(event, aarm_state=self._aarm_state)
            self._history.append((event, decision))
            if decision.decision in {"deny", "halt", "require_human"}:
                halted = True
                break

        return LoopResult(
            run_id=self.run_id,
            decisions=[decision for _, decision in self._history],
            receipt=build_receipt(self.run_id, self.original_intent, self._history),
            halted=halted,
        )
