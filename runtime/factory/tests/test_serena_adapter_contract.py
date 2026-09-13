import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "bin" / "valo-serena"
POLICY = ROOT / "config" / "serena_adapter.json"


def _fake_serena(directory: str, *, echo_env: bool = False) -> Path:
    path = Path(directory) / "serena"
    if echo_env:
        path.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os\n"
            "print(json.dumps({\n"
            "  'GITHUB_TOKEN': os.getenv('GITHUB_TOKEN'),\n"
            "  'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),\n"
            "  'VALO_SANDBOX_ATTESTED': os.getenv('VALO_SANDBOX_ATTESTED'),\n"
            "  'SERENA_HOME': os.getenv('SERENA_HOME'),\n"
            "}))\n",
            encoding="utf-8",
        )
    else:
        path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def _env(workspace: Path, binary: Path, **overrides):
    env = os.environ.copy()
    env.update({
        "VALO_WORKSPACE_ROOT": str(workspace),
        "VALO_SANDBOX_ATTESTED": "1",
        "VALO_SERENA_BIN": str(binary),
    })
    for key, value in overrides.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    return env


def _run(project: Path, workspace: Path, binary: Path, **overrides):
    return subprocess.run(
        [sys.executable, str(WRAPPER), "--project", str(project), "--dry-run"],
        text=True,
        capture_output=True,
        env=_env(workspace, binary, **overrides),
        check=False,
    )


class SerenaAdapterContractTests(unittest.TestCase):
    def test_policy_is_replaceable_non_authoritative_adapter(self):
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertEqual(policy["schema"], "valo.serena-semantic-adapter.v1")
        self.assertEqual(policy["role"], "replaceable_semantic_code_intelligence")
        self.assertFalse(policy["memory"]["enabled"])
        self.assertFalse(policy["memory"]["authoritative"])
        self.assertTrue(policy["execution"]["no_direct_effect_path"])
        self.assertTrue(policy["sandbox"]["required"])

    def test_dry_run_pins_safe_mcp_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            project = workspace / "repo"
            project.mkdir(parents=True)
            binary = _fake_serena(tmp)
            proc = _run(project, workspace, binary)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        command = payload["command"]
        self.assertIn("start-mcp-server", command)
        self.assertEqual(command[command.index("--transport") + 1], "stdio")
        self.assertEqual(command[command.index("--context") + 1], "ide")
        self.assertEqual(command[command.index("--open-web-dashboard") + 1], "false")
        self.assertIn("no-memories", command)
        self.assertTrue(payload["sandbox_attested"])
        self.assertEqual(payload["memory"], "disabled")

    def test_child_process_has_no_ambient_provider_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            project = workspace / "repo"
            project.mkdir(parents=True)
            binary = _fake_serena(tmp, echo_env=True)
            proc = subprocess.run(
                [sys.executable, str(WRAPPER), "--project", str(project)],
                text=True,
                capture_output=True,
                env=_env(
                    workspace,
                    binary,
                    GITHUB_TOKEN="host-secret",
                    OPENAI_API_KEY="host-secret",
                ),
                check=False,
            )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertIsNone(payload["GITHUB_TOKEN"])
        self.assertIsNone(payload["OPENAI_API_KEY"])
        self.assertEqual(payload["VALO_SANDBOX_ATTESTED"], "1")
        self.assertTrue(payload["SERENA_HOME"])

    def test_missing_sandbox_attestation_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            project = workspace / "repo"
            project.mkdir(parents=True)
            binary = _fake_serena(tmp)
            proc = _run(project, workspace, binary, VALO_SANDBOX_ATTESTED=None)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("sandbox attestation", proc.stderr)

    def test_project_outside_workspace_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            project = Path(tmp) / "outside"
            project.mkdir()
            binary = _fake_serena(tmp)
            proc = _run(project, workspace, binary)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("inside VALO_WORKSPACE_ROOT", proc.stderr)

    def test_missing_workspace_root_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "repo"
            project.mkdir()
            binary = _fake_serena(tmp)
            env = os.environ.copy()
            env.pop("VALO_WORKSPACE_ROOT", None)
            env["VALO_SANDBOX_ATTESTED"] = "1"
            env["VALO_SERENA_BIN"] = str(binary)
            proc = subprocess.run(
                [sys.executable, str(WRAPPER), "--project", str(project), "--dry-run"],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("VALO_WORKSPACE_ROOT is required", proc.stderr)


if __name__ == "__main__":
    unittest.main()
