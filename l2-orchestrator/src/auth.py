from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from enum import Enum

class Role(Enum):
    OPERATOR = 1      # 1-person, routine
    MANAGER = 2       # 2-person, critical
    ADMINISTRATOR = 3 # Hardware token, existential

@dataclass
class AuthSession:
    role: Role
    tokens_validated: int
    start_time: float
    is_active: bool = False
    token_ids: tuple[str, ...] = ()
    expires_at: float = 0.0
    nonce: str = ""
    session_proof: str = ""

class YubiKeyOrchestrator:
    """
    Simulates hierarchical authorization using YubiKey 5 FIPS.
    In production, this interfaces with the yubico-python library.
    """
    def __init__(self):
        # Hardcoded serial numbers for 2-person control simulation
        self.authorized_keys = {
            "SER-VALO-001": "Manager_A",
            "SER-VALO-002": "Manager_B",
            "SER-VALO-999": "Admin_Root"
        }
        self.revoked_keys: set[str] = set()
        self._consumed_nonces: set[str] = set()
        self._consumed_proofs: set[str] = set()
        self._handshake_secret = secrets.token_hex(32)
        self.session = None

    def initiate_handshake(self, role: Role, presented_keys: tuple[str, ...] | list[str] | None = None):
        print(f"[AUTH] Initiating handshake for {role.name}...")
        now = time.time()
        keys = tuple(presented_keys or ())
        nonce = f"{role.name.lower()}-{int(now * 1_000_000)}"
        self.session = AuthSession(
            role=role,
            tokens_validated=0,
            start_time=now,
            token_ids=keys,
            expires_at=now + 300.0,
            nonce=nonce,
        )

        if role == Role.OPERATOR:
            self._validate_operator()
        elif role == Role.MANAGER:
            self._validate_manager()
        elif role == Role.ADMINISTRATOR:
            raise NotImplementedError(
                "ADMINISTRATOR role requires hardware token — not implemented in simulation"
            )

        if self.session and self.session.is_active:
            self.session.session_proof = self._sign_session(self.session)

    def _validate_operator(self):
        # Standard PIN + TOTP simulation
        self.session.tokens_validated = 1
        self.session.is_active = True
        self.session.token_ids = ("OPERATOR_PIN",)
        print("[AUTH] Operator validated (PIN+TOTP). Mode: ACTIVE")

    def _validate_manager(self):
        # 2-person control: Requires two distinct YubiKeys
        print("[AUTH] Waiting for 2x YubiKey 5 FIPS tokens...")
        keys = tuple(dict.fromkeys(self.session.token_ids))
        valid_keys = [key for key in keys if key in self.authorized_keys and key not in self.revoked_keys]
        if len(valid_keys) != 2:
            self.session.tokens_validated = len(valid_keys)
            self.session.is_active = False
            print("[AUTH] 2-person control failed. Critical override DISABLED.")
            return

        self.session.token_ids = tuple(valid_keys)
        self.session.tokens_validated = 2
        self.session.is_active = True
        print("[AUTH] 2-person control verified. Critical override ENABLED.")

    def _sign_session(self, session: AuthSession) -> str:
        payload = "|".join(
            [
                session.role.name,
                str(session.tokens_validated),
                repr(session.start_time),
                repr(session.expires_at),
                session.nonce,
                ",".join(session.token_ids),
            ]
        )
        return hmac.new(
            self._handshake_secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def check_integrity(self):
        if not self.session or not self.session.is_active:
            return False
        if time.time() > self.session.expires_at:
            return False
        expected_proof = self._sign_session(self.session)
        if (
            not self.session.session_proof
            or self.session.session_proof in self._consumed_proofs
            or not hmac.compare_digest(self.session.session_proof, expected_proof)
        ):
            return False

        if self.session.role == Role.MANAGER:
            if self.session.tokens_validated < 2:
                return False
            if len(self.session.token_ids) != 2:
                return False
            if len(set(self.session.token_ids)) != 2:
                return False
            if any(key not in self.authorized_keys for key in self.session.token_ids):
                return False
            if any(key in self.revoked_keys for key in self.session.token_ids):
                return False
            if not self.session.nonce or self.session.nonce in self._consumed_nonces:
                return False
            self._consumed_nonces.add(self.session.nonce)

        self._consumed_proofs.add(self.session.session_proof)

        return True
