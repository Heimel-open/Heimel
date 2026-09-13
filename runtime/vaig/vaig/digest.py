"""Canonical digest helpers for VAIG — deterministic SHA-256 over stable JSON."""

from __future__ import annotations

import hashlib
import json
from typing import Any

CANONICALIZATION_ALGORITHM = "sha256-stable-json"


def canonical_digest(value: Any) -> str:
    """Return ``sha256:<hex>`` over the stable-JSON serialization of ``value``."""
    return "sha256:" + hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def stable_json(value: Any) -> str:
    """Recursively serialize JSON with sorted keys, compact separators."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
