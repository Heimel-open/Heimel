"""
VACS session state gate.

Small recovered Fidelity gate for bounded state transitions. It maps outcomes to
existing ACS/VACS decisions and signs gate receipts with the session key.
"""

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

try:
    from .intent_session import IntentSession
    from .session_key import sign_session_payload, verify_session_payload
except ImportError:
    from intent_session import IntentSession
    from session_key import sign_session_payload, verify_session_payload


@dataclass(frozen=True)
class AgentState:
    data: Any
    state_hash: str
    step_number: int = 0
    checkpoint_id: str = ""

    @staticmethod
    def compute_hash(data: Any) -> str:
        normalized = json.dumps(data, sort_keys=True, default=str, ensure_ascii=False)
        return hashlib.sha256(normalized.encode()).hexdigest()[:32]

    @classmethod
    def from_data(cls, data: Any, step_number: int = 0, checkpoint_id: str = "") -> "AgentState":
        return cls(
            data=data,
            state_hash=cls.compute_hash(data),
            step_number=step_number,
            checkpoint_id=checkpoint_id,
        )


@dataclass(frozen=True)
class StateDiff:
    operations: List[str] = field(default_factory=list)
    modifications_count: int = 0
    insertions_count: int = 0
    deletions_count: int = 0
    is_structural: bool = False

    @classmethod
    def compute(cls, previous: AgentState, proposed: AgentState) -> "StateDiff":
        previous_data = previous.data if isinstance(previous.data, dict) else {}
        proposed_data = proposed.data if isinstance(proposed.data, dict) else {}
        operations: List[str] = []
        insertions = 0
        deletions = 0
        modifications = 0

        for key in proposed_data:
            if key not in previous_data:
                insertions += 1
                operations.append(f"add:{key}")

        for key in previous_data:
            if key not in proposed_data:
                deletions += 1
                operations.append(f"delete:{key}")

        for key in previous_data:
            if key in proposed_data and previous_data[key] != proposed_data[key]:
                modifications += 1
                operations.append(f"modify:{key}")

        return cls(
            operations=operations,
            modifications_count=modifications,
            insertions_count=insertions,
            deletions_count=deletions,
            is_structural=bool(insertions or deletions),
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "operations": list(self.operations),
            "modifications_count": self.modifications_count,
            "insertions_count": self.insertions_count,
            "deletions_count": self.deletions_count,
            "is_structural": self.is_structural,
        }


@dataclass(frozen=True)
class GateReceipt:
    receipt_id: str
    session_id: str
    key_id: str
    decision: str
    timestamp: float
    previous_state_hash: str
    proposed_state_hash: str
    diff_summary: Dict[str, object]
    policy_version: str
    hmac_signature: str

    def signing_payload(self) -> str:
        return json.dumps({
            "receipt_id": self.receipt_id,
            "session_id": self.session_id,
            "key_id": self.key_id,
            "decision": self.decision,
            "timestamp": self.timestamp,
            "previous_state_hash": self.previous_state_hash,
            "proposed_state_hash": self.proposed_state_hash,
            "diff_summary": self.diff_summary,
            "policy_version": self.policy_version,
        }, sort_keys=True, ensure_ascii=False)

    def verify(self, session_key: bytes) -> bool:
        return verify_session_payload(session_key, self.signing_payload(), self.hmac_signature)

    def to_dict(self) -> Dict[str, object]:
        return {
            "receipt_id": self.receipt_id,
            "session_id": self.session_id,
            "key_id": self.key_id,
            "decision": self.decision,
            "timestamp": self.timestamp,
            "previous_state_hash": self.previous_state_hash,
            "proposed_state_hash": self.proposed_state_hash,
            "diff_summary": self.diff_summary,
            "policy_version": self.policy_version,
            "hmac_signature": self.hmac_signature,
        }


class SessionStateGate:
    POLICY_VERSION = "vacs-session-gate-v0.1"

    def __init__(self, intent_session: IntentSession, session_key: bytes, key_id: str):
        self.intent_session = intent_session
        self.session_key = session_key
        self.key_id = key_id
        self.decision_log: List[GateReceipt] = []

    def evaluate(self, previous: AgentState, proposed: AgentState) -> Tuple[str, GateReceipt]:
        diff = StateDiff.compute(previous, proposed)
        decision = self._decision_for(diff, proposed)
        receipt = self._receipt(decision, previous, proposed, diff)
        self.decision_log.append(receipt)
        return decision, receipt

    def _decision_for(self, diff: StateDiff, proposed: AgentState) -> str:
        if not self.intent_session.is_within_hours():
            return "DENY"
        if proposed.step_number > self.intent_session.max_steps:
            return "STEP_UP"
        for operation in diff.operations:
            operation_type = operation.split(":", 1)[0]
            if not self.intent_session.is_operation_allowed(operation_type):
                return "DENY"
        if diff.is_structural:
            return "STEP_UP"
        return "ALLOW"

    def _receipt(self, decision: str, previous: AgentState, proposed: AgentState, diff: StateDiff) -> GateReceipt:
        unsigned = GateReceipt(
            receipt_id=str(uuid.uuid4()),
            session_id=self.intent_session.session_id,
            key_id=self.key_id,
            decision=decision,
            timestamp=time.time(),
            previous_state_hash=previous.state_hash,
            proposed_state_hash=proposed.state_hash,
            diff_summary=diff.to_dict(),
            policy_version=self.POLICY_VERSION,
            hmac_signature="",
        )
        signature = sign_session_payload(self.session_key, unsigned.signing_payload())
        return GateReceipt(
            receipt_id=unsigned.receipt_id,
            session_id=unsigned.session_id,
            key_id=unsigned.key_id,
            decision=unsigned.decision,
            timestamp=unsigned.timestamp,
            previous_state_hash=unsigned.previous_state_hash,
            proposed_state_hash=unsigned.proposed_state_hash,
            diff_summary=unsigned.diff_summary,
            policy_version=unsigned.policy_version,
            hmac_signature=signature,
        )