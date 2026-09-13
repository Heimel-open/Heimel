"""Cryptographic origin proof for a resolved Kernel execution context.

The proof attests only that one exact context came from a configured Kernel
signer without modification. It does not grant authority, admit truth, or
replace REHT's fresh authorization decision.
"""

from __future__ import annotations

import base64
import re
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Any, Protocol

import rfc8785
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .errors import ExecutionContextError

KERNEL_CONTEXT_ORIGIN_SCHEMA = "kernel_execution_context_origin.v1"
KERNEL_CONTEXT_SIGNATURE_DOMAIN = b"VALO-KERNEL-CONTEXT-V1\x00"
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class KernelContextSigner(Protocol):
    """Signing boundary implemented by a software key, HSM, or KMS adapter."""

    kernel_id: str
    key_id: str
    algorithm: str

    def sign(self, payload: bytes) -> str: ...


@dataclass(frozen=True)
class Ed25519KernelContextSigner:
    """Reference signer backed by explicitly injected Ed25519 key material."""

    kernel_id: str
    key_id: str
    _private_key: Ed25519PrivateKey
    algorithm: str = "Ed25519"

    @classmethod
    def from_private_key_bytes(
        cls,
        *,
        kernel_id: str,
        key_id: str,
        private_key_bytes: bytes,
    ) -> Ed25519KernelContextSigner:
        if not kernel_id or not key_id:
            raise ValueError("kernel_id and key_id are required")
        if len(private_key_bytes) != 32:
            raise ValueError("Ed25519 private key seed must be exactly 32 bytes")
        return cls(
            kernel_id=kernel_id,
            key_id=key_id,
            _private_key=Ed25519PrivateKey.from_private_bytes(private_key_bytes),
        )

    def sign(self, payload: bytes) -> str:
        if not payload:
            raise ValueError("Kernel context signature payload must not be empty")
        return _b64url_encode(self._private_key.sign(payload))

    def public_key(self) -> Ed25519PublicKey:
        return self._private_key.public_key()


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _canonicalize(value: Mapping[str, Any]) -> bytes:
    try:
        encoded = rfc8785.dumps(dict(value))
    except Exception as exc:
        raise ExecutionContextError(
            "execution context is not valid RFC 8785 JSON"
        ) from exc
    return encoded if isinstance(encoded, bytes) else encoded.encode("utf-8")


def execution_context_digest(execution_context: Mapping[str, Any]) -> str:
    """Return the RACS-JCS-1 digest of an unsigned or sealed context."""
    return "sha256:" + sha256(_canonicalize(execution_context)).hexdigest()


def context_origin_signature_input(proof: Mapping[str, Any]) -> bytes:
    """Return the domain-separated bytes signed by a Kernel context signer."""
    candidate = dict(proof)
    candidate.pop("signature", None)
    return KERNEL_CONTEXT_SIGNATURE_DOMAIN + _canonicalize(candidate)


def _require_context_shape(execution_context: Mapping[str, Any]) -> tuple[str, str]:
    tenant_id = execution_context.get("tenant_id")
    if not isinstance(tenant_id, str) or not tenant_id.strip():
        raise ExecutionContextError("execution context tenant_id is required")

    context_time = execution_context.get("time")
    if not isinstance(context_time, Mapping):
        raise ExecutionContextError("execution context time is required")
    issued_at = context_time.get("now")
    if not isinstance(issued_at, str) or not issued_at:
        raise ExecutionContextError("execution context time.now is required")
    normalized = issued_at[:-1] + "+00:00" if issued_at.endswith("Z") else issued_at
    try:
        parsed_time = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ExecutionContextError("execution context time.now is invalid") from exc
    if parsed_time.tzinfo is None or parsed_time.utcoffset() is None:
        raise ExecutionContextError("execution context time.now must be timezone-aware")

    for field in ("state_root", "state_ref"):
        value = execution_context.get(field)
        if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
            raise ExecutionContextError(
                f"execution context {field} must be a Kernel SHA-256 digest"
            )

    sequence = execution_context.get("sequence")
    if (
        not isinstance(sequence, int)
        or isinstance(sequence, bool)
        or sequence < 0
    ):
        raise ExecutionContextError("execution context sequence is invalid")

    nonce = execution_context.get("execution_nonce")
    if not isinstance(nonce, str) or not nonce:
        raise ExecutionContextError("execution context execution_nonce is required")

    transition = execution_context.get("requested_transition")
    if not isinstance(transition, Mapping):
        raise ExecutionContextError("execution context requested_transition is required")
    if transition.get("tenant_id") != tenant_id:
        raise ExecutionContextError(
            "execution context transition tenant differs from context tenant"
        )

    workspace_binding = execution_context.get("workspace_binding")
    if workspace_binding is not None:
        if not isinstance(workspace_binding, Mapping):
            raise ExecutionContextError("execution context workspace_binding is invalid")
        if workspace_binding.get("tenant_id") != tenant_id:
            raise ExecutionContextError(
                "execution context workspace tenant differs from context tenant"
            )
        if workspace_binding.get("authority_effect") != "NO_AUTHORITY_CREATION":
            raise ExecutionContextError("workspace binding cannot claim authority")
        if workspace_binding.get("can_issue_clearance") is not False:
            raise ExecutionContextError("workspace binding cannot issue clearance")

    return tenant_id, issued_at


def seal_execution_context(
    execution_context: Mapping[str, Any],
    *,
    signer: KernelContextSigner,
) -> dict[str, Any]:
    """Copy and seal one context without mutating or authorizing it."""
    if "origin_proof" in execution_context:
        raise ExecutionContextError("execution context is already sealed")
    if signer.algorithm != "Ed25519":
        raise ExecutionContextError("unsupported Kernel context signature algorithm")
    if not signer.kernel_id or not signer.key_id:
        raise ExecutionContextError("Kernel signer identity and key are required")

    sealed = deepcopy(dict(execution_context))
    tenant_id, issued_at = _require_context_shape(sealed)
    content_digest = execution_context_digest(sealed)
    proof: dict[str, Any] = {
        "schema_version": KERNEL_CONTEXT_ORIGIN_SCHEMA,
        "canonicalization": "RACS-JCS-1",
        "digest_algorithm": "SHA-256",
        "signature_algorithm": signer.algorithm,
        "kernel_id": signer.kernel_id,
        "key_id": signer.key_id,
        "tenant_id": tenant_id,
        "issued_at": issued_at,
        "content_digest": content_digest,
    }
    signature = signer.sign(context_origin_signature_input(proof))
    if not isinstance(signature, str) or not signature:
        raise ExecutionContextError("Kernel signer returned an invalid signature")
    proof["signature"] = signature
    sealed["origin_proof"] = proof
    return sealed
