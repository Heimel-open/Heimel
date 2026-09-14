from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "heimel_preflight.py"
spec = importlib.util.spec_from_file_location("heimel_preflight", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_missing_profile_fails_closed(capsys):
    assert module.main(["--runtime-id", "test-runtime"]) == 2
    payload = json.loads(capsys.readouterr().err)
    assert payload["ok"] is False
    assert "profile" in payload["error"]


def test_missing_gateway_fails_closed(tmp_path, monkeypatch, capsys):
    profile = tmp_path / "profile.json"
    profile.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(module.shutil, "which", lambda _: None)

    assert module.main(["--profile", str(profile), "--runtime-id", "test-runtime"]) == 2
    payload = json.loads(capsys.readouterr().err)
    assert payload["ok"] is False
    assert "consequence execution must remain blocked" in payload["error"]


def test_success_never_claims_effect_authorized(tmp_path, monkeypatch, capsys):
    profile = tmp_path / "profile.json"
    profile.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(module.shutil, "which", lambda _: "/usr/bin/valo-gateway")

    responses = iter(
        [
            {"valid": True, "profile_id": "p1", "profile_digest": "abc", "authorization_boundary": "REHT"},
            {"profile_id": "p1", "runtime_id": "test-runtime"},
            {"session_id": "s1", "runtime_id": "test-runtime"},
        ]
    )
    monkeypatch.setattr(module, "_run_json", lambda command: next(responses))

    assert module.main(["--profile", str(profile), "--runtime-id", "test-runtime"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["effect_authorized"] is False
    assert payload["effect_executed"] is False
    assert payload["authorization_boundary"] == "REHT"
