from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

from .gate import GateDecision, GateEvent


def build_receipt(run_id: str, original_intent: str, decisions: list[tuple[GateEvent, GateDecision]]) -> dict[str, Any]:
    highest_risk = _highest_risk([decision.risk_class for _, decision in decisions])
    max_drift = max((event.drift_score for event, _ in decisions), default=0.0)
    max_uncertainty = max((event.uncertainty for event, _ in decisions), default=0.0)
    final_decision = decisions[-1][1].decision if decisions else "deny"
    human_transfer_required = final_decision in {"deny", "halt", "require_human", "slow_path"}

    return {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "final_decision": final_decision,
        "original_intent_hash": sha256(original_intent.encode("utf-8")).hexdigest(),
        "steps": [
            {
                "event": asdict(event),
                "decision": asdict(decision),
            }
            for event, decision in decisions
            if decision.receipt_required
        ],
        "highest_risk_class": highest_risk,
        "max_drift_score": max_drift,
        "max_uncertainty": max_uncertainty,
        "human_transfer": {
            "required": human_transfer_required,
            "why": _human_why(decisions) if human_transfer_required else "",
            "remaining_uncertainty": _remaining_uncertainty(decisions) if human_transfer_required else "",
            "standing_to_act": _standing_to_act(decisions) if human_transfer_required else "",
            "available_options": _available_options(decisions) if human_transfer_required else [],
            "accountability_path": "receipt -> operator review -> scoped authorization or halt" if human_transfer_required else "",
        },
    }


def _highest_risk(risks: list[str]) -> str:
    order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    if not risks:
        return "low"
    return max(risks, key=lambda item: order[item])


def _human_why(decisions: list[tuple[GateEvent, GateDecision]]) -> str:
    if not decisions:
        return "no governed decision was produced"
    return decisions[-1][1].reason


def _remaining_uncertainty(decisions: list[tuple[GateEvent, GateDecision]]) -> str:
    if not decisions:
        return "No decision context is available. Treat the run as unresolved."

    event, decision = decisions[-1]
    if decision.decision == "deny" and "authority" in decision.reason:
        return "The system does not know whether the user intended read-only work or authorized a higher-authority action."
    if decision.decision == "halt":
        return "The system detected boundary loss and cannot safely infer the next valid action."
    if decision.decision == "require_human":
        return "The system requires accountable human judgment before execution can continue."
    if decision.decision == "slow_path":
        return "The step may be permissible, but requires deeper verification before execution."
    return f"Review step {event.step_id} and decision rationale before continuing."


def _standing_to_act(decisions: list[tuple[GateEvent, GateDecision]]) -> str:
    if not decisions:
        return "designated accountable operator"

    _, decision = decisions[-1]
    if decision.decision == "deny":
        return "user, repository owner, or designated operator with sufficient authority"
    if decision.decision == "halt":
        return "designated system owner or boundary override authority"
    if decision.decision == "require_human":
        return "designated human operator or accountable system owner"
    if decision.decision == "slow_path":
        return "operator with authority to verify, re-scope, or escalate"
    return "designated accountable operator"


def _available_options(decisions: list[tuple[GateEvent, GateDecision]]) -> list[str]:
    if not decisions:
        return ["stop execution", "open review"]

    _, decision = decisions[-1]
    if decision.decision == "deny":
        return [
            "stop execution",
            "ask user to confirm authority and scope",
            "re-scope to an allowed lower-authority action",
            "escalate to a designated authority",
        ]
    if decision.decision == "halt":
        return [
            "stop execution",
            "open governance review",
            "preserve receipt and context",
            "restart only after explicit authorization",
        ]
    if decision.decision == "require_human":
        return [
            "route to designated human reviewer",
            "approve within scope",
            "re-scope",
            "terminate workflow",
        ]
    if decision.decision == "slow_path":
        return [
            "perform deeper verification",
            "re-ground against original intent",
            "re-scope",
            "escalate if uncertainty remains",
        ]
    return []
