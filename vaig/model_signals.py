"""Typed native model signals for VAIG instruments.

Raw token and hidden-state arrays are supplied to instruments in memory. Audit
records receive only model binding metadata and deterministic signal digests.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Tuple


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class ModelSignalBundle:
    """Hash-bound native signals for one exact model response."""

    provider: str
    model_id: str
    model_version: str
    generation_config_hash: str
    response_id: Optional[str] = None
    logprobs: Tuple[float, ...] = ()
    hidden_states: Tuple[Tuple[float, ...], ...] = ()

    def __post_init__(self) -> None:
        for field_name in (
            "provider",
            "model_id",
            "model_version",
            "generation_config_hash",
        ):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} is required")

        normalized_logprobs = tuple(float(value) for value in self.logprobs)
        if any(not math.isfinite(value) or value > 0.0 for value in normalized_logprobs):
            raise ValueError("logprobs must be finite natural-log probabilities <= 0")
        object.__setattr__(self, "logprobs", normalized_logprobs)

        normalized_states = tuple(
            tuple(float(value) for value in state)
            for state in self.hidden_states
        )
        if normalized_states:
            width = len(normalized_states[0])
            if width == 0 or any(len(state) != width for state in normalized_states):
                raise ValueError("hidden states must be non-empty and dimensionally consistent")
            if any(not math.isfinite(value) for state in normalized_states for value in state):
                raise ValueError("hidden states must contain finite values")
        object.__setattr__(self, "hidden_states", normalized_states)

    def instrument_inputs(self) -> Dict[str, Dict[str, Any]]:
        inputs: Dict[str, Dict[str, Any]] = {}
        if self.logprobs:
            inputs["logprob_scorer"] = {"logprobs": self.logprobs}
        if self.hidden_states:
            inputs["activation_probe"] = {"hidden_states": self.hidden_states}
        return inputs

    def evidence_refs(self) -> Mapping[str, Tuple[str, ...]]:
        refs: Dict[str, Tuple[str, ...]] = {}
        if self.logprobs:
            refs["logprob_scorer"] = (self.logprobs_digest,)
        if self.hidden_states:
            refs["activation_probe"] = (self.hidden_states_digest,)
        return refs

    @property
    def logprobs_digest(self) -> str:
        return _digest(self.logprobs) if self.logprobs else ""

    @property
    def hidden_states_digest(self) -> str:
        return _digest(self.hidden_states) if self.hidden_states else ""

    def audit_metadata(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "provider": self.provider,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "generation_config_hash": self.generation_config_hash,
            "response_id": self.response_id,
            "signals": {
                "logprobs_supplied": bool(self.logprobs),
                "hidden_states_supplied": bool(self.hidden_states),
            },
        }
        if self.logprobs:
            payload["signals"]["logprobs_digest"] = self.logprobs_digest
            payload["signals"]["logprob_count"] = len(self.logprobs)
        if self.hidden_states:
            payload["signals"]["hidden_states_digest"] = self.hidden_states_digest
            payload["signals"]["hidden_state_count"] = len(self.hidden_states)
            payload["signals"]["hidden_state_width"] = len(self.hidden_states[0])
        return payload
