"""
ACS Receipt Generator v0.1
Generates attestation receipts after each decision.
"""

import json
import hashlib
import hmac
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from enum import Enum

try:
    from .session_key import sign_session_payload, verify_session_payload
except ImportError:
    from session_key import sign_session_payload, verify_session_payload


COHERENCE_EVIDENCE_KEY = "vaig_coherence_evaluation"


class Decision(Enum):
    ALLOW = "ALLOW"
    MODIFY = "MODIFY"
    DEFER = "DEFER"
    DENY = "DENY"
    STEP_UP = "STEP_UP"
    HALT = "HALT"


class ACSReceiptGenerator:
    """Generates cryptographically verifiable attestation receipts."""

    def generate(self, packet: Dict[str, Any], decision: Decision) -> Dict[str, Any]:
        evidence = packet.get("evidence", {})
        action_hash = self._hash_dict(packet.get("intent", {}))
        input_hash = self._hash_dict(evidence)
        policy_hash = self._hash_dict(packet.get("policy", {}))
        coherence = self._coherence_receipt_fields(evidence)

        receipt = {
            "receipt_id": str(uuid.uuid4()),
            "packet_id": packet.get("packet_id"),
            "action_hash": action_hash,
            "input_hash": input_hash,
            "policy_hash": policy_hash,
            "decision": decision.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "signature": self._sign_receipt(action_hash, input_hash, policy_hash, decision.value),
            **coherence,
        }

        return receipt

    def generate_session_bound(
        self,
        packet: Dict[str, Any],
        decision: Decision,
        session_id: str,
        key_id: str,
        session_key: bytes,
        previous_state_hash: Optional[str] = None,
        proposed_state_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a receipt bound to one authority session.

        This extends the existing ACS receipt shape without replacing it. The
        HMAC signature proves the receipt belongs to the bounded session context.
        """
        if not session_id:
            raise ValueError("session_id is required")
        if not key_id:
            raise ValueError("key_id is required")

        receipt = self.generate(packet, decision)
        receipt.update({
            "session_id": session_id,
            "key_id": key_id,
            "previous_state_hash": previous_state_hash,
            "proposed_state_hash": proposed_state_hash,
            "session_signature_alg": "hmac-sha256",
        })
        payload = self.session_signing_payload(receipt)
        receipt["session_signature"] = sign_session_payload(session_key, payload)
        return receipt

    def verify_session_bound(self, receipt: Dict[str, Any], session_key: bytes) -> bool:
        signature = receipt.get("session_signature")
        if not signature:
            return False
        payload = self.session_signing_payload(receipt)
        return verify_session_payload(session_key, payload, signature)

    def session_signing_payload(self, receipt: Dict[str, Any]) -> str:
        payload = {
            "receipt_id": receipt.get("receipt_id"),
            "packet_id": receipt.get("packet_id"),
            "action_hash": receipt.get("action_hash"),
            "input_hash": receipt.get("input_hash"),
            "policy_hash": receipt.get("policy_hash"),
            "decision": receipt.get("decision"),
            "timestamp": receipt.get("timestamp"),
            "vaig_coherence_result_digest": receipt.get("vaig_coherence_result_digest"),
            "vaig_coherence_status": receipt.get("vaig_coherence_status"),
            "session_id": receipt.get("session_id"),
            "key_id": receipt.get("key_id"),
            "previous_state_hash": receipt.get("previous_state_hash"),
            "proposed_state_hash": receipt.get("proposed_state_hash"),
        }
        return json.dumps(payload, sort_keys=True, ensure_ascii=False)

    def _coherence_receipt_fields(self, evidence: Any) -> Dict[str, Any]:
        if not isinstance(evidence, dict):
            return {}
        binding = evidence.get(COHERENCE_EVIDENCE_KEY)
        if not isinstance(binding, dict):
            return {}
        result = binding.get("result")
        if not isinstance(result, dict):
            result = {}
        return {
            "vaig_coherence_result_digest": binding.get("result_digest"),
            "vaig_coherence_status": result.get("status"),
        }

    def _hash_dict(self, data: Dict[str, Any]) -> str:
        normalized = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return f"sha256:{hashlib.sha256(normalized.encode()).hexdigest()}"

    def _sign_receipt(self, *components) -> str:
        payload = "".join(components)
        return f"ed25519:{hashlib.sha256(payload.encode()).hexdigest()[:64]}"