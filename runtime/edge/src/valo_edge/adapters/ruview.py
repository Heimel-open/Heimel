"""RuView WiFi-CSI intake for VALO Edge.

RuView is an observation source only. This adapter normalizes a RuView reading
into existing VALO Edge evidence contracts; it never authorizes an action and
never writes authoritative world state.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from valo_edge.contracts import sha256_digest
from valo_edge.vaig import ModelSignalV1, PhysicalStateEvidenceV1, SensorEvidenceV1


class RuViewObservationV1(BaseModel):
    """Normalized RuView observation at the VALO Edge boundary."""

    source_id: str
    observed_at_iso: str
    environment_id: str
    calibration_id: str
    pipeline_version: str
    presence: Optional[bool] = None
    motion_score: Optional[float] = Field(default=None, ge=0.0)
    breathing_bpm: Optional[float] = Field(default=None, ge=0.0)
    heart_rate_bpm: Optional[float] = Field(default=None, ge=0.0)
    fall_detected: Optional[bool] = None
    occupancy_estimate: Optional[int] = Field(default=None, ge=0)
    signal_quality: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    model_hash: str = ""
    witness_digest: str = ""
    simulated: bool = False

    @field_validator("observed_at_iso")
    @classmethod
    def timestamp_must_be_zoned(cls, value: str) -> str:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("observed_at_iso must include a timezone")
        return value

    @model_validator(mode="after")
    def require_observation(self) -> "RuViewObservationV1":
        values = (
            self.presence,
            self.motion_score,
            self.breathing_bpm,
            self.heart_rate_bpm,
            self.fall_detected,
            self.occupancy_estimate,
            self.signal_quality,
        )
        if all(value is None for value in values):
            raise ValueError("at least one RuView observation value is required")
        if not self.source_id or not self.environment_id or not self.calibration_id:
            raise ValueError("source, environment and calibration binding are required")
        if not self.pipeline_version:
            raise ValueError("pipeline_version is required")
        return self


class RuViewEvidenceBundleV1(BaseModel):
    """Evidence-only output suitable for Local VAIG Edge."""

    sensor: SensorEvidenceV1
    physical_state: PhysicalStateEvidenceV1
    model_signal: Optional[ModelSignalV1] = None


class RuViewAdapter:
    """Convert normalized RuView observations to existing VALO Edge evidence."""

    def __init__(
        self,
        *,
        expected_environment_id: Optional[str] = None,
        require_witness: bool = False,
        allow_simulated: bool = False,
    ) -> None:
        self.expected_environment_id = expected_environment_id
        self.require_witness = require_witness
        self.allow_simulated = allow_simulated

    def adapt(self, observation: RuViewObservationV1) -> RuViewEvidenceBundleV1:
        if (
            self.expected_environment_id is not None
            and observation.environment_id != self.expected_environment_id
        ):
            raise ValueError("RuView observation environment does not match adapter binding")
        if self.require_witness and not observation.witness_digest:
            raise ValueError("RuView witness evidence is required")
        if observation.simulated and not self.allow_simulated:
            raise ValueError("simulated RuView observations are disabled")

        normalized = observation.model_dump(mode="json", exclude_none=True)
        evidence_digest = sha256_digest(normalized)
        provenance = [
            "ruview",
            f"source:{observation.source_id}",
            f"environment:{observation.environment_id}",
            f"calibration:{observation.calibration_id}",
            f"pipeline:{observation.pipeline_version}",
        ]
        if observation.model_hash:
            provenance.append(f"model:{observation.model_hash}")
        if observation.witness_digest:
            provenance.append(f"witness:{observation.witness_digest}")

        sensor = SensorEvidenceV1(
            source_id=observation.source_id,
            source_type="wifi-csi/ruview",
            evidence_digest=evidence_digest,
            observed_at_iso=observation.observed_at_iso,
            provenance=provenance,
        )

        state = {
            "ruview.environment_id": observation.environment_id,
            "ruview.calibration_id": observation.calibration_id,
            "ruview.pipeline_version": observation.pipeline_version,
            "ruview.simulated": observation.simulated,
        }
        optional_state = {
            "ruview.presence": observation.presence,
            "ruview.motion_score": observation.motion_score,
            "ruview.breathing_bpm": observation.breathing_bpm,
            "ruview.heart_rate_bpm": observation.heart_rate_bpm,
            "ruview.fall_detected": observation.fall_detected,
            "ruview.occupancy_estimate": observation.occupancy_estimate,
            "ruview.signal_quality": observation.signal_quality,
        }
        state.update({key: value for key, value in optional_state.items() if value is not None})

        contradictions = []
        if observation.simulated:
            contradictions.append(
                "RuView observation is simulated and cannot establish physical reality"
            )

        physical_state = PhysicalStateEvidenceV1(
            state=state,
            contradictions=contradictions,
        )
        model_signal = None
        if observation.model_hash:
            model_signal = ModelSignalV1(
                model_hash=observation.model_hash,
                confidence=observation.confidence,
                calibration=observation.calibration_id,
            )

        return RuViewEvidenceBundleV1(
            sensor=sensor,
            physical_state=physical_state,
            model_signal=model_signal,
        )


__all__ = ["RuViewAdapter", "RuViewEvidenceBundleV1", "RuViewObservationV1"]
