"""
VACS signed intent session.

Recovered from VAIG Fidelity as the session authority contract. This is not an
EvidenceCondition. EvidenceCondition governs premise admissibility; IntentSession
bounds what one authority session may attempt.
"""

import hashlib
import hmac
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class IntentSession:
    session_id: str
    intent_id: str
    signed_by: str
    signature: str
    target_schema: str = "generic-json"
    max_steps: int = 20
    human_gate_interval: int = 5
    max_retries_per_step: int = 3
    completion_criteria: Dict[str, Any] = field(default_factory=dict)
    allowed_operations: List[str] = field(default_factory=lambda: ["add", "modify", "delete"])
    prohibited_operations: List[str] = field(default_factory=list)
    allowed_hours: Optional[Tuple[int, int]] = None
    domain: str = "generic"

    def signing_payload(self) -> str:
        return f"{self.session_id}:{self.intent_id}:{self.signed_by}:{self.target_schema}"

    def verify_signature(self, signing_key: bytes) -> bool:
        if not self.signature.startswith("hmac-sha256:"):
            return False
        digest = self.signature[12:]
        if len(digest) != 64:
            return False
        expected = hmac.new(signing_key, self.signing_payload().encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, digest)

    @staticmethod
    def sign(session_id: str, intent_id: str, signed_by: str, target_schema: str, signing_key: bytes) -> str:
        payload = f"{session_id}:{intent_id}:{signed_by}:{target_schema}"
        digest = hmac.new(signing_key, payload.encode(), hashlib.sha256).hexdigest()
        return f"hmac-sha256:{digest}"

    def is_operation_allowed(self, operation: str) -> bool:
        if operation in self.prohibited_operations:
            return False
        if self.allowed_operations:
            return operation in self.allowed_operations
        return True

    def is_within_hours(self) -> bool:
        if self.allowed_hours is None:
            return True
        current_hour = time.localtime().tm_hour
        start_hour, end_hour = self.allowed_hours
        return start_hour <= current_hour < end_hour

    def is_complete(self, data: Dict[str, Any]) -> bool:
        if not self.completion_criteria:
            return False
        return all(data.get(key) == value for key, value in self.completion_criteria.items())

    def to_authority_profile(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "intent_id": self.intent_id,
            "signed_by": self.signed_by,
            "domain": self.domain,
            "target_schema": self.target_schema,
            "max_steps": self.max_steps,
            "human_gate_interval": self.human_gate_interval,
            "allowed_operations": list(self.allowed_operations),
            "prohibited_operations": list(self.prohibited_operations),
            "allowed_hours": list(self.allowed_hours) if self.allowed_hours else None,
        }