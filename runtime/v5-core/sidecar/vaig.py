#!/usr/bin/env python3
"""
VAIG — Valo AI-Inference Guard
HTTP proxy between application and LLM API.
Validates per-token confidence via L1 Guardian before forwarding to client.

Usage:
    python sidecar/vaig.py --upstream http://localhost:11434 --port 8080 --l1-tcp 127.0.0.1:7743

Supports OpenAI-compatible streaming APIs (vLLM, Ollama, OpenAI).
On Halt: replaces token content with [REDACTED] and logs to WORM audit log.
On Degraded: forwards token, adds X-Valo-Confidence: degraded response header.
"""

import argparse
import importlib.util
import json
import math
import pathlib
import sys
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = pathlib.Path(__file__).parents[1]


def _bootstrap_l2():
    """Register l2-orchestrator as l2_orchestrator package in sys.modules."""
    l2_dir = ROOT / "l2-orchestrator"
    pkg_spec = importlib.util.spec_from_file_location(
        "l2_orchestrator", l2_dir / "__init__.py",
        submodule_search_locations=[str(l2_dir)],
    )
    pkg = importlib.util.module_from_spec(pkg_spec)
    sys.modules["l2_orchestrator"] = pkg
    pkg_spec.loader.exec_module(pkg)
    return pkg


_bootstrap_l2()
from l2_orchestrator import BridgeFactory
from l2_orchestrator.observability import StructuredLogger

StructuredLogger.set_component("vaig")
from l2_orchestrator.codec import TCPTransport, UDSTransport

ValoBridge, Decision = BridgeFactory.load()


def _load_worm():
    spec = importlib.util.spec_from_file_location(
        "worm_log", ROOT / "l2-orchestrator" / "src" / "worm_log.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.WORMAuditLog


WORMAuditLog = _load_worm()

# ------------------------------------------------------------------ globals
_bridge: ValoBridge | None = None
_worm: WORMAuditLog | None = None
_upstream: str = ""
_tau: float = 0.10
_confidence_floor: float = 0.05


def _validate_token(confidence: float, token_id: int) -> Decision:
    """Send a VAIG frame to L1 and return the Decision."""
    primary = max(_tau, _confidence_floor)
    secondary = confidence
    frame = _bridge.pack_valo_frame(
        val_primary=primary,
        val_secondary=secondary,
        max_spread=100.0,
        identifier=token_id,
        domain=1,
    )
    decision, _ = _bridge.send_frame(frame)
    return decision


def _process_stream(response_body: bytes, response_headers: dict) -> tuple[bytes, str]:
    global _tokens_allowed, _tokens_degraded, _tokens_halted
    overall_status = "allow"
    output_lines = []
    token_idx = 0

    for line in response_body.split(b"\n"):
        if not line.startswith(b"data: "):
            output_lines.append(line)
            continue

        data_str = line[6:].decode("utf-8", errors="replace").strip()
        if data_str == "[DONE]":
            output_lines.append(line)
            continue

        try:
            chunk = json.loads(data_str)
        except json.JSONDecodeError:
            output_lines.append(line)
            continue

        choices = chunk.get("choices", [])
        for choice in choices:
            delta = choice.get("delta", {})
            content = delta.get("content", "")
            logprobs = choice.get("logprobs")

            if not content:
                continue

            if logprobs is None:
                confidence = _confidence_floor
            else:
                token_logprobs = logprobs.get("content", [])
                if token_logprobs:
                    logprob = token_logprobs[0].get("logprob", 0.0)
                    confidence = math.exp(logprob)
                else:
                    confidence = _confidence_floor

            decision = _validate_token(confidence, token_idx)

            if decision == Decision.HALT:
                overall_status = "halt"
                delta["content"] = "[REDACTED]"
                _tokens_halted += 1
                _worm.append_event("VAIG", "TOKEN_HALTED", {
                    "token_idx": token_idx,
                    "confidence": confidence,
                    "threshold": _tau,
                    "floor": _confidence_floor,
                })
            elif decision == Decision.DEGRADED:
                _tokens_degraded += 1
                if overall_status == "allow":
                    overall_status = "degraded"
            else:
                _tokens_allowed += 1

            token_idx += 1

        modified = json.dumps(chunk).encode("utf-8")
        output_lines.append(b"data: " + modified)

    return b"\n".join(output_lines), overall_status


_tokens_allowed: int = 0
_tokens_degraded: int = 0
_tokens_halted: int = 0


class VAIGHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path == "/health":
            body = json.dumps({"status": "ok", "bridge": _bridge is not None}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/v1/status":
            body = json.dumps({
                "bridge_connected": _bridge is not None,
                "upstream": _upstream,
                "tau": _tau,
                "confidence_floor": _confidence_floor,
                "tokens": {
                    "allowed": _tokens_allowed,
                    "degraded": _tokens_degraded,
                    "halted": _tokens_halted,
                },
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
            return

        upstream_url = _upstream.rstrip("/") + self.path
        try:
            with urllib.request.urlopen(upstream_url) as resp:
                body = resp.read()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(body)
        except urllib.error.URLError as e:
            self.send_error(502, str(e))

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            req_json = json.loads(body)
            req_json["logprobs"] = True
            req_json["stream"] = True
            body = json.dumps(req_json).encode("utf-8")
        except (json.JSONDecodeError, AttributeError):
            pass

        upstream_url = _upstream.rstrip("/") + self.path
        req = urllib.request.Request(
            upstream_url, data=body, method="POST",
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req) as resp:
                resp_body = resp.read()
                resp_headers = dict(resp.headers)
        except urllib.error.URLError as e:
            self.send_error(502, f"Upstream error: {e}")
            return

        processed_body, valo_status = _process_stream(resp_body, resp_headers)

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("X-Valo-Status", valo_status)
        if valo_status == "degraded":
            self.send_header("X-Valo-Confidence", "degraded")
        self.end_headers()
        self.wfile.write(processed_body)



def main():
    global _bridge, _worm, _upstream, _tau, _confidence_floor

    parser = argparse.ArgumentParser(description="VAIG — Valo AI-Inference Guard")
    parser.add_argument("--upstream", default="http://127.0.0.1:11434")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--l1-tcp", default="127.0.0.1:7743")
    parser.add_argument("--l1-uds", default=None)
    parser.add_argument("--tau", type=float, default=0.10)
    parser.add_argument("--confidence-floor", type=float, default=0.05)
    args = parser.parse_args()

    _upstream = args.upstream
    _tau = args.tau
    _confidence_floor = args.confidence_floor

    if args.l1_uds:
        transport = UDSTransport()
        _bridge = ValoBridge(transport=transport)
        _bridge.connect({"path": args.l1_uds})
        print(f"[VAIG] L1 via UDS {args.l1_uds}")
    else:
        host, port = args.l1_tcp.rsplit(":", 1)
        transport = TCPTransport()
        _bridge = ValoBridge(transport=transport)
        _bridge.connect({"host": host, "port": int(port)})
        print(f"[VAIG] L1 via TCP {args.l1_tcp}")

    _worm = WORMAuditLog("/tmp/valo_vaig_audit/")
    print(f"[VAIG] Proxy listening on :{args.port}  upstream={_upstream}")
    print(f"[VAIG] tau={_tau}  confidence_floor={_confidence_floor}")

    server = HTTPServer(("0.0.0.0", args.port), VAIGHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if _bridge:
            _bridge.close()


if __name__ == "__main__":
    main()
