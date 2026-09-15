from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence


class ModelRuntimeError(RuntimeError):
    """Base error for shared model runtime failures."""


class UnknownModelProvider(ModelRuntimeError):
    """Raised when a request names an unregistered provider."""


class CarrierControlNamespaceForbidden(ModelRuntimeError):
    """Raised when carrier data tries to enter Heimel control state."""


@dataclass(frozen=True)
class ModelMessage:
    role: str
    content: str


@dataclass(frozen=True)
class ModelRequest:
    runner_id: str
    provider: str
    model: str
    messages: Sequence[ModelMessage]
    tools: Sequence[str] = ()
    timeout_s: float = 60.0
    max_attempts: int = 1
    metadata: Mapping[str, Any] = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self) -> None:
        if not self.runner_id.strip():
            raise ValueError("runner_id is required")
        if not self.provider.strip():
            raise ValueError("provider is required")
        if not self.model.strip():
            raise ValueError("model is required")
        if not self.messages:
            raise ValueError("messages are required")
        if self.timeout_s <= 0:
            raise ValueError("timeout_s must be positive")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        _reject_control_namespace(self.metadata)


@dataclass(frozen=True)
class ModelUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float | None = None

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class AdapterResult:
    text: str
    usage: ModelUsage = field(default_factory=ModelUsage)
    provider_metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelReceipt:
    request_id: str
    runner_id: str
    provider: str
    model: str
    attempts: int
    input_tokens: int
    output_tokens: int
    cost_usd: float | None
    elapsed_ms: int
    evidence_sha256: str


@dataclass(frozen=True)
class ModelResult:
    text: str
    usage: ModelUsage
    provider_metadata: Mapping[str, Any]
    receipt: ModelReceipt


class ModelAdapter(Protocol):
    def invoke(self, request: ModelRequest) -> AdapterResult:
        """Invoke one model provider. Authority is intentionally absent."""


class ModelRuntime:
    """Single provider-neutral model access path for Heimel runners.

    Runners identify themselves but receive no authority through this layer.
    Authority and governed effects remain the responsibility of the existing
    Heimel consequence-time path.
    """

    def __init__(self, adapters: Mapping[str, ModelAdapter] | None = None) -> None:
        self._adapters: dict[str, ModelAdapter] = dict(adapters or {})

    def register(self, provider: str, adapter: ModelAdapter) -> None:
        key = provider.strip()
        if not key:
            raise ValueError("provider is required")
        self._adapters[key] = adapter

    def run(self, request: ModelRequest) -> ModelResult:
        adapter = self._adapters.get(request.provider)
        if adapter is None:
            raise UnknownModelProvider(
                f"MODEL_PROVIDER_UNREGISTERED:{request.provider}"
            )

        started = time.monotonic()
        last_error: Exception | None = None
        for attempt in range(1, request.max_attempts + 1):
            try:
                raw = adapter.invoke(request)
                _reject_control_namespace(raw.provider_metadata)
                elapsed_ms = max(0, int((time.monotonic() - started) * 1000))
                receipt = _receipt(request, raw, attempt, elapsed_ms)
                return ModelResult(
                    text=raw.text,
                    usage=raw.usage,
                    provider_metadata=dict(raw.provider_metadata),
                    receipt=receipt,
                )
            except CarrierControlNamespaceForbidden:
                raise
            except Exception as exc:
                last_error = exc

        assert last_error is not None
        raise ModelRuntimeError(
            f"MODEL_PROVIDER_FAILED:{request.provider}:{type(last_error).__name__}"
        ) from last_error


def _receipt(
    request: ModelRequest,
    result: AdapterResult,
    attempts: int,
    elapsed_ms: int,
) -> ModelReceipt:
    evidence = {
        "request_id": request.request_id,
        "runner_id": request.runner_id,
        "provider": request.provider,
        "model": request.model,
        "messages": [
            {"role": message.role, "content": message.content}
            for message in request.messages
        ],
        "tools": list(request.tools),
        "metadata": dict(request.metadata),
        "result": {
            "text": result.text,
            "usage": {
                "input_tokens": result.usage.input_tokens,
                "output_tokens": result.usage.output_tokens,
                "cost_usd": result.usage.cost_usd,
            },
            "provider_metadata": dict(result.provider_metadata),
        },
    }
    encoded = json.dumps(
        evidence,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return ModelReceipt(
        request_id=request.request_id,
        runner_id=request.runner_id,
        provider=request.provider,
        model=request.model,
        attempts=attempts,
        input_tokens=result.usage.input_tokens,
        output_tokens=result.usage.output_tokens,
        cost_usd=result.usage.cost_usd,
        elapsed_ms=elapsed_ms,
        evidence_sha256=hashlib.sha256(encoded).hexdigest(),
    )


def _reject_control_namespace(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key) == "_heimel":
                raise CarrierControlNamespaceForbidden(
                    "CARRIER_CONTROL_NAMESPACE_FORBIDDEN:_heimel"
                )
            _reject_control_namespace(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            _reject_control_namespace(nested)
