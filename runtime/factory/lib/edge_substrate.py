"""Provider-neutral governed edge substrate admission.

This module assesses whether a constrained edge runtime is suitable to enter a
governed VALO path. It never executes, grants authority, validates REHT, or
stores credentials.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "valo.edge-substrate-decision.v1"
AUTHORITY_EFFECT = "none"

OBSERVE = "observe"
NETWORK_EGRESS = "network_egress"
ACTUATE = "actuate"
ALLOWED_ACTIONS = (OBSERVE, NETWORK_EGRESS, ACTUATE)

ADMISSIBLE = "ADMISSIBLE"
ADMISSIBLE_TO_EGRESS_GATE = "ADMISSIBLE_TO_EGRESS_GATE"
ADMISSIBLE_TO_REHT = "ADMISSIBLE_TO_REHT"
REFUSED = "REFUSED"

_STATUS_NEXT_BOUNDARY = {
    ADMISSIBLE: "observation",
    ADMISSIBLE_TO_EGRESS_GATE: "governed-egress",
    ADMISSIBLE_TO_REHT: "fresh-reht",
    REFUSED: "repair-substrate-evidence",
}

_RAW_SECRET_KEYS = {
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "credential",
    "credentials",
}


class EdgeSubstrateError(ValueError):
    """Malformed or inadmissible edge-substrate contract input."""


def _require_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EdgeSubstrateError(f"{field_name}: non-empty string required")
    return value.strip()


def _tuple_of_text(value: Any, field_name: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if value is None:
        value = ()
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise EdgeSubstrateError(f"{field_name}: array of strings required")
    out: list[str] = []
    for item in value:
        text = _require_text(item, field_name)
        if text not in out:
            out.append(text)
    if not allow_empty and not out:
        raise EdgeSubstrateError(f"{field_name}: at least one item required")
    return tuple(out)


def _stable_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class EdgeSubstrateManifest:
    runtime_id: str
    runtime_family: str
    board_family: str
    firmware_version: str
    owner_id: str
    device_identity: str
    capabilities: tuple[str, ...]
    access_scopes: tuple[str, ...]
    data_scopes: tuple[str, ...]
    verification_refs: tuple[str, ...]
    network_validated: bool
    tls_available: bool
    audit_ref: str
    authority_effect: str = AUTHORITY_EFFECT

    def as_dict(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "runtime_family": self.runtime_family,
            "board_family": self.board_family,
            "firmware_version": self.firmware_version,
            "owner_id": self.owner_id,
            "device_identity": self.device_identity,
            "capabilities": list(self.capabilities),
            "access_scopes": list(self.access_scopes),
            "data_scopes": list(self.data_scopes),
            "verification_refs": list(self.verification_refs),
            "network_validated": self.network_validated,
            "tls_available": self.tls_available,
            "audit_ref": self.audit_ref,
            "authority_effect": self.authority_effect,
        }


@dataclass(frozen=True)
class EdgeAdmissionRequest:
    action: str
    purpose: str
    required_capabilities: tuple[str, ...] = ()
    requested_access_scopes: tuple[str, ...] = ()
    requested_data_scopes: tuple[str, ...] = ()
    sensitive_data: bool = False
    cloud_required: bool = False
    evidence_refs: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "purpose": self.purpose,
            "required_capabilities": list(self.required_capabilities),
            "requested_access_scopes": list(self.requested_access_scopes),
            "requested_data_scopes": list(self.requested_data_scopes),
            "sensitive_data": self.sensitive_data,
            "cloud_required": self.cloud_required,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True)
class EdgeSubstrateDecision:
    schema_version: str
    status: str
    runtime_id: str
    action: str
    authority_effect: str
    next_boundary: str
    reasons: tuple[str, ...]
    missing_capabilities: tuple[str, ...]
    replay_digest: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "runtime_id": self.runtime_id,
            "action": self.action,
            "authority_effect": self.authority_effect,
            "next_boundary": self.next_boundary,
            "reasons": list(self.reasons),
            "missing_capabilities": list(self.missing_capabilities),
            "replay_digest": self.replay_digest,
        }


_MANIFEST_KEYS = {
    "runtime_id",
    "runtime_family",
    "board_family",
    "firmware_version",
    "owner_id",
    "device_identity",
    "capabilities",
    "access_scopes",
    "data_scopes",
    "verification_refs",
    "network_validated",
    "tls_available",
    "audit_ref",
    "authority_effect",
}

_REQUEST_KEYS = {
    "action",
    "purpose",
    "required_capabilities",
    "requested_access_scopes",
    "requested_data_scopes",
    "sensitive_data",
    "cloud_required",
    "evidence_refs",
}


def _reject_raw_secrets(data: Mapping[str, Any]) -> None:
    for key in data:
        normalized = str(key).strip().lower().replace("-", "_")
        if normalized in _RAW_SECRET_KEYS:
            raise EdgeSubstrateError(
                f"{key}: raw secrets/credentials are outside this contract"
            )


def manifest_from_dict(data: Mapping[str, Any]) -> EdgeSubstrateManifest:
    if not isinstance(data, Mapping):
        raise EdgeSubstrateError("manifest: object required")
    _reject_raw_secrets(data)
    unknown = sorted(set(data) - _MANIFEST_KEYS)
    if unknown:
        raise EdgeSubstrateError(f"manifest: unknown fields: {', '.join(unknown)}")

    authority_effect = data.get("authority_effect", AUTHORITY_EFFECT)
    if authority_effect != AUTHORITY_EFFECT:
        raise EdgeSubstrateError("authority_effect: edge substrate cannot grant authority")

    network_validated = data.get("network_validated")
    tls_available = data.get("tls_available")
    if not isinstance(network_validated, bool):
        raise EdgeSubstrateError("network_validated: boolean required")
    if not isinstance(tls_available, bool):
        raise EdgeSubstrateError("tls_available: boolean required")

    manifest = EdgeSubstrateManifest(
        runtime_id=_require_text(data.get("runtime_id"), "runtime_id"),
        runtime_family=_require_text(data.get("runtime_family"), "runtime_family"),
        board_family=_require_text(data.get("board_family"), "board_family"),
        firmware_version=_require_text(data.get("firmware_version"), "firmware_version"),
        owner_id=_require_text(data.get("owner_id"), "owner_id"),
        device_identity=_require_text(data.get("device_identity"), "device_identity"),
        capabilities=_tuple_of_text(data.get("capabilities"), "capabilities"),
        access_scopes=_tuple_of_text(data.get("access_scopes"), "access_scopes"),
        data_scopes=_tuple_of_text(data.get("data_scopes"), "data_scopes"),
        verification_refs=_tuple_of_text(
            data.get("verification_refs"), "verification_refs", allow_empty=False
        ),
        network_validated=network_validated,
        tls_available=tls_available,
        audit_ref=_require_text(data.get("audit_ref"), "audit_ref"),
        authority_effect=AUTHORITY_EFFECT,
    )

    if manifest.network_validated and "network" not in manifest.capabilities:
        raise EdgeSubstrateError(
            "network_validated: network capability must be declared"
        )
    if manifest.tls_available and "tls" not in manifest.capabilities:
        raise EdgeSubstrateError("tls_available: tls capability must be declared")
    return manifest


def request_from_dict(data: Mapping[str, Any]) -> EdgeAdmissionRequest:
    if not isinstance(data, Mapping):
        raise EdgeSubstrateError("request: object required")
    _reject_raw_secrets(data)
    unknown = sorted(set(data) - _REQUEST_KEYS)
    if unknown:
        raise EdgeSubstrateError(f"request: unknown fields: {', '.join(unknown)}")

    action = _require_text(data.get("action"), "action")
    if action not in ALLOWED_ACTIONS:
        raise EdgeSubstrateError(
            f"action: must be one of {', '.join(ALLOWED_ACTIONS)}"
        )

    sensitive_data = data.get("sensitive_data", False)
    cloud_required = data.get("cloud_required", False)
    if not isinstance(sensitive_data, bool):
        raise EdgeSubstrateError("sensitive_data: boolean required")
    if not isinstance(cloud_required, bool):
        raise EdgeSubstrateError("cloud_required: boolean required")

    return EdgeAdmissionRequest(
        action=action,
        purpose=_require_text(data.get("purpose"), "purpose"),
        required_capabilities=_tuple_of_text(
            data.get("required_capabilities"), "required_capabilities"
        ),
        requested_access_scopes=_tuple_of_text(
            data.get("requested_access_scopes"), "requested_access_scopes"
        ),
        requested_data_scopes=_tuple_of_text(
            data.get("requested_data_scopes"), "requested_data_scopes"
        ),
        sensitive_data=sensitive_data,
        cloud_required=cloud_required,
        evidence_refs=_tuple_of_text(data.get("evidence_refs"), "evidence_refs"),
    )


def assess_edge_substrate(
    manifest: EdgeSubstrateManifest,
    request: EdgeAdmissionRequest,
) -> EdgeSubstrateDecision:
    """Assess substrate eligibility without granting execution authority."""
    reasons: list[str] = []
    missing_capabilities = sorted(
        set(request.required_capabilities) - set(manifest.capabilities)
    )

    if missing_capabilities:
        reasons.append("required capability is not declared by the pinned runtime")

    missing_access = sorted(
        set(request.requested_access_scopes) - set(manifest.access_scopes)
    )
    if missing_access:
        reasons.append("requested access scope exceeds the substrate declaration")

    missing_data = sorted(
        set(request.requested_data_scopes) - set(manifest.data_scopes)
    )
    if missing_data:
        reasons.append("requested data scope exceeds the substrate declaration")

    if request.action in (NETWORK_EGRESS, ACTUATE) and not request.evidence_refs:
        reasons.append("consequence-bearing admission requires request evidence")

    if request.action == NETWORK_EGRESS:
        if "network" not in manifest.capabilities or not manifest.network_validated:
            reasons.append("network path has not been verified for this runtime")
        if request.sensitive_data and (
            "tls" not in manifest.capabilities or not manifest.tls_available
        ):
            reasons.append("sensitive network egress requires verified TLS capability")
        if request.cloud_required and "cloud-egress" not in manifest.capabilities:
            reasons.append("cloud egress was requested but not declared as a capability")

    if request.action == ACTUATE and "actuate" not in manifest.capabilities:
        reasons.append("actuation capability is not declared by the pinned runtime")

    if reasons:
        status = REFUSED
    elif request.action == NETWORK_EGRESS:
        status = ADMISSIBLE_TO_EGRESS_GATE
    elif request.action == ACTUATE:
        status = ADMISSIBLE_TO_REHT
    else:
        status = ADMISSIBLE

    replay_digest = _stable_digest(
        {
            "schema_version": SCHEMA_VERSION,
            "manifest": manifest.as_dict(),
            "request": request.as_dict(),
            "status": status,
            "reasons": reasons,
            "missing_capabilities": missing_capabilities,
        }
    )

    return EdgeSubstrateDecision(
        schema_version=SCHEMA_VERSION,
        status=status,
        runtime_id=manifest.runtime_id,
        action=request.action,
        authority_effect=AUTHORITY_EFFECT,
        next_boundary=_STATUS_NEXT_BOUNDARY[status],
        reasons=tuple(reasons),
        missing_capabilities=tuple(missing_capabilities),
        replay_digest=replay_digest,
    )
