"""Signed transport envelope — vendor-neutral delivery binding.

This module binds an already-sealed canonical artifact (for example an
``ExternalProviderRequest``) to a transport target (a Kafka topic or a NATS
subject) with an Ed25519 signature over ``(domain, envelope_digest)``.

The signature proves *integrity, signer authenticity and exact binding* of the
delivery envelope. It does NOT prove that the enclosed artifact is
authorised, and it creates no authority of any kind. A transport envelope is a
delivery receipt, not an execution decision.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Literal, Protocol

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..contracts import canonical_digest

TRANSPORT_SIGNATURE_DOMAIN = b"VALO-TRANSPORT-ENVELOPE-V1\x00"


class TransportKind(StrEnum):
    KAFKA = "KAFKA"
    NATS = "NATS"


class TransportArtifactSigner(Protocol):
    signer_id: str
    key_id: str
    algorithm: str

    def sign(self, payload: bytes) -> str: ...


@dataclass(frozen=True)
class Ed25519TransportSigner:
    """Thin Ed25519 signer compatible with the contract layer's signer shape."""

    signer_id: str
    key_id: str
    _private_key: Ed25519PrivateKey
    algorithm: str = "Ed25519"

    @classmethod
    def from_private_key_bytes(
        cls, *, signer_id: str, key_id: str, private_key_bytes: bytes
    ) -> Ed25519TransportSigner:
        return cls(
            signer_id=signer_id,
            key_id=key_id,
            _private_key=Ed25519PrivateKey.from_private_bytes(private_key_bytes),
        )

    @property
    def public_key(self) -> Ed25519PublicKey:
        return self._private_key.public_key()

    def sign(self, payload: bytes) -> str:
        raw = self._private_key.sign(payload)
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _signature_input(domain: bytes, digest: str) -> bytes:
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise ValueError("signature digest must be a lowercase SHA-256 hex digest")
    return domain + digest.encode("ascii")


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


def _require_digest(value: str, field_name: str) -> None:
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 hex digest")


def _require_nonempty(value: str, field_name: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"{field_name} is required")


TransportPayloadValue = str | int | bool | float | None


class SignedTransportEnvelope(BaseModel):
    """A signed delivery envelope for one canonical artifact.

    The envelope carries an opaque reference to the enclosed artifact
    (``artifact_ref`` / ``artifact_digest``); it does not interpret or re-author
    the artifact. Its only authority effect is ``NO_AUTHORITY_CREATION``.
    """

    schema_version: Literal["transport_envelope.v1"] = "transport_envelope.v1"
    transport: TransportKind
    target: str
    message_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifact_ref: str
    artifact_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    transport_payload: dict[str, TransportPayloadValue]
    transport_payload_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    nonce: str
    signer_id: str
    key_id: str
    signed_at: datetime
    envelope_digest: str = ""
    transport_signature: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False
    can_create_authority: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(
            mode="json",
            exclude={"envelope_digest", "transport_signature"},
        )

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_envelope(self) -> SignedTransportEnvelope:
        for value, field_name in (
            (self.target, "target"),
            (self.artifact_ref, "artifact_ref"),
            (self.nonce, "nonce"),
            (self.signer_id, "signer_id"),
            (self.key_id, "key_id"),
        ):
            _require_nonempty(value, field_name)
        _require_aware(self.signed_at, "signed_at")
        if not self.nonce.strip():
            raise ValueError("transport envelope nonce must not be blank")
        if not self.transport_payload:
            raise ValueError("transport_payload must not be empty")
        if self.transport_payload_digest != canonical_digest(self.transport_payload):
            raise ValueError("transport payload digest mismatch")
        if self.envelope_digest and self.envelope_digest != self.computed_digest:
            raise ValueError("transport envelope digest mismatch")
        return self


def seal_transport_envelope(
    *,
    transport: TransportKind,
    target: str,
    artifact_ref: str,
    artifact_digest: str,
    transport_payload: dict[str, TransportPayloadValue],
    signer: TransportArtifactSigner,
    nonce: str,
    signed_at: datetime,
) -> SignedTransportEnvelope:
    """Seal a signed transport envelope.

    Fails closed if the signer is not Ed25519, the artifact digest is malformed,
    or the payload digest does not match the provided payload.
    """
    if signer.algorithm != "Ed25519":
        raise ValueError("unsupported signature algorithm")
    _require_nonempty(target, "target")
    _require_nonempty(artifact_ref, "artifact_ref")
    _require_digest(artifact_digest, "artifact_digest")
    _require_nonempty(nonce, "nonce")
    if not nonce.strip():
        raise ValueError("transport envelope nonce must not be blank")
    if not transport_payload:
        raise ValueError("transport_payload must not be empty")
    _require_aware(signed_at, "signed_at")
    if signed_at.utcoffset() is None:
        raise ValueError("signed_at must be timezone-aware")

    payload_digest = canonical_digest(transport_payload)
    if payload_digest != canonical_digest(transport_payload):  # sanity, idempotent
        raise ValueError("transport payload digest mismatch")
    message_id = canonical_digest(
        {
            "transport": transport.value,
            "target": target,
            "artifact_digest": artifact_digest,
            "transport_payload_digest": payload_digest,
            "nonce": nonce,
        }
    )
    unsealed = SignedTransportEnvelope(
        transport=transport,
        target=target,
        message_id=message_id,
        artifact_ref=artifact_ref,
        artifact_digest=artifact_digest,
        transport_payload=transport_payload,
        transport_payload_digest=payload_digest,
        nonce=nonce,
        signer_id=signer.signer_id,
        key_id=signer.key_id,
        signed_at=signed_at,
    )
    envelope_digest = unsealed.computed_digest
    signature = signer.sign(_signature_input(TRANSPORT_SIGNATURE_DOMAIN, envelope_digest))
    return SignedTransportEnvelope.model_validate(
        {
            **unsealed.model_dump(mode="python"),
            "envelope_digest": envelope_digest,
            "transport_signature": signature,
        }
    )


def verify_transport_envelope(
    *,
    envelope: SignedTransportEnvelope,
    public_key: Ed25519PublicKey,
) -> None:
    """Verify integrity and signature. Raises ValueError on any failure (fail closed)."""
    if envelope.envelope_digest != envelope.computed_digest:
        raise ValueError("transport envelope is unsealed or tampered")
    if not envelope.transport_signature:
        raise ValueError("transport envelope signature is required")
    try:
        public_key.verify(
            _b64url_decode(envelope.transport_signature),
            _signature_input(TRANSPORT_SIGNATURE_DOMAIN, envelope.envelope_digest),
        )
    except (InvalidSignature, ValueError) as exc:
        raise ValueError("transport envelope signature verification failed") from exc
