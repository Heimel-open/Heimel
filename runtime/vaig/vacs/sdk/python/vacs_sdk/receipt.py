import hashlib
import json
import time
import uuid
from dataclasses import asdict

from .schema import ExecutionRequest, Receipt, VerificationResult


def _stable_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def issue_receipt(
    request: ExecutionRequest,
    result: VerificationResult,
    previous_hash: str | None = None,
) -> Receipt:
    timestamp = time.time_ns()
    request_hash = _stable_hash(asdict(request))
    base = {
        "timestamp": timestamp,
        "request_hash": request_hash,
        "decision": result.decision.value,
        "status": result.status.value,
        "reason": result.reason,
        "previous_hash": previous_hash,
    }
    receipt_hash = _stable_hash(base)
    return Receipt(
        receipt_id=str(uuid.uuid4()),
        timestamp=timestamp,
        request_hash=request_hash,
        decision=result.decision,
        status=result.status,
        reason=result.reason,
        previous_hash=previous_hash,
        receipt_hash=receipt_hash,
    )
