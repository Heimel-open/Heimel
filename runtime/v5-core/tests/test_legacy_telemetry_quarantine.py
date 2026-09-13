"""Source-level audit for the legacy telemetry adapter boundary."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "adapters" / "legacy-telemetry" / "src" / "lib.rs"

# The adapter may translate legacy telemetry into ExecutionSignal, but it must
# not grow into an execution path, effect dispatcher, or permit runtime.
FORBIDDEN_TOKENS = {
    "process_permit",
    "GoldenExecutionPath",
    "RacsGoldenPathBridge",
    "ExclusiveEffector",
    "ExecutionReceipt",
    "SideEffectRecord",
    "permit_runtime",
}


def test_legacy_telemetry_adapter_remains_translation_only():
    text = ADAPTER.read_text(encoding="utf-8")
    hits = sorted(token for token in FORBIDDEN_TOKENS if token in text)
    assert not hits, f"{ADAPTER} contains execution-path tokens: {hits}"
