"""Source-level audit for the legacy demo and sidecar bridge alignment.

The demo-server and sidecar remain legacy telemetry entrypoints, but they must
stay on the shared BridgeFactory loader path and must not grow permit/runtime
logic.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demo-server" / "app.py"
SIDECAR = ROOT / "sidecar" / "vaig.py"

MUST_HAVE = {
    "BridgeFactory",
}

MUST_NOT_HAVE = {
    "process_permit",
    "permit_runtime",
    "RacsGoldenPathRuntime",
    "GoldenExecutionPath",
    "SignedClearanceEnvelope",
    "ExclusiveEffector",
}


def _check_legacy_entrypoint(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    for token in MUST_HAVE:
        assert token in text, f"{path} should still use {token}"

    hits = sorted(token for token in MUST_NOT_HAVE if token in text)
    assert not hits, f"{path} unexpectedly references permit-path tokens: {hits}"


def test_demo_server_remains_legacy_telemetry_and_uses_shared_bridge_loader():
    _check_legacy_entrypoint(DEMO)


def test_sidecar_remains_legacy_telemetry_and_uses_shared_bridge_loader():
    _check_legacy_entrypoint(SIDECAR)
