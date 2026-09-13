import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "bin" / "valo-graft"


def _fake_graft(directory: str) -> Path:
    path = Path(directory) / "graft"
    path.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, pathlib, sys\n"
        "marker = os.environ.get('FAKE_GRAFT_MARKER')\n"
        "payload = {\n"
        "  'argv': sys.argv[1:],\n"
        "  'cwd': os.getcwd(),\n"
        "  'home': os.environ.get('HOME'),\n"
        "  'graft_api_key': bool(os.environ.get('GRAFT_API_KEY')),\n"
        "  'graft_base_url': os.environ.get('GRAFT_BASE_URL'),\n"
        "  'graft_provider': os.environ.get('GRAFT_PROVIDER'),\n"
        "  'openai_api_key': bool(os.environ.get('OPENAI_API_KEY')),\n"
        "  'anthropic_api_key': bool(os.environ.get('ANTHROPIC_API_KEY')),\n"
        "  'openrouter_api_key': bool(os.environ.get('OPENROUTER_API_KEY')),\n"
        "}\n"
        "if marker:\n"
        "  pathlib.Path(marker).write_text(json.dumps(payload), encoding='utf-8')\n"
        "print(json.dumps(payload))\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _repo(directory: str, *, ignored: bool = True) -> Path:
    repo = Path(directory) / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / ".gitignore").write_text("graft/\n" if ignored else "__pycache__/\n", encoding="utf-8")
    return repo


def _run(repo: Path, fake: Path, *args: str, extra_env=None):
    env = os.environ.copy()
    env["VALO_GRAFT_BIN"] = str(fake)
    env["OPENAI_API_KEY"] = "ambient-openai"
    env["ANTHROPIC_API_KEY"] = "ambient-anthropic"
    env["OPENROUTER_API_KEY"] = "ambient-openrouter"
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, str(WRAPPER), "--repo", str(repo), *args],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


class ValoGraftTests(unittest.TestCase):
    def test_structural_build_runs_isolated_and_strips_model_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = _repo(tmp)
            fake = _fake_graft(tmp)
            proc = _run(repo, fake, "build")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["argv"], ["build"])
        self.assertEqual(payload["cwd"], str(repo))
        self.assertIn("valo-graft-home-", payload["home"])
        self.assertFalse(payload["graft_api_key"])
        self.assertIsNone(payload["graft_base_url"])
        self.assertIsNone(payload["graft_provider"])
        self.assertFalse(payload["openai_api_key"])
        self.assertFalse(payload["anthropic_api_key"])
        self.assertFalse(payload["openrouter_api_key"])

    def test_machine_global_and_server_commands_are_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = _repo(tmp)
            fake = _fake_graft(tmp)
            for command in ("init", "upgrade", "mcp", "viz", "version", "_update-check"):
                with self.subTest(command=command):
                    proc = _run(repo, fake, command)
                    self.assertEqual(proc.returncode, 2)
                    self.assertIn("outside the governed context boundary", proc.stderr)

    def test_missing_preignored_graft_cache_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = _repo(tmp, ignored=False)
            fake = _fake_graft(tmp)
            proc = _run(repo, fake, "build")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("refusing to let upstream mutate .gitignore", proc.stderr)

    def test_deep_build_requires_explicit_llm_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = _repo(tmp)
            fake = _fake_graft(tmp)
            proc = _run(
                repo,
                fake,
                "build",
                "--deep",
                extra_env={
                    "GRAFT_BASE_URL": "http://127.0.0.1:4000/v1",
                    "GRAFT_API_KEY": "private-key",
                },
            )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("VALO_GRAFT_ALLOW_LLM=1", proc.stderr)

    def test_public_llm_endpoint_is_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = _repo(tmp)
            fake = _fake_graft(tmp)
            proc = _run(
                repo,
                fake,
                "ask",
                "where is auth",
                extra_env={
                    "VALO_GRAFT_ALLOW_LLM": "1",
                    "GRAFT_BASE_URL": "https://api.example.com/v1",
                    "GRAFT_API_KEY": "private-key",
                },
            )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("private-network", proc.stderr)

    def test_private_llm_endpoint_is_allowed_and_ambient_keys_stay_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = _repo(tmp)
            fake = _fake_graft(tmp)
            proc = _run(
                repo,
                fake,
                "ask",
                "where is auth",
                extra_env={
                    "VALO_GRAFT_ALLOW_LLM": "1",
                    "GRAFT_BASE_URL": "http://127.0.0.1:4000/v1",
                    "GRAFT_API_KEY": "private-key",
                },
            )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["argv"], ["ask", "where is auth"])
        self.assertTrue(payload["graft_api_key"])
        self.assertEqual(payload["graft_base_url"], "http://127.0.0.1:4000/v1")
        self.assertEqual(payload["graft_provider"], "openai")
        self.assertFalse(payload["openai_api_key"])
        self.assertFalse(payload["anthropic_api_key"])
        self.assertFalse(payload["openrouter_api_key"])

    def test_cli_secrets_and_endpoints_are_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = _repo(tmp)
            fake = _fake_graft(tmp)
            for option in ("--api-key=secret", "--base-url=http://127.0.0.1:4000/v1"):
                with self.subTest(option=option):
                    proc = _run(repo, fake, "build", option)
                    self.assertEqual(proc.returncode, 2)
                    self.assertIn("forbidden on the command line", proc.stderr)

    def test_dry_run_validates_without_executing_upstream(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = _repo(tmp)
            fake = _fake_graft(tmp)
            marker = Path(tmp) / "ran.json"
            proc = _run(
                repo,
                fake,
                "--dry-run",
                "map",
                extra_env={"FAKE_GRAFT_MARKER": str(marker)},
            )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"][1:], ["map"])
        self.assertFalse(marker.exists())

    def test_multi_repo_workspace_requires_each_child_to_preignore_graft(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            for name, ignored in (("a", True), ("b", False)):
                child = workspace / name
                child.mkdir()
                (child / ".git").mkdir()
                (child / ".gitignore").write_text("graft/\n" if ignored else "*.pyc\n", encoding="utf-8")
            fake = _fake_graft(tmp)
            proc = _run(workspace, fake, "build")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(str(workspace / "b" / ".gitignore"), proc.stderr)


if __name__ == "__main__":
    unittest.main()
