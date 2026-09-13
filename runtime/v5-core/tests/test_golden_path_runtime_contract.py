"""Contract tests for the explicit permit runtime wrapper.

These tests exercise the subprocess boundary directly so the Python runtime
contract stays explicit even without invoking the full Rust bridge.
"""

from __future__ import annotations

import stat
import textwrap
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "l2-orchestrator"))

from src.golden_path import RacsGoldenPathRuntime  # noqa: E402


def _make_executable(tmp_path: Path, name: str, contents: str) -> Path:
    path = tmp_path / name
    path.write_text(textwrap.dedent(contents), encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


def test_runtime_process_permit_parses_json_response(tmp_path):
    script = _make_executable(
        tmp_path,
        "stub_runtime.py",
        """\
        #!/usr/bin/env python3
        import json
        import sys

        request = json.load(sys.stdin)
        assert request["permit"]["artifact_id"] == "permit-1"
        assert request["trusted_issuer"]["issuer_id"] == "platform:test"
        assert request["now_epoch_ms"] == 1234567890
        print(json.dumps({
            "ok": True,
            "outcome": "Executed",
            "execution_allowed": True,
            "receipt": {
                "receipt_id": "rcpt-001",
                "effector_id": "connector.erp",
                "replay_nonce": "nonce-0123456789",
                "binding_valid": True,
                "replay_free": True,
                "not_expired": True,
                "binding_digest": "sha256:binding",
            },
        }))
        """,
    )

    runtime = RacsGoldenPathRuntime(command=[str(script)])
    result = runtime.process_permit(
        permit={"artifact_id": "permit-1"},
        trusted_issuer={"issuer_id": "platform:test"},
        now_epoch_ms=1234567890,
        revocation_registry_path="/tmp/revocations.jsonl",
    )

    assert result["ok"] is True
    assert result["outcome"] == "Executed"
    assert result["receipt"]["receipt_id"] == "rcpt-001"
    assert result["receipt"]["replay_nonce"] == "nonce-0123456789"
    assert result["receipt"]["binding_valid"] is True
    assert result["receipt"]["replay_free"] is True


def test_runtime_raises_runtimeerror_on_nonzero_exit(tmp_path):
    script = _make_executable(
        tmp_path,
        "stub_failure.py",
        """\
        #!/usr/bin/env python3
        import sys

        sys.stderr.write("bridge failure: invalid permit\\n")
        sys.exit(7)
        """,
    )

    runtime = RacsGoldenPathRuntime(command=[str(script)])

    with pytest.raises(RuntimeError, match="bridge failure: invalid permit"):
        runtime.process_permit(
            permit={"artifact_id": "permit-1"},
            trusted_issuer={"issuer_id": "platform:test"},
        )


def test_runtime_raises_runtimeerror_on_invalid_json_response(tmp_path):
    script = _make_executable(
        tmp_path,
        "stub_invalid_json.py",
        """\
        #!/usr/bin/env python3
        import sys

        sys.stdout.write("not-json")
        """,
    )

    runtime = RacsGoldenPathRuntime(command=[str(script)])

    with pytest.raises(RuntimeError, match=r"^invalid_response:not-json$"):
        runtime.process_permit(
            permit={"artifact_id": "permit-1"},
            trusted_issuer={"issuer_id": "platform:test"},
        )


def test_default_command_builds_once_and_returns_binary(monkeypatch, tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    target_dir = tmp_path / "target"
    binary = target_dir / "debug" / "ai-pls-racs-bridge"
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        binary.parent.mkdir(parents=True, exist_ok=True)
        binary.write_text("binary")

        class Completed:
            returncode = 0
            stderr = b""

        return Completed()

    monkeypatch.setenv("CARGO_TARGET_DIR", str(target_dir))
    monkeypatch.setattr("src.golden_path.subprocess.run", fake_run)

    command = RacsGoldenPathRuntime()._command

    assert command == [str(binary)]
    assert len(calls) == 1
    assert calls[0][0][:2] == ["cargo", "build"]
    assert calls[0][1]["cwd"] == repo_root
