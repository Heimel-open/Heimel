"""Unit tests for TinyLLM Constrained Edge Profile & OEM Demo (valo-edge)."""

import pytest
from valo_edge.contracts import EdgeDecision, OfflineAuthorityEnvelope
from valo_edge.tinyllm import (
    PhysicalOperatorType,
    PhysicalOperatorV1,
    TinyLLMModelManifestV1,
    TinyLLMInferenceClaimV1,
    TinyLLMRuntimeAdapter,
    CameraOperatorIntake,
)
from valo_edge.demos.tinyllm_oem_sensor_actuator_demo import run_tinyllm_oem_demo


def test_tinyllm_inference_claim_creation():
    op = PhysicalOperatorV1(
        operator_id="camera-01",
        operator_type=PhysicalOperatorType.CAMERA,
        hardware_attestation_hash="sha256:1111111111111111111111111111111111111111111111111111111111111111",
        physical_location="Zone A",
        firmware_version="1.0.0",
    )

    manifest = TinyLLMModelManifestV1(
        model_name="TinyLlama-1.1B",
        model_hash="sha256:2222222222222222222222222222222222222222222222222222222222222222",
        quantization_type="INT8",
    )

    adapter = TinyLLMRuntimeAdapter(manifest)
    intake = CameraOperatorIntake(op, adapter)

    claim = intake.process_frame_event(
        frame_id="f-100",
        detected_objects=["smoke"],
        anomaly_detected=True,
        timestamp_iso="2026-08-04T12:00:00Z",
    )

    assert claim.operator_id == "camera-01"
    assert claim.suggested_action == "EMERGENCY_SHUTDOWN"
    assert claim.confidence_score == 0.98

    proposal = adapter.claim_to_edge_proposal(claim)
    assert proposal.device_id == "camera-01"
    assert proposal.action_type == "EMERGENCY_SHUTDOWN"


def test_revoked_operator_fails_closed():
    op = PhysicalOperatorV1(
        operator_id="camera-revoked",
        operator_type=PhysicalOperatorType.CAMERA,
        hardware_attestation_hash="sha256:1111111111111111111111111111111111111111111111111111111111111111",
        physical_location="Zone A",
        firmware_version="1.0.0",
        is_revoked=True,  # Revoked!
    )

    manifest = TinyLLMModelManifestV1(
        model_name="TinyLlama-1.1B",
        model_hash="sha256:2222222222222222222222222222222222222222222222222222222222222222",
        quantization_type="INT8",
    )

    adapter = TinyLLMRuntimeAdapter(manifest)
    with pytest.raises(ValueError, match="revoked"):
        adapter.infer(
            operator=op,
            prompt="test",
            telemetry={},
            timestamp_iso="2026-08-04T12:00:00Z",
        )


def test_tinyllm_oem_demo_runs_successfully():
    success = run_tinyllm_oem_demo()
    assert success is True
