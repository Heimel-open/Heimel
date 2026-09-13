"""Tests for the JANUS telemetry gateway."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JANUS_PATH = ROOT / "janus_integration.py"


def _load_janus_module():
    spec = importlib.util.spec_from_file_location("janus_integration_test_module", JANUS_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeDecision:
    def __init__(self, name: str):
        self.name = name


class FakeBridge:
    def __init__(self, decision_name: str = "ALLOW"):
        self.decision_name = decision_name
        self.calls = []

    def pack_telemetry_packet(self, ai_confidence, c0_threshold, syntax_valid=True, latency_ok=True):
        self.calls.append(
            {
                "ai_confidence": ai_confidence,
                "c0_threshold": c0_threshold,
                "syntax_valid": syntax_valid,
                "latency_ok": latency_ok,
            }
        )
        return b"telemetry-frame"

    def send_frame(self, frame):
        return FakeDecision(self.decision_name), 1234


def test_gateway_is_explicitly_legacy_telemetry():
    janus = _load_janus_module()
    gateway = janus.VALOJanusGateway(FakeBridge())

    description = gateway.describe()

    assert description == {
        "kind": "legacy_telemetry",
        "agents": ("ARCHITECT", "CLAW-BOT", "PANOPTIKON", "RISK-ASSESSOR"),
        "inverted_score_agents": ("RISK-ASSESSOR",),
        "wire_type": "telemetry",
        "permit_processing": False,
    }


def test_gateway_routes_agent_scores_through_telemetry_path():
    janus = _load_janus_module()
    bridge = FakeBridge("DEGRADED")
    gateway = janus.VALOJanusGateway(bridge, c0_threshold=0.5)

    decision = gateway.route("PANOPTIKON", {"confidence_score": 0.87})

    assert decision == "DEGRADED"
    assert bridge.calls == [
        {
            "ai_confidence": 0.87,
            "c0_threshold": 0.5,
            "syntax_valid": True,
            "latency_ok": True,
        }
    ]


def test_gateway_inverts_risk_assessor_scores_before_routing():
    janus = _load_janus_module()
    bridge = FakeBridge("ALLOW")
    gateway = janus.VALOJanusGateway(bridge, c0_threshold=0.5)

    decision = gateway.route("RISK-ASSESSOR", {"risk_score": 0.25})

    assert decision == "ALLOW"
    assert bridge.calls[0]["ai_confidence"] == 0.75
