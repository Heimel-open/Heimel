from __future__ import annotations

"""WHY Gate runtime module.

CAN asks capability.
SHOULD asks policy.
WHY asks continuity.

WHY Gate verifies that the justification for execution remains valid until
consequence commitment. Scores are normalised to [0.0, 1.0]; the composite
why_score is the weakest-link minimum of all four input dimensions.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any, Optional
from uuid import uuid4


class WhyDecision(str, Enum):
    """Runtime decision emitted by WHY Gate."""

    CONTINUE = "CONTINUE"
    WATCH = "WATCH"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    HALT = "HALT"


@dataclass(frozen=True)
class WhyInputs:
    """Four-dimension justification-continuity inputs.

    Scores must be in [0.0, 1.0]; values outside that range are clamped.
    """

    action_id: str
    authority_score: float
    policy_score: float
    reality_score: float
    consequence_score: float
    previous_hash: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class WhyState:
    """Immutable result of a WHY Gate evaluation.

    state_hash covers all fields except itself; verify with verify_why_chain.
    """

    why_id: str
    action_id: str
    timestamp: str
    authority_score: float
    policy_score: float
    reality_score: float
    consequence_score: float
    why_score: float
    decision: WhyDecision
    previous_hash: Optional[str]
    state_hash: str
    metadata: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class WhyReceipt:
    """Auditable receipt for a WHY Gate decision."""

    receipt_id: str
    receipt_type: str
    why_id: str
    action_id: str
    timestamp: str
    decision: WhyDecision
    why_score: float
    state_hash: str
    previous_hash: Optional[str]
    receipt_hash: str
    metadata: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "receipt_type": self.receipt_type,
            "why_id": self.why_id,
            "action_id": self.action_id,
            "timestamp": self.timestamp,
            "decision": self.decision.value,
            "why_score": self.why_score,
            "state_hash": self.state_hash,
            "previous_hash": self.previous_hash,
            "receipt_hash": self.receipt_hash,
            "metadata": self.metadata,
        }


def decide_why(score: float) -> WhyDecision:
    """Map a score to a WhyDecision (values outside [0,1] are clamped).

    >= 0.85 -> CONTINUE
    >= 0.65 -> WATCH
    >= 0.45 -> HUMAN_REVIEW
     < 0.45 -> HALT
    """
    score = max(0.0, min(1.0, score))
    if score >= 0.85:
        return WhyDecision.CONTINUE
    if score >= 0.65:
        return WhyDecision.WATCH
    if score >= 0.45:
        return WhyDecision.HUMAN_REVIEW
    return WhyDecision.HALT


def _state_json(
    why_id: str,
    action_id: str,
    timestamp: str,
    authority_score: float,
    policy_score: float,
    reality_score: float,
    consequence_score: float,
    why_score: float,
    decision: WhyDecision,
    previous_hash: Optional[str],
    metadata: Optional[dict[str, Any]],
) -> str:
    data = {
        "action_id": action_id,
        "authority_score": authority_score,
        "consequence_score": consequence_score,
        "decision": decision.value,
        "metadata": metadata,
        "policy_score": policy_score,
        "previous_hash": previous_hash,
        "reality_score": reality_score,
        "timestamp": timestamp,
        "why_id": why_id,
        "why_score": why_score,
    }
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def evaluate_why(inputs: WhyInputs) -> WhyState:
    """Evaluate justification continuity and return an immutable WhyState."""
    authority = max(0.0, min(1.0, inputs.authority_score))
    policy = max(0.0, min(1.0, inputs.policy_score))
    reality = max(0.0, min(1.0, inputs.reality_score))
    consequence = max(0.0, min(1.0, inputs.consequence_score))

    why_score = min(authority, policy, reality, consequence)
    decision = decide_why(why_score)
    why_id = f"why_{uuid4().hex}"
    timestamp = datetime.now(timezone.utc).isoformat()

    state_hash = hashlib.sha256(
        _state_json(
            why_id, inputs.action_id, timestamp,
            authority, policy, reality, consequence,
            why_score, decision, inputs.previous_hash, inputs.metadata,
        ).encode()
    ).hexdigest()

    return WhyState(
        why_id=why_id,
        action_id=inputs.action_id,
        timestamp=timestamp,
        authority_score=authority,
        policy_score=policy,
        reality_score=reality,
        consequence_score=consequence,
        why_score=why_score,
        decision=decision,
        previous_hash=inputs.previous_hash,
        state_hash=state_hash,
        metadata=inputs.metadata,
    )


def make_why_receipt(state: WhyState) -> WhyReceipt:
    """Create an auditable receipt from a WhyState."""
    receipt_id = f"why_receipt_{uuid4().hex}"
    receipt_type = "WHY_GATE_DECISION"
    timestamp = datetime.now(timezone.utc).isoformat()

    payload = {
        "action_id": state.action_id,
        "decision": state.decision.value,
        "metadata": state.metadata,
        "previous_hash": state.previous_hash,
        "receipt_id": receipt_id,
        "receipt_type": receipt_type,
        "state_hash": state.state_hash,
        "timestamp": timestamp,
        "why_id": state.why_id,
        "why_score": state.why_score,
    }
    receipt_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()

    return WhyReceipt(
        receipt_id=receipt_id,
        receipt_type=receipt_type,
        why_id=state.why_id,
        action_id=state.action_id,
        timestamp=timestamp,
        decision=state.decision,
        why_score=state.why_score,
        state_hash=state.state_hash,
        previous_hash=state.previous_hash,
        receipt_hash=receipt_hash,
        metadata=state.metadata,
    )


def verify_why_receipt(receipt: WhyReceipt, state: Optional[WhyState] = None) -> bool:
    """Verify receipt integrity and optionally that it is bound to *state*."""
    payload = {
        "action_id": receipt.action_id,
        "decision": receipt.decision.value,
        "metadata": receipt.metadata,
        "previous_hash": receipt.previous_hash,
        "receipt_id": receipt.receipt_id,
        "receipt_type": receipt.receipt_type,
        "state_hash": receipt.state_hash,
        "timestamp": receipt.timestamp,
        "why_id": receipt.why_id,
        "why_score": receipt.why_score,
    }
    expected = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
    if receipt.receipt_hash != expected:
        return False

    if state is not None:
        if receipt.why_id != state.why_id or receipt.state_hash != state.state_hash:
            return False

    return True


def verify_why_chain(states: list[WhyState]) -> bool:
    """Verify the integrity of an ordered sequence of WhyState objects.

    Rules:
    - Empty list is valid.
    - First state must have previous_hash=None.
    - Every state_hash must match a recomputation from the state's fields.
    - Each state after the first must have previous_hash equal to the
      previous state's state_hash.
    """
    if not states:
        return True

    for i, state in enumerate(states):
        expected = hashlib.sha256(
            _state_json(
                state.why_id, state.action_id, state.timestamp,
                state.authority_score, state.policy_score,
                state.reality_score, state.consequence_score,
                state.why_score, state.decision,
                state.previous_hash, state.metadata,
            ).encode()
        ).hexdigest()
        if state.state_hash != expected:
            return False

        if i == 0:
            if state.previous_hash is not None:
                return False
        else:
            if state.previous_hash != states[i - 1].state_hash:
                return False

    return True
