from __future__ import annotations

import base64
import json
import os
from datetime import datetime
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from ..contracts.common import canonical_bytes, canonical_digest
from ..contracts.semantic_disclosure import (
    DisclosedConsequenceAction,
    ExecutionBoundaryDisclosureContext,
    ExecutionBoundaryKey,
    SealedConsequenceAction,
    SealedWorkspaceExecutionBinding,
)
from ..contracts.workspace import (
    CandidateResult,
    ConformanceReport,
    GovernedWorkspaceEnvelope,
    ProposedAction,
)
from .errors import FailClosedError
from .workspace import bind_workspace_execution

_HKDF_INFO_PREFIX = b"valo-jit-semantic-disclosure-v1:"


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _unb64(value: str, *, label: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except Exception as exc:
        raise FailClosedError(f"invalid {label} encoding") from exc


def _aad_payload(
    *,
    envelope_id: str,
    tenant_id: str,
    work_unit_id: str,
    workspace_id: str,
    action_id: str,
    action_commitment: str,
    recipient_boundary_id: str,
    recipient_key_ref: str,
    sealed_at: datetime,
    valid_until: datetime,
) -> dict[str, Any]:
    return {
        "schema_version": "sealed_consequence_action.v1",
        "envelope_id": envelope_id,
        "tenant_id": tenant_id,
        "work_unit_id": work_unit_id,
        "workspace_id": workspace_id,
        "action_id": action_id,
        "action_commitment": action_commitment,
        "recipient_boundary_id": recipient_boundary_id,
        "recipient_key_ref": recipient_key_ref,
        "sealed_at": sealed_at.isoformat(),
        "valid_until": valid_until.isoformat(),
        "disclosure_audience": "REHT_EXECUTION_BOUNDARY",
        "unseal_effect": "NO_EXECUTION_EFFECT",
    }


def _derive_key(shared_secret: bytes, aad_digest: str) -> bytes:
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=_HKDF_INFO_PREFIX + aad_digest.encode("ascii"),
    ).derive(shared_secret)


def seal_consequence_action(
    action: ProposedAction,
    recipient_key: ExecutionBoundaryKey,
    *,
    tenant_id: str,
    work_unit_id: str,
    workspace_id: str,
    sealed_at: datetime,
    valid_until: datetime,
) -> SealedConsequenceAction:
    if sealed_at < recipient_key.valid_from or sealed_at >= recipient_key.valid_until:
        raise FailClosedError("execution boundary key is not valid at seal time")
    if valid_until <= sealed_at:
        raise FailClosedError("sealed consequence action requires a future validity end")
    if valid_until > recipient_key.valid_until:
        raise FailClosedError("sealed consequence action cannot outlive boundary key")

    action_payload = action.model_dump(mode="json")
    action_commitment = canonical_digest(action_payload)
    envelope_id = f"sealed:{action.action_id}:{action_commitment}"
    aad_payload = _aad_payload(
        envelope_id=envelope_id,
        tenant_id=tenant_id,
        work_unit_id=work_unit_id,
        workspace_id=workspace_id,
        action_id=action.action_id,
        action_commitment=action_commitment,
        recipient_boundary_id=recipient_key.boundary_id,
        recipient_key_ref=recipient_key.key_ref,
        sealed_at=sealed_at,
        valid_until=valid_until,
    )
    aad = canonical_bytes(aad_payload)
    aad_digest = canonical_digest(aad_payload)

    recipient_public = X25519PublicKey.from_public_bytes(
        _unb64(recipient_key.public_key_b64, label="boundary public key")
    )
    ephemeral_private = X25519PrivateKey.generate()
    ephemeral_public = ephemeral_private.public_key().public_bytes(
        Encoding.Raw,
        PublicFormat.Raw,
    )
    shared_secret = ephemeral_private.exchange(recipient_public)
    content_key = _derive_key(shared_secret, aad_digest)
    nonce = os.urandom(12)
    ciphertext = AESGCM(content_key).encrypt(
        nonce,
        canonical_bytes(action_payload),
        aad,
    )

    provisional = SealedConsequenceAction(
        envelope_id=envelope_id,
        tenant_id=tenant_id,
        work_unit_id=work_unit_id,
        workspace_id=workspace_id,
        action_id=action.action_id,
        action_commitment=action_commitment,
        recipient_boundary_id=recipient_key.boundary_id,
        recipient_key_ref=recipient_key.key_ref,
        ephemeral_public_key_b64=_b64(ephemeral_public),
        nonce_b64=_b64(nonce),
        ciphertext_b64=_b64(ciphertext),
        aad_digest=aad_digest,
        sealed_at=sealed_at,
        valid_until=valid_until,
    )
    return provisional.model_copy(
        update={"envelope_digest": provisional.computed_digest}
    )


def disclose_consequence_action(
    envelope: SealedConsequenceAction,
    context: ExecutionBoundaryDisclosureContext,
    *,
    boundary_private_key: bytes,
) -> DisclosedConsequenceAction:
    if envelope.envelope_digest != envelope.computed_digest:
        raise FailClosedError("sealed consequence action is unsealed or tampered")
    if (
        context.boundary_id != envelope.recipient_boundary_id
        or context.key_ref != envelope.recipient_key_ref
    ):
        raise FailClosedError("semantic disclosure attempted at the wrong boundary")
    if (
        context.tenant_id != envelope.tenant_id
        or context.work_unit_id != envelope.work_unit_id
        or context.workspace_id != envelope.workspace_id
    ):
        raise FailClosedError("semantic disclosure context binding mismatch")
    if context.disclosed_at < envelope.sealed_at:
        raise FailClosedError("semantic disclosure predates sealing")
    if context.disclosed_at >= envelope.valid_until:
        raise FailClosedError("semantic disclosure window has expired")
    if len(boundary_private_key) != 32:
        raise FailClosedError("boundary private key must be 32-byte X25519 material")

    aad_payload = _aad_payload(
        envelope_id=envelope.envelope_id,
        tenant_id=envelope.tenant_id,
        work_unit_id=envelope.work_unit_id,
        workspace_id=envelope.workspace_id,
        action_id=envelope.action_id,
        action_commitment=envelope.action_commitment,
        recipient_boundary_id=envelope.recipient_boundary_id,
        recipient_key_ref=envelope.recipient_key_ref,
        sealed_at=envelope.sealed_at,
        valid_until=envelope.valid_until,
    )
    if canonical_digest(aad_payload) != envelope.aad_digest:
        raise FailClosedError("semantic disclosure associated data mismatch")
    aad = canonical_bytes(aad_payload)

    try:
        private_key = X25519PrivateKey.from_private_bytes(boundary_private_key)
        ephemeral_public = X25519PublicKey.from_public_bytes(
            _unb64(envelope.ephemeral_public_key_b64, label="ephemeral public key")
        )
        shared_secret = private_key.exchange(ephemeral_public)
        content_key = _derive_key(shared_secret, envelope.aad_digest)
        plaintext = AESGCM(content_key).decrypt(
            _unb64(envelope.nonce_b64, label="nonce"),
            _unb64(envelope.ciphertext_b64, label="ciphertext"),
            aad,
        )
    except (InvalidTag, ValueError) as exc:
        raise FailClosedError("semantic disclosure cryptographic verification failed") from exc

    try:
        action = ProposedAction.model_validate(json.loads(plaintext))
    except Exception as exc:
        raise FailClosedError("disclosed consequence action is invalid") from exc
    if action.action_id != envelope.action_id:
        raise FailClosedError("disclosed action identity mismatch")
    if canonical_digest(action.model_dump(mode="json")) != envelope.action_commitment:
        raise FailClosedError("disclosed action commitment mismatch")

    return DisclosedConsequenceAction(
        envelope_id=envelope.envelope_id,
        envelope_digest=envelope.envelope_digest,
        action=action,
        action_commitment=envelope.action_commitment,
        disclosure_context_digest=context.context_digest,
        disclosed_at=context.disclosed_at,
    )


def bind_sealed_workspace_execution(
    workspace: GovernedWorkspaceEnvelope,
    candidate: CandidateResult,
    report: ConformanceReport,
    *,
    action_id: str,
    recipient_key: ExecutionBoundaryKey,
) -> SealedWorkspaceExecutionBinding:
    clear_binding = bind_workspace_execution(
        workspace,
        candidate,
        report,
        action_id=action_id,
    )
    valid_until = min(workspace.spec.expires_at, recipient_key.valid_until)
    sealed_action = seal_consequence_action(
        clear_binding.proposed_action,
        recipient_key,
        tenant_id=clear_binding.tenant_id,
        work_unit_id=clear_binding.work_unit_id,
        workspace_id=clear_binding.workspace_id,
        sealed_at=clear_binding.conformed_at,
        valid_until=valid_until,
    )
    provisional = SealedWorkspaceExecutionBinding(
        tenant_id=clear_binding.tenant_id,
        work_unit_id=clear_binding.work_unit_id,
        workspace_id=clear_binding.workspace_id,
        workspace_digest=clear_binding.workspace_digest,
        workspace_expires_at=clear_binding.workspace_expires_at,
        program_ref=clear_binding.program_ref,
        program_digest=clear_binding.program_digest,
        governing_contract_ids=clear_binding.governing_contract_ids,
        invocation_id=clear_binding.invocation_id,
        candidate_id=clear_binding.candidate_id,
        candidate_digest=clear_binding.candidate_digest,
        sealed_action=sealed_action,
        proposed_action_digest=clear_binding.proposed_action_digest,
        conformance_report_id=clear_binding.conformance_report_id,
        conformance_digest=clear_binding.conformance_digest,
        source_state_root=clear_binding.source_state_root,
        conformed_state_root=clear_binding.conformed_state_root,
        source_event_position=clear_binding.source_event_position,
        conformed_at=clear_binding.conformed_at,
        dependency_digest=clear_binding.dependency_digest,
        dependencies=clear_binding.dependencies,
    )
    return provisional.model_copy(
        update={"binding_digest": provisional.computed_digest}
    )
