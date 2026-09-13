"""Tests for the parity report summarizer CLI."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "parity_report.py"


def test_parity_report_cli_prints_summary_and_exits_zero_for_alignment(tmp_path):
    report_path = tmp_path / "parity-report.json"
    report_path.write_text(
        json.dumps(
            {
                "legacy_telemetry": {"passed": True, "checks": 9},
                "permit_shadow": {"passed": True, "checks": 2},
                "aligned": True,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(CLI), "--input", str(report_path)],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, f"parity_report.py failed:\n{result.stdout}\n{result.stderr}"
    assert "legacy_telemetry: passed=True checks=9" in result.stdout
    assert "permit_shadow: passed=True checks=2" in result.stdout
    assert "aligned: True" in result.stdout


def test_parity_report_cli_exits_nonzero_for_misalignment(tmp_path):
    report_path = tmp_path / "parity-report.json"
    report_path.write_text(
        json.dumps(
            {
                "legacy_telemetry": {"passed": True, "checks": 9},
                "permit_shadow": {"passed": False, "checks": 2},
                "aligned": False,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(CLI), "--input", str(report_path), "--quiet"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 1
    assert result.stdout == ""
