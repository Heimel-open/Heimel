from __future__ import annotations

import base64
import binascii
import hashlib
import json
from datetime import datetime, timezone
from enum import StrEnum
from typing import Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from pydantic import BaseModel, ConfigDict, Field, model_validator


CREDENTIAL_SCHEMA = "valo.agent-credential.v0"
SIGNATURE_DOMAIN = b"VALO_AGENT_CREDENTIAL_V0\x00"


class CredentialDisposition(StrEnum):
    ADMISSIBLE = "ADMISSIBLE"
    DENY = "DENY"


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)


class CapabilityConformance(BaseModel):
    model_config = ConfigDict(frozen=True)

    capability_id: str = Field(min_length=1)
    test_suite: str = Field(min_length=1)
    test_suite_version: str = Field(min_length=1)
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    evidence_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evaluated_at: datetime

    @model_validator(mode="after")
    def require_clean_conformance(self) -> "CapabilityConformance":
        _utc(self.evaluated_at)
        if self.passed < 1:
            raise ValueError("at least one conformance test must pass")
        if self.failed != 0:
            raise ValueError("credential evidence must have zero failed tests")
        return self


class AgentCapabilityCredential(BaseModel):
    """Portable evidence that an agent demonstrated a bounded capability.

    This is not authority. A valid credential may satisfy a capability gate, but
    REHT / Kernel authority must still be resolved independently at consequence time.
    """

    model_config = ConfigDict(frozen=True)

    schema_id: str = CREDENTIAL_SCHEMA
    credential_id: str = Field(min_length=1)
    issuer_id: str = Field(min_length=1)
    subject_agent_id: str = Field(min_length=1)
    capability_id: str = Field(min_length=1)
    scope: tuple[str, ...] = ()
    risk_class: str = Field(min_length=1)
    issued_at: datetime
    valid_from: datetime
    valid_until: datetime
    conformance: CapabilityConformance
    signature: str | None = None

    @model_validator(mode="after")
    def validate_semantics(self) -> "AgentCapabilityCredential":
        issued_at = _utc(self.issued_at)
        valid_from = _utc(self.valid_from)
        valid_until = _utc(self.valid_until)
        if self.conformance.capability_id != self.capability_id:
            raise ValueError("conformance capability must match credential capability")
        if valid_until <= valid_from:
            raise ValueError("valid_until must be after valid_from")
        if issued_at > valid_until:
            raise ValueError("issued_at cannot be after credential expiry")
        return self


class CapabilityGateRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    agent_id: str = Field(min_length=1)
    capability_id: str = Field(min_length=1)
    required_scope: tuple[str, ...] = ()
    at: datetime

    @model_validator(mode="after")
    def validate_timestamp(self) -> "CapabilityGateRequest":
        _utc(self.at)
        return self


class CapabilityGateDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    disposition: CredentialDisposition
    credential_id: str | None = None
    reason: str


def _unsigned_payload(credential: AgentCapabilityCredential) -> bytes:
    body = credential.model_dump(mode="json", exclude={"signature"})
    encoded = json.dumps(
        body,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return SIGNATURE_DOMAIN + encoded


def credential_digest(credential: AgentCapabilityCredential) -> str:
    return "sha256:" + hashlib.sha256(_unsigned_payload(credential)).hexdigest()


def issue_agent_capability_credential(
    credential: AgentCapabilityCredential,
    private_key: Ed25519PrivateKey,
) -> AgentCapabilityCredential:
    if credential.signature is not None:
        raise ValueError("credential is already signed")
    signature = private_key.sign(_unsigned_payload(credential))
    return credential.model_copy(
        update={"signature": base64.urlsafe_b64encode(signature).decode("ascii")}
    )


def verify_agent_capability_credential(
    credential: AgentCapabilityCredential,
    issuer_public_key: Ed25519PublicKey,
) -> bool:
    if credential.signature is None:
        return False
    try:
        signature = base64.urlsafe_b64decode(credential.signature.encode("ascii"))
        issuer_public_key.verify(signature, _unsigned_payload(credential))
    except (binascii.Error, InvalidSignature, ValueError):
        return False
    return True


def assess_agent_capability(
    request: CapabilityGateRequest,
    credentials: tuple[AgentCapabilityCredential, ...],
    trusted_issuers: Mapping[str, Ed25519PublicKey],
    revoked_credential_ids: frozenset[str] = frozenset(),
) -> CapabilityGateDecision:
    """Fail-closed consequence-time capability gate.

    The gate proves only demonstrated capability. It intentionally does not
    produce ALLOW for execution and must be composed with fresh authority checks.
    """

    at = _utc(request.at)
    candidates = [
        credential
        for credential in credentials
        if credential.subject_agent_id == request.agent_id
        and credential.capability_id == request.capability_id
    ]
    if not candidates:
        return CapabilityGateDecision(
            disposition=CredentialDisposition.DENY,
            reason="no matching capability credential",
        )

    for credential in candidates:
        if credential.credential_id in revoked_credential_ids:
            continue
        issuer_key = trusted_issuers.get(credential.issuer_id)
        if issuer_key is None:
            continue
        if not verify_agent_capability_credential(credential, issuer_key):
            continue
        if not (_utc(credential.valid_from) <= at <= _utc(credential.valid_until)):
            continue
        if not set(request.required_scope).issubset(set(credential.scope)):
            continue
        return CapabilityGateDecision(
            disposition=CredentialDisposition.ADMISSIBLE,
            credential_id=credential.credential_id,
            reason="capability credential verified; authority remains independently required",
        )

    return CapabilityGateDecision(
        disposition=CredentialDisposition.DENY,
        reason="no trusted, valid, unrevoked credential satisfies the requested scope",
    )
