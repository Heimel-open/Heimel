"""Integration tests — require L1 binary.

Build first:
    cd l1-guardian && cargo build --features simulation

Then run:
    pytest tests/test_integration.py
"""
import pathlib
import subprocess
import sys
import pytest

ROOT = pathlib.Path(__file__).parents[1]
L1_BINARY = ROOT / "l1-guardian" / "target" / "debug" / "l1-guardian"

needs_binary = pytest.mark.skipif(
    not L1_BINARY.exists(),
    reason="L1 binary not built — run: cd l1-guardian && cargo build --features simulation",
)


@needs_binary
def test_infrastructure_simulation_5_of_5():
    """5 infrastructure frames: ALLOW, HALT×2, DEGRADED, L4-sentinel HALT."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "simulate.py")],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, f"simulate.py failed:\n{result.stdout}\n{result.stderr}"
    assert "ALL PASS" in result.stdout


@needs_binary
def test_vaig_simulation_4_of_4():
    """4 VAIG token-confidence frames: ALLOW×2, HALT×2."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "simulate_vaig.py")],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, f"simulate_vaig.py failed:\n{result.stdout}\n{result.stderr}"
    assert "ALL PASS" in result.stdout


@needs_binary
def test_total_9_of_9():
    """Convenience check: both simulations pass = 9/9 as claimed in whitepaper."""
    for script in ("simulate.py", "simulate_vaig.py"):
        result = subprocess.run(
            [sys.executable, str(ROOT / script)],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, f"{script} failed:\n{result.stdout}"


@needs_binary
def test_shadow_alignment_demo_passes():
    """Shadow mode exercises both the legacy telemetry demo and the permit demo."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "simulate.py"), "--mode", "shadow"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, f"simulate.py --mode shadow failed:\n{result.stdout}\n{result.stderr}"
    assert "ALL PASS" in result.stdout


@needs_binary
def test_parity_report_is_explicit():
    """Parity mode emits an explicit JSON report over legacy + shadow alignment."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "simulate.py"), "--mode", "parity"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, f"simulate.py --mode parity failed:\n{result.stdout}\n{result.stderr}"
    assert "\"aligned\": true" in result.stdout
    assert "\"legacy_telemetry\"" in result.stdout
    assert "\"permit_shadow\"" in result.stdout


@needs_binary
def test_parity_report_writes_json_artifact(tmp_path):
    """Parity mode can persist the alignment report as a JSON artifact."""
    report_path = tmp_path / "parity-report.json"
    result = subprocess.run(
        [sys.executable, str(ROOT / "simulate.py"), "--mode", "parity", f"--report-json={report_path}"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, f"simulate.py --mode parity failed:\n{result.stdout}\n{result.stderr}"
    assert report_path.exists(), "parity report JSON artifact was not written"
    payload = report_path.read_text(encoding="utf-8")
    assert "\"aligned\": true" in payload
    assert "\"legacy_telemetry\"" in payload
    assert "\"permit_shadow\"" in payload
