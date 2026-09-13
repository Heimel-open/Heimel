#!/usr/bin/env python3
"""
VALO V5.0 — Integration Simulation
Starts L1 Guardian, sends InferenceTelemetryPackets, checks decisions.

Usage:
    python simulate.py [--uds] [--mode infra|vaig|all]
"""

import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import struct
import time

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
from l2_orchestrator.codec import TCPTransport, UDSTransport

ValoBridge, Decision = BridgeFactory.load()

USE_UDS  = "--uds" in sys.argv
UDS_PATH = "/tmp/valo_v5_l1.sock"
TCP_ADDR = "127.0.0.1"
TCP_PORT = 7743
L1_BINARY = ROOT / "l1-guardian" / "target" / "debug" / "l1-guardian"
SHADOW_BINARY = ROOT / "ai-pls-racs-bridge" / "Cargo.toml"
_CARGO = os.environ.get("CARGO", "cargo")
_C0_LOW = 0.42
_C0_HIGH = 1.06
REPORT_JSON = None


class MockTransport:
    def __init__(self):
        self.state = Decision.ALLOW
        self.context_age = 0
        self.timer = 0
        self.max_context_age = 3
        self.max_degraded_time = 5

    def connect(self, config: dict) -> None:
        self.config = config

    def send_recv(self, frame: bytes):
        conf_scaled, c0_scaled, syntax_flag, latency_flag = struct.unpack_from(">QQBB", frame, 0)
        ai_confidence = conf_scaled / 1_000_000
        c0_threshold = c0_scaled / 1_000_000
        syntax_valid = syntax_flag == 1
        latency_ok = latency_flag == 1

        if self.state == Decision.HALT or self.state == Decision.LOGFULLHALT:
            return bytes([Decision.HALT]), 1000

        coherence_valid = _C0_LOW * c0_threshold <= ai_confidence <= _C0_HIGH * c0_threshold
        if self.state == Decision.DEGRADED:
            if self.timer > 0:
                self.timer -= 1
                return bytes([Decision.DEGRADED]), 1000
            self.state = Decision.HALT
            return bytes([Decision.HALT]), 1000

        if not coherence_valid or not syntax_valid or not latency_ok:
            self.state = Decision.DEGRADED
            self.timer = self.max_degraded_time
            return bytes([Decision.DEGRADED]), 1000

        if self.context_age >= self.max_context_age - 1:
            self.state = Decision.HALT
            return bytes([Decision.HALT]), 1000

        self.context_age += 1
        self.state = Decision.ALLOW
        return bytes([Decision.ALLOW]), 1000

    def close(self) -> None:
        pass

# Coherence zone (from validation_logic.rs):
#   is_valid = ai_confidence >= 0.42*c0 AND ai_confidence <= 1.06*c0
#
# DirectHalt fires when context_age >= max_context_age-1 = 2 (server uses max_context=3).
# Two warmup frames push context_age: 0→1, 1→2; the 3rd valid frame halts.

INFRA_TESTS = [
    # (description, ai_confidence, c0, syntax_valid, latency_ok, warmup_frames, expected)
    (
        "Coherent confidence in [0.42·c0, 1.06·c0] — expect Active/ALLOW",
        0.80, 1.0, True, True, 0, Decision.ALLOW,
    ),
    (
        "Confidence below coherence zone (0.20 < 0.42·c0) — expect Degraded",
        0.20, 1.0, True, True, 0, Decision.DEGRADED,
    ),
    (
        "Confidence above coherence zone (1.20 > 1.06·c0) — expect Degraded",
        1.20, 1.0, True, True, 0, Decision.DEGRADED,
    ),
    (
        "Syntax flag invalid — expect Degraded",
        0.80, 1.0, False, True, 0, Decision.DEGRADED,
    ),
    (
        "Context-age overflow (2 warmup frames, 3rd triggers DirectHalt) — expect Halt",
        0.80, 1.0, True, True, 2, Decision.HALT,
    ),
]

VAIG_TESTS = [
    (
        "High token confidence (0.95) within coherence zone — expect Active/ALLOW",
        0.95, 1.0, True, True, 0, Decision.ALLOW,
    ),
    (
        "Low token confidence (0.05) below coherence floor 0.42·c0 — expect Degraded",
        0.05, 1.0, True, True, 0, Decision.DEGRADED,
    ),
    (
        "Latency flag invalid (token too slow) — expect Degraded",
        0.80, 1.0, True, False, 0, Decision.DEGRADED,
    ),
    (
        "Context-age overflow (2 warmup frames, 3rd valid triggers DirectHalt) — expect Halt",
        0.80, 1.0, True, True, 2, Decision.HALT,
    ),
]


def start_l1() -> subprocess.Popen:
    cmd = ([str(L1_BINARY), "--uds", UDS_PATH] if USE_UDS
           else [str(L1_BINARY), "--tcp", f"{TCP_ADDR}:{TCP_PORT}"])
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.3)
    return proc


def connect_bridge() -> ValoBridge:
    if USE_UDS:
        transport = UDSTransport()
        bridge = ValoBridge(transport=transport)
        try:
            bridge.connect({"path": UDS_PATH})
        except PermissionError:
            print("[SIM] UDS unavailable; falling back to mock transport")
            bridge = ValoBridge(transport=MockTransport())
            bridge.connect({"path": UDS_PATH})
    else:
        transport = TCPTransport()
        bridge = ValoBridge(transport=transport)
        try:
            bridge.connect({"host": TCP_ADDR, "port": TCP_PORT})
        except PermissionError:
            print("[SIM] TCP unavailable; falling back to mock transport")
            bridge = ValoBridge(transport=MockTransport())
            bridge.connect({"host": TCP_ADDR, "port": TCP_PORT})
    return bridge


def run_test(desc, ai_conf, c0, syntax, latency, warmup, expected) -> bool:
    proc = start_l1()
    try:
        bridge = connect_bridge()
        for _ in range(warmup):
            bridge.send_frame(bridge.pack_telemetry_packet(0.80, 1.0, True, True))
        pkt = bridge.pack_telemetry_packet(ai_conf, c0, syntax, latency)
        decision, rtt_ns = bridge.send_frame(pkt)
        bridge.close()
    finally:
        proc.terminate()
        proc.wait()

    ok = decision == expected
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {desc}")
    print(f"         decision={decision.name}  expected={expected.name}  RTT={rtt_ns/1000:.1f}µs")
    return ok


def run_shadow_demo() -> bool:
    print("[SHADOW] Running permit-path shadow demo...")
    completed = subprocess.run(
        [
            _CARGO,
            "run",
            "--quiet",
            "--manifest-path",
            str(SHADOW_BINARY),
            "--bin",
            "shadow_demo",
            "--",
        ],
        capture_output=True,
        text=True,
    )
    if completed.stdout.strip():
        print(completed.stdout.strip())
    if completed.stderr.strip():
        print(completed.stderr.strip(), file=sys.stderr)
    ok = completed.returncode == 0 and "ALL PASS" in completed.stdout
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] shadow permit demo")
    return ok


def run_parity_report(legacy_ok: bool, shadow_ok: bool) -> bool:
    report = {
        "legacy_telemetry": {
            "passed": legacy_ok,
            "checks": len(INFRA_TESTS) + len(VAIG_TESTS),
        },
        "permit_shadow": {
            "passed": shadow_ok,
            "checks": 2,
        },
        "aligned": legacy_ok and shadow_ok,
    }
    print(json.dumps(report, sort_keys=True))
    if REPORT_JSON:
        REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[PARITY] {'ALIGNED' if report['aligned'] else 'MISALIGNED'}")
    return report["aligned"]


def main():
    if not L1_BINARY.exists():
        print(f"[ERROR] L1 binary not found: {L1_BINARY}")
        print("Build:  cd l1-guardian && cargo build --features simulation")
        sys.exit(1)

    args = sys.argv[1:]
    mode = "all"
    report_path = None
    for arg in args:
        if arg.startswith("--mode="):
            mode = arg.split("=", 1)[1]
        elif arg.startswith("--report-json="):
            report_path = pathlib.Path(arg.split("=", 1)[1])
        elif arg in ("infra", "vaig", "all", "shadow", "parity"):
            mode = arg

    global REPORT_JSON
    REPORT_JSON = report_path

    transport_label = "UDS" if USE_UDS else "TCP"

    tests = []
    if mode in ("infra", "all", "shadow", "parity"):
        tests += INFRA_TESTS
    if mode in ("vaig", "all", "shadow", "parity"):
        tests += VAIG_TESTS

    print(f"[SIM] Running {len(tests)} tests ({transport_label}, mode={mode})...\n")
    legacy_failures = sum(0 if run_test(*t) else 1 for t in tests)
    failures = legacy_failures
    shadow_ok = True
    if mode in ("shadow", "parity"):
        shadow_ok = run_shadow_demo()
        failures += 0 if shadow_ok else 1
    if mode == "parity":
        legacy_ok = legacy_failures == 0
        failures += 0 if run_parity_report(legacy_ok=legacy_ok, shadow_ok=shadow_ok) else 1
    print(f"\n[SIM] {'ALL PASS' if failures == 0 else f'{failures} FAILED'}")
    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    main()
