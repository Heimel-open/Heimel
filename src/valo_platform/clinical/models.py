"""Canonical clinical event and shadow-observation models.

These models are intentionally domain-observational. They do not diagnose,
recommend treatment, or authorize clinical execution.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ClinicalEventType(str, Enum):
    VITAL_MEASUREMENT = "vital_measurement"
    EWS_CALCULATED = "ews_calculated"
    REASSURANCE_MEASUREMENT = "reassurance_measurement"
    NOTIFICATION_CREATED = "notification_created"
    NOTIFICATION_DELIVERED = "notification_delivered"
    ACKNOWLEDGED = "acknowledged"
    PATIENT_TRANSFERRED = "patient_transferred"
    PATIENT_DISCHARGED = "patient_discharged"
    CONTEXT_CHANGED = "context_changed"
    INTERVENTION_RECORDED = "intervention_recorded"
    DEVICE_STATUS = "device_status"
    SIGNAL_QUALITY = "signal_quality"


class DataQualityState(str, Enum):
    VALID = "valid"
    DEGRADED = "degraded"
    INVALID = "invalid"
    UNKNOWN = "unknown"


class GuardianShadowObservation(str, Enum):
    UNCHANGED = "unchanged"
    CHANGED_RECHECK = "changed_recheck"
    EVIDENCE_DEGRADED = "evidence_degraded"
    SUPERSEDED = "superseded"
    CONTEXT_MISMATCH = "context_mismatch"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ClinicalEvent(BaseModel):
    """Normalized event emitted by a deployment-specific adapter.

    `encounter_token` MUST be pseudonymous. Direct patient identifiers are not
    permitted in this model or downstream receipts.
    """

    event_id: str
    event_type: ClinicalEventType
    encounter_token: str
    source_timestamp: datetime
    ingestion_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    source_system: str
    source_device: str | None = None
    source_sequence: int | None = None
    schema_version: str = "clinical-event-v0.1"
    mapping_profile_version: str = "unmapped"
    evidence_fingerprint: str
    quality_state: DataQualityState = DataQualityState.UNKNOWN
    values: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    model_config = ConfigDict(frozen=True, use_enum_values=False)


class ClinicalStateSnapshot(BaseModel):
    """Deterministically reconstructed state at one workflow checkpoint."""

    encounter_token: str
    checkpoint: str
    timestamp: datetime
    event_refs: list[str] = Field(default_factory=list)
    latest_measurement_refs: list[str] = Field(default_factory=list)
    context_refs: list[str] = Field(default_factory=list)
    quality_refs: list[str] = Field(default_factory=list)
    state_fingerprint: str
    values: dict[str, Any] = Field(default_factory=dict)
    complete: bool = False
    missing_requirements: list[str] = Field(default_factory=list)
    model_config = ConfigDict(frozen=True)
