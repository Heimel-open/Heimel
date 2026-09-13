"""Separately deployable second-operator replay for VAIG Coherence.

The replay service receives the frozen pre-replay packet, verifies its exact
VAIG replay digest, reruns the canonical deterministic evaluator with a distinct
operator identity, and emits a digest-bound evidence artifact. It never creates
REHT clearance or execution authority.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from typing import Any, Mapping

import rfc8785

from .coherence_evaluation import (
    CoherenceEvaluationGateV1,
    EvaluationStatus,
    replay_packet_digest,
)
from .coherence_service import CoherenceTransportError, parse_evaluation_input

_REPLAY_SCHEMA = "runtime_coherence_replay_artifact.v1"
_PACKET_VERSION = "coherence-evaluation-input-v1"
_NO_AUTHORITY = "NO_AUTHORITY_CREATION"


class CoherenceReplayError(ValueError):
    """The replay request cannot be independently reconstructed or verified."""


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CoherenceReplayError(f"{field} is required")
    return value.strip()


def _sha256(value: Any, field: str) -> str:
    raw = _text(value, field)
    if not raw.startswith("sha256:") or len(raw) != 71:
        raise CoherenceReplayError(f"{field} must be a sha256 binding")
    try:
        int(raw[7:], 16)
    except ValueError as exc:
        raise CoherenceReplayError(f"{field} must be a sha256 binding") from exc
    return raw


def _digest(value: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(rfc8785.dumps(dict(value))).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def replay_frozen_packet(
    request: Mapping[str, Any],
    *,
    operator_ref: str,
) -> dict[str, Any]:
    """Replay one exact pre-replay packet as a distinct INDEPENDENT operator."""
    if not isinstance(request, Mapping):
        raise CoherenceReplayError("replay request must be an object")
    operator = _text(operator_ref, "operator_ref")
    action_ref = _text(request.get("action_ref"), "action_ref")
    supplied_digest = _sha256(request.get("packet_digest"), "packet_digest")
    packet_version = _text(request.get("packet_version"), "packet_version")
    if packet_version != _PACKET_VERSION:
        raise CoherenceReplayError("unsupported replay packet version")
    evidence_bundle_digest = _sha256(
        request.get("evidence_bundle_digest"), "evidence_bundle_digest"
    )
    evidence_producer_ref = _text(
        request.get("evidence_producer_ref"), "evidence_producer_ref"
    )
    if operator == evidence_producer_ref:
        raise CoherenceReplayError(
            "second-operator identity must differ from evidence producer"
        )

    frozen = request.get("frozen_packet")
    if not isinstance(frozen, Mapping):
        raise CoherenceReplayError("frozen_packet must be an object")
    if "replay" in frozen:
        raise CoherenceReplayError("frozen_packet must not contain prior replay outcome")
    boundary = frozen.get("boundary")
    if not isinstance(boundary, Mapping) or boundary.get("object_id") != action_ref:
        raise CoherenceReplayError("frozen packet action boundary mismatch")

    # Candidate replay is inserted only after the first-outcome-free packet has
    # been received. Parsing fills the exact canonical defaults used by VAIG.
    candidate = dict(frozen)
    candidate["replay"] = {
        "operator": "INDEPENDENT",
        "result": "PASS",
        "operator_ref": operator,
        "packet_digest": supplied_digest,
        "packet_version": packet_version,
        "blind": True,
        "deltas": [],
        "unresolved": [],
    }
    try:
        evaluation = parse_evaluation_input(candidate)
    except CoherenceTransportError as exc:
        raise CoherenceReplayError(str(exc)) from exc

    reconstructed_digest = replay_packet_digest(evaluation)
    if reconstructed_digest != supplied_digest:
        raise CoherenceReplayError("replay packet digest mismatch")

    result = CoherenceEvaluationGateV1().evaluate(evaluation)
    unresolved = [] if result.status is EvaluationStatus.PASS else list(result.reason_codes)
    executed_at = _now()
    verification_material = {
        "action_ref": action_ref,
        "packet_digest": reconstructed_digest,
        "packet_version": packet_version,
        "evidence_bundle_digest": evidence_bundle_digest,
        "evidence_producer_ref": evidence_producer_ref,
        "operator_ref": operator,
        "operator_kind": "INDEPENDENT",
        "result": result.status.value,
        "reason_codes": list(result.reason_codes),
        "evaluation_input_digest": result.input_digest,
        "executed_at": executed_at,
    }
    verification_digest = _digest(verification_material)
    artifact = {
        "schema_version": _REPLAY_SCHEMA,
        "action_ref": action_ref,
        "packet_digest": reconstructed_digest,
        "packet_version": packet_version,
        "evidence_bundle_digest": evidence_bundle_digest,
        "evidence_producer_ref": evidence_producer_ref,
        "operator_ref": operator,
        "operator_kind": "INDEPENDENT",
        "result": result.status.value,
        "blind": True,
        "deltas": [],
        "unresolved": unresolved,
        "executed_at": executed_at,
        "verification_ref": f"vaig-second-operator:{operator}",
        "verification_digest": verification_digest,
        "independently_verified": True,
        "authority_effect": _NO_AUTHORITY,
        "can_issue_clearance": False,
    }
    return {**artifact, "artifact_digest": _digest(artifact)}


__all__ = ["CoherenceReplayError", "replay_frozen_packet"]
