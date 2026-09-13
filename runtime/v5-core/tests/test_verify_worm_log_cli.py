"""Tests for the WORM log verification CLI."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "verify_worm_log.py"

sys.path.insert(0, str(ROOT / "l2-orchestrator"))
from src.worm_log import WORMAuditLog  # noqa: E402


def _log_file(log_dir: Path) -> Path:
    return log_dir / f"valo_audit_{__import__('datetime').datetime.now().strftime('%Y%m%d')}.log"


def test_verify_worm_log_cli_reports_integrity(tmp_path):
    log = WORMAuditLog(log_dir=str(tmp_path))
    log.append_event("L2", "FIRST", {"value": 1})
    log.append_event("L2", "SECOND", {"value": 2})
    path = _log_file(tmp_path)

    result = subprocess.run(
        [sys.executable, str(CLI), "--input", str(path)],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, f"verify_worm_log.py failed:\n{result.stdout}\n{result.stderr}"
    assert "integrity: True" in result.stdout


def test_verify_worm_log_cli_exits_nonzero_for_tampering(tmp_path):
    log = WORMAuditLog(log_dir=str(tmp_path))
    log.append_event("L2", "FIRST", {"value": 1})
    log.append_event("L2", "SECOND", {"value": 2})
    path = _log_file(tmp_path)

    lines = path.read_text(encoding="utf-8").splitlines()
    stored_hash, payload = lines[1].split(" | ", 1)
    lines[1] = f"{stored_hash} | {payload.replace('2', '3', 1)}"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(CLI), "--input", str(path), "--quiet"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 1
    assert result.stdout.strip() == ""
