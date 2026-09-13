import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".claude" / "hooks" / "authorize-tool.py"


def _event(tool_name="Write", tool_input=None):
    return {
        "session_id": "test-session",
        "cwd": str(ROOT),
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": tool_input or {"file_path": "/tmp/x", "content": "x"},
        "tool_use_id": "tool-test",
    }


def _run(event, *, gate=None):
    env = os.environ.copy()
    if gate is None:
        env.pop("VALO_REHT_PRETOOL_GATE", None)
    else:
        env["VALO_REHT_PRETOOL_GATE"] = str(gate)
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(event),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(proc.stderr)
    return json.loads(proc.stdout)


def _gate(directory, payload, *, returncode=0):
    path = Path(directory) / "gate.py"
    script = (
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        "json.load(sys.stdin)\n"
        f"print({json.dumps(json.dumps(payload))})\n"
        f"raise SystemExit({returncode})\n"
    )
    path.write_text(script, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _permission(result):
    return result["hookSpecificOutput"]["permissionDecision"]


class ClaudeCodeAdapterTests(unittest.TestCase):
    def test_missing_gate_fails_closed(self):
        result = _run(_event())
        self.assertEqual(_permission(result), "deny")
        self.assertIn(
            "not configured",
            result["hookSpecificOutput"]["permissionDecisionReason"],
        )

    def test_explicit_external_allow_is_relayed(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = _gate(
                tmp,
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "allow",
                        "permissionDecisionReason": "reht permits exact effect",
                    }
                },
            )
            result = _run(_event("Bash", {"command": "python3 -m unittest"}), gate=gate)
        self.assertEqual(_permission(result), "allow")
        self.assertEqual(
            result["hookSpecificOutput"]["permissionDecisionReason"],
            "reht permits exact effect",
        )

    def test_external_deny_is_relayed(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = _gate(
                tmp,
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": "outside current mandate",
                    }
                },
            )
            result = _run(_event(), gate=gate)
        self.assertEqual(_permission(result), "deny")

    def test_non_final_or_invalid_gate_decision_fails_closed(self):
        for decision in ("ask", "defer", "ALLOW", None):
            with self.subTest(decision=decision), tempfile.TemporaryDirectory() as tmp:
                gate = _gate(
                    tmp,
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "permissionDecision": decision,
                        }
                    },
                )
                result = _run(_event(), gate=gate)
                self.assertEqual(_permission(result), "deny")
                self.assertIn(
                    "final allow/deny",
                    result["hookSpecificOutput"]["permissionDecisionReason"],
                )

    def test_gate_cannot_rewrite_authorized_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = _gate(
                tmp,
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "allow",
                        "permissionDecisionReason": "allowed",
                        "updatedInput": {
                            "file_path": "/different",
                            "content": "changed",
                        },
                    }
                },
            )
            result = _run(_event(), gate=gate)
        self.assertEqual(_permission(result), "allow")
        self.assertNotIn("updatedInput", result["hookSpecificOutput"])

    def test_gate_failure_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = _gate(
                tmp,
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "allow",
                    }
                },
                returncode=9,
            )
            result = _run(_event(), gate=gate)
        self.assertEqual(_permission(result), "deny")
        self.assertIn(
            "external gate failed",
            result["hookSpecificOutput"]["permissionDecisionReason"],
        )


if __name__ == "__main__":
    unittest.main()
