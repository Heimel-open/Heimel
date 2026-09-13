"""TinyLLM Constrained Edge Profile Contracts and Domain Models (valo-edge).

Provides TinyLLM model manifests, inference claims, physical operator identity (PhysicalOperatorV1),
and telemetry contracts.
"""

from __future__ import annotations

from enum import Enum
import hashlib
import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PhysicalOperatorType(str, Enum):
    CAMERA = "CAMERA"
    SENSOR_ARRAY = "SENSOR_ARRAY"
    ROBOTIC_ARM = "ROBOTIC_ARM"
    INDUSTRIAL_PUMP = "INDUSTRIAL_PUMP"
    EDGE_CONTROLLER = "EDGE_CONTROLLER"


class PhysicalOperatorV1(BaseModel):
    """Physical AI operator identity modeling cameras, sensors, and edge controllers.

    Attested, identified, and revokable physical operator.
    """
    operator_id: str
    operator_type: PhysicalOperatorType
    hardware_attestation_hash: str
    physical_location: str
    firmware_version: str
    is_revoked: bool = False

    def compute_digest(self) -> str:
        payload = f"{self.operator_id}:{self.operator_type.value}:{self.hardware_attestation_hash}:{self.physical_location}:{self.firmware_version}:{self.is_revoked}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class TinyLLMModelManifestV1(BaseModel):
    """Model provenance and resource footprint manifest for TinyLLM model."""
    model_name: str
    model_hash: str  # sha256 of model weights
    quantization_type: str  # e.g. "Q4_K_M", "INT8", "FP16"
    max_context_tokens: int = 2048
    memory_footprint_mb: float = 512.0
    runtime_framework: str = "LiteRT.js"  # LiteRT.js, ONNX Edge, TFLite, llama.cpp, Needle 2


class TinyLLMInferenceClaimV1(BaseModel):
    """Structured inference claim emitted by local TinyLLM inference.

    Runtime provenance fields are optional to preserve compatibility with existing
    TinyLLM adapters while allowing concrete runtimes such as Needle 2 to bind the
    candidate call to the declared toolset and raw runtime response.
    """
    claim_id: str
    operator_id: str
    model_hash: str
    prompt_digest: str
    suggested_action: str
    action_parameters: Dict[str, Any] = Field(default_factory=dict)
    confidence_score: float
    telemetry_hash: str
    timestamp_iso: str
    runtime_framework: Optional[str] = None
    toolset_hash: Optional[str] = None
    runtime_response_hash: Optional[str] = None
    reasoning_digest: Optional[str] = None
    claim_hash: Optional[str] = None

    def compute_hash(self) -> str:
        payload = f"{self.claim_id}:{self.operator_id}:{self.model_hash}:{self.prompt_digest}:{self.suggested_action}:{json.dumps(self.action_parameters, sort_keys=True)}:{self.confidence_score}:{self.telemetry_hash}:{self.timestamp_iso}"
        provenance = (
            self.runtime_framework,
            self.toolset_hash,
            self.runtime_response_hash,
            self.reasoning_digest,
        )
        if any(value is not None for value in provenance):
            payload += ":" + ":".join(value or "" for value in provenance)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def model_post_init(self, __context: Any) -> None:
        if not self.claim_hash:
            self.claim_hash = self.compute_hash()
