from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from vaig.aarm import (
    AARMSignal,
    AARMSignalError,
    AARMState,
    AARMVerdict,
    evaluate_signal,
)

from .risk_engine import classify_event

EventType = Literal["input", "plan", "tool_call", "observation", "action", "output"]
Authority = Literal["none", "read", "write", "execute", "send", "delete"]
Reversibility = Literal["reversible", "partially_reversible", "irreversible"]
RiskClass = Literal["low", "medium", "high", "critical"]
ModelTierGate = Literal["local", "small", "standard", "frontier"]
ValueLevel = Literal["low", "medium", "high", "critical"]
Decision = Literal[
    "allow", "allow_fast", "slow_path", "require_human", "deny", "halt",
    "downshift_model", "reduce_context", "require_value_justification", "deny_cost",
]


@dataclass(frozen=True)
class GateEvent:
    run_id: str
    step_id: str
    event_type: EventType
    original_intent: str
    current_frame: str
    proposed_action: str = ""
    tool: str = ""
    tool_authority: Authority = "none"
    task_authority: Authority = "none"
    reversibility: Reversibility = "reversible"
    domain_risk: RiskClass = "low"
    uncertainty: float = 0.0
    drift_score: float = 0.0
    observation_trust: float = 1.0
    claims_substantiated: bool = True
    prior_steps: list[dict[str, Any]] = field(default_factory=list)
    estimated_tokens: int = 0
    model_tier: ModelTierGate = "standard"
    context_tokens: int = 0
    expected_latency_ms: int = 0
    human_time_minutes: float = 0.0
    expected_value: ValueLevel = "medium"
    value_confidence: float = 1.0


@dataclass(frozen=True)
class GateDecision:
    """VAIG-local progression decision; never execution authority."""

    decision: Decision
    reason: str
    risk_class: RiskClass
    checks_run: list[str]
    receipt_required: bool = True
    aarm_verdict: Optional[str] = None
    aarm_digest: Optional[str] = None
    aarm_reason: Optional[str] = None
    execution_authority: bool = False
    requires_reht_clearance: bool = True

    def __post_init__(self) -> None:
        if self.execution_authority:
            raise ValueError("VAIG GateDecision cannot grant execution authority")
        if not self.requires_reht_clearance:
            raise ValueError("VAIG GateDecision must require REHT clearance")

    @property
    def can_execute(self) -> bool:
        return False


# AARM is a restrictive evaluation backstop. It may force a more conservative
# VAIG-local progression state, but its ALLOW value never authorizes an effect.
_AARM_TO_GATE: dict[AARMVerdict, str] = {
    AARMVerdict.ALLOW: "allow",
    AARMVerdict.MODIFY: "slow_path",
    AARMVerdict.DEFER: "require_human",
    AARMVerdict.STEP_UP: "require_human",
    AARMVerdict.DENY: "deny",
    AARMVerdict.HALT: "halt",
}

_AARM_GATE_SEVERITY: dict[AARMVerdict, int] = {
    AARMVerdict.ALLOW: 0,
    AARMVerdict.MODIFY: 1,
    AARMVerdict.DEFER: 2,
    AARMVerdict.STEP_UP: 2,
    AARMVerdict.DENY: 3,
    AARMVerdict.HALT: 4,
}

_GATE_SEVERITY: dict[str, int] = {
    "allow": 0, "allow_fast": 0,
    "slow_path": 1, "downshift_model": 1, "reduce_context": 1,
    "require_value_justification": 1, "require_human": 2,
    "deny": 3, "deny_cost": 3,
    "halt": 4,
}


def _event_to_signal(event: GateEvent) -> AARMSignal:
    return AARMSignal(
        risk_class=event.domain_risk,
        uncertainty=event.uncertainty,
        reversibility=event.reversibility,
        tool_authority=event.tool_authority,
        task_authority=event.task_authority,
        drift_score=event.drift_score,
        observation_trust=event.observation_trust,
        claims_substantiated=event.claims_substantiated,
        evidence_valid=True,
        human_time_minutes=event.human_time_minutes,
        expected_value=event.expected_value,
        value_confidence=event.value_confidence,
        estimated_tokens=event.estimated_tokens,
        context_tokens=event.context_tokens,
        model_tier=event.model_tier,
        actor_id=event.run_id,
        action_type=event.event_type,
        nonce=f"{event.run_id}:{event.step_id}",
    )


def _fail_closed_signal() -> AARMSignal:
    return AARMSignal(
        risk_class="critical",
        uncertainty=1.0,
        reversibility="irreversible",
        tool_authority="none",
        task_authority="none",
        drift_score=1.0,
        observation_trust=0.0,
        claims_substantiated=False,
        evidence_valid=False,
    )


def vaig_gate(event: GateEvent, aarm_state: Optional[AARMState] = None) -> GateDecision:
    """Evaluate one VAIG-local boundary crossing.

    The result may control VAIG's own progression, but it is not an execution
    clearance. Any consequential tool/effect path still requires REHT.
    """
    try:
        signal = _event_to_signal(event)
    except AARMSignalError:
        signal = _fail_closed_signal()

    decision = (
        aarm_state.evaluate(signal)
        if aarm_state is not None
        else evaluate_signal(signal)
    )
    gate = classify_event(event)

    if _AARM_GATE_SEVERITY[decision.verdict] > _GATE_SEVERITY[gate.decision]:
        decision_text = _AARM_TO_GATE[decision.verdict]
        reason = decision.reason
        checks = gate.checks_run + ["aarm_verdict"]
    else:
        decision_text = gate.decision
        reason = gate.reason
        checks = gate.checks_run

    return GateDecision(
        decision=decision_text,
        reason=reason,
        risk_class=gate.risk_class,
        checks_run=checks,
        receipt_required=gate.receipt_required,
        aarm_verdict=decision.verdict.value,
        aarm_digest=decision.decision_digest,
        aarm_reason=decision.reason,
    )
