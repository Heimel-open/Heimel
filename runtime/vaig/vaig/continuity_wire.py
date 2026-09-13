"""Strict network envelope for the VAIG continuity assessment service."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from .continuity_assessment import (
    ContinuityAssessmentError,
    assess_continuity_request,
)


WIRE_SCHEMA_VERSION = "operational-continuity-vaig-request/1.0"


def _parse_assessed_at(value: Any) -> datetime:
    if not isinstance(value, str) or not value:
        raise ContinuityAssessmentError("assessed_at is required")
    try:
        assessed_at = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContinuityAssessmentError("assessed_at is invalid") from exc
    if assessed_at.tzinfo is None:
        raise ContinuityAssessmentError("assessed_at must be timezone-aware")
    return assessed_at.astimezone(timezone.utc)


def assess_continuity_wire(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the exact wire envelope and evaluate at the gateway checkpoint time."""

    if not isinstance(payload, Mapping):
        raise ContinuityAssessmentError("wire payload must be an object")
    expected_keys = {"schema_version", "assessed_at", "request"}
    if set(payload) != expected_keys:
        raise ContinuityAssessmentError(
            "wire payload must contain only schema_version, assessed_at and request"
        )
    if payload.get("schema_version") != WIRE_SCHEMA_VERSION:
        raise ContinuityAssessmentError("unsupported continuity wire schema")
    request = payload.get("request")
    if not isinstance(request, Mapping):
        raise ContinuityAssessmentError("request must be an object")
    return assess_continuity_request(
        request,
        assessed_at=_parse_assessed_at(payload.get("assessed_at")),
    )


__all__ = ["WIRE_SCHEMA_VERSION", "assess_continuity_wire"]
