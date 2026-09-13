"""VAIG-only materiality assessment for Operational Continuity.

This module validates a complete, digest-bound ContinuityRevalidationRequest
wire payload and returns a ContinuityImpactAssessment-compatible payload.

It evaluates materiality only. It never issues clearance, selects an execution
permit, calls a provider, or returns an AARM/REHT authorization outcome.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "operational-continuity-vaig-assessment/1.0"
SERVICE_ID = "vaig-continuity-assessment"
ASSESSOR_REF = "vaig:continuity-assessment:1.0"


class ContinuityAssessmentError(ValueError):
    """Raised when the request is malformed, unbound or internally inconsistent."""


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _parse_aware_timestamp(value: Any, *, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ContinuityAssessmentError(f"{field} must be a timestamp string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContinuityAssessmentError(f"{field} is invalid") from exc
    if parsed.tzinfo is None:
        raise ContinuityAssessmentError(f"{field} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _require_mapping(value: Any, *, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContinuityAssessmentError(f"{field} must be an object")
    return value


def _require_sequence(value: Any, *, field: str) -> Sequence[Any]:
    if not isinstance(value, list):
        raise ContinuityAssessmentError(f"{field} must be an array")
    return value


def _require_text(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContinuityAssessmentError(f"{field} is required")
    return value


def _normalized_texts(values: Any, *, field: str) -> tuple[str, ...]:
    sequence = _require_sequence(values, field=field)
    normalized: set[str] = set()
    for item in sequence:
        normalized.add(_require_text(item, field=field))
    return tuple(sorted(normalized))


def _verify_request_digest(request: Mapping[str, Any]) -> str:
    supplied = _require_text(request.get("request_digest"), field="request_digest")
    payload = dict(request)
    payload.pop("request_digest", None)
    expected = canonical_digest(payload)
    if supplied != expected:
        raise ContinuityAssessmentError(
            "request_digest does not match canonical request content"
        )
    return supplied


def _binding(value: Mapping[str, Any], *, field: str) -> tuple[str, str, str, str]:
    return (
        _require_text(value.get("tenant_id"), field=f"{field}.tenant_id"),
        _require_text(
            value.get("action_case_id"), field=f"{field}.action_case_id"
        ),
        _require_text(
            value.get("action_case_hash"), field=f"{field}.action_case_hash"
        ),
        _require_text(value.get("clearance_ref"), field=f"{field}.clearance_ref"),
    )


def _validate_source_coverage(
    request: Mapping[str, Any],
) -> None:
    baseline = _require_mapping(request.get("source_baseline"), field="source_baseline")
    bundle = _require_mapping(request.get("source_bundle"), field="source_bundle")
    entries = _require_sequence(baseline.get("entries"), field="source_baseline.entries")
    observations = _require_sequence(
        bundle.get("observations"), field="source_bundle.observations"
    )

    baseline_keys: dict[tuple[str, str], str] = {}
    for index, raw in enumerate(entries):
        entry = _require_mapping(raw, field=f"source_baseline.entries[{index}]")
        key = (
            _require_text(entry.get("domain"), field="baseline.domain"),
            _require_text(entry.get("source_ref"), field="baseline.source_ref"),
        )
        if key in baseline_keys:
            raise ContinuityAssessmentError("duplicate source baseline entry")
        baseline_keys[key] = _require_text(
            entry.get("fingerprint"), field="baseline.fingerprint"
        )

    observation_keys: dict[tuple[str, str], str] = {}
    for index, raw in enumerate(observations):
        observation = _require_mapping(
            raw, field=f"source_bundle.observations[{index}]"
        )
        key = (
            _require_text(observation.get("domain"), field="observation.domain"),
            _require_text(
                observation.get("source_ref"), field="observation.source_ref"
            ),
        )
        if key in observation_keys:
            raise ContinuityAssessmentError("duplicate source observation")
        observation_keys[key] = _require_text(
            observation.get("expected_fingerprint"),
            field="observation.expected_fingerprint",
        )

    if set(baseline_keys) != set(observation_keys):
        raise ContinuityAssessmentError(
            "source observations do not exactly cover the frozen baseline"
        )
    for key, fingerprint in baseline_keys.items():
        if observation_keys[key] != fingerprint:
            raise ContinuityAssessmentError(
                "source observation is not bound to baseline fingerprint"
            )


def _validate_request(
    raw_request: Mapping[str, Any],
) -> tuple[
    dict[str, Any],
    str,
    str,
    tuple[str, str, str, str],
    tuple[Mapping[str, Any], ...],
    tuple[str, ...],
    datetime,
]:
    request = dict(raw_request)
    required_keys = {
        "request_id",
        "requester_ref",
        "basis",
        "source_baseline",
        "source_bundle",
        "current_fingerprints",
        "triggers",
        "evidence_refs",
        "requested_at",
        "request_digest",
    }
    missing = sorted(required_keys - set(request))
    if missing:
        raise ContinuityAssessmentError(
            "revalidation request is incomplete: " + ",".join(missing)
        )

    request_digest = _verify_request_digest(request)
    request_ref = f"continuity-revalidation-request:{request_digest}"
    _require_text(request.get("request_id"), field="request_id")
    _require_text(request.get("requester_ref"), field="requester_ref")
    requested_at = _parse_aware_timestamp(
        request.get("requested_at"), field="requested_at"
    )

    basis = _require_mapping(request.get("basis"), field="basis")
    binding = _binding(basis, field="basis")

    baseline = _require_mapping(request.get("source_baseline"), field="source_baseline")
    bundle = _require_mapping(request.get("source_bundle"), field="source_bundle")
    baseline_binding = _binding(
        _require_mapping(baseline.get("binding"), field="source_baseline.binding"),
        field="source_baseline.binding",
    )
    bundle_binding = _binding(
        _require_mapping(bundle.get("binding"), field="source_bundle.binding"),
        field="source_bundle.binding",
    )
    if baseline_binding != binding or bundle_binding != binding:
        raise ContinuityAssessmentError(
            "source baseline or bundle does not match the decision basis"
        )
    _validate_source_coverage(request)

    triggers_raw = _require_sequence(request.get("triggers"), field="triggers")
    if not triggers_raw:
        raise ContinuityAssessmentError("revalidation request requires triggers")
    triggers: list[Mapping[str, Any]] = []
    trigger_ids: set[str] = set()
    for index, raw in enumerate(triggers_raw):
        trigger = _require_mapping(raw, field=f"triggers[{index}]")
        trigger_id = _require_text(trigger.get("trigger_id"), field="trigger_id")
        if trigger_id in trigger_ids:
            raise ContinuityAssessmentError("duplicate continuity trigger")
        trigger_ids.add(trigger_id)
        if _binding(trigger, field=f"triggers[{index}]") != binding:
            raise ContinuityAssessmentError(
                "continuity trigger does not match the decision basis"
            )
        observed_at = _parse_aware_timestamp(
            trigger.get("observed_at"), field="trigger.observed_at"
        )
        if observed_at > requested_at:
            raise ContinuityAssessmentError(
                "continuity trigger cannot be newer than the request"
            )
        _require_text(trigger.get("trigger_kind"), field="trigger.trigger_kind")
        _require_text(trigger.get("severity"), field="trigger.severity")
        _require_text(trigger.get("source_ref"), field="trigger.source_ref")
        _require_text(trigger.get("observer_ref"), field="trigger.observer_ref")
        _require_text(
            trigger.get("integrity_status"), field="trigger.integrity_status"
        )
        confidence = trigger.get("confidence")
        freshness = trigger.get("freshness")
        if not isinstance(confidence, (int, float)) or not 0.0 <= confidence <= 1.0:
            raise ContinuityAssessmentError("trigger confidence is invalid")
        if not isinstance(freshness, (int, float)) or not 0.0 <= freshness <= 1.0:
            raise ContinuityAssessmentError("trigger freshness is invalid")
        _normalized_texts(
            trigger.get("source_evidence_refs", []),
            field="trigger.source_evidence_refs",
        )
        triggers.append(trigger)

    evidence_refs = _normalized_texts(
        request.get("evidence_refs"), field="evidence_refs"
    )
    required_evidence: set[str] = set()
    for trigger in triggers:
        required_evidence.update(
            _normalized_texts(
                trigger.get("source_evidence_refs", []),
                field="trigger.source_evidence_refs",
            )
        )
    if not required_evidence.issubset(set(evidence_refs)):
        raise ContinuityAssessmentError(
            "request omits continuity trigger evidence references"
        )

    checkpoint_kinds = {
        trigger.get("trigger_kind") == "revalidation_checkpoint"
        for trigger in triggers
    }
    if True in checkpoint_kinds and len(checkpoint_kinds) > 1:
        raise ContinuityAssessmentError(
            "checkpoint evidence cannot be mixed with drift triggers"
        )
    if True in checkpoint_kinds and len(triggers) != 1:
        raise ContinuityAssessmentError(
            "stable revalidation requires exactly one checkpoint trigger"
        )

    return (
        request,
        request_ref,
        request_digest,
        binding,
        tuple(triggers),
        evidence_refs,
        requested_at,
    )


def _impact_dimensions(triggers: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    mapping = {
        "mandate_changed": "authority",
        "delegation_changed": "authority",
        "identity_changed": "authority",
        "purpose_changed": "purpose",
        "scope_changed": "scope",
        "policy_changed": "policy",
        "evidence_changed": "evidence",
        "evidence_expired": "evidence",
        "asset_state_changed": "state",
        "target_changed": "target",
        "dependency_changed": "dependency",
        "environment_changed": "environment",
        "assumption_invalidated": "assumption",
        "risk_changed": "risk",
        "reversibility_changed": "reversibility",
        "time_window_expired": "time",
        "external_condition_changed": "external_condition",
        "manual_review_requested": "human_review",
        "revalidation_checkpoint": "operational_continuity",
    }
    return tuple(
        sorted(
            {
                mapping.get(str(trigger.get("trigger_kind")), "operational_continuity")
                for trigger in triggers
            }
        )
    )


def _conflicting_source_state(triggers: Sequence[Mapping[str, Any]]) -> bool:
    states: dict[str, set[str]] = {}
    for trigger in triggers:
        source_ref = str(trigger.get("source_ref"))
        current = trigger.get("current_fingerprint")
        if current is None:
            continue
        states.setdefault(source_ref, set()).add(str(current))
    return any(len(values) > 1 for values in states.values())


def _classify_materiality(
    triggers: Sequence[Mapping[str, Any]],
) -> tuple[str, tuple[str, ...], float]:
    if _conflicting_source_state(triggers):
        return (
            "conflicting_evidence",
            ("conflicting_current_source_fingerprints",),
            0.0,
        )

    integrity_failed = any(
        trigger.get("integrity_status") != "verified"
        or float(trigger.get("freshness", 0.0)) < 0.5
        for trigger in triggers
    )
    if integrity_failed:
        return (
            "insufficient_evidence",
            ("unverified_or_stale_continuity_evidence",),
            0.0,
        )

    if (
        len(triggers) == 1
        and triggers[0].get("trigger_kind") == "revalidation_checkpoint"
    ):
        trigger = triggers[0]
        if trigger.get("previous_fingerprint") != trigger.get("current_fingerprint"):
            raise ContinuityAssessmentError(
                "revalidation checkpoint cannot conceal source drift"
            )
        if tuple(trigger.get("changed_fields") or ()):
            raise ContinuityAssessmentError(
                "revalidation checkpoint cannot carry changed fields"
            )
        return (
            "no_material_change",
            ("all_sources_revalidated", "decision_basis_unchanged"),
            1.0,
        )

    return (
        "material_change",
        ("authoritative_source_drift_observed",),
        1.0,
    )


def assess_continuity_request(
    raw_request: Mapping[str, Any],
    *,
    assessed_at: datetime | None = None,
) -> dict[str, Any]:
    """Validate the exact request and return a deterministic VAIG assessment."""

    (
        request,
        request_ref,
        request_digest,
        binding,
        triggers,
        evidence_refs,
        requested_at,
    ) = _validate_request(raw_request)

    assessed_at = assessed_at or datetime.now(timezone.utc)
    if assessed_at.tzinfo is None:
        raise ContinuityAssessmentError("assessed_at must be timezone-aware")
    assessed_at = assessed_at.astimezone(timezone.utc)
    if assessed_at < requested_at:
        raise ContinuityAssessmentError(
            "assessment cannot predate the revalidation request"
        )

    materiality, reason_codes, confidence = _classify_materiality(triggers)
    trigger_refs = tuple(sorted(str(trigger["trigger_id"]) for trigger in triggers))
    assessment_id = (
        "continuity-assessment:"
        + request_digest.split(":", 1)[1][:24]
        + ":"
        + str(int(assessed_at.timestamp() * 1_000_000))
    )
    assessment: dict[str, Any] = {
        "assessment_id": assessment_id,
        "tenant_id": binding[0],
        "trigger_refs": list(trigger_refs),
        "action_case_id": binding[1],
        "action_case_hash": binding[2],
        "clearance_ref": binding[3],
        "materiality": materiality,
        "impact_dimensions": list(_impact_dimensions(triggers)),
        "reason_codes": list(reason_codes),
        "evidence_refs": list(tuple(sorted({request_ref, *evidence_refs}))),
        "assessor_refs": [ASSESSOR_REF],
        "minority_report_refs": [],
        "confidence": confidence,
        "bounded_modification_available": False,
        "bounded_modification_digest": None,
        "assessed_at": assessed_at.isoformat().replace("+00:00", "Z"),
        "assessment_digest": "",
    }
    assessment["assessment_digest"] = canonical_digest(
        {key: value for key, value in assessment.items() if key != "assessment_digest"}
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "service_id": SERVICE_ID,
        "request_ref": request_ref,
        "request_digest": request_digest,
        "assessment": assessment,
    }


__all__ = [
    "ASSESSOR_REF",
    "ContinuityAssessmentError",
    "SCHEMA_VERSION",
    "SERVICE_ID",
    "assess_continuity_request",
    "canonical_digest",
]
