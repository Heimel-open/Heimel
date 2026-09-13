"""Provider-neutral confidential execution continuity for REHT.

This validator treats TEE/confidential-compute attestation as execution evidence,
never as authority. It is deterministic and consumes only the current execution
context plus the exact action contract.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any


def validate_confidential_execution_continuity(
    execution_context: dict[str, Any],
    action_contract: dict[str, Any],
) -> str | None:
    """Return a fail-closed reason when required substrate continuity is broken."""
    if action_contract.get("requires_confidential_execution") is not True:
        return None

    expected_digest = action_contract.get("execution_substrate_binding_digest")
    if not _is_sha256_digest(expected_digest):
        return "EA-19: confidential execution requires an exact substrate binding digest"

    substrate = execution_context.get("execution_substrate")
    if not isinstance(substrate, dict):
        return "EA-19: required confidential execution substrate evidence is absent"

    claimed_digest = substrate.get("binding_digest")
    if not _is_sha256_digest(claimed_digest):
        return "EA-19: execution substrate binding digest is missing or malformed"

    binding_payload = {key: value for key, value in substrate.items() if key != "binding_digest"}
    computed = _digest(binding_payload)
    if not _digest_matches(claimed_digest, computed):
        return "EA-19: execution substrate binding evidence is internally inconsistent"
    if not _same_digest(expected_digest, claimed_digest):
        return "EA-19: execution substrate binding differs from the evaluated action"

    expected_evidence_ref = action_contract.get("execution_substrate_evidence_ref")
    if expected_evidence_ref is not None:
        if not isinstance(expected_evidence_ref, str) or not expected_evidence_ref:
            return "EA-19: confidential execution evidence reference is malformed"
        if substrate.get("evidence_ref") != expected_evidence_ref:
            return "EA-19: execution substrate evidence reference differs from the evaluated action"

    if substrate.get("verification_status") != "VERIFIED":
        return "EA-19: execution substrate attestation is not verified"
    if substrate.get("revoked") is True:
        return "EA-19: execution substrate attestation is revoked"
    if substrate.get("confidentiality_protected") is not True:
        return "EA-19: required confidentiality protection is not established"
    if substrate.get("integrity_protected") is not True:
        return "EA-19: required execution integrity protection is not established"
    if substrate.get("isolation_enforced") is not True:
        return "EA-19: required execution isolation is not established"
    if substrate.get("authority_effect") != "NO_AUTHORITY_CREATION":
        return "EA-19: execution substrate evidence attempted to create authority"
    if substrate.get("can_issue_clearance") is not False:
        return "EA-19: execution substrate evidence attempted to issue clearance"

    now = _parse_aware((execution_context.get("time") or {}).get("now"))
    attested_at = _parse_aware(substrate.get("attested_at"))
    valid_until = _parse_aware(substrate.get("valid_until"))
    max_age = substrate.get("max_attestation_age_seconds")
    if now is None or attested_at is None or valid_until is None:
        return "EA-19: confidential execution freshness cannot be proven"
    if isinstance(max_age, bool) or not isinstance(max_age, int) or max_age <= 0:
        return "EA-19: confidential execution freshness limit is invalid"
    if valid_until <= attested_at or attested_at > now:
        return "EA-19: execution substrate attestation is future-dated or malformed"
    if valid_until <= now:
        return "EA-19: execution substrate attestation is expired"
    if (now - attested_at).total_seconds() > max_age:
        return "EA-19: execution substrate attestation is stale"

    expected_model = action_contract.get("execution_model_digest")
    if expected_model is not None and substrate.get("model_digest") != expected_model:
        return "EA-19: attested model differs from the evaluated action"
    expected_workload = action_contract.get("execution_workload_digest")
    if expected_workload is not None and substrate.get("workload_digest") != expected_workload:
        return "EA-19: attested workload differs from the evaluated action"
    expected_measurement = action_contract.get("execution_measurement")
    if expected_measurement is not None and substrate.get("measurement") != expected_measurement:
        return "EA-19: attested execution measurement differs from the evaluated action"

    return None


def substrate_binding_digest(substrate_evidence: dict[str, Any]) -> str:
    """Return the canonical prefixed digest for normalized substrate evidence."""
    payload = {
        key: value
        for key, value in substrate_evidence.items()
        if key != "binding_digest"
    }
    return "sha256:" + _digest(payload)


def _is_sha256_digest(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    raw = value[7:] if value.startswith("sha256:") else value
    return len(raw) == 64 and all(char in "0123456789abcdef" for char in raw)


def _same_digest(left: str, right: str) -> bool:
    left_raw = left[7:] if left.startswith("sha256:") else left
    right_raw = right[7:] if right.startswith("sha256:") else right
    return left_raw == right_raw


def _digest_matches(claimed: str, computed_raw: str) -> bool:
    return _same_digest(claimed, computed_raw)


def _parse_aware(raw: Any) -> datetime | None:
    if not isinstance(raw, str) or not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return None
    return parsed


def _digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
