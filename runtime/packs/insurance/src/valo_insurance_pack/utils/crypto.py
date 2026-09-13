from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from typing import Any


def utcnow() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(UTC)


def iso_format(dt: datetime) -> str:
    """Format datetime as UTC ISO-8601 string with Z suffix."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def parse_iso(ts: str) -> datetime:
    """Parse ISO-8601 string into timezone-aware UTC datetime."""
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def canonical_json_bytes(obj: Any) -> bytes:
    """Canonicalize a JSON-serializable object into deterministic UTF-8 bytes.

    Uses RFC 8785 (JCS) as the single canonical scheme. Digest determinism is a
    core integrity property of this product, so there is intentionally no
    fallback: a silently different canonical form across environments would
    break verification. If ``rfc8785`` is unavailable the caller fails loudly.
    """
    import rfc8785

    return rfc8785.dumps(obj)


def canonical_json_str(obj: Any) -> str:
    """Return canonical JSON as string."""
    return canonical_json_bytes(obj).decode("utf-8")


def sha256_digest(obj: Any) -> str:
    """Compute sha256 digest of canonical representation prefixed with 'sha256:'."""
    if isinstance(obj, bytes):
        h = sha256(obj).hexdigest()
    elif isinstance(obj, str):
        h = sha256(obj.encode("utf-8")).hexdigest()
    else:
        h = sha256(canonical_json_bytes(obj)).hexdigest()
    return f"sha256:{h}"


def verify_digest(obj: Any, expected_digest: str) -> bool:
    """Check if object digest matches expected digest."""
    return sha256_digest(obj) == expected_digest
