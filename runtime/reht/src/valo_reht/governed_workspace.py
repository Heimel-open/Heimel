"""Canonical Governed Workspace verification for the VALO REHT runtime.

The workspace and Kernel origin proof are evidence inputs only. They cannot
create authority or clearance. This module verifies exact workspace lineage,
fresh Kernel context origin and action continuity before ``RealReht`` evaluates
current authority.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any

import rfc8785
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

GOVERNED_WORKSPACE_V1 = "governed_workspace_v1"
_KERNEL_CONTEXT_ORIGIN_SCHEMA = "kernel_execution_context_origin.v1"
_KERNEL_CONTEXT_SIGNATURE_DOMAIN = b"VALO-KERNEL-CONTEXT-V1\x00"
_KERNEL_CONTEXT_PROOF_FIELDS = frozenset(
    {
        "schema_version",
        "canonicalization",
        "digest_algorithm",
        "signature_algorithm",
        "kernel_id",
        "key_id",
        "tenant_id",
        "issued_at",
        "content_digest",
        "signature",
    }
)


def _canonicalize(value: Mapping[str, Any] | dict[str, Any]) -> bytes:
    try:
        encoded = rfc8785.dumps(dict(value))
    except Exception as exc:
        raise ValueError("Kernel execution context is not valid RFC 8785 JSON") from exc
    return encoded if isinstance(encoded, bytes) else encoded.encode("utf-8")


def _racs_digest(value: Mapping[str, Any] | dict[str, Any]) -> str:
    return "sha256:" + sha256(_canonicalize(value)).hexdigest()


def _kernel_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def _is_prefixed_digest(value: object) -> bool:
    return (
        isinstance(value, str)
        and value.startswith("sha256:")
        and len(value) == 71
        and all(ch in "0123456789abcdef" for ch in value[7:])
    )


def _is_plain_digest(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value)
    )


def _parse_aware(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} is required")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{field} is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return parsed.astimezone(UTC)


def _b64url_decode(value: object) -> bytes:
    if not isinstance(value, str) or not value:
        raise ValueError("Kernel context signature is required")
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(value + padding)
    except Exception as exc:
        raise ValueError("Kernel context signature is malformed") from exc


def _active_validity(value: object, *, at_time: datetime, field: str) -> bool:
    if not isinstance(value, Mapping):
        raise ValueError(f"fresh Kernel {field} validity is required")
    valid_from = _parse_aware(value.get("valid_from"), f"{field}.valid_from")
    valid_until = _parse_aware(value.get("valid_until"), f"{field}.valid_until")
    if valid_until <= valid_from:
        raise ValueError(f"fresh Kernel {field} validity is invalid")
    return valid_from <= at_time < valid_until


@dataclass(frozen=True)
class TrustedKernelContextKey:
    kernel_id: str
    key_id: str
    tenant_ids: frozenset[str]
    public_key: Ed25519PublicKey
    valid_from: datetime
    valid_until: datetime

    def __post_init__(self) -> None:
        if not self.kernel_id or not self.key_id:
            raise ValueError("trusted Kernel identity and key id are required")
        if not self.tenant_ids or any(
            not tenant_id or tenant_id == "*" for tenant_id in self.tenant_ids
        ):
            raise ValueError("trusted Kernel key requires explicit tenant ids")
        if not isinstance(self.public_key, Ed25519PublicKey):
            raise TypeError("trusted Kernel key must be an Ed25519 public key")
        if self.valid_from.tzinfo is None or self.valid_until.tzinfo is None:
            raise ValueError("trusted Kernel key validity must be timezone-aware")
        if self.valid_until <= self.valid_from:
            raise ValueError("trusted Kernel key validity interval is invalid")

    def is_active(self, at_time: datetime) -> bool:
        moment = at_time.astimezone(UTC)
        return self.valid_from.astimezone(UTC) <= moment < self.valid_until.astimezone(UTC)


class Ed25519KernelExecutionContextVerifier:
    """Verify exact Kernel origin/integrity against tenant-bound trust."""

    def __init__(self, trusted_keys: tuple[TrustedKernelContextKey, ...]) -> None:
        if not trusted_keys:
            raise ValueError("at least one trusted Kernel context key is required")
        indexed: dict[tuple[str, str], TrustedKernelContextKey] = {}
        for trusted_key in trusted_keys:
            identity = (trusted_key.kernel_id, trusted_key.key_id)
            if identity in indexed:
                raise ValueError("duplicate trusted Kernel context key")
            indexed[identity] = trusted_key
        self._trusted_keys = indexed

    def verify(
        self,
        *,
        execution_context: Mapping[str, Any],
        context_digest: str,
        tenant_id: str,
        action_id: str,
        authorization_time: datetime,
    ) -> None:
        if _racs_digest(dict(execution_context)) != context_digest:
            raise ValueError("Kernel context digest mismatch")

        proof = execution_context.get("origin_proof")
        if not isinstance(proof, Mapping):
            raise ValueError("Kernel context origin proof is required")
        if set(proof) != _KERNEL_CONTEXT_PROOF_FIELDS:
            raise ValueError("Kernel context origin proof is malformed")
        if (
            proof.get("schema_version") != _KERNEL_CONTEXT_ORIGIN_SCHEMA
            or proof.get("canonicalization") != "RACS-JCS-1"
            or proof.get("digest_algorithm") != "SHA-256"
            or proof.get("signature_algorithm") != "Ed25519"
        ):
            raise ValueError("Kernel context origin profile is unsupported")

        if execution_context.get("tenant_id") != tenant_id or proof.get("tenant_id") != tenant_id:
            raise ValueError("Kernel context tenant mismatch")

        unsigned = dict(execution_context)
        unsigned.pop("origin_proof", None)
        if proof.get("content_digest") != _racs_digest(unsigned):
            raise ValueError("Kernel context content digest mismatch")

        context_time = execution_context.get("time")
        if not isinstance(context_time, Mapping):
            raise ValueError("Kernel context time is required")
        resolved_at = _parse_aware(context_time.get("now"), "Kernel context time")
        issued_at = _parse_aware(proof.get("issued_at"), "Kernel proof issued_at")
        if resolved_at != issued_at:
            raise ValueError("Kernel context proof is not bound to resolved time")

        binding = execution_context.get("workspace_binding")
        proposed_action = binding.get("proposed_action") if isinstance(binding, Mapping) else None
        if not isinstance(proposed_action, Mapping) or proposed_action.get("action_id") != action_id:
            raise ValueError("Kernel context action mismatch")

        kernel_id = proof.get("kernel_id")
        key_id = proof.get("key_id")
        if not isinstance(kernel_id, str) or not isinstance(key_id, str):
            raise ValueError("Kernel context key identity is malformed")
        trusted_key = self._trusted_keys.get((kernel_id, key_id))
        if trusted_key is None:
            raise ValueError("Kernel context origin is untrusted")
        if tenant_id not in trusted_key.tenant_ids:
            raise ValueError("Kernel context key tenant mismatch")
        if not trusted_key.is_active(issued_at):
            raise ValueError("Kernel context key inactive at signing")
        if not trusted_key.is_active(authorization_time):
            raise ValueError("Kernel context key inactive at authorization")

        signature_payload = dict(proof)
        signature_payload.pop("signature", None)
        signature_input = _KERNEL_CONTEXT_SIGNATURE_DOMAIN + _canonicalize(signature_payload)
        try:
            trusted_key.public_key.verify(
                _b64url_decode(proof.get("signature")),
                signature_input,
            )
        except InvalidSignature as exc:
            raise ValueError("Kernel context signature is invalid") from exc


@dataclass(frozen=True)
class GovernedWorkspaceVerification:
    workspace_binding_digest: str
    kernel_context_digest: str
    workspace_expires_at: datetime


def validate_governed_workspace_context(
    execution_context: Mapping[str, Any],
    action_contract: Mapping[str, Any],
    *,
    verifier: Ed25519KernelExecutionContextVerifier | None,
    authorization_time: datetime,
    max_context_age: timedelta = timedelta(seconds=5),
    max_future_skew: timedelta = timedelta(seconds=1),
) -> GovernedWorkspaceVerification | None:
    """Fail closed on workspace downgrade, stale state, drift or untrusted origin."""

    binding = execution_context.get("workspace_binding")
    requested = action_contract.get("governed_workspace_required") is True
    if binding is None:
        if requested:
            raise ValueError("governed workspace execution binding is required")
        return None
    if not requested:
        raise ValueError("workspace context requires governed_workspace_required=true")
    if not isinstance(binding, Mapping):
        raise ValueError("workspace execution binding is invalid")
    if verifier is None:
        raise ValueError("canonical Kernel execution-context verifier is required")
    if authorization_time.tzinfo is None or authorization_time.utcoffset() is None:
        raise ValueError("REHT authorization clock must be timezone-aware")
    authorization_time = authorization_time.astimezone(UTC)
    if max_context_age < timedelta(0) or max_future_skew < timedelta(0):
        raise ValueError("Kernel context freshness bounds cannot be negative")

    context_time = execution_context.get("time")
    if not isinstance(context_time, Mapping):
        raise ValueError("fresh Kernel context time is required")
    resolved_at = _parse_aware(context_time.get("now"), "fresh Kernel context time")
    if resolved_at - authorization_time > max_future_skew:
        raise ValueError("Kernel execution context is in the future")
    if authorization_time - resolved_at > max_context_age:
        raise ValueError("Kernel execution context is stale")

    tenant_id = execution_context.get("tenant_id")
    if not isinstance(tenant_id, str) or not tenant_id:
        raise ValueError("fresh Kernel tenant is required")
    if action_contract.get("tenant_id") != tenant_id or binding.get("tenant_id") != tenant_id:
        raise ValueError("governed workspace tenant mismatch")
    if binding.get("schema_version") != "workspace_execution_binding.v1":
        raise ValueError("unsupported workspace execution binding")
    if binding.get("conformance_outcome") != "PASS":
        raise ValueError("workspace conformance outcome must be PASS")
    if binding.get("authority_effect") != "NO_AUTHORITY_CREATION":
        raise ValueError("workspace binding attempted to create authority")
    if binding.get("can_issue_clearance") is not False:
        raise ValueError("workspace binding attempted to issue clearance")

    for field in (
        "workspace_digest",
        "candidate_digest",
        "proposed_action_digest",
        "conformance_digest",
        "source_state_root",
        "conformed_state_root",
        "dependency_digest",
    ):
        if not _is_plain_digest(binding.get(field)):
            raise ValueError(f"workspace binding {field} must be a Kernel SHA-256 digest")
    program_ref = binding.get("program_ref")
    program_digest = binding.get("program_digest")
    if bool(program_ref) != bool(program_digest):
        raise ValueError("workspace program ref and digest must be bound together")
    if program_digest is not None and not _is_plain_digest(program_digest):
        raise ValueError("workspace program digest must be a Kernel SHA-256 digest")

    workspace_expires_at = _parse_aware(binding.get("workspace_expires_at"), "workspace_expires_at")
    conformed_at = _parse_aware(binding.get("conformed_at"), "conformed_at")
    if conformed_at > authorization_time:
        raise ValueError("workspace conformance is in the future")
    if authorization_time >= workspace_expires_at:
        raise ValueError("workspace is expired at REHT authorization")

    source_position = binding.get("source_event_position")
    sequence = execution_context.get("sequence")
    if not isinstance(source_position, int) or isinstance(source_position, bool) or source_position < 0:
        raise ValueError("workspace source event position is invalid")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < source_position:
        raise ValueError("fresh Kernel sequence predates governed projection")

    dependencies = binding.get("dependencies")
    if not isinstance(dependencies, list):
        raise ValueError("workspace dependencies must be a list")
    if _kernel_digest(dependencies) != binding.get("dependency_digest"):
        raise ValueError("workspace dependency digest mismatch")
    if execution_context.get("state_ref") != binding.get("dependency_digest"):
        raise ValueError("fresh Kernel state reference differs from workspace dependencies")

    proposed_action = binding.get("proposed_action")
    if not isinstance(proposed_action, Mapping):
        raise ValueError("workspace proposed action is required")
    if _kernel_digest(dict(proposed_action)) != binding.get("proposed_action_digest"):
        raise ValueError("workspace proposed action digest mismatch")
    for field in ("action_id", "capability", "target", "purpose_id"):
        if proposed_action.get(field) != action_contract.get(field):
            raise ValueError(f"workspace {field} differs from action contract")
    parameters = proposed_action.get("parameters")
    if not isinstance(parameters, Mapping) or dict(parameters) != action_contract.get("parameters", {}):
        raise ValueError("workspace action parameters differ from action contract")

    purpose = execution_context.get("purpose")
    if not isinstance(purpose, Mapping):
        raise ValueError("fresh Kernel purpose is required")
    if purpose.get("purpose_id") != proposed_action.get("purpose_id"):
        raise ValueError("fresh Kernel purpose differs from workspace action")
    if not _active_validity(purpose.get("validity"), at_time=authorization_time, field="purpose"):
        raise ValueError("fresh Kernel purpose is expired")
    permitted_actions = purpose.get("permitted_actions")
    if not isinstance(permitted_actions, (list, tuple)) or proposed_action.get("capability") not in permitted_actions:
        raise ValueError("fresh Kernel purpose does not permit workspace capability")
    purpose_scope = purpose.get("scope")
    if not isinstance(purpose_scope, (list, tuple)):
        raise ValueError("fresh Kernel purpose scope is invalid")
    if purpose_scope and "*" not in purpose_scope and proposed_action.get("target") not in purpose_scope:
        raise ValueError("fresh Kernel purpose does not cover workspace target")

    workspace_binding_digest = _racs_digest(dict(binding))
    kernel_context_digest = _racs_digest(dict(execution_context))
    if not _is_prefixed_digest(action_contract.get("workspace_binding_digest")):
        raise ValueError("action contract workspace binding digest is required")
    if not _is_prefixed_digest(action_contract.get("kernel_context_digest")):
        raise ValueError("action contract Kernel context digest is required")
    if action_contract.get("workspace_binding_digest") != workspace_binding_digest:
        raise ValueError("action contract workspace binding digest mismatch")
    if action_contract.get("kernel_context_digest") != kernel_context_digest:
        raise ValueError("action contract Kernel context digest mismatch")

    action_id = proposed_action.get("action_id")
    if not isinstance(action_id, str) or not action_id:
        raise ValueError("workspace action id is required")
    verifier.verify(
        execution_context=execution_context,
        context_digest=kernel_context_digest,
        tenant_id=tenant_id,
        action_id=action_id,
        authorization_time=authorization_time,
    )

    return GovernedWorkspaceVerification(
        workspace_binding_digest=workspace_binding_digest,
        kernel_context_digest=kernel_context_digest,
        workspace_expires_at=workspace_expires_at,
    )


__all__ = [
    "GOVERNED_WORKSPACE_V1",
    "Ed25519KernelExecutionContextVerifier",
    "GovernedWorkspaceVerification",
    "TrustedKernelContextKey",
    "validate_governed_workspace_context",
]
