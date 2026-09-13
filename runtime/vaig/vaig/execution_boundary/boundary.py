from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any, Dict


class BoundaryDecision(Enum):
    PASS = "PASS"
    DEFER = "DEFER"
    HALT = "HALT"


@dataclass
class BoundaryResult:
    decision: BoundaryDecision
    reason: str
    receipt: Dict[str, Any]


class ExecutionBoundary:
    def check(self, intent: Dict[str, Any], evidence: Dict[str, Any] | None = None, context: Dict[str, Any] | None = None) -> BoundaryResult:
        evidence = evidence or {}
        context = context or {}
        required = intent.get("required_authority", intent.get("tool_authority", "none"))
        granted = intent.get("granted_authority", intent.get("task_authority", "none"))
        order = {"none": 0, "read": 1, "write": 2, "send": 3, "execute": 4, "delete": 5}
        if order.get(required, 99) > order.get(granted, -1):
            decision = BoundaryDecision.HALT
            reason = f"authority mismatch: required {required} exceeds granted {granted}"
        elif float(evidence.get("evidence_gap", 0.0)) > 0.5:
            decision = BoundaryDecision.DEFER
            reason = "evidence gap requires review"
        else:
            decision = BoundaryDecision.PASS
            reason = "execution boundary passed"
        receipt = self._receipt(intent, evidence, context, decision, reason)
        return BoundaryResult(decision=decision, reason=reason, receipt=receipt)

    def _receipt(self, intent: Dict[str, Any], evidence: Dict[str, Any], context: Dict[str, Any], decision: BoundaryDecision, reason: str) -> Dict[str, Any]:
        payload = {
            "type": "execution_boundary",
            "version": "0.1",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "intent_hash": self._hash(intent),
            "evidence_hash": self._hash(evidence),
            "context_hash": self._hash(context),
            "decision": decision.value,
            "reason": reason,
        }
        payload["receipt_hash"] = self._hash(payload)
        return payload

    def _hash(self, data: Dict[str, Any]) -> str:
        return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()
