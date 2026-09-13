"""Audit that the permit-based golden path stays in the intended ingress.

The golden path is deliberately exposed through:
  - mcp_server.py
  - l2-orchestrator/src/propagator.py
  - the golden-path runtime wrappers

Legacy runtime entrypoints such as sidecar/vaig.py, demo-server/app.py,
janus_integration.py and simulate.py should remain telemetry-only and must
not grow permit-processing logic.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

ALLOWED_FILES = [
    ROOT / "mcp_server.py",
    ROOT / "l2-orchestrator" / "src" / "propagator.py",
    ROOT / "l2-orchestrator" / "src" / "golden_path.py",
    ROOT / "ai-pls-racs-bridge" / "src" / "lib.rs",
    ROOT / "ai-pls-racs-bridge" / "src" / "main.rs",
]

BANNED_RUNTIME_FILES = [
    ROOT / "sidecar" / "vaig.py",
    ROOT / "demo-server" / "app.py",
    ROOT / "janus_integration.py",
    ROOT / "simulate.py",
]

FORBIDDEN_TOKENS = {
    "process_permit",
    "RacsGoldenPathRuntime",
    "permit_runtime",
    "SignedClearanceEnvelope",
    "GoldenExecutionPath",
    "ExclusiveEffector",
}


def test_permit_ingress_is_scoped_to_the_golden_path_entrypoints():
    allowed_text = "\n".join(path.read_text(encoding="utf-8") for path in ALLOWED_FILES)
    for token in FORBIDDEN_TOKENS:
        assert token in allowed_text, f"expected {token} to exist in the golden-path files"

    for path in BANNED_RUNTIME_FILES:
        text = path.read_text(encoding="utf-8")
        hits = sorted(token for token in FORBIDDEN_TOKENS if token in text)
        assert not hits, f"{path} unexpectedly references permit-path tokens: {hits}"
