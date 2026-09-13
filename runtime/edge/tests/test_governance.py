"""Tests for embedded governance primitives (stdlib-only)."""

import pytest

from valo_edge.governance import (
    RateLimiter,
    RevocationLog,
    WormLog,
    canonical_digest,
    verify_canonical_digest,
)


class TestCanonicalDigest:
    def test_deterministic(self):
        assert canonical_digest({"b": 2, "a": 1}) == canonical_digest({"a": 1, "b": 2})

    def test_key_order_independent(self):
        assert canonical_digest({"x": "y", "z": [1, 2]}) == canonical_digest({"z": [1, 2], "x": "y"})

    def test_verify(self):
        d = canonical_digest({"k": "v"})
        assert verify_canonical_digest({"k": "v"}, d)
        assert not verify_canonical_digest({"k": "other"}, d)

    def test_sha256_length(self):
        # Platform-compatible format: "sha256:<64 hex>"
        d = canonical_digest("any")
        assert d.startswith("sha256:")
        assert len(d) == 7 + 64

    def test_rejects_unsupported(self):
        with pytest.raises(Exception):
            canonical_digest(object())


class TestWormLog:
    def test_append_and_verify(self):
        w = WormLog()
        w.append({"source": "sensor", "value": 0.5})
        w.append({"source": "sensor", "value": 0.9})
        assert w.count() == 2
        assert w.verify()

    def test_tamper_detected(self):
        w = WormLog()
        w.append({"source": "a", "value": 1})
        w.append({"source": "b", "value": 2})
        w._entries[0].payload["value"] = 999  # tamper
        assert not w.verify()

    def test_hash_chain(self):
        w = WormLog()
        e1 = w.append({"n": 1})
        e2 = w.append({"n": 2})
        assert e2.prev_hash == e1.entry_hash
        assert w.tail_hash == e2.entry_hash


class TestRevocationLog:
    def test_threshold_required(self):
        r = RevocationLog(threshold=2)
        p = r.propose_revocation("key1", "compromised", "g1", "sig1")
        assert not r.execute(p)  # only 1 vote
        p = r.vote(p, "g2", "sig2")
        assert r.execute(p)
        assert r.is_revoked("key1")
        assert r.verify()

    def test_tamper_detected(self):
        r = RevocationLog(threshold=1)
        p = r.propose_revocation("key1", "compromised", "g1", "sig1")
        r.execute(p)
        r._entries[0]["target_key"] = "hacked"
        assert not r.verify()


class TestRateLimiter:
    def test_allows_within_limit(self):
        rl = RateLimiter(max_requests=2, window_seconds=60)
        assert rl.is_allowed("dev-1", now=100.0)
        assert rl.is_allowed("dev-1", now=100.1)
        assert not rl.is_allowed("dev-1", now=100.2)

    def test_window_resets(self):
        rl = RateLimiter(max_requests=1, window_seconds=10)
        assert rl.is_allowed("dev-1", now=100.0)
        assert not rl.is_allowed("dev-1", now=105.0)
        assert rl.is_allowed("dev-1", now=110.0)  # window expired

    def test_per_key_isolation(self):
        rl = RateLimiter(max_requests=1, window_seconds=60)
        assert rl.is_allowed("a", now=100.0)
        assert rl.is_allowed("b", now=100.0)  # different key unaffected


def test_governance_is_stdlib_only():
    """The embedded governance package must not import third-party deps."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "src" / "valo_edge" / "governance"
    forbidden = {"pydantic", "rfc8785", "numpy", "torch", "cryptography",
                 "fastapi", "requests", "httpx"}
    for path in root.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("from ") or s.startswith("import "):
                for mod in forbidden:
                    assert mod not in s, f"{path.name} imports forbidden {mod}: {s}"
