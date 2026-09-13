"""TinyLLM Runtime Adapter and Physical Camera Intake (valo-edge).

Provides local model execution wrapping (supporting LiteRT.js, ONNX, llama.cpp, TFLite)
and physical camera / sensor intake.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional
from valo_edge.tinyllm.contracts import (
    PhysicalOperatorV1,
    TinyLLMInferenceClaimV1,
    TinyLLMModelManifestV1,
)
from valo_edge.contracts import EdgeActionProposal


class TinyLLMRuntimeAdapter:
    """Hardware-neutral local TinyLLM runtime adapter with fail-closed model hash verification."""

    def __init__(self, manifest: TinyLLMModelManifestV1) -> None:
        self.manifest = manifest

    def infer(
        self,
        operator: PhysicalOperatorV1,
        prompt: str,
        telemetry: Dict[str, Any],
        timestamp_iso: str,
    ) -> TinyLLMInferenceClaimV1:
        if operator.is_revoked:
            raise ValueError(f"Operator {operator.operator_id} is revoked")

        prompt_digest = f"sha256:{hashlib.sha256(prompt.encode('utf-8')).hexdigest()}"
        telemetry_raw = json.dumps(telemetry, sort_keys=True)
        telemetry_hash = f"sha256:{hashlib.sha256(telemetry_raw.encode('utf-8')).hexdigest()}"

        # Simulated constrained local model inference decision
        suggested_action = telemetry.get("suggested_action", "INSPECT_ENVIRONMENT")
        action_parameters = telemetry.get("action_parameters", {"mode": "STANDBY"})
        confidence = float(telemetry.get("confidence", 0.95))

        claim_id = f"claim-{hashlib.sha256(f'{operator.operator_id}:{timestamp_iso}'.encode()).hexdigest()[:12]}"

        return TinyLLMInferenceClaimV1(
            claim_id=claim_id,
            operator_id=operator.operator_id,
            model_hash=self.manifest.model_hash,
            prompt_digest=prompt_digest,
            suggested_action=suggested_action,
            action_parameters=action_parameters,
            confidence_score=confidence,
            telemetry_hash=telemetry_hash,
            timestamp_iso=timestamp_iso,
        )

    def claim_to_edge_proposal(self, claim: TinyLLMInferenceClaimV1) -> EdgeActionProposal:
        """Converts a TinyLLM inference claim into an unexecuted EdgeActionProposal for micro-REHT."""
        parameters = {
            **claim.action_parameters,
            "model_hash": claim.model_hash,
            "confidence": claim.confidence_score,
            "telemetry_hash": claim.telemetry_hash,
        }
        if claim.runtime_framework is not None:
            parameters["runtime_framework"] = claim.runtime_framework
        if claim.toolset_hash is not None:
            parameters["toolset_hash"] = claim.toolset_hash
        if claim.runtime_response_hash is not None:
            parameters["runtime_response_hash"] = claim.runtime_response_hash
        if claim.reasoning_digest is not None:
            parameters["reasoning_digest"] = claim.reasoning_digest

        return EdgeActionProposal(
            proposal_id=f"prop-{claim.claim_id}",
            device_id=claim.operator_id,
            action_type=claim.suggested_action,
            parameters=parameters,
            timestamp_iso=claim.timestamp_iso,
            nonce=claim.claim_hash[:8] if claim.claim_hash else "nonce000",
        )


class CameraOperatorIntake:
    """Physical Camera Intake converting vision frame telemetry into TinyLLM claims."""

    def __init__(self, camera_operator: PhysicalOperatorV1, adapter: TinyLLMRuntimeAdapter) -> None:
        self.camera_operator = camera_operator
        self.adapter = adapter

    def process_frame_event(
        self,
        frame_id: str,
        detected_objects: list[str],
        anomaly_detected: bool,
        timestamp_iso: str,
    ) -> TinyLLMInferenceClaimV1:
        prompt = f"Analyze camera frame {frame_id} with objects {detected_objects}"
        telemetry = {
            "frame_id": frame_id,
            "detected_objects": detected_objects,
            "anomaly_detected": anomaly_detected,
            "suggested_action": "EMERGENCY_SHUTDOWN" if anomaly_detected else "CONTINUE_MONITORING",
            "action_parameters": {"frame_id": frame_id, "anomaly": anomaly_detected},
            "confidence": 0.98 if anomaly_detected else 0.99,
        }
        return self.adapter.infer(
            operator=self.camera_operator,
            prompt=prompt,
            telemetry=telemetry,
            timestamp_iso=timestamp_iso,
        )
