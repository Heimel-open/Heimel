from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

_KEY_ID = re.compile(r"^[A-Za-z0-9._-]+$")


class CredentialStoreError(RuntimeError):
    pass


class CredentialStore(ABC):
    """Credential custody interface.

    Credentials authenticate a principal/device/agent. They never create or own
    authority; logical authority remains governed Kernel state.
    """

    @abstractmethod
    def create_credential(self, key_id: str, passphrase: bytes) -> bytes: ...

    @abstractmethod
    def public_key(self, key_id: str) -> bytes: ...

    @abstractmethod
    def sign(self, key_id: str, payload: bytes, passphrase: bytes) -> bytes: ...

    @abstractmethod
    def verify(self, key_id: str, payload: bytes, signature: bytes) -> bool: ...


class EncryptedFileCredentialStore(CredentialStore):
    """Reference encrypted-file credential backend.

    Production deployments can replace this backend with Secure Enclave, TPM,
    HSM, threshold custody or another implementation without changing authority
    semantics. Private keys are encrypted PKCS#8 files; passphrases are never
    persisted by this class.
    """

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.directory, 0o700)
        except OSError:
            pass

    def _validate_key_id(self, key_id: str) -> str:
        if not key_id or _KEY_ID.fullmatch(key_id) is None:
            raise CredentialStoreError("credential key id contains invalid characters")
        return key_id

    def _private_path(self, key_id: str) -> Path:
        return self.directory / f"{self._validate_key_id(key_id)}.key.pem"

    def _public_path(self, key_id: str) -> Path:
        return self.directory / f"{self._validate_key_id(key_id)}.pub"

    @staticmethod
    def _atomic_write(path: Path, content: bytes, mode: int) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        with temporary.open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)

    def create_credential(self, key_id: str, passphrase: bytes) -> bytes:
        if not passphrase:
            raise CredentialStoreError("credential encryption passphrase is required")
        private_path = self._private_path(key_id)
        public_path = self._public_path(key_id)
        if private_path.exists() or public_path.exists():
            raise CredentialStoreError(f"credential already exists: {key_id}")

        private_key = Ed25519PrivateKey.generate()
        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(passphrase),
        )
        public_bytes = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self._atomic_write(private_path, private_bytes, 0o600)
        try:
            self._atomic_write(public_path, public_bytes, 0o644)
        except Exception:
            private_path.unlink(missing_ok=True)
            raise
        return public_bytes

    def public_key(self, key_id: str) -> bytes:
        path = self._public_path(key_id)
        if not path.exists():
            raise CredentialStoreError(f"unknown credential: {key_id}")
        return path.read_bytes()

    def _load_private(self, key_id: str, passphrase: bytes) -> Ed25519PrivateKey:
        path = self._private_path(key_id)
        if not path.exists():
            raise CredentialStoreError(f"unknown credential: {key_id}")
        try:
            loaded = serialization.load_pem_private_key(
                path.read_bytes(),
                password=passphrase,
            )
        except (TypeError, ValueError) as exc:
            raise CredentialStoreError("credential unlock failed") from exc
        if not isinstance(loaded, Ed25519PrivateKey):
            raise CredentialStoreError("credential is not an Ed25519 key")
        return loaded

    def sign(self, key_id: str, payload: bytes, passphrase: bytes) -> bytes:
        return self._load_private(key_id, passphrase).sign(payload)

    def verify(self, key_id: str, payload: bytes, signature: bytes) -> bool:
        try:
            Ed25519PublicKey.from_public_bytes(self.public_key(key_id)).verify(
                signature,
                payload,
            )
        except (InvalidSignature, ValueError):
            return False
        return True
