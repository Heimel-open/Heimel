from __future__ import annotations

from typing import Any

from ..contracts.common import canonical_digest
from ..contracts.policy import IdempotencyPolicy


def derive_idempotency_key(policy: IdempotencyPolicy, inputs: dict[str, Any]) -> str:
    """Deterministic idempotency-key derivation. Used by both the WRITE
    pipeline and the verify-before-replay path so they agree on the key."""
    if not policy.require_key:
        return ""
    if policy.key_source:
        value = inputs.get(policy.key_source)
        if value is not None:
            return canonical_digest(value)
    return canonical_digest({k: v for k, v in sorted(inputs.items())})
