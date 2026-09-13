"""WORM audit log — SHA-256 hash-chained, append-only, authenticated encrypted content."""

import base64
import hashlib
import json
import os
import fcntl
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
except ImportError:  # pragma: no cover - optional dependency
    ChaCha20Poly1305 = None

_NONCE_SIZE = 12


def _require_crypto() -> None:
    if ChaCha20Poly1305 is None:
        raise ImportError(
            "cryptography is required for WORMLog encryption; "
            "install it with 'pip install cryptography>=41'"
        )


def _encrypt(data: str, key: bytes) -> Tuple[str, str]:
    """AEAD-encrypt (ChaCha20-Poly1305) with a fresh random nonce.

    Returns (base64 ciphertext, base64 nonce). The same plaintext under the
    same key produces distinct ciphertext per entry, and any tampering with the
    ciphertext or nonce fails authentication on decrypt.
    """
    _require_crypto()
    nonce = os.urandom(_NONCE_SIZE)
    ciphertext = ChaCha20Poly1305(key).encrypt(nonce, data.encode("utf-8"), None)
    return (
        base64.b64encode(ciphertext).decode(),
        base64.b64encode(nonce).decode(),
    )


def _decrypt(data: str, nonce: str, key: bytes) -> str:
    """Authenticated decrypt; raises on tampered ciphertext or wrong key."""
    _require_crypto()
    raw = base64.b64decode(data.encode())
    raw_nonce = base64.b64decode(nonce.encode())
    plaintext = ChaCha20Poly1305(key).decrypt(raw_nonce, raw, None)
    return plaintext.decode("utf-8")


class WORMLog:
    """
    Write-Once-Read-Many audit log.

    Every entry is linked to the previous via SHA-256 hash chain.
    Tamper-evident: any modification breaks the chain.

    Two audit levels — both active simultaneously if encryption_key is set:

      Level 1 (always): SHA-256 hashes of prompt + response.
        Proves what was said without revealing content.
        Sufficient for integrity verification.

      Level 2 (with encryption_key): authenticated encrypted (ChaCha20-Poly1305,
        fresh nonce per entry) prompt + response stored in entry.
        Customer holds the key — VALO never sees plaintext.
        Sufficient for full EU AI Act Article 12/13 reconstruction.

    Usage:
        # Hash-only (default)
        worm = WORMLog("audit.jsonl")

        # Hash + encrypted content
        key = os.urandom(32)  # store securely — customer owns this
        worm = WORMLog("audit.jsonl", encryption_key=key)

        worm.append("req-123", data, prompt="What is the dose?", response="Take 500mg.")
    """

    def __init__(
        self,
        path: str = "vaig_audit.jsonl",
        encryption_key: Optional[bytes] = None,
    ):
        self.path = Path(path)
        # Normalize any key length to the 32-byte ChaCha20-Poly1305 key size.
        self._key = (
            hashlib.sha256(encryption_key).digest()
            if encryption_key is not None
            else None
        )
        if encryption_key is not None:
            _require_crypto()
        self._prev_hash = self._load_tail_hash()
        self._lock = threading.Lock()

    def _load_tail_hash(self) -> str:
        if not self.path.exists():
            return "genesis"
        try:
            lines = self.path.read_text().strip().splitlines()
            if lines:
                last = json.loads(lines[-1])
                return last.get("hash", "genesis")
        except Exception:
            pass
        return "genesis"

    def append(
        self,
        entry_id: str,
        data: Dict[str, Any],
        prompt: Optional[str] = None,
        response: Optional[str] = None,
    ) -> str:
        with self._lock:
            payload: Dict[str, Any] = {
                "id": entry_id,
                "ts": time.time(),
                "prev": self._prev_hash,
                **data,
            }

            # Level 1 — always: full SHA-256 of prompt and response
            if prompt is not None:
                payload["prompt_sha256"] = hashlib.sha256(prompt.encode()).hexdigest()
            if response is not None:
                payload["response_sha256"] = hashlib.sha256(response.encode()).hexdigest()

            # Level 2 — if encryption key set: encrypted content
            if self._key is not None:
                if prompt is not None:
                    enc, nonce = _encrypt(prompt, self._key)
                    payload["prompt_enc"] = enc
                    payload["prompt_nonce"] = nonce
                if response is not None:
                    enc, nonce = _encrypt(response, self._key)
                    payload["response_enc"] = enc
                    payload["response_nonce"] = nonce

            raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
            h = hashlib.sha256(raw.encode()).hexdigest()
            payload["hash"] = h

            # Process-safe append via fcntl exclusive lock
            with self.path.open("a", encoding="utf-8") as f:
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    f.write(json.dumps(payload, ensure_ascii=False) + "\n")
                    f.flush()
                    os.fsync(f.fileno())
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            self._prev_hash = h
            return h

    def verify(self) -> bool:
        """Verify full chain integrity. Returns True if intact."""
        if not self.path.exists():
            return True
        prev = "genesis"
        for line in self.path.read_text().strip().splitlines():
            try:
                entry = json.loads(line)
                stored_hash = entry.pop("hash")
                raw = json.dumps(entry, sort_keys=True, ensure_ascii=False)
                computed = hashlib.sha256(raw.encode()).hexdigest()
                if computed != stored_hash or entry.get("prev") != prev:
                    return False
                prev = stored_hash
            except Exception:
                return False
        return True

    def decrypt_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt prompt_enc and response_enc in an entry.
        Returns entry with prompt_plaintext and response_plaintext added.
        Requires encryption_key to be set.
        """
        if self._key is None:
            raise ValueError("Ingen krypteringsnøkkel satt — kan ikke dekryptere")
        result = dict(entry)
        if "prompt_enc" in entry:
            result["prompt_plaintext"] = _decrypt(
                entry["prompt_enc"], entry["prompt_nonce"], self._key
            )
        if "response_enc" in entry:
            result["response_plaintext"] = _decrypt(
                entry["response_enc"], entry["response_nonce"], self._key
            )
        return result

    def read_all(self) -> list[Dict[str, Any]]:
        """Return all entries as dicts."""
        if not self.path.exists():
            return []
        entries = []
        for line in self.path.read_text().strip().splitlines():
            try:
                entries.append(json.loads(line))
            except Exception:
                pass
        return entries
