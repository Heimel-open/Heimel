from __future__ import annotations

import pytest

from valo_gateway.model_runtime import (
    AdapterResult,
    CarrierControlNamespaceForbidden,
    ModelMessage,
    ModelRequest,
    ModelRuntime,
    ModelRuntimeError,
    ModelUsage,
    UnknownModelProvider,
)


class RecordingAdapter:
    def __init__(self, *, failures: int = 0, metadata=None):
        self.failures = failures
        self.metadata = metadata or {}
        self.requests = []

    def invoke(self, request):
        self.requests.append(request)
        if len(self.requests) <= self.failures:
            raise RuntimeError("transient")
        return AdapterResult(
            text=f"ok:{request.runner_id}",
            usage=ModelUsage(input_tokens=11, output_tokens=7, cost_usd=0.002),
            provider_metadata=self.metadata,
        )


def _request(runner_id: str, **overrides):
    values = {
        "runner_id": runner_id,
        "provider": "test",
        "model": "carrier-1",
        "messages": [ModelMessage(role="user", content="work")],
    }
    values.update(overrides)
    return ModelRequest(**values)


def test_all_runners_share_the_same_model_runtime_path():
    adapter = RecordingAdapter()
    runtime = ModelRuntime({"test": adapter})

    results = [runtime.run(_request(name)) for name in ("speider", "baro", "hermes")]

    assert [item.text for item in results] == [
        "ok:speider",
        "ok:baro",
        "ok:hermes",
    ]
    assert [item.receipt.runner_id for item in results] == [
        "speider",
        "baro",
        "hermes",
    ]
    assert all(item.receipt.provider == "test" for item in results)
    assert all(item.receipt.model == "carrier-1" for item in results)


def test_hermes_has_no_runtime_authority_bypass():
    request = _request("hermes")

    assert not hasattr(request, "authority")
    assert not hasattr(request, "permit")
    assert not hasattr(request, "clearance")


def test_unknown_provider_fails_closed():
    runtime = ModelRuntime()

    with pytest.raises(UnknownModelProvider, match="MODEL_PROVIDER_UNREGISTERED"):
        runtime.run(_request("speider"))


def test_request_metadata_cannot_inject_heimel_control_state():
    with pytest.raises(
        CarrierControlNamespaceForbidden,
        match="CARRIER_CONTROL_NAMESPACE_FORBIDDEN",
    ):
        _request("baro", metadata={"nested": {"_heimel": {"authority": "fake"}}})


def test_provider_metadata_cannot_inject_heimel_control_state():
    runtime = ModelRuntime(
        {"test": RecordingAdapter(metadata={"_heimel": {"authority": "fake"}})}
    )

    with pytest.raises(
        CarrierControlNamespaceForbidden,
        match="CARRIER_CONTROL_NAMESPACE_FORBIDDEN",
    ):
        runtime.run(_request("hermes"))


def test_runtime_retries_within_declared_budget_and_emits_receipt():
    adapter = RecordingAdapter(failures=1)
    runtime = ModelRuntime({"test": adapter})

    result = runtime.run(_request("speider", max_attempts=2))

    assert len(adapter.requests) == 2
    assert result.receipt.attempts == 2
    assert result.receipt.input_tokens == 11
    assert result.receipt.output_tokens == 7
    assert result.receipt.cost_usd == 0.002
    assert len(result.receipt.evidence_sha256) == 64


def test_runtime_stops_after_retry_budget():
    runtime = ModelRuntime({"test": RecordingAdapter(failures=3)})

    with pytest.raises(ModelRuntimeError, match="MODEL_PROVIDER_FAILED"):
        runtime.run(_request("baro", max_attempts=2))
