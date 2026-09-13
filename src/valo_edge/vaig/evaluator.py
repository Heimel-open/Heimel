"""Deterministic local evidence assembly for VALO Edge.

VAIG evaluates evidence quality only. It never authorizes or denies execution.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional

from valo_edge.contracts import EdgeActionCommitmentV1, EdgeEvidenceV1, sha256_digest
from valo_edge.vaig.contracts import (
    DeviceAttestationEvidenceV1,
    EvidenceGapSeverity,
    EvidenceGapV1,
    EvidenceRequirementsV1,
    LocalVaigAssessmentV1,
    ModelSignalV1,
    PhysicalStateEvidenceV1,
    SensorEvidenceV1,
)


def _parse_iso(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamps must include a timezone")
    return parsed.astimezone(timezone.utc)


def _sensor_commitment(sensors: Iterable[SensorEvidenceV1]) -> str:
    payload = [
        sensor.model_dump(mode="json", exclude_none=True)
        for sensor in sorted(sensors, key=lambda item: (item.source_id, item.evidence_digest))
    ]
    return sha256_digest(payload)


class LocalVaigEdge:
    """Assemble canonical EdgeEvidenceV1 and report evidence defects."""

    def __init__(self, producer_id: str = "edge-vaig-1") -> None:
        self.producer_id = producer_id

    def evaluate(
        self,
        proposal: EdgeActionCommitmentV1,
        *,
        device_attestation: Optional[DeviceAttestationEvidenceV1] = None,
        sensors: Iterable[SensorEvidenceV1] = (),
        physical_state: Optional[PhysicalStateEvidenceV1] = None,
        model_signal: Optional[ModelSignalV1] = None,
        requirements: Optional[EvidenceRequirementsV1] = None,
        evaluated_at_iso: Optional[str] = None,
    ) -> LocalVaigAssessmentV1:
        requirements = requirements or EvidenceRequirementsV1()
        evaluated_at_iso = evaluated_at_iso or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        evaluated_at = _parse_iso(evaluated_at_iso)
        sensors = list(sensors)
        physical_state = physical_state or PhysicalStateEvidenceV1()

        gaps: List[EvidenceGapV1] = []
        contradictions: List[str] = []

        def gap(field: str, severity: EvidenceGapSeverity, reason: str) -> None:
            gaps.append(EvidenceGapV1(field=field, severity=severity, reason=reason))
            if severity == EvidenceGapSeverity.CONTRADICTORY:
                contradictions.append(reason)

        if device_attestation is None:
            if requirements.require_device_attestation:
                gap("device_attestation", EvidenceGapSeverity.MISSING, "device attestation is required")
            device_digest = sha256_digest({"device_id": proposal.device_id, "missing": True})
            firmware_hash = ""
            runtime_hash = ""
        else:
            device_digest = device_attestation.compute_digest()
            firmware_hash = device_attestation.firmware_hash
            runtime_hash = device_attestation.runtime_hash
            if device_attestation.device_id != proposal.device_id:
                gap("device_id", EvidenceGapSeverity.CONTRADICTORY, "device attestation does not match proposal device")
            if device_attestation.revoked:
                gap("device_attestation", EvidenceGapSeverity.UNTRUSTED, "device attestation is revoked")
            if requirements.require_device_attestation and not device_attestation.hardware_attestation_hash:
                gap("hardware_attestation_hash", EvidenceGapSeverity.MISSING, "hardware attestation hash is required")
            if requirements.require_device_attestation and not device_attestation.boot_epoch:
                gap("boot_epoch", EvidenceGapSeverity.MISSING, "attested boot epoch is required")
            elif device_attestation.boot_epoch != proposal.boot_epoch:
                gap("boot_epoch", EvidenceGapSeverity.CONTRADICTORY, "attested boot epoch does not match proposal")
            if requirements.require_device_attestation and not device_attestation.key_id:
                gap("key_id", EvidenceGapSeverity.MISSING, "attestation key ID is required")
            elif device_attestation.key_id != proposal.signer_key_id:
                gap("key_id", EvidenceGapSeverity.CONTRADICTORY, "attestation key ID does not match proposal signer")
            if requirements.require_firmware_hash and not firmware_hash:
                gap("firmware_hash", EvidenceGapSeverity.MISSING, "firmware hash is required")
            if firmware_hash and firmware_hash != proposal.firmware_hash:
                gap("firmware_hash", EvidenceGapSeverity.CONTRADICTORY, "firmware hash does not match proposal")
            if requirements.require_runtime_hash and not runtime_hash:
                gap("runtime_hash", EvidenceGapSeverity.MISSING, "runtime hash is required")
            if runtime_hash and runtime_hash != proposal.runtime_hash:
                gap("runtime_hash", EvidenceGapSeverity.CONTRADICTORY, "runtime hash does not match proposal")

        model_required = requirements.require_model or bool(proposal.model_hash)
        model_hash = model_signal.model_hash if model_signal is not None else ""
        if model_required and model_signal is None:
            gap("model_signal", EvidenceGapSeverity.MISSING, "model evidence is required by the proposal or profile")
        if model_signal is not None and model_signal.model_hash != proposal.model_hash:
            gap("model_hash", EvidenceGapSeverity.CONTRADICTORY, "model hash does not match proposal")
        if model_signal is not None and model_signal.confidence is None and model_signal.uncertainty is None:
            gap(
                "model_signal_quality",
                EvidenceGapSeverity.MISSING,
                "model confidence or uncertainty is required when a model signal is present",
            )

        if len(sensors) < requirements.min_sensor_sources:
            gap("sensor_sources", EvidenceGapSeverity.MISSING, "insufficient sensor evidence sources")

        sources_by_id: Dict[str, str] = {}
        max_freshness_ms = 0
        for sensor in sensors:
            if not sensor.source_id or not sensor.evidence_digest or not sensor.observed_at_iso:
                gap("sensor_provenance", EvidenceGapSeverity.MISSING, "sensor source, digest and timestamp are required")
                continue
            if not sensor.provenance:
                gap("sensor_provenance", EvidenceGapSeverity.MISSING, f"sensor source {sensor.source_id} lacks provenance")
            previous = sources_by_id.get(sensor.source_id)
            if previous is not None and previous != sensor.evidence_digest:
                gap(
                    "sensor_provenance",
                    EvidenceGapSeverity.CONTRADICTORY,
                    f"sensor source {sensor.source_id} has conflicting digests",
                )
            sources_by_id[sensor.source_id] = sensor.evidence_digest
            observed_at = _parse_iso(sensor.observed_at_iso)
            age_ms = int((evaluated_at - observed_at).total_seconds() * 1000)
            if age_ms < 0:
                gap("sensor_time", EvidenceGapSeverity.CONTRADICTORY, f"sensor source {sensor.source_id} is from the future")
                age_ms = 0
            max_freshness_ms = max(max_freshness_ms, age_ms)
            if age_ms > requirements.max_freshness_ms:
                gap("freshness", EvidenceGapSeverity.STALE, f"sensor source {sensor.source_id} is stale")

        actual_sensor_digest = _sensor_commitment(sensors)
        if sensors and actual_sensor_digest != proposal.sensor_evidence_digest:
            gap("sensor_evidence_digest", EvidenceGapSeverity.CONTRADICTORY, "sensor evidence commitment does not match proposal")

        for key in requirements.required_state_keys:
            if key not in physical_state.state:
                gap("physical_state", EvidenceGapSeverity.MISSING, f"required physical state key is missing: {key}")
        for key, expected in requirements.expected_state.items():
            if key not in physical_state.state:
                gap("physical_state", EvidenceGapSeverity.MISSING, f"expected physical state key is missing: {key}")
            elif physical_state.state[key] != expected:
                gap(
                    "physical_state",
                    EvidenceGapSeverity.CONTRADICTORY,
                    f"physical state {key} does not match expected value",
                )
        for reason in physical_state.contradictions:
            gap("physical_state", EvidenceGapSeverity.CONTRADICTORY, reason)

        if physical_state.compute_digest() != proposal.physical_state_digest:
            gap("physical_state_digest", EvidenceGapSeverity.CONTRADICTORY, "physical state commitment does not match proposal")

        requirements_digest = requirements.compute_digest()
        vaig_metadata = {
            "requirements_digest": requirements_digest,
            "missing_or_invalid": [item.field for item in gaps],
            "state_consistent": not any(item.field.startswith("physical_state") for item in gaps),
            "sensor_provenance_digest": actual_sensor_digest,
            "model_confidence": model_signal.confidence if model_signal is not None else None,
            "model_uncertainty": model_signal.uncertainty if model_signal is not None else None,
            "model_used": model_signal is not None,
        }
        observed_state = {
            "physical": physical_state.state,
            "vaig": vaig_metadata,
        }
        evidence_id = "evidence-" + sha256_digest(
            {
                "proposal_digest": proposal.compute_digest(),
                "producer_id": self.producer_id,
                "evaluated_at_iso": evaluated_at_iso,
            }
        ).split(":", 1)[1][:16]

        evidence = EdgeEvidenceV1(
            evidence_id=evidence_id,
            proposal_digest=proposal.compute_digest(),
            device_attestation_digest=device_digest,
            model_hash=model_hash,
            firmware_hash=firmware_hash,
            runtime_hash=runtime_hash,
            sensor_sources=[
                f"{sensor.source_id}@{sensor.evidence_digest}"
                for sensor in sorted(sensors, key=lambda item: (item.source_id, item.evidence_digest))
            ],
            observed_state=observed_state,
            observed_at_iso=evaluated_at_iso,
            freshness_ms=max_freshness_ms,
            completeness=not gaps,
            contradictions=contradictions,
            producer_id=self.producer_id,
        )
        return LocalVaigAssessmentV1(
            evidence=evidence,
            requirements_digest=requirements_digest,
            gaps=gaps,
        )


__all__ = ["LocalVaigEdge", "_sensor_commitment"]
