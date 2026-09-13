"""
VACS session key primitives.

Recovered from VAIG Fidelity as the session-security substrate for ACS/VACS.
Provides per-session HMAC keys, rotation checks, and revocation tracking.
"""

import hashlib
import hmac
import os
import time
from dataclasses import dataclass, field
from typing import Set, Tuple


HKDF_INFO_PREFIX = b"VACS-session-signing-v1"


def _hkdf_extract(salt: bytes, ikm: bytes) -> bytes:
    return hmac.new(salt, ikm, hashlib.sha256).digest()


def _hkdf_expand(prk: bytes, info: bytes, length: int = 32) -> bytes:
    output = b""
    previous = b""
    counter = 1

    while len(output) < length:
        previous = hmac.new(prk, previous + info + bytes([counter]), hashlib.sha256).digest()
        output += previous
        counter += 1

    return output[:length]


def derive_session_key(fleet_secret: bytes, session_id: str) -> bytes:
    """Derive a 32-byte per-session HMAC key using HKDF-SHA256."""
    if len(fleet_secret) < 32:
        raise ValueError("fleet_secret must be at least 32 bytes")
    if not session_id:
        raise ValueError("session_id is required")

    session_bytes = session_id.encode()
    prk = _hkdf_extract(salt=session_bytes, ikm=fleet_secret)
    return _hkdf_expand(prk, info=HKDF_INFO_PREFIX + session_bytes, length=32)


@dataclass
class SessionKeyManager:
    """Manages session key derivation, rotation, and revocation."""

    fleet_secret: bytes
    max_secret_age_days: int = 90
    _revoked_key_ids: Set[str] = field(default_factory=set)
    _secret_created_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if len(self.fleet_secret) < 32:
            raise ValueError("fleet_secret must be at least 32 bytes")

    def derive(self, session_id: str) -> Tuple[bytes, str]:
        self._check_rotation_due()
        key_id = self.key_id_for(session_id)
        if key_id in self._revoked_key_ids:
            raise ValueError(f"key_id '{key_id}' has been revoked")
        return derive_session_key(self.fleet_secret, session_id), key_id

    def revoke(self, key_id: str) -> None:
        self._revoked_key_ids.add(key_id)

    def is_revoked(self, key_id: str) -> bool:
        return key_id in self._revoked_key_ids

    def revoked_key_ids(self) -> list:
        return sorted(self._revoked_key_ids)

    def apply_revocation_list(self, key_ids: list) -> None:
        self._revoked_key_ids.update(key_ids)

    def secret_age_days(self) -> float:
        return (time.time() - self._secret_created_at) / 86400

    def is_rotation_due(self) -> bool:
        return self.secret_age_days() >= self.max_secret_age_days

    def rotate(self, new_fleet_secret: bytes) -> None:
        if len(new_fleet_secret) < 32:
            raise ValueError("new_fleet_secret must be at least 32 bytes")
        self.fleet_secret = new_fleet_secret
        self._secret_created_at = time.time()

    def _check_rotation_due(self) -> None:
        if self.is_rotation_due():
            raise RuntimeError("fleet_secret rotation is due before deriving new session keys")

    @staticmethod
    def key_id_for(session_id: str) -> str:
        if not session_id:
            raise ValueError("session_id is required")
        return session_id[:12]

    @classmethod
    def generate(cls, max_secret_age_days: int = 90) -> "SessionKeyManager":
        return cls(os.urandom(32), max_secret_age_days=max_secret_age_days)


def sign_session_payload(session_key: bytes, payload: str) -> str:
    return hmac.new(session_key, payload.encode(), hashlib.sha256).hexdigest()


def verify_session_payload(session_key: bytes, payload: str, signature: str) -> bool:
    expected = sign_session_payload(session_key, payload)
    return hmac.compare_digest(expected, signature)