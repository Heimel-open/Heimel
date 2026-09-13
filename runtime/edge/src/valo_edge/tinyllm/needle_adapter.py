"""Governed Needle 2 adapter for VALO Edge.

Needle is used only to produce a structured candidate tool call. This adapter never
calls ``Needle.run()`` and never executes a tool. The resulting claim must continue
through the normal VALO path (VAIG -> micro-reht -> gateway -> Veritas).
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib
import json
from typing import Any, Mapping, Sequence

from valo_edge.tinyllm.contracts import PhysicalOperatorV1, TinyLLMInferenceClaimV1, TinyLLMModelManifestV1
from valo_edge.tinyllm.inference_adapter import TinyLLMRuntimeAdapter


class NeedleAdapterError(RuntimeError):
    """Base error for fail-closed Needle adapter failures."""


class NeedleUnavailableError(NeedleAdapterError):
    """Raised when the optional cactus-needle runtime is not installed."""


class NeedleResponseError(NeedleAdapterError):
    """Raised when Needle returns a malformed or inadmissible response."""


class NeedleNoCallError(NeedleAdapterError):
    """Raised when Needle returns no candidate tool call."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _sha256(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def _validate_tool_schema(tool: Mapping[str, Any]) -> dict[str, Any]:
    copied = deepcopy(dict(tool))
    name = copied.get("name")
    parameters = copied.get("parameters")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Needle tool schema requires a non-empty name")
    if not isinstance(parameters, dict) or parameters.get("type") != "object":
        raise ValueError(f"Needle tool {name!r} requires parameters.type='object'")
    return copied


class NeedleRuntimeAdapter(TinyLLMRuntimeAdapter):
    """Needle 2 candidate-call adapter with no execution authority.

    ``tools`` are plain JSON tool schemas. Supplying schemas instead of executable
    callables keeps the model/runtime boundary mechanically non-executing.

    A client may be injected for tests. Otherwise the optional ``needle`` package is
    imported lazily and a ``needle.Needle`` client is created.
    """

    def __init__(
        self,
        manifest: TinyLLMModelManifestV1,
        tools: Sequence[Mapping[str, Any]],
        *,
        tool_index_path: str | None = None,
        weights: str | None = None,
        client: Any | None = None,
    ) -> None:
        super().__init__(manifest)
        if not tools:
            raise ValueError("NeedleRuntimeAdapter requires at least one tool schema")
        self.tools = tuple(_validate_tool_schema(tool) for tool in tools)
        self.tool_names = frozenset(tool["name"] for tool in self.tools)
        self.toolset_hash = _sha256(_canonical_json(self.tools))
        self.client = client or self._build_client(tool_index_path=tool_index_path, weights=weights)

    def _build_client(self, *, tool_index_path: str | None, weights: str | None) -> Any:
        try:
            needle = importlib.import_module("needle")
        except ImportError as exc:  # pragma: no cover - exercised only without optional dependency
            raise NeedleUnavailableError(
                "cactus-needle is not installed; install valo-edge[needle]"
            ) from exc

        kwargs: dict[str, Any] = {"tools": list(self.tools)}
        if tool_index_path is not None:
            kwargs["tool_index_path"] = tool_index_path
        if weights is not None:
            kwargs["weights"] = weights
        return needle.Needle(**kwargs)

    def infer(
        self,
        operator: PhysicalOperatorV1,
        prompt: str,
        telemetry: dict[str, Any],
        timestamp_iso: str,
    ) -> TinyLLMInferenceClaimV1:
        """Return one unexecuted Needle tool-call candidate as a TinyLLM claim."""
        if operator.is_revoked:
            raise ValueError(f"Operator {operator.operator_id} is revoked")

        response = self.client.complete(prompt)
        if not isinstance(response, Mapping):
            raise NeedleResponseError("Needle response must be a mapping")
        if response.get("success") is False:
            raise NeedleResponseError(
                f"Needle inference failed: {response.get('error_code') or response.get('error') or 'unknown error'}"
            )

        function_calls = response.get("function_calls")
        if response.get("type") != "call" or not isinstance(function_calls, list) or not function_calls:
            raise NeedleNoCallError("Needle returned no candidate tool call")
        if len(function_calls) != 1:
            raise NeedleResponseError("VALO Edge admits exactly one Needle candidate call per inference")

        call = function_calls[0]
        if not isinstance(call, Mapping):
            raise NeedleResponseError("Needle function call must be a mapping")
        name = call.get("name")
        arguments = call.get("arguments")
        if not isinstance(name, str) or name not in self.tool_names:
            raise NeedleResponseError("Needle returned a tool outside the declared toolset")
        if not isinstance(arguments, Mapping):
            raise NeedleResponseError("Needle function arguments must be an object")

        try:
            confidence = float(response.get("confidence"))
        except (TypeError, ValueError) as exc:
            raise NeedleResponseError("Needle response requires numeric confidence") from exc
        if not 0.0 <= confidence <= 1.0:
            raise NeedleResponseError("Needle confidence must be between 0 and 1")

        prompt_digest = _sha256(prompt)
        telemetry_hash = _sha256(_canonical_json(telemetry))
        runtime_response_hash = _sha256(_canonical_json(response))
        reasoning = response.get("reasoning")
        reasoning_digest = _sha256(reasoning) if isinstance(reasoning, str) and reasoning else None
        claim_id_seed = f"{operator.operator_id}:{timestamp_iso}:{runtime_response_hash}"
        claim_id = f"claim-{hashlib.sha256(claim_id_seed.encode('utf-8')).hexdigest()[:12]}"

        return TinyLLMInferenceClaimV1(
            claim_id=claim_id,
            operator_id=operator.operator_id,
            model_hash=self.manifest.model_hash,
            prompt_digest=prompt_digest,
            suggested_action=name,
            action_parameters=dict(arguments),
            confidence_score=confidence,
            telemetry_hash=telemetry_hash,
            timestamp_iso=timestamp_iso,
            runtime_framework="Needle 2",
            toolset_hash=self.toolset_hash,
            runtime_response_hash=runtime_response_hash,
            reasoning_digest=reasoning_digest,
        )

    def reset(self) -> None:
        """Reset Needle conversation state without changing the declared toolset."""
        reset = getattr(self.client, "reset", None)
        if callable(reset):
            reset()
