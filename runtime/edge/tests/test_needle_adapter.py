"""Tests for the governed Needle 2 edge adapter."""

from __future__ import annotations

import pytest

from valo_edge.tinyllm import (
    NeedleNoCallError,
    NeedleResponseError,
    NeedleRuntimeAdapter,
    PhysicalOperatorType,
    PhysicalOperatorV1,
    TinyLLMModelManifestV1,
)


TOOLS = [
    {
        "name": "SET_PUMP_SPEED",
        "description": "Request a target pump speed. This is a candidate intent only.",
        "parameters": {
            "type": "object",
            "properties": {
                "rpm": {"type": "integer", "minimum": 0, "maximum": 3000},
                "pump_id": {"type": "string"},
            },
            "required": ["rpm", "pump_id"],
        },
    }
]


class FakeNeedleClient:
    def __init__(self, response):
        self.response = response
        self.complete_calls = []
        self.reset_called = False

    def complete(self, prompt):
        self.complete_calls.append(prompt)
        return self.response

    def run(self, prompt):  # pragma: no cover - must never be called by the adapter
        raise AssertionError("Needle.run() would execute tools and must never be used")

    def reset(self):
        self.reset_called = True


def _operator(*, revoked: bool = False) -> PhysicalOperatorV1:
    return PhysicalOperatorV1(
        operator_id="edge-controller-01",
        operator_type=PhysicalOperatorType.EDGE_CONTROLLER,
        hardware_attestation_hash="sha256:" + "1" * 64,
        physical_location="Plant A",
        firmware_version="1.0.0",
        is_revoked=revoked,
    )


def _manifest() -> TinyLLMModelManifestV1:
    return TinyLLMModelManifestV1(
        model_name="Needle 2",
        model_hash="sha256:" + "2" * 64,
        quantization_type="CQ2",
        max_context_tokens=256,
        memory_footprint_mb=28.0,
        runtime_framework="Needle 2",
    )


def _response(**overrides):
    response = {
        "type": "call",
        "success": True,
        "error": None,
        "error_code": None,
        "function_calls": [
            {"name": "SET_PUMP_SPEED", "arguments": {"rpm": 1200, "pump_id": "P-7"}}
        ],
        "reasoning": "'1200 rpm' -> rpm 1200; 'P-7' -> pump_id",
        "confidence": 0.94,
    }
    response.update(overrides)
    return response


def test_needle_emits_unexecuted_claim_with_provenance():
    client = FakeNeedleClient(_response())
    adapter = NeedleRuntimeAdapter(_manifest(), TOOLS, client=client)

    claim = adapter.infer(
        operator=_operator(),
        prompt="Set pump P-7 to 1200 rpm",
        telemetry={"source": "voice"},
        timestamp_iso="2026-08-11T11:00:00Z",
    )

    assert client.complete_calls == ["Set pump P-7 to 1200 rpm"]
    assert claim.suggested_action == "SET_PUMP_SPEED"
    assert claim.action_parameters == {"rpm": 1200, "pump_id": "P-7"}
    assert claim.confidence_score == 0.94
    assert claim.runtime_framework == "Needle 2"
    assert claim.toolset_hash.startswith("sha256:")
    assert claim.runtime_response_hash.startswith("sha256:")
    assert claim.reasoning_digest.startswith("sha256:")

    proposal = adapter.claim_to_edge_proposal(claim)
    assert proposal.action_type == "SET_PUMP_SPEED"
    assert proposal.parameters["toolset_hash"] == claim.toolset_hash
    assert proposal.parameters["runtime_response_hash"] == claim.runtime_response_hash
    assert proposal.parameters["confidence"] == 0.94


def test_empty_call_fails_closed():
    client = FakeNeedleClient(_response(function_calls=[]))
    adapter = NeedleRuntimeAdapter(_manifest(), TOOLS, client=client)

    with pytest.raises(NeedleNoCallError):
        adapter.infer(_operator(), "do something else", {}, "2026-08-11T11:00:00Z")


def test_unknown_tool_fails_closed():
    client = FakeNeedleClient(
        _response(function_calls=[{"name": "BYPASS_REHT", "arguments": {}}])
    )
    adapter = NeedleRuntimeAdapter(_manifest(), TOOLS, client=client)

    with pytest.raises(NeedleResponseError, match="outside the declared toolset"):
        adapter.infer(_operator(), "bypass", {}, "2026-08-11T11:00:00Z")


def test_multiple_calls_fail_closed_at_edge_boundary():
    client = FakeNeedleClient(
        _response(
            function_calls=[
                {"name": "SET_PUMP_SPEED", "arguments": {"rpm": 1000, "pump_id": "P-7"}},
                {"name": "SET_PUMP_SPEED", "arguments": {"rpm": 1200, "pump_id": "P-8"}},
            ]
        )
    )
    adapter = NeedleRuntimeAdapter(_manifest(), TOOLS, client=client)

    with pytest.raises(NeedleResponseError, match="exactly one"):
        adapter.infer(_operator(), "set two pumps", {}, "2026-08-11T11:00:00Z")


def test_invalid_confidence_fails_closed():
    client = FakeNeedleClient(_response(confidence=1.1))
    adapter = NeedleRuntimeAdapter(_manifest(), TOOLS, client=client)

    with pytest.raises(NeedleResponseError, match="between 0 and 1"):
        adapter.infer(_operator(), "set pump", {}, "2026-08-11T11:00:00Z")


def test_revoked_operator_fails_before_model_call():
    client = FakeNeedleClient(_response())
    adapter = NeedleRuntimeAdapter(_manifest(), TOOLS, client=client)

    with pytest.raises(ValueError, match="revoked"):
        adapter.infer(_operator(revoked=True), "set pump", {}, "2026-08-11T11:00:00Z")
    assert client.complete_calls == []


def test_tool_schema_must_be_object_schema():
    with pytest.raises(ValueError, match="parameters.type='object'"):
        NeedleRuntimeAdapter(
            _manifest(),
            [{"name": "BAD", "parameters": {"type": "array"}}],
            client=FakeNeedleClient(_response()),
        )


def test_reset_delegates_without_changing_toolset():
    client = FakeNeedleClient(_response())
    adapter = NeedleRuntimeAdapter(_manifest(), TOOLS, client=client)
    before = adapter.toolset_hash

    adapter.reset()

    assert client.reset_called is True
    assert adapter.toolset_hash == before
