"""Deterministic VAIG evaluation of RACS AAEC trajectory evidence.

This module emits typed evaluation signals and a canonical recommendation.
It never establishes authority, issues REHT clearance, creates a permit, or
executes a consequence-bearing action.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "vaig-aaec-trajectory-evaluation/1.0"
SERVICE_ID = "vaig-aaec-trajectory-evaluator"
ASSESSOR_REF = "vaig:aaec-trajectory-evaluator:1.0"

_PRECEDENCE = {
    "ALLOW": 0,
    "MODIFY": 1,
    "DEFER": 2,
    "STEP_UP": 3,
    "DENY": 4,
    "HALT": 5,
}
_RACS_MINIMUM = {
    "NONE": "ALLOW",
    "STEP_UP": "STEP_UP",
    "DENY": "DENY",
    "HALT": "HALT",
}
_ALLOWED_STATUS = {"MATCH", "MISMATCH", "INCOMPLETE", "UNVERIFIABLE"}

# signal_type -> (decision, hard_gate, VAIG reason code)
_SIGNAL_POLICY = {
    "trajectory_goal_divergence": ("DENY", True, "VAIG_AAEC_GOAL_DIVERGENCE"),
    "target_set_expansion": ("STEP_UP", False, "VAIG_AAEC_TARGET_SET_EXPANSION"),
    "credential_harvesting_or_secret_access": (
        "DENY", True, "VAIG_AAEC_CREDENTIAL_HARVESTING_OR_SECRET_ACCESS"
    ),
    "unverified_credential_provenance": (
        "DENY", True, "VAIG_AAEC_UNVERIFIED_CREDENTIAL_PROVENANCE"
    ),
    "authority_amplification": (
        "STEP_UP", False, "VAIG_AAEC_AUTHORITY_AMPLIFICATION"
    ),
    "persistence_creation": ("STEP_UP", False, "VAIG_AAEC_PERSISTENCE_CREATION"),
    "lateral_movement": ("DENY", True, "VAIG_AAEC_LATERAL_MOVEMENT"),
    "integrity_control_disablement": (
        "HALT", True, "VAIG_AAEC_INTEGRITY_CONTROL_DISABLEMENT"
    ),
    "container_boundary_probe": (
        "DENY", True, "VAIG_AAEC_CONTAINER_BOUNDARY_PROBE"
    ),
    "destructive_action": ("STEP_UP", False, "VAIG_AAEC_DESTRUCTIVE_ACTION"),
    "cumulative_irreversible_effect": (
        "STEP_UP", False, "VAIG_AAEC_CUMULATIVE_IRREVERSIBLE_EFFECT"
    ),
    "machine_speed_adaptive_retry": (
        "STEP_UP", False, "VAIG_AAEC_MACHINE_SPEED_ADAPTIVE_RETRY"
    ),
    "unverified_self_reported_claim": (
        "STEP_UP", False, "VAIG_AAEC_UNVERIFIED_SELF_REPORTED_CLAIM"
    ),
    "incomplete_receipt_lineage": (
        "DENY", True, "VAIG_AAEC_INCOMPLETE_RECEIPT_LINEAGE"
    ),
    "substituted_receipt_lineage": (
        "DENY", True, "VAIG_AAEC_SUBSTITUTED_RECEIPT_LINEAGE"
    ),
    "context_integrity_failure": (
        "DENY", True, "VAIG_AAEC_CONTEXT_INTEGRITY_FAILURE"
    ),
    "independent_halt": ("HALT", True, "VAIG_AAEC_INDEPENDENT_HALT"),
    "insufficient_observation_evidence": (
        "DEFER", True, "VAIG_AAEC_INSUFFICIENT_OBSERVATION_EVIDENCE"
    ),
}
_RACS_REASON_TO_SIGNAL = {
    "AAEC_CONTEXT_DIGEST_MISMATCH": "context_integrity_failure",
    "AAEC_UNSUPPORTED_VERSION": "context_integrity_failure",
    "AAEC_AUTHORITY_CREATION_FORBIDDEN": "context_integrity_failure",
    "AAEC_CONTEXT_EXPIRED": "context_integrity_failure",
    "AAEC_CONTEXT_NOT_YET_VALID": "context_integrity_failure",
    "AAEC_TRAJECTORY_LINEAGE_MISSING": "incomplete_receipt_lineage",
    "AAEC_TRAJECTORY_LINEAGE_MISMATCH": "substituted_receipt_lineage",
    "AAEC_ACTION_SEQUENCE_GAP": "incomplete_receipt_lineage",
    "AAEC_AUTHORITY_LINEAGE_CHANGED": "authority_amplification",
    "AAEC_PRINCIPAL_BINDING_CHANGED": "authority_amplification",
    "AAEC_AGENT_IDENTITY_CHANGED": "authority_amplification",
    "AAEC_TARGET_SET_DIGEST_MISMATCH": "context_integrity_failure",
    "AAEC_TARGET_SET_EXPANSION": "target_set_expansion",
    "AAEC_TARGET_EXPANSION_EVIDENCE_MISSING": "target_set_expansion",
    "AAEC_COUNTER_REGRESSION": "context_integrity_failure",
    "AAEC_COUNTER_TRANSITION_MISMATCH": "context_integrity_failure",
    "AAEC_CUMULATIVE_CEILING_EXCEEDED": "cumulative_irreversible_effect",
    "AAEC_HARVESTED_CREDENTIAL_PROVENANCE": "unverified_credential_provenance",
    "AAEC_SELF_CREATED_AUTHORITY": "unverified_credential_provenance",
    "AAEC_MANDATORY_EVIDENCE_MISSING": "insufficient_observation_evidence",
    "AAEC_DESTRUCTIVE_OBLIGATION_MISSING": "destructive_action",
    "AAEC_UNVERIFIED_EXFILTRATION_CLAIM": "unverified_self_reported_claim",
    "AAEC_VERIFIED_CLAIM_EVIDENCE_MISSING": "insufficient_observation_evidence",
    "AAEC_MACHINE_SPEED_ADAPTIVE_RETRY": "machine_speed_adaptive_retry",
    "AAEC_INDEPENDENT_HALT": "independent_halt",
}
_ALLOWED_RACS_REASONS = frozenset(_RACS_REASON_TO_SIGNAL)
_CONDITIONS = {
    "authority_amplification": "fresh_authority_verification",
    "persistence_creation": "fresh_human_approval",
    "destructive_action": "fresh_human_approval",
    "cumulative_irreversible_effect": "cumulative_consequence_review",
    "machine_speed_adaptive_retry": "human_review_before_next_action",
    "unverified_self_reported_claim": "independent_observation_required",
    "insufficient_observation_evidence": "additional_verified_evidence_required",
}


class AAECTrajectoryEvaluationError(ValueError):
    """The request is malformed, unbound, stale or internally inconsistent."""


def canonical_digest(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise AAECTrajectoryEvaluationError(f"{field} is required")
    return value


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AAECTrajectoryEvaluationError(f"{field} must be an object")
    return value


def _list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise AAECTrajectoryEvaluationError(f"{field} must be an array")
    return value


def _timestamp(value: Any, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(_text(value, field).replace("Z", "+00:00"))
    except ValueError as exc:
        raise AAECTrajectoryEvaluationError(f"{field} is invalid") from exc
    if parsed.tzinfo is None:
        raise AAECTrajectoryEvaluationError(f"{field} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _refs(values: Any, field: str) -> tuple[str, ...]:
    raw = _list(values, field)
    normalized = tuple(sorted({_text(item, field) for item in raw}))
    if len(normalized) != len(raw):
        raise AAECTrajectoryEvaluationError(f"{field} contains duplicates")
    return normalized


def _verify_digest(request: Mapping[str, Any]) -> str:
    supplied = _text(request.get("request_digest"), "request_digest")
    payload = dict(request)
    payload.pop("request_digest", None)
    if supplied != canonical_digest(payload):
        raise AAECTrajectoryEvaluationError(
            "request_digest does not match canonical request content"
        )
    return supplied


def _signal(
    signal_type: str,
    *,
    source: str,
    evidence_refs: Sequence[str],
    confidence: float = 1.0,
    extra_reasons: Sequence[str] = (),
) -> dict[str, Any]:
    decision, hard_gate, reason = _SIGNAL_POLICY[signal_type]
    return {
        "signal_type": signal_type,
        "source": source,
        "decision": decision,
        "hard_gate": hard_gate,
        "confidence": round(float(confidence), 6),
        "reason_codes": sorted({reason, *extra_reasons}),
        "evidence_refs": sorted(set(evidence_refs)),
    }


def _upsert(signals: dict[str, dict[str, Any]], candidate: dict[str, Any]) -> None:
    key = str(candidate["signal_type"])
    current = signals.get(key)
    if current is None:
        signals[key] = candidate
        return
    current["decision"] = max(
        (current["decision"], candidate["decision"]),
        key=_PRECEDENCE.__getitem__,
    )
    current["hard_gate"] = bool(current["hard_gate"] or candidate["hard_gate"])
    current["confidence"] = max(current["confidence"], candidate["confidence"])
    current["reason_codes"] = sorted(
        set(current["reason_codes"]) | set(candidate["reason_codes"])
    )
    current["evidence_refs"] = sorted(
        set(current["evidence_refs"]) | set(candidate["evidence_refs"])
    )
    current["source"] = "+".join(
        sorted(set(str(current["source"]).split("+")) | {str(candidate["source"])})
    )


def _validate_racs(
    context: Mapping[str, Any],
    validation: Mapping[str, Any],
) -> tuple[str, str, int, tuple[str, ...]]:
    if context.get("trajectory_version") != "aaec-trajectory-context-0.3":
        raise AAECTrajectoryEvaluationError("unsupported RACS AAEC trajectory version")
    trajectory_id = _text(context.get("trajectory_id"), "trajectory_context.trajectory_id")
    context_digest = _text(
        context.get("context_digest"), "trajectory_context.context_digest"
    )
    sequence_no = context.get("sequence_no")
    if not isinstance(sequence_no, int) or sequence_no < 0:
        raise AAECTrajectoryEvaluationError(
            "trajectory_context.sequence_no must be a non-negative integer"
        )

    status = _text(validation.get("validation_status"), "racs_validation.validation_status")
    minimum = _text(validation.get("minimum_response"), "racs_validation.minimum_response")
    if status not in _ALLOWED_STATUS or minimum not in _RACS_MINIMUM:
        raise AAECTrajectoryEvaluationError("unsupported RACS validation result")
    if validation.get("execution_authority") != "NONE":
        raise AAECTrajectoryEvaluationError(
            "RACS validation must not carry execution authority"
        )
    for field, expected in {
        "context_digest": context_digest,
        "trajectory_id": trajectory_id,
        "sequence_no": sequence_no,
    }.items():
        if validation.get(field) != expected:
            raise AAECTrajectoryEvaluationError(
                f"racs_validation.{field} does not match trajectory context"
            )

    reasons = tuple(
        sorted(
            {
                _text(item, "racs_validation.reason_codes")
                for item in _list(
                    validation.get("reason_codes", []),
                    "racs_validation.reason_codes",
                )
            }
        )
    )
    unknown = sorted(set(reasons) - _ALLOWED_RACS_REASONS)
    if unknown:
        raise AAECTrajectoryEvaluationError(
            "unsupported RACS AAEC reason codes: " + ",".join(unknown)
        )
    if status != "MATCH" and minimum == "NONE":
        raise AAECTrajectoryEvaluationError(
            "non-matching RACS validation cannot have minimum response NONE"
        )
    if status != "MATCH" and not reasons:
        raise AAECTrajectoryEvaluationError(
            "non-matching RACS validation requires reason codes"
        )
    return context_digest, trajectory_id, sequence_no, reasons


def _context_signals(
    context: Mapping[str, Any], evidence_refs: Sequence[str]
) -> list[dict[str, Any]]:
    action = _mapping(
        context.get("action_observation"),
        "trajectory_context.action_observation",
    )
    action_class = str(action.get("action_class", "GENERAL"))
    present: list[str] = []
    if action.get("new_target_ids"):
        present.append("target_set_expansion")
    if action.get("secret_access"):
        present.append("credential_harvesting_or_secret_access")
    if action.get("credential_provenance") in {"HARVESTED", "UNKNOWN"}:
        present.append("unverified_credential_provenance")
    if action.get("identity_provenance") == "SELF_CREATED_IN_TRAJECTORY":
        present.append("unverified_credential_provenance")
    if action.get("authority_amplification"):
        present.append("authority_amplification")
    if action.get("persistence_creation"):
        present.append("persistence_creation")
    if action.get("lateral_movement"):
        present.append("lateral_movement")
    if action.get("integrity_control_change"):
        present.append("integrity_control_disablement")
    if action_class == "CONTAINER_BOUNDARY_PROBE":
        present.append("container_boundary_probe")
    if action.get("destructive"):
        present.append("destructive_action")
    if action.get("irreversible"):
        present.append("cumulative_irreversible_effect")
    if action.get("machine_speed_adaptive_retry"):
        present.append("machine_speed_adaptive_retry")
    claims = _list(action.get("claims", []), "action_observation.claims")
    if any(
        isinstance(claim, Mapping)
        and claim.get("verification_state") != "VERIFIED"
        for claim in claims
    ):
        present.append("unverified_self_reported_claim")
    return [
        _signal(item, source="racs_context", evidence_refs=evidence_refs)
        for item in sorted(set(present))
    ]


def _observation_signals(
    observations: Sequence[Any], request_refs: Sequence[str]
) -> list[dict[str, Any]]:
    available = set(request_refs)
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for index, raw in enumerate(observations):
        item = _mapping(raw, f"observations[{index}]")
        signal_type = _text(item.get("signal_type"), f"observations[{index}].signal_type")
        if signal_type not in _SIGNAL_POLICY:
            raise AAECTrajectoryEvaluationError(
                f"unsupported AAEC signal type: {signal_type}"
            )
        if signal_type in seen:
            raise AAECTrajectoryEvaluationError(
                f"duplicate AAEC signal observation: {signal_type}"
            )
        seen.add(signal_type)
        if not isinstance(item.get("present"), bool):
            raise AAECTrajectoryEvaluationError(
                f"observations[{index}].present must be boolean"
            )
        if not item["present"]:
            continue
        confidence, freshness = item.get("confidence"), item.get("freshness")
        if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            raise AAECTrajectoryEvaluationError(
                f"observations[{index}].confidence is invalid"
            )
        if not isinstance(freshness, (int, float)) or not 0 <= freshness <= 1:
            raise AAECTrajectoryEvaluationError(
                f"observations[{index}].freshness is invalid"
            )
        evidence = _refs(
            item.get("evidence_refs", []),
            f"observations[{index}].evidence_refs",
        )
        if not evidence or not set(evidence).issubset(available):
            raise AAECTrajectoryEvaluationError(
                f"observations[{index}] evidence is not fully bound to the request"
            )
        if item.get("integrity_status") != "VERIFIED" or freshness < 0.5:
            result.append(
                _signal(
                    "insufficient_observation_evidence",
                    source="vaig_observation",
                    evidence_refs=evidence,
                    confidence=0.0,
                    extra_reasons=(f"VAIG_AAEC_UNVERIFIED_{signal_type.upper()}",),
                )
            )
        else:
            result.append(
                _signal(
                    signal_type,
                    source="vaig_observation",
                    evidence_refs=evidence,
                    confidence=float(confidence),
                )
            )
    return result


def evaluate_aaec_trajectory(
    raw_request: Mapping[str, Any],
    *,
    evaluated_at: datetime | None = None,
) -> dict[str, Any]:
    """Evaluate one exact trajectory state and return evidence-only output."""

    request = deepcopy(dict(raw_request))
    required = {
        "request_id",
        "trajectory_context",
        "racs_validation",
        "observations",
        "evidence_refs",
        "requested_at",
        "request_digest",
    }
    missing = sorted(required - set(request))
    if missing:
        raise AAECTrajectoryEvaluationError(
            "AAEC evaluation request is incomplete: " + ",".join(missing)
        )

    request_digest = _verify_digest(request)
    request_ref = f"aaec-trajectory-evaluation-request:{request_digest}"
    _text(request.get("request_id"), "request_id")
    requested_at = _timestamp(request.get("requested_at"), "requested_at")
    evaluated_at = evaluated_at or datetime.now(timezone.utc)
    if evaluated_at.tzinfo is None:
        raise AAECTrajectoryEvaluationError("evaluated_at must be timezone-aware")
    evaluated_at = evaluated_at.astimezone(timezone.utc)
    if evaluated_at < requested_at:
        raise AAECTrajectoryEvaluationError("evaluation cannot predate the request")

    context = _mapping(request.get("trajectory_context"), "trajectory_context")
    validation = _mapping(request.get("racs_validation"), "racs_validation")
    context_digest, trajectory_id, sequence_no, racs_reasons = _validate_racs(
        context, validation
    )
    request_refs = _refs(request.get("evidence_refs"), "evidence_refs")
    context_bindings = _mapping(
        context.get("evidence_bindings", {}),
        "trajectory_context.evidence_bindings",
    )
    context_refs = tuple(
        sorted({_text(value, "trajectory_context.evidence_bindings") for value in context_bindings.values()})
    )
    all_refs = tuple(sorted({request_ref, *request_refs, *context_refs}))
    signals: dict[str, dict[str, Any]] = {}

    for reason in racs_reasons:
        candidate = _signal(
            _RACS_REASON_TO_SIGNAL[reason],
            source="racs_validation",
            evidence_refs=all_refs,
            extra_reasons=(reason,),
        )
        minimum = str(validation["minimum_response"])
        if minimum in {"DENY", "HALT"}:
            candidate["decision"] = minimum
            candidate["hard_gate"] = True
        _upsert(signals, candidate)
    for candidate in _context_signals(context, all_refs):
        _upsert(signals, candidate)
    for candidate in _observation_signals(
        _list(request.get("observations"), "observations"),
        request_refs,
    ):
        _upsert(signals, candidate)

    ordered = [signals[key] for key in sorted(signals)]
    decisions = [
        _RACS_MINIMUM[str(validation["minimum_response"])],
        *(item["decision"] for item in ordered),
    ]
    outcome = max(decisions, key=_PRECEDENCE.__getitem__)
    reasons = sorted(
        {reason for item in ordered for reason in item["reason_codes"]}
    )
    conditions = sorted(
        {
            _CONDITIONS[item["signal_type"]]
            for item in ordered
            if item["signal_type"] in _CONDITIONS
        }
    )
    confidence = min((item["confidence"] for item in ordered), default=1.0)

    evaluation = {
        "evaluation_id": (
            "vaig-aaec-evaluation:"
            + request_digest.split(":", 1)[1][:24]
            + ":"
            + str(int(evaluated_at.timestamp() * 1_000_000))
        ),
        "trajectory_id": trajectory_id,
        "sequence_no": sequence_no,
        "context_digest": context_digest,
        "racs_validation_status": validation["validation_status"],
        "racs_minimum_response": validation["minimum_response"],
        "signals": ordered,
        "reason_codes": reasons,
        "recommended_outcome": outcome,
        "conditions": conditions,
        "evidence_refs": list(all_refs),
        "confidence": round(float(confidence), 6),
        "authority_effect": "NO_AUTHORITY_CREATION",
        "execution_authority": "NONE",
        "can_issue_clearance": False,
        "evaluated_at": evaluated_at.isoformat().replace("+00:00", "Z"),
        "assessment_ref": ASSESSOR_REF,
        "evaluation_digest": "",
    }
    evaluation["evaluation_digest"] = canonical_digest(
        {key: value for key, value in evaluation.items() if key != "evaluation_digest"}
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "service_id": SERVICE_ID,
        "request_ref": request_ref,
        "request_digest": request_digest,
        "evaluation": evaluation,
    }
