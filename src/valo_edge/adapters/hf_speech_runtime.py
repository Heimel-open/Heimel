"""Proposal-only adapter for Hugging Face speech-to-speech realtime tool calls."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from valo_edge.contracts import EdgeActionProposal


FUNCTION_CALL_DONE = "response.function_call_arguments.done"


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing or invalid {field}")
    return value


class HFSpeechRuntimeAdapter:
    """Translate realtime voice tool-call events into non-executable proposals."""

    def __init__(
        self,
        *,
        device_id: str,
        actor_id: str,
        actor_attestation_hash: str = "",
        model_manifest_hash: str = "",
    ) -> None:
        self._device_id = _required_text(device_id, "device_id")
        self._actor_id = _required_text(actor_id, "actor_id")
        self._actor_attestation_hash = actor_attestation_hash
        self._model_manifest_hash = model_manifest_hash

    def proposal_from_event(
        self,
        event: Mapping[str, Any],
        *,
        session_id: str,
        timestamp_iso: str,
        transcript_digest: str = "",
    ) -> EdgeActionProposal:
        if not isinstance(event, Mapping):
            raise ValueError("event must be a mapping")
        if event.get("type") != FUNCTION_CALL_DONE:
            raise ValueError("event is not a completed function call")

        session_id = _required_text(session_id, "session_id")
        timestamp_iso = _required_text(timestamp_iso, "timestamp_iso")
        event_id = _required_text(event.get("event_id"), "event_id")
        call_id = _required_text(event.get("call_id"), "call_id")
        tool_name = _required_text(event.get("name"), "name")
        raw_arguments = event.get("arguments")
        if not isinstance(raw_arguments, str):
            raise ValueError("arguments must be JSON text")

        try:
            arguments = json.loads(raw_arguments)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("arguments must contain valid JSON") from exc
        if not isinstance(arguments, dict):
            raise ValueError("function-call arguments must decode to an object")

        voice_context = {
            "runtime": "huggingface/speech-to-speech",
            "protocol": "openai-realtime",
            "session_id": session_id,
            "event_id": event_id,
            "call_id": call_id,
            "actor_id": self._actor_id,
            "actor_attestation_hash": self._actor_attestation_hash,
        }
        for optional_field in ("response_id", "item_id", "output_index"):
            if optional_field in event:
                voice_context[optional_field] = event[optional_field]

        return EdgeActionProposal(
            proposal_id=f"hf-s2s:{session_id}:{call_id}",
            device_id=self._device_id,
            action_type=f"VOICE_TOOL:{tool_name}",
            parameters={
                "tool_name": tool_name,
                "arguments": arguments,
                "voice_context": voice_context,
            },
            timestamp_iso=timestamp_iso,
            nonce=f"hf-s2s:{session_id}:{event_id}",
            model_manifest_hash=self._model_manifest_hash,
            sensor_digest=transcript_digest,
        )
