from __future__ import annotations

from copy import deepcopy

import pytest
from cryptography.exceptions import InvalidSignature

from valo_kernel import (
    Ed25519KernelContextSigner,
    ExecutionContextError,
    context_origin_signature_input,
    execution_context_digest,
    seal_execution_context,
)


def context() -> dict:
    return {
        "tenant_id": "tenant-a",
        "actor": "worker-a",
        "time": {"now": "2026-08-12T08:00:00+00:00"},
        "state_root": "a" * 64,
        "state_ref": "b" * 64,
        "sequence": 42,
        "execution_nonce": "nonce-1",
        "workspace_binding": {
            "tenant_id": "tenant-a",
            "authority_effect": "NO_AUTHORITY_CREATION",
            "can_issue_clearance": False,
        },
        "requested_transition": {
            "tenant_id": "tenant-a",
            "event_id": "transition-1",
        },
    }


def signer(seed: bytes = b"k" * 32) -> Ed25519KernelContextSigner:
    return Ed25519KernelContextSigner.from_private_key_bytes(
        kernel_id="kernel-prod-eu-1",
        key_id="kernel-context-2026-08",
        private_key_bytes=seed,
    )


def test_seal_copies_context_and_binds_exact_origin() -> None:
    unsigned = context()
    unsigned_digest = execution_context_digest(unsigned)

    sealed = seal_execution_context(unsigned, signer=signer())
    proof = sealed["origin_proof"]

    assert "origin_proof" not in unsigned
    assert proof == {
        "schema_version": "kernel_execution_context_origin.v1",
        "canonicalization": "RACS-JCS-1",
        "digest_algorithm": "SHA-256",
        "signature_algorithm": "Ed25519",
        "kernel_id": "kernel-prod-eu-1",
        "key_id": "kernel-context-2026-08",
        "tenant_id": "tenant-a",
        "issued_at": "2026-08-12T08:00:00+00:00",
        "content_digest": unsigned_digest,
        "signature": proof["signature"],
    }
    signer().public_key().verify(
        _signature_bytes(proof["signature"]),
        context_origin_signature_input(proof),
    )
    assert execution_context_digest(sealed) != unsigned_digest


def test_origin_signature_detects_context_or_proof_tampering() -> None:
    sealed = seal_execution_context(context(), signer=signer())
    proof = sealed["origin_proof"]

    tampered_context = deepcopy(sealed)
    tampered_context["sequence"] = 43
    assert execution_context_digest(tampered_context) != execution_context_digest(
        sealed
    )

    tampered_proof = deepcopy(proof)
    tampered_proof["tenant_id"] = "tenant-b"
    with pytest.raises(InvalidSignature):
        signer().public_key().verify(
            _signature_bytes(proof["signature"]),
            context_origin_signature_input(tampered_proof),
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value.pop("tenant_id"), "tenant_id is required"),
        (
            lambda value: value["time"].update({"now": "2026-08-12T08:00:00"}),
            "timezone-aware",
        ),
        (
            lambda value: value["requested_transition"].update(
                {"tenant_id": "tenant-b"}
            ),
            "transition tenant differs",
        ),
        (
            lambda value: value["workspace_binding"].update(
                {"authority_effect": "GRANTS_AUTHORITY"}
            ),
            "cannot claim authority",
        ),
        (
            lambda value: value.update({"state_root": "not-a-digest"}),
            "state_root must be",
        ),
    ],
)
def test_seal_rejects_malformed_or_authority_claiming_context(
    mutation, message: str
) -> None:
    value = context()
    mutation(value)
    with pytest.raises(ExecutionContextError, match=message):
        seal_execution_context(value, signer=signer())


def test_context_cannot_be_silently_resealed() -> None:
    sealed = seal_execution_context(context(), signer=signer())

    with pytest.raises(ExecutionContextError, match="already sealed"):
        seal_execution_context(sealed, signer=signer(b"z" * 32))


def test_private_key_seed_and_signer_metadata_fail_closed() -> None:
    with pytest.raises(ValueError, match="exactly 32 bytes"):
        Ed25519KernelContextSigner.from_private_key_bytes(
            kernel_id="kernel-1",
            key_id="key-1",
            private_key_bytes=b"short",
        )

    invalid = signer()
    object.__setattr__(invalid, "algorithm", "none")
    with pytest.raises(ExecutionContextError, match="unsupported"):
        seal_execution_context(context(), signer=invalid)


def _signature_bytes(value: str) -> bytes:
    import base64

    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
