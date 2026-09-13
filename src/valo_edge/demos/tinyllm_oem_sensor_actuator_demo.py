"""End-to-end TinyLLM-on-Sensor / Camera OEM Demonstration (valo-edge).

Demonstrates complete execution governance chain:
Physical Operator (Camera/Sensor)
→ TinyLLM Local Model (LiteRT.js / ONNX / TFLite)
→ TinyLLMInferenceClaimV1
→ Micro-REHT (Fail-Closed Monotonic Gate & Offline Envelope)
→ Hardware-Neutral Gateway
→ Bounded Actuator
→ Signed Veritas Edge Receipt
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from valo_edge.contracts import OfflineAuthorityEnvelope, EdgeDecision
from valo_edge.runtime import MicroRehtEngine
from valo_edge.gateway import HardwareNeutralGateway
from valo_edge.tinyllm import (
    PhysicalOperatorType,
    PhysicalOperatorV1,
    TinyLLMModelManifestV1,
    TinyLLMRuntimeAdapter,
    CameraOperatorIntake,
)


def run_tinyllm_oem_demo() -> bool:
    device_id = "camera-operator-oem-01"
    now_iso = "2026-08-04T12:00:00Z"
    future_expiry_iso = "2026-08-05T12:00:00Z"

    print("======================================================================")
    print("VALO EDGE — TINYLLM ON SENSOR / CAMERA OEM DEMONSTRATION")
    print("======================================================================")

    # 1. Instantiate Attested Physical Operator (Camera)
    camera_op = PhysicalOperatorV1(
        operator_id=device_id,
        operator_type=PhysicalOperatorType.CAMERA,
        hardware_attestation_hash="sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        physical_location="Factory Floor 3 - Station B",
        firmware_version="v2.4.1-edge",
        is_revoked=False,
    )
    print(f"[1. Physical Operator] Registered {camera_op.operator_id} ({camera_op.physical_location})")

    # 2. Instantiate TinyLLM Model Manifest and Runtime Adapter
    model_manifest = TinyLLMModelManifestV1(
        model_name="TinyLlama-1.1B-Chat-v1.0",
        model_hash="sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        quantization_type="Q4_K_M",
        max_context_tokens=2048,
        memory_footprint_mb=480.0,
        runtime_framework="LiteRT.js",
    )
    adapter = TinyLLMRuntimeAdapter(manifest=model_manifest)
    intake = CameraOperatorIntake(camera_operator=camera_op, adapter=adapter)
    print(f"[2. TinyLLM Model] Loaded {model_manifest.model_name} [{model_manifest.quantization_type}] via {model_manifest.runtime_framework}")

    # 3. Process Vision Frame Event -> Produce TinyLLM Claim
    claim = intake.process_frame_event(
        frame_id="frame-9901",
        detected_objects=["conveyor_belt", "thermal_overheat_signal"],
        anomaly_detected=True,
        timestamp_iso=now_iso,
    )
    print(f"[3. Inference Claim] Suggested Action: '{claim.suggested_action}' (Confidence: {claim.confidence_score})")

    # Convert claim to unexecuted EdgeActionProposal
    proposal = adapter.claim_to_edge_proposal(claim)

    # 4. Evaluate via Micro-REHT Engine & Offline Authority Envelope
    engine = MicroRehtEngine()
    envelope = OfflineAuthorityEnvelope(
        envelope_id="env-camera-oem-01",
        device_id=device_id,
        allowed_action_types=["EMERGENCY_SHUTDOWN", "CONTINUE_MONITORING"],
        max_rate_per_sec=10.0,
        valid_until_iso=future_expiry_iso,
        is_revoked=False,
    )

    clearance = engine.evaluate_proposal(proposal, envelope, current_time_iso=now_iso)
    print(f"[4. Micro-REHT Gate] Decision: {clearance.decision.value} — Reason: '{clearance.reason}'")

    # 5. Enforce Action via Hardware-Neutral Actuator Gateway
    gateway = HardwareNeutralGateway()
    receipt = gateway.execute_action(proposal, clearance, timestamp_iso=now_iso)
    print(f"[5. Hardware Gateway] Actuator Executed: {receipt.executed}")
    print(f"[6. Veritas Receipt] Receipt Digest: {receipt.receipt_digest}")
    print("======================================================================\n")

    return receipt.executed and receipt.decision == EdgeDecision.ALLOW


if __name__ == "__main__":
    success = run_tinyllm_oem_demo()
    print(f"[DEMO RESULT] TinyLLM OEM Demo completion: {'SUCCESS' if success else 'FAILED'}")
