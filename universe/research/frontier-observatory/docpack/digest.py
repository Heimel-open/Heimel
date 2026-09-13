"""Deterministic canonical serialization and digest helpers for docpack.

Every contract in this package hashes a canonical JSON encoding of its
content, so identical logical content always yields identical digests
regardless of construction order, key ordering or float formatting.
"""

from __future__ import annotations

import enum
import hashlib
import json
from typing import Any

HASH_ALGORITHM = "sha256"


def _canonical_float(value: float) -> str:
    """Render a float in a byte-stable, sign-stable form."""
    if value != value:  # NaN
        return "nan"
    if value == float("inf"):
        return "inf"
    if value == float("-inf"):
        return "-inf"
    if value == 0.0:
        return "0"
    rendered = f"{value:.8f}".rstrip("0").rstrip(".")
    return rendered if rendered not in ("-0", "") else "0"


def _canonical(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if value is None or isinstance(value, (int, str)):
        return value
    if isinstance(value, float):
        return _canonical_float(value)
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, (list, tuple)):
        return [_canonical(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _canonical(v) for k, v in value.items()}
    if hasattr(value, "to_canonical"):
        return _canonical(value.to_canonical())
    raise TypeError(f"Cannot canonicalize {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    payload = _canonical(value)
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def digest_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
