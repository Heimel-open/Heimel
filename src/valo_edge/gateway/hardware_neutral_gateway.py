"""Hardware-neutral device enforcement gateway for Tiny Edge physical AI."""

from datetime import datetime, timezone
import hashlib
from typing import List
from valo_edge.contracts import (
    EdgeActionProposal,
    EdgeClearance,
    EdgeDecision,
    EdgeExecutionReceipt,
)


class HardwareNeutralGateway:
    """Hardware-neutral gateway. Enforces that physical actuators execute ONLY
    when micro-REHT clearance decision == ALLOW. Emits Veritas execution receipts."""

    def __init__(self) -> None:
        self._receipt_log: List[EdgeExecutionReceipt] = []

    def execute_action(
        self,
        proposal: EdgeActionProposal,
        clearance: EdgeClearance,
        timestamp_iso: str,
    ) -> EdgeExecutionReceipt:
        # Evidence chaining: refuse to execute unless the clearance and proposal
        # digests match their canonical recomputation.
        if clearance.decision_digest != clearance.compute_digest():
            raise ValueError("clearance decision_digest mismatch: refusing to execute")
        if clearance.proposal_id != proposal.proposal_id:
            raise ValueError("clearance proposal_id does not match proposal")
        if proposal.proposal_hash != proposal.compute_hash():
            raise ValueError("proposal hash mismatch: refusing to execute")

        receipt_id = f"rcpt-edge-{hashlib.sha256(f'{clearance.clearance_id}:{timestamp_iso}'.encode()).hexdigest()[:12]}"

        # Enforcement rule: execute ONLY if clearance == ALLOW
        if clearance.decision == EdgeDecision.ALLOW:
            executed = True
        else:
            executed = False

        receipt = EdgeExecutionReceipt(
            receipt_id=receipt_id,
            proposal_id=proposal.proposal_id,
            clearance_id=clearance.clearance_id,
            device_id=proposal.device_id,
            decision=clearance.decision,
            executed=executed,
            timestamp_iso=timestamp_iso,
        )

        self._receipt_log.append(receipt)
        return receipt

    def get_receipt_history(self) -> List[EdgeExecutionReceipt]:
        return list(self._receipt_log)
