"""Deterministic, fail-closed federation of MAL policy packs.

Federation imports admissibility policy only. It never grants execution
clearance or action authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Iterable, Mapping


def canonical_digest(value: Mapping[str, object]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return sha256(payload).hexdigest()


@dataclass(frozen=True)
class TrustRoot:
    root_id: str
    issuer: str
    public_key_fingerprint: str
    allowed_tenants: tuple[str, ...]
    allowed_policy_scopes: tuple[str, ...]
    valid_from: int
    valid_until: int
    revoked: bool = False


@dataclass(frozen=True)
class SignedPolicyPack:
    pack_id: str
    issuer: str
    source_tenant: str
    policy_scope: str
    version: str
    payload: Mapping[str, object]
    payload_digest: str
    signature: str
    trust_root_id: str
    issued_at: int
    expires_at: int


@dataclass(frozen=True)
class FederationRequest:
    target_tenant: str
    expected_scope: str
    expected_region: str
    imported_at: int
    import_nonce: str


@dataclass(frozen=True)
class FederationResult:
    decision: str
    reasons: tuple[str, ...]
    imported_pack_digest: str | None
    federation_receipt_digest: str


def evaluate_import(
    pack: SignedPolicyPack,
    request: FederationRequest,
    roots: Iterable[TrustRoot],
    seen_nonces: set[str],
) -> FederationResult:
    reasons: list[str] = []
    root = next((item for item in roots if item.root_id == pack.trust_root_id), None)
    if root is None:
        reasons.append("UNKNOWN_TRUST_ROOT")
    else:
        if root.revoked:
            reasons.append("TRUST_ROOT_REVOKED")
        if root.issuer != pack.issuer:
            reasons.append("ISSUER_MISMATCH")
        if request.target_tenant not in root.allowed_tenants:
            reasons.append("TENANT_NOT_TRUSTED")
        if pack.policy_scope not in root.allowed_policy_scopes:
            reasons.append("SCOPE_NOT_TRUSTED")
        if not (root.valid_from <= request.imported_at <= root.valid_until):
            reasons.append("TRUST_ROOT_EXPIRED")

    actual_digest = canonical_digest(pack.payload)
    if actual_digest != pack.payload_digest:
        reasons.append("PAYLOAD_DIGEST_MISMATCH")
    if request.expected_scope != pack.policy_scope:
        reasons.append("REQUEST_SCOPE_MISMATCH")
    if not (pack.issued_at <= request.imported_at <= pack.expires_at):
        reasons.append("POLICY_PACK_EXPIRED")
    if request.import_nonce in seen_nonces:
        reasons.append("IMPORT_REPLAY")
    if pack.payload.get("region") != request.expected_region:
        reasons.append("REGION_MISMATCH")
    if not pack.signature:
        reasons.append("MISSING_SIGNATURE")

    decision = "REJECT" if reasons else "IMPORT_FOR_LOCAL_REVIEW"
    receipt = {
        "decision": decision,
        "pack_id": pack.pack_id,
        "target_tenant": request.target_tenant,
        "scope": request.expected_scope,
        "nonce": request.import_nonce,
        "reasons": sorted(reasons),
        "payload_digest": actual_digest,
    }
    return FederationResult(
        decision=decision,
        reasons=tuple(sorted(reasons)),
        imported_pack_digest=actual_digest if not reasons else None,
        federation_receipt_digest=canonical_digest(receipt),
    )
