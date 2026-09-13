import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

from vaig.economy.decision import EconomyDecision


@dataclass
class EconomyReceipt:
    session_id: str
    outcome: str
    model_tier: str
    token_cost: int
    reasoning: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    hash: str = field(default="", init=False)

    def __post_init__(self):
        self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        payload = json.dumps({
            "session_id": self.session_id,
            "outcome": self.outcome,
            "model_tier": self.model_tier,
            "token_cost": self.token_cost,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp,
        }, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "outcome": self.outcome,
            "model_tier": self.model_tier,
            "token_cost": self.token_cost,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp,
            "hash": self.hash,
        }


def make_receipt(decision: EconomyDecision, session_id: str) -> EconomyReceipt:
    return EconomyReceipt(
        session_id=session_id,
        outcome=decision.outcome.value,
        model_tier=decision.model_tier.value,
        token_cost=decision.token_cost,
        reasoning=decision.reasoning,
    )
