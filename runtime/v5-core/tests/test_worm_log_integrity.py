"""Tests for the chained WORM audit log."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "l2-orchestrator"))

from src.worm_log import WORMAuditLog  # noqa: E402


def _log_file(log_dir: Path) -> Path:
    return log_dir / f"valo_audit_{__import__('datetime').datetime.now().strftime('%Y%m%d')}.log"


def test_worm_log_verifies_intact_chain():
    log_dir = Path(tempfile.mkdtemp(prefix="valo_worm_"))
    log = WORMAuditLog(log_dir=str(log_dir))

    first = log.append_event("L2", "FIRST", {"value": 1})
    second = log.append_event("L2", "SECOND", {"value": 2})

    path = _log_file(log_dir)
    assert path.exists()
    assert log.verify_integrity(str(path)) is True

    lines = path.read_text(encoding="utf-8").splitlines()
    first_entry = json.loads(lines[0].split(" | ", 1)[1])
    second_entry = json.loads(lines[1].split(" | ", 1)[1])

    assert first_entry["sequence"] == 1
    assert first_entry["previous_hash"] == "0" * 64
    assert second_entry["sequence"] == 2
    assert second_entry["previous_hash"] == first
    assert second == lines[1].split(" | ", 1)[0]


def test_worm_log_detects_tampering():
    log_dir = Path(tempfile.mkdtemp(prefix="valo_worm_"))
    log = WORMAuditLog(log_dir=str(log_dir))
    log.append_event("L2", "FIRST", {"value": 1})
    log.append_event("L2", "SECOND", {"value": 2})

    path = _log_file(log_dir)
    lines = path.read_text(encoding="utf-8").splitlines()
    stored_hash, payload = lines[1].split(" | ", 1)
    entry = json.loads(payload)
    entry["data"]["value"] = 99
    lines[1] = f"{stored_hash} | {json.dumps(entry, sort_keys=True)}"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    assert log.verify_integrity(str(path)) is False
