from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "heimel_search.py"
spec = importlib.util.spec_from_file_location("heimel_search", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def completed(command, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(command, returncode, stdout, stderr)


def test_precise_fixed_string_prefers_tgrep(monkeypatch, tmp_path):
    commands = []

    monkeypatch.setattr(module.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(module, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(module, "_index_path", lambda root: tmp_path / "index")
    monkeypatch.setattr(module, "_ensure_index", lambda root, index: True)
    monkeypatch.setattr(module, "_server_ready", lambda root, index: True)

    def fake_run(command, capture=False):
        commands.append(command)
        return completed(command, 0)

    monkeypatch.setattr(module, "_run", fake_run)

    assert module.search("NO_DIRECT_EFFECT_PATH") == 0
    assert commands == [
        ["tgrep", "-F", "--index-path", str(tmp_path / "index"), "--", "NO_DIRECT_EFFECT_PATH", "."]
    ]


def test_broad_query_routes_directly_to_rg(monkeypatch):
    commands = []
    monkeypatch.setattr(module.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(
        module,
        "_run",
        lambda command, capture=False: commands.append(command) or completed(command, 0),
    )

    assert module.search("evidence", broad=True) == 0
    assert commands == [["rg", "--no-heading", "--color", "never", "-F", "evidence", "."]]


def test_regex_routes_to_rg_without_fixed_string(monkeypatch):
    commands = []
    monkeypatch.setattr(module.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(
        module,
        "_run",
        lambda command, capture=False: commands.append(command) or completed(command, 0),
    )

    assert module.search(r"permit_[0-9]+", regex=True) == 0
    assert commands == [["rg", "--no-heading", "--color", "never", r"permit_[0-9]+", "."]]


def test_filtered_search_routes_to_rg_and_preserves_options(monkeypatch):
    commands = []
    monkeypatch.setattr(module.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(
        module,
        "_run",
        lambda command, capture=False: commands.append(command) or completed(command, 0),
    )

    assert module.search(
        "REHT",
        "runtime",
        hidden=True,
        globs=("*.py",),
        rg_args=("--ignore-case",),
    ) == 0
    assert commands == [[
        "rg",
        "--no-heading",
        "--color",
        "never",
        "-F",
        "--hidden",
        "--glob",
        "*.py",
        "--ignore-case",
        "REHT",
        "runtime",
    ]]


def test_missing_tgrep_falls_back_to_rg(monkeypatch):
    commands = []

    def which(name):
        return "/usr/bin/rg" if name == "rg" else None

    monkeypatch.setattr(module.shutil, "which", which)
    monkeypatch.setattr(
        module,
        "_run",
        lambda command, capture=False: commands.append(command) or completed(command, 0),
    )

    assert module.search("Veritas") == 0
    assert commands == [["rg", "--no-heading", "--color", "never", "-F", "Veritas", "."]]


def test_tgrep_execution_error_falls_back_to_rg(monkeypatch, tmp_path):
    commands = []
    monkeypatch.setattr(module.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(module, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(module, "_index_path", lambda root: tmp_path / "index")
    monkeypatch.setattr(module, "_ensure_index", lambda root, index: True)
    monkeypatch.setattr(module, "_server_ready", lambda root, index: True)

    def fake_run(command, capture=False):
        commands.append(command)
        return completed(command, 2 if command[0] == "tgrep" else 0)

    monkeypatch.setattr(module, "_run", fake_run)

    assert module.search("REHT") == 0
    assert commands[0][0] == "tgrep"
    assert commands[1] == ["rg", "--no-heading", "--color", "never", "-F", "REHT", "."]


def test_tgrep_no_match_is_not_treated_as_failure(monkeypatch, tmp_path):
    commands = []
    monkeypatch.setattr(module.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(module, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(module, "_index_path", lambda root: tmp_path / "index")
    monkeypatch.setattr(module, "_ensure_index", lambda root, index: True)
    monkeypatch.setattr(module, "_server_ready", lambda root, index: True)

    def fake_run(command, capture=False):
        commands.append(command)
        return completed(command, 1)

    monkeypatch.setattr(module, "_run", fake_run)

    assert module.search("definitely-not-present") == 1
    assert len(commands) == 1
    assert commands[0][0] == "tgrep"


def test_missing_rg_fails_explicitly(monkeypatch, capsys):
    monkeypatch.setattr(module.shutil, "which", lambda name: None)
    assert module.search("REHT") == 127
    assert "ripgrep" in capsys.readouterr().err


def test_backend_policy_only_uses_tgrep_for_plain_precise_searches():
    assert module.should_use_tgrep(
        broad=False,
        regex=False,
        force_rg=False,
        hidden=False,
        globs=(),
        rg_args=(),
    )
    assert not module.should_use_tgrep(
        broad=True,
        regex=False,
        force_rg=False,
        hidden=False,
        globs=(),
        rg_args=(),
    )
    assert not module.should_use_tgrep(
        broad=False,
        regex=False,
        force_rg=False,
        hidden=False,
        globs=("*.py",),
        rg_args=(),
    )
