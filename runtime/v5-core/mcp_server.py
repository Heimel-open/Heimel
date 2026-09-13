#!/usr/bin/env python3
"""
VALO V5.0 — MCP Server
Exposes VALO decision-making to AI assistants via the Model Context Protocol.

Tools:
    validate_decision   — legacy telemetry: evaluate a confidence score against the L1 Guardian
    check_coherence     — legacy telemetry: check if confidence is within [0.42·c0, 1.06·c0]
    report_status       — legacy telemetry: current bridge / L1 connection state and last decision
    evaluate_prompt     — legacy telemetry: confidence + action label → full VALO evaluation
    process_permit      — golden path: verify and process a signed RACS permit

Usage (stdio, Claude Desktop):
    python mcp_server.py [--l1-tcp 127.0.0.1:7743] [--l1-uds /tmp/valo_v5_l1.sock]

Usage without L1 (coherence check only):
    python mcp_server.py --no-l1

Requires:
    pip install mcp
"""

import argparse
import importlib.util
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent
L2_ROOT = ROOT / "l2-orchestrator"

if str(L2_ROOT) not in sys.path:
    sys.path.insert(0, str(L2_ROOT))


def _bootstrap_l2() -> None:
    l2_dir = L2_ROOT
    pkg_spec = importlib.util.spec_from_file_location(
        "l2_orchestrator", l2_dir / "__init__.py",
        submodule_search_locations=[str(l2_dir)],
    )
    pkg = importlib.util.module_from_spec(pkg_spec)
    sys.modules["l2_orchestrator"] = pkg
    pkg_spec.loader.exec_module(pkg)


_bootstrap_l2()
from l2_orchestrator import BridgeFactory
ValoBridge, Decision = BridgeFactory.load()
from l2_orchestrator.golden_path import RacsGoldenPathRuntime
from l2_orchestrator.observability import StructuredLogger
from l2_orchestrator.codec import TCPTransport, UDSTransport

StructuredLogger.set_component("mcp-server")

# Coherence window multipliers — must match validation_logic.rs constants.
# Production: required env vars only (VALO_C0_LOW_MULTIPLIER / VALO_C0_HIGH_MULTIPLIER).
# Simulation/test fallback: read from VALO_C0_LOW_DEFAULT / VALO_C0_HIGH_DEFAULT
# (no hardcoded C0 in source — supply via env/test config).
_C0_LOW_DEFAULT = float(os.environ.get("VALO_C0_LOW_DEFAULT", "0.42"))
_C0_HIGH_DEFAULT = float(os.environ.get("VALO_C0_HIGH_DEFAULT", "1.06"))

_C0_LOW = float(os.environ.get("VALO_C0_LOW_MULTIPLIER", _C0_LOW_DEFAULT))
_C0_HIGH = float(os.environ.get("VALO_C0_HIGH_MULTIPLIER", _C0_HIGH_DEFAULT))

if "VALO_C0_LOW_MULTIPLIER" not in os.environ or "VALO_C0_HIGH_MULTIPLIER" not in os.environ:
    print(
        f"[WARN] Using default C0 multipliers (_LOW={_C0_LOW_DEFAULT}, _HIGH={_C0_HIGH_DEFAULT}). "
        "For production, set VALO_C0_LOW_MULTIPLIER and VALO_C0_HIGH_MULTIPLIER.",
        file=sys.stderr,
    )

# State shared across tool calls
_bridge: "ValoBridge | None" = None
_last_decision: "Decision | None" = None
_frame_count: int = 0
_permit_runtime: "RacsGoldenPathRuntime | None" = None

# ACS distrust levels → AARM decisions
# L0 = Trusted, L1 = Monitor, L2 = Caution, L3 = Suspicious, L4 = Untrusted
_DISTRUST_THRESHOLDS = [
    (0.90, "L0", "ALLOW",    "Confidence within nominal range. Output admissible."),
    (0.75, "L1", "ALLOW",    "Minor drift detected. Allow with monitoring."),
    (0.55, "L2", "MODIFY",   "Moderate drift. Prepend disclaimer before forwarding to user."),
    (0.40, "L3", "DEFER",    "High drift. Route to human approval queue before proceeding."),
    (0.00, "L4", "DENY",     "Critical drift. Reject output. Escalate to Council (STEP_UP)."),
]

# OWASP Agentic Security Initiatives (ACS) coverage status
_OWASP_ASI = {
    "ASI01": {"name": "Prompt Injection",       "covered": True,  "mechanism": "hedge_detector + injection pattern scan"},
    "ASI02": {"name": "Tool Misuse",            "covered": True,  "mechanism": "format_check + syntax_valid_flag in L1"},
    "ASI03": {"name": "Memory Poisoning",       "covered": True,  "mechanism": "cot_auditor + context_age overflow → DirectHalt"},
    "ASI04": {"name": "Privilege Escalation",   "covered": False, "mechanism": "Planned: IntentSpec in DeterministicGate (ACS §9.1)"},
    "ASI05": {"name": "PII / Data Exfiltration","covered": True,  "mechanism": "data_leakage instrument + Presidio adapter"},
    "ASI06": {"name": "Misinformation",         "covered": True,  "mechanism": "logprob_scorer + semantic_entropy"},
    "ASI07": {"name": "Excessive Autonomy",     "covered": True,  "mechanism": "DeltaBox + iteration limit (vaig-fidelity)"},
    "ASI08": {"name": "Cascading Failures",     "covered": True,  "mechanism": "CAKM monitor + L1 Halt is terminal"},
    "ASI09": {"name": "Trust Exploitation",     "covered": True,  "mechanism": "sycophancy_detector instrument"},
    "ASI10": {"name": "Audit Tampering",        "covered": True,  "mechanism": "SHA-256 hash-chained WORM log (append-only)"},
}

# Simple injection pattern scanner (ASI01)
import re as _re
_INJECTION_PATTERNS = [
    r"ignore\s+(previous|all|prior)\s+instructions?",
    r"disregard\s+.{0,40}\s+instructions?",
    r"you\s+are\s+now\s+(?:a|an)\s+\w",
    r"jailbreak",
    r"dan\s+mode",
    r"pretend\s+you\s+(?:are|have\s+no)",
    r"act\s+as\s+if\s+you\s+(?:are|were)",
    r"forget\s+(?:all|your)\s+",
    r"system\s*:\s*override",
]


# ---------------------------------------------------------------------------
# Core logic (sync — called from async tool handlers)
# ---------------------------------------------------------------------------

def _do_validate(confidence: float, c0: float, syntax: bool, latency: bool) -> dict:
    global _last_decision, _frame_count
    if _bridge is None:
        return {
            "error": "L1 Guardian not connected. Start with --l1-tcp or --l1-uds, or use check_coherence instead."
        }
    try:
        frame = _bridge.pack_telemetry_packet(confidence, c0, syntax, latency)
        decision, rtt_ns = _bridge.send_frame(frame)
        _last_decision = decision
        _frame_count += 1
        low, high = c0 * _C0_LOW, c0 * _C0_HIGH
        return {
            "decision": decision.name,
            "confidence": confidence,
            "c0_threshold": c0,
            "coherence_window": [round(low, 6), round(high, 6)],
            "in_coherence_window": low <= confidence <= high,
            "syntax_valid": syntax,
            "latency_ok": latency,
            "rtt_ns": rtt_ns,
            "explanation": _explain(decision, confidence, c0, syntax, latency),
        }
    except Exception as exc:
        return {"error": str(exc)}


def _do_check_coherence(confidence: float, c0: float) -> dict:
    low, high = c0 * _C0_LOW, c0 * _C0_HIGH
    in_window = low <= confidence <= high
    return {
        "confidence_score": confidence,
        "c0_threshold": c0,
        "coherence_window": [round(low, 6), round(high, 6)],
        "in_coherence_window": in_window,
        "verdict": "WITHIN_WINDOW" if in_window else (
            "BELOW_FLOOR" if confidence < low else "ABOVE_CEILING"
        ),
    }


def _do_get_distrust_level(confidence: float) -> dict:
    for threshold, level, decision, explanation in _DISTRUST_THRESHOLDS:
        if confidence >= threshold:
            return {
                "confidence_score": confidence,
                "distrust_level": level,
                "aarm_decision": decision,
                "explanation": explanation,
            }
    last = _DISTRUST_THRESHOLDS[-1]
    return {
        "confidence_score": confidence,
        "distrust_level": last[1],
        "aarm_decision": last[2],
        "explanation": last[3],
    }


def _do_check_aarm_decision(confidence: float, output_text: str, action: str) -> dict:
    distrust = _do_get_distrust_level(confidence)
    injection_hits = []
    if output_text:
        for pattern in _INJECTION_PATTERNS:
            if _re.search(pattern, output_text, _re.IGNORECASE):
                injection_hits.append(pattern)
    if injection_hits:
        distrust["aarm_decision"] = "DENY"
        distrust["injection_detected"] = True
        distrust["injection_patterns"] = injection_hits
        distrust["explanation"] = (
            f"ASI01 PROMPT INJECTION DETECTED ({len(injection_hits)} pattern(s)). "
            "Output rejected regardless of confidence. Escalate immediately."
        )
    else:
        distrust["injection_detected"] = False
    if action:
        distrust["action"] = action
    return distrust


def _do_check_owasp_coverage() -> dict:
    covered = [k for k, v in _OWASP_ASI.items() if v["covered"]]
    gaps = [k for k, v in _OWASP_ASI.items() if not v["covered"]]
    return {
        "standard": "OWASP Agentic Security Initiative v1.0 (May 2026)",
        "coverage_count": len(covered),
        "total_controls": len(_OWASP_ASI),
        "coverage_pct": round(100 * len(covered) / len(_OWASP_ASI)),
        "controls": {
            k: {
                "name": v["name"],
                "covered": v["covered"],
                "mechanism": v["mechanism"],
            }
            for k, v in _OWASP_ASI.items()
        },
        "gaps": gaps,
        "gap_note": (
            "ASI04 (Privilege Escalation) is planned via IntentSpec in DeterministicGate (ACS §9.1). "
            "All other controls are implemented."
            if gaps else "Full coverage."
        ),
    }


def _do_report_status() -> dict:
    connected = _bridge is not None
    if connected:
        connected = getattr(_bridge, "_transport", None) is not None
    return {
        "bridge_connected": connected,
        "last_decision": _last_decision.name if _last_decision else None,
        "frames_sent": _frame_count,
        "coherence_constants": {"c0_low_multiplier": _C0_LOW, "c0_high_multiplier": _C0_HIGH},
        "l1_formal_verification": {
            "tool": "TLC Model Checker v2.16",
            "distinct_states": 1662,
            "counterexamples": 0,
            "spec": "formal-verification/ValoStateMachine.tla",
        },
    }


def _get_permit_runtime() -> RacsGoldenPathRuntime:
    global _permit_runtime
    if _permit_runtime is None:
        _permit_runtime = RacsGoldenPathRuntime()
    return _permit_runtime


def _do_process_permit(
    permit: dict,
    trusted_issuer: dict,
    now_epoch_ms: int | None = None,
    revocation_registry_path: str | None = None,
) -> dict:
    try:
        result = _get_permit_runtime().process_permit(
            permit=permit,
            trusted_issuer=trusted_issuer,
            now_epoch_ms=now_epoch_ms,
            revocation_registry_path=revocation_registry_path,
        )
        result["tool"] = "process_permit"
        return result
    except Exception as exc:
        return {"ok": False, "error": str(exc), "tool": "process_permit"}


def _dispatch_tool(name: str, arguments: dict) -> dict:
    if name == "validate_decision":
        result = _do_validate(
            confidence=float(arguments["confidence_score"]),
            c0=float(arguments.get("c0_threshold", 1.0)),
            syntax=bool(arguments.get("syntax_valid", True)),
            latency=bool(arguments.get("latency_ok", True)),
        )
    elif name == "check_coherence":
        result = _do_check_coherence(
            confidence=float(arguments["confidence_score"]),
            c0=float(arguments.get("c0_threshold", 1.0)),
        )
    elif name == "report_status":
        result = _do_report_status()
    elif name == "evaluate_prompt":
        result = _do_validate(
            confidence=float(arguments["confidence_score"]),
            c0=float(arguments.get("c0_threshold", 1.0)),
            syntax=True,
            latency=True,
        )
        if arguments.get("action"):
            result["action"] = arguments["action"]
    elif name == "get_distrust_level":
        result = _do_get_distrust_level(float(arguments["confidence_score"]))
    elif name == "check_aarm_decision":
        result = _do_check_aarm_decision(
            confidence=float(arguments["confidence_score"]),
            output_text=str(arguments.get("output_text", "")),
            action=str(arguments.get("action", "")),
        )
    elif name == "check_owasp_coverage":
        result = _do_check_owasp_coverage()
    elif name == "process_permit":
        result = _do_process_permit(
            permit=dict(arguments["permit"]),
            trusted_issuer=dict(arguments["trusted_issuer"]),
            now_epoch_ms=arguments.get("now_epoch_ms"),
            revocation_registry_path=arguments.get("revocation_registry_path"),
        )
    else:
        result = {"error": f"Unknown tool: {name}"}

    return result


def _explain(decision: Decision, confidence: float, c0: float, syntax: bool, latency: bool) -> str:
    low, high = c0 * _C0_LOW, c0 * _C0_HIGH
    if decision == Decision.ALLOW:
        return (
            f"Confidence {confidence:.4f} is within coherence window "
            f"[{low:.4f}, {high:.4f}]. Output is admissible."
        )
    if decision == Decision.DEGRADED:
        reasons = []
        if not syntax:
            reasons.append("syntax validation failed")
        if not latency:
            reasons.append("latency constraint violated")
        if confidence < low:
            reasons.append(f"confidence {confidence:.4f} below floor {low:.4f}")
        elif confidence > high:
            reasons.append(f"confidence {confidence:.4f} above ceiling {high:.4f}")
        return "DEGRADED: " + "; ".join(reasons or ["L1 triggered degraded state"])
    if decision == Decision.HALT:
        return (
            "HALT: Terminal state reached. Context age overflow or saturated distrust. "
            "Authorized 2-person reset required to resume."
        )
    if decision == Decision.LOGFULLHALT:
        return "HALT (LOG FULL): Audit log capacity exhausted. Log rotation required before restart."
    return f"Unknown decision: {decision}"


# ---------------------------------------------------------------------------
# MCP server (async)
# ---------------------------------------------------------------------------

_TOOLS = [
    {
        "name": "validate_decision",
        "description": (
            "Legacy telemetry tool. Send a confidence score to the VALO V5 L1 Guardian "
            "and get a decision: ALLOW, DEGRADED, or HALT. The L1 Guardian is formally "
            "verified in TLA+ (1662 distinct states, 0 counterexamples). Requires a live "
            "L1 connection."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "confidence_score": {
                    "type": "number",
                    "description": "AI output confidence, 0.0–1.0",
                },
                "c0_threshold": {
                    "type": "number",
                    "description": "Coherence threshold (default 1.0 for normalised inputs)",
                    "default": 1.0,
                },
                "syntax_valid": {
                    "type": "boolean",
                    "description": "Whether output passes syntax validation",
                    "default": True,
                },
                "latency_ok": {
                    "type": "boolean",
                    "description": "Whether response latency is within bounds",
                    "default": True,
                },
            },
            "required": ["confidence_score"],
        },
    },
    {
        "name": "check_coherence",
        "description": (
            "Legacy telemetry tool. Check whether a confidence score falls within the "
            "VALO coherence window [0.42·c0, 1.06·c0] — pure calculation, no L1 "
            "connection required."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "confidence_score": {
                    "type": "number",
                    "description": "Confidence score to evaluate",
                },
                "c0_threshold": {
                    "type": "number",
                    "description": "Coherence threshold (default 1.0)",
                    "default": 1.0,
                },
            },
            "required": ["confidence_score"],
        },
    },
    {
        "name": "report_status",
        "description": (
            "Legacy telemetry tool. Report current VALO bridge and L1 Guardian status: "
            "connection state, last decision, frames sent, formal verification metadata."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "evaluate_prompt",
        "description": (
            "Legacy telemetry tool. Evaluate an AI action against VALO. "
            "Supply confidence_score (0.0–1.0) and an optional action label. "
            "Returns full VALO evaluation with human-readable explanation."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "confidence_score": {
                    "type": "number",
                    "description": "AI output confidence, 0.0–1.0",
                },
                "action": {
                    "type": "string",
                    "description": "Label for the action being evaluated (e.g. OUTBOUND_CALL, DIAGNOSIS)",
                    "default": "",
                },
                "c0_threshold": {
                    "type": "number",
                    "description": "Coherence threshold (default 1.0)",
                    "default": 1.0,
                },
            },
            "required": ["confidence_score"],
        },
    },
    {
        "name": "get_distrust_level",
        "description": (
            "Legacy telemetry tool. Map a confidence score to an ACS distrust level "
            "(L0–L4) and AARM decision. L0=Trusted/ALLOW, L1=Monitor/ALLOW, "
            "L2=Caution/MODIFY, L3=Suspicious/DEFER, L4=Untrusted/DENY+STEP_UP. "
            "No L1 connection required — pure threshold lookup."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "confidence_score": {
                    "type": "number",
                    "description": "AI output confidence, 0.0–1.0",
                },
            },
            "required": ["confidence_score"],
        },
    },
    {
        "name": "check_aarm_decision",
        "description": (
            "Legacy telemetry tool. Full AARM (Agentic Risk Mitigation) evaluation: "
            "distrust level, decision, explanation, and optional injection scan. "
            "Supply confidence_score and optionally the output text to scan for prompt "
            "injection (ASI01)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "confidence_score": {
                    "type": "number",
                    "description": "AI output confidence, 0.0–1.0",
                },
                "output_text": {
                    "type": "string",
                    "description": "AI output text to scan for prompt injection patterns (optional)",
                    "default": "",
                },
                "action": {
                    "type": "string",
                    "description": "Action label for logging (e.g. OUTBOUND_CALL, DIAGNOSIS)",
                    "default": "",
                },
            },
            "required": ["confidence_score"],
        },
    },
    {
        "name": "check_owasp_coverage",
        "description": (
            "Legacy telemetry tool. Report VALO's coverage of the OWASP Agentic Security "
            "Initiative (ASI01–ASI10). Returns coverage status, mechanism, and a summary "
            "of gaps. Based on OWASP ASI v1.0 (May 2026)."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "process_permit",
        "description": (
            "Golden path tool. Verify and process a signed RACS execution permit through "
            "the explicit execution path from permit JSON to execution receipt JSON."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "permit": {
                    "type": "object",
                    "description": "Signed execution permit JSON artifact",
                },
                "trusted_issuer": {
                    "type": "object",
                    "description": "Trusted issuer JSON with public key material",
                },
                "now_epoch_ms": {
                    "type": "integer",
                    "description": "Optional evaluation time in Unix epoch milliseconds",
                },
                "revocation_registry_path": {
                    "type": "string",
                    "description": "Optional durable invalidation registry path",
                },
            },
            "required": ["permit", "trusted_issuer"],
        },
    },
]


async def _run_mcp_server() -> None:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    import mcp.types as types

    server = Server("valo-v5")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name=t["name"],
                description=t["description"],
                inputSchema=t["inputSchema"],
            )
            for t in _TOOLS
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        result = _dispatch_tool(name, arguments)

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream,
            server.create_initialization_options(),
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _connect_bridge(args) -> "ValoBridge | None":
    try:
        if args.l1_uds:
            transport = UDSTransport()
            bridge = ValoBridge(transport=transport)
            bridge.connect({"path": args.l1_uds})
            print(f"[MCP] L1 via UDS {args.l1_uds}", file=sys.stderr)
        else:
            host, port_str = args.l1_tcp.rsplit(":", 1)
            transport = TCPTransport()
            bridge = ValoBridge(transport=transport)
            bridge.connect({"host": host, "port": int(port_str)})
            print(f"[MCP] L1 via TCP {args.l1_tcp}", file=sys.stderr)
        return bridge
    except Exception as exc:
        print(f"[MCP] Warning: L1 unavailable ({exc}). validate_decision will return error.", file=sys.stderr)
        return None


def main() -> None:
    global _bridge

    parser = argparse.ArgumentParser(description="VALO V5.0 MCP Server")
    parser.add_argument("--l1-tcp", default="127.0.0.1:7743", metavar="HOST:PORT")
    parser.add_argument("--l1-uds", default=None, metavar="PATH")
    parser.add_argument("--no-l1", action="store_true",
                        help="Start without L1 connection (check_coherence still works)")
    args = parser.parse_args()

    try:
        import mcp  # noqa: F401
    except ImportError:
        print("[MCP] ERROR: 'mcp' package not installed. Run: pip install mcp", file=sys.stderr)
        sys.exit(1)

    if not args.no_l1:
        _bridge = _connect_bridge(args)

    import asyncio
    asyncio.run(_run_mcp_server())


if __name__ == "__main__":
    main()
