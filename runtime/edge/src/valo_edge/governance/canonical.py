"""Embedded canonical digest — stdlib-only RFC 8785-compatible hashing.

For embedded devices we cannot depend on ``rfc8785``. This module provides a
deterministic, canonically-serialised SHA-256 digest using only the stdlib.
It mirrors ``valo_platform.canonical`` semantics so digests are portable
between platform and edge while staying dependency-free on-device.

Canonical form (RFC 8785 subset):
- keys sorted lexicographically
- no insignificant whitespace
- strings, numbers, booleans, null, arrays, objects

NOTE: JSON numbers are serialised by ``json``; for float edge cases use the
``preserve_precision`` path only when exactness matters. The default is
deterministic for integer/bool/str/list/dict payloads.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


class CanonicalizationError(ValueError):
    """Raised when a value cannot be canonically serialised."""


def to_json_value(value: Any) -> Any:
    """Normalise a value into a JSON-serialisable, sortable form."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise CanonicalizationError(f"non-finite float: {value!r}")
        return value
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, (list, tuple)):
        return [to_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_json_value(item) for key, item in value.items()}
    # dataclasses and pydantic-like objects: best-effort attribute dump
    if hasattr(value, "model_dump"):
        return to_json_value(value.model_dump(mode="json"))
    if hasattr(value, "__dict__"):
        return to_json_value(value.__dict__)
    raise CanonicalizationError(f"unsupported type: {type(value)!r}")


def canonical_bytes(value: Any) -> bytes:
    """Return the canonically-serialised bytes for a value."""
    normalized = to_json_value(value)
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def digest_bytes(payload: bytes) -> str:
    """SHA-256 hex digest of raw bytes, matching platform ``sha256:<hex>`` format."""
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def canonical_digest(value: Any) -> str:
    """SHA-256 digest of a value's canonical serialisation (platform-compatible)."""
    return digest_bytes(canonical_bytes(value))


def verify_canonical_digest(value: Any, expected_digest: str) -> bool:
    """Return True if the value's canonical digest equals expected_digest."""
    return canonical_digest(value) == expected_digest
