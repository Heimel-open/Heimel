from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from .types import GovernanceContext


@dataclass
class ValidityContract:
    contract_id: str
    issued_at: str
    valid_until: str
    context_hash: str
    policy_hash: str
    authority_hash: str
    action_id: str


@dataclass
class TADResult:
    valid: bool
    reason: str
    invalidation_event: Optional[str] = None


class TADGate:
    """Temporal Admissibility as validity contract, not timer-only cache."""

    def evaluate(self, contract: ValidityContract, context: GovernanceContext) -> TADResult:
        now = datetime.now(timezone.utc)
        expiry = datetime.fromisoformat(contract.valid_until.replace("Z", "+00:00"))

        if now >= expiry:
            return TADResult(False, "validity_horizon_expired", "expiry")
        if contract.context_hash != context.state_hash:
            return TADResult(False, "context_hash_changed", "context")
        if contract.policy_hash != context.policy_hash:
            return TADResult(False, "policy_hash_changed", "policy")
        if contract.authority_hash != context.authority_hash:
            return TADResult(False, "authority_hash_changed", "authority")
        if context.metadata.get("baro_escalation") is True:
            return TADResult(False, "baro_escalation", "baro")
        if context.metadata.get("pert_deviation") is True:
            return TADResult(False, "pert_deviation", "pert")

        return TADResult(True, "validity_contract_intact")
