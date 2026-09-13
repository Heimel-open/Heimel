#!/usr/bin/env python3
"""JANUS-NEXUS → VALO V5.0 legacy telemetry integration.

Routes agent output from PANOPTIKON, CLAW-BOT, ARCHITECT, and RISK-ASSESSOR
through VALO V5.0 before any downstream infrastructure action is taken.

Integration pattern:
    JANUS-NEXUS output (JSON) → VALOJanusGateway.route() → ALLOW / DEGRADED / HALT
This gateway remains telemetry-only and does not process permits or execution state.

Usage:
    from janus_integration import VALOJanusGateway
    from l2_orchestrator import BridgeFactory
    from l2_orchestrator.codec import TCPTransport

    ValoBridge, _ = BridgeFactory.load()
    bridge = ValoBridge(transport=TCPTransport())
    bridge.connect({"host": "127.0.0.1", "port": 7743})
    gateway = VALOJanusGateway(bridge)
    result = gateway.route("PANOPTIKON", {"confidence_score": 0.87})
    # → "ALLOW"
"""
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent

# Bootstrap l2_orchestrator package
_l2_dir = ROOT / "l2-orchestrator"
if "l2_orchestrator" not in sys.modules:
    _pkg_spec = importlib.util.spec_from_file_location(
        "l2_orchestrator", _l2_dir / "__init__.py",
        submodule_search_locations=[str(_l2_dir)],
    )
    _pkg = importlib.util.module_from_spec(_pkg_spec)
    sys.modules["l2_orchestrator"] = _pkg
    _pkg_spec.loader.exec_module(_pkg)

from l2_orchestrator import BridgeFactory
from l2_orchestrator.observability import StructuredLogger

StructuredLogger.set_component("janus-gateway")
ValoBridge, Decision = BridgeFactory.load()
GATEWAY_KIND = "legacy_telemetry"

# L1 domain per agent: PANOPTIKON outputs LLM-style confidence → VAIG domain
_AGENT_DOMAIN = {
    "PANOPTIKON": 1,    # market analysis → VAIG/LLM domain
    "CLAW-BOT": 0,      # data extraction → infrastructure domain
    "ARCHITECT": 0,     # system design   → infrastructure domain
    "RISK-ASSESSOR": 0, # risk analysis   → infrastructure domain
}

# Which field in the agent output carries the primary score
_AGENT_SCORE_FIELD = {
    "PANOPTIKON": "confidence_score",
    "CLAW-BOT": "data_quality",
    "ARCHITECT": "design_score",
    "RISK-ASSESSOR": "risk_score",
}

# RISK-ASSESSOR: high risk_score = bad → invert so high score → blocked by L1
_INVERT_SCORE = {"RISK-ASSESSOR"}


class VALOJanusGateway:
    """Routes JANUS-NEXUS agent outputs through VALO L1 for deterministic gating.

    Each agent output is encoded as a telemetry frame and submitted to L1.
    L1 returns ALLOW, DEGRADED, or HALT in ~43ns.
    """

    def __init__(self, bridge: ValoBridge, c0_threshold: float = 0.5):
        self.bridge = bridge
        self.c0_threshold = c0_threshold

    def route(self, agent_name: str, agent_output: dict) -> str:
        """Gate an agent decision through VALO L1.

        Args:
            agent_name: One of PANOPTIKON, CLAW-BOT, ARCHITECT, RISK-ASSESSOR.
            agent_output: JSON dict from the agent.

        Returns:
            "ALLOW", "DEGRADED", or "HALT".
        """
        score_field = _AGENT_SCORE_FIELD.get(agent_name, "score")
        score = float(agent_output.get(score_field, 0.5))

        if agent_name in _INVERT_SCORE:
            score = 1.0 - score

        frame = self.bridge.pack_telemetry_packet(
            ai_confidence=score,
            c0_threshold=self.c0_threshold,
        )
        decision, rtt_ns = self.bridge.send_frame(frame)
        StructuredLogger.log_info(
            f"JANUS→VALO: {agent_name} → {decision.name}",
            kind=GATEWAY_KIND,
            agent=agent_name,
            score=round(score, 3),
            decision=decision.name,
            rtt_us=round(rtt_ns / 1_000, 1),
        )
        return decision.name

    def describe(self) -> dict:
        return {
            "kind": GATEWAY_KIND,
            "agents": tuple(sorted(_AGENT_SCORE_FIELD)),
            "inverted_score_agents": tuple(sorted(_INVERT_SCORE)),
            "wire_type": "telemetry",
            "permit_processing": False,
        }

    def route_all(self, agent_outputs: dict[str, dict]) -> dict[str, str]:
        """Route outputs from multiple agents. Returns {agent_name: decision}."""
        return {name: self.route(name, output) for name, output in agent_outputs.items()}
