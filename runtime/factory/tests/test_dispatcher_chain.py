import importlib.machinery
import importlib.util
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).parent.parent / "bin" / "valo-orchestrator"
SPEC = importlib.util.spec_from_file_location(
    "valo_orchestrator",
    MODULE_PATH,
    loader=importlib.machinery.SourceFileLoader(
        "valo_orchestrator", str(MODULE_PATH)
    ),
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

REPO = "nsolland/valo-platform"


class FakeResp:
    def __init__(self, rc=0, out="", err=""):
        self.returncode = rc
        self.stdout = out
        self.stderr = err


class DispatcherChainTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.worktree = self.root / "run" / "valo-platform"
        self.worktree.mkdir(parents=True)
        self.primary = self.root / "primary"
        self.primary.mkdir()
        self.receipts = self.root / "receipts" / "factory.jsonl"
        self.db = self.root / "orchestrator.db"
        self.calls = []
        self.qc_decision = "MERGE_READY"
        self.qc_rc = 0
        self.risk_class = "A"
        self.merge_payload = {"merged": True}
        self.merge_rc = 0
        self.claim_rc = 0
        self.mode = True
        self.worker_rc = 0
        self.worker_pushed = False
        self.rev_count = 0
        self.worker_changes_head = False

    def tearDown(self):
        self.temp.cleanup()

    def fake_run(self, cmd, *args, **kwargs):
        self.calls.append({"cmd": list(cmd), "kwargs": dict(kwargs)})

        if cmd[:2] == ["valo-claim", "expire"]:
            return FakeResp(0, json.dumps({"expired": 0}))
        if cmd[:2] == ["valo-claim", "claim"]:
            return FakeResp(self.claim_rc, json.dumps({"ok": self.claim_rc == 0}))
        if cmd[:2] == ["valo-claim", "release"]:
            return FakeResp(0, json.dumps({"released": True}))

        if cmd[:3] == ["gh", "issue", "list"]:
            return FakeResp(0, json.dumps([
                {"number": 1377, "title": "Build it", "labels": []}
            ]))
        if cmd[:3] == ["gh", "issue", "view"]:
            return FakeResp(0, json.dumps({
                "title": "Build it",
                "body": "Implement the governed change.",
            }))
        if cmd[:3] == ["gh", "pr", "create"]:
            return FakeResp(0, f"https://github.com/{REPO}/pull/200\n")
        if cmd[:3] == ["gh", "pr", "view"]:
            return FakeResp(0, "b" * 40)
        if cmd[:3] == ["gh", "repo", "view"]:
            return FakeResp(0, "a" * 40)

        if cmd and cmd[0] == "valo-run":
            return FakeResp(0, json.dumps({
                "run_id": "run-abc123",
                "worktree": str(self.worktree),
                "branch": "orch-1377-abc123",
            }))
        if cmd and cmd[0] == "valo-agent-provider":
            if self.worker_rc == 0:
                target = self.worktree / "src" / "delivery.py"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("VALUE = 1\n", encoding="utf-8")
            receipt = {
                "provider_id": "openai_codex",
                "returncode": self.worker_rc,
                "authority_effect": "none",
            }
            return FakeResp(
                self.worker_rc,
                "",
                "VALO_PROVIDER_RECEIPT " + json.dumps(receipt),
            )
        if cmd and cmd[0] == "valo-classify":
            return FakeResp(0, self.risk_class)
        if cmd and cmd[0] == "valo-qc":
            return FakeResp(self.qc_rc, json.dumps({
                "decision": self.qc_decision,
                "head_sha": "b" * 40,
                "ports": {"security_matrix": "PASS"},
            }))
        if cmd and cmd[0] == "valo-merge":
            return FakeResp(self.merge_rc, json.dumps(self.merge_payload))

        if cmd and cmd[0] == "git":
            if "rev-parse" in cmd:
                self.rev_count += 1
                if self.worker_changes_head and self.rev_count > 1:
                    return FakeResp(0, "c" * 40)
                return FakeResp(0, "a" * 40)
            if "status" in cmd and "--porcelain" in cmd:
                return FakeResp(0, "?? src/delivery.py\n")
            if "ls-remote" in cmd:
                if self.worker_pushed:
                    return FakeResp(
                        0, "d" * 40 + "\trefs/heads/orch-1377-abc123\n"
                    )
                return FakeResp(2, "")
            if "diff" in cmd and "--cached" in cmd and "--quiet" in cmd:
                return FakeResp(1, "")
            return FakeResp(0, "")

        return FakeResp(0, "")

    def run_tick(self):
        with patch.object(mod, "VALO", str(self.primary)), patch.object(
            mod, "RECEIPTS", str(self.receipts)
        ), patch.object(mod, "DB", str(self.db)), patch.object(
            mod, "mode_check", side_effect=lambda: self.mode
        ), patch.object(
            mod.subprocess, "run", side_effect=self.fake_run
        ):
            return mod.cmd_tick(types.SimpleNamespace())

    def commands(self, name):
        return [call for call in self.calls if call["cmd"][0] == name]

    def test_happy_path_runs_provider_then_qc_merge_and_cleanup(self):
        self.assertEqual(self.run_tick(), 0)
        worker = self.commands("valo-agent-provider")[0]["cmd"]
        self.assertEqual(worker[:3], [
            "valo-agent-provider", "run", "openai_codex"
        ])
        self.assertIn("--cwd", worker)
        self.assertIn(str(self.worktree), worker)
        self.assertIn("--prompt-file", worker)

        run_cmd = self.commands("valo-run")[0]["cmd"]
        self.assertIn("origin/main", run_cmd)

        pr_call = next(
            call for call in self.commands("gh")
            if call["cmd"][:3] == ["gh", "pr", "create"]
        )
        self.assertIn("--head", pr_call["cmd"])
        self.assertIn("orch-1377-abc123", pr_call["cmd"])
        self.assertIn("--base", pr_call["cmd"])
        self.assertIn("main", pr_call["cmd"])

        receipts = [
            json.loads(line)
            for line in self.receipts.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(
            [receipt["outcome"] for receipt in receipts],
            ["READY_TO_MERGE", "MERGED"],
        )
        self.assertEqual(
            receipts[-1]["worker"]["provider_id"], "openai_codex"
        )
        self.assertTrue(receipts[-1]["receipt_sha256"])

        import sqlite3
        conn = sqlite3.connect(self.db)
        state = conn.execute(
            "select state from runs where run_id='run-abc123'"
        ).fetchone()[0]
        conn.close()
        self.assertEqual(state, "MERGED")

        self.assertTrue(any(
            call["cmd"][:2] == ["valo-claim", "release"]
            for call in self.calls
        ))
        self.assertTrue(any(
            call["cmd"][:5] == [
                "git", "-C", str(self.primary), "worktree", "remove"
            ]
            for call in self.calls
        ))

    def test_mode_gate_prevents_dispatch(self):
        self.mode = False
        self.assertEqual(self.run_tick(), 0)
        self.assertEqual(self.calls, [])
        self.assertFalse(self.receipts.exists())

    def test_claim_failure_stops_before_worker(self):
        self.claim_rc = 2
        self.assertEqual(self.run_tick(), 0)
        self.assertEqual(self.commands("valo-agent-provider"), [])
        self.assertEqual(self.commands("valo-qc"), [])

    def test_worker_failure_fails_closed_and_releases_claim(self):
        self.worker_rc = 4
        self.assertEqual(self.run_tick(), 1)
        self.assertFalse(any(
            call["cmd"][:3] == ["gh", "pr", "create"]
            for call in self.calls
        ))
        receipt = json.loads(
            self.receipts.read_text(encoding="utf-8").splitlines()[-1]
        )
        self.assertEqual(receipt["outcome"], "FAILED")
        self.assertTrue(any(
            call["cmd"][:2] == ["valo-claim", "release"]
            for call in self.calls
        ))

    def test_worker_commit_is_rejected(self):
        self.worker_changes_head = True
        self.assertEqual(self.run_tick(), 1)
        self.assertFalse(any(
            call["cmd"][:3] == ["gh", "pr", "create"]
            for call in self.calls
        ))

    def test_worker_remote_push_is_rejected(self):
        self.worker_pushed = True
        self.assertEqual(self.run_tick(), 1)
        self.assertFalse(any(
            call["cmd"][:3] == ["gh", "pr", "create"]
            for call in self.calls
        ))

    def test_blocked_qc_routes_to_human_without_merge(self):
        self.qc_decision = "BLOCKED"
        self.qc_rc = 1
        self.risk_class = "B"
        self.assertEqual(self.run_tick(), 0)
        self.assertEqual(self.commands("valo-merge"), [])
        receipt = json.loads(
            self.receipts.read_text(encoding="utf-8").splitlines()[-1]
        )
        self.assertEqual(receipt["outcome"], "NEEDS_HUMAN")

    def test_class_c_never_auto_merges(self):
        self.qc_decision = "MERGE_READY"
        self.risk_class = "C"
        self.assertEqual(self.run_tick(), 0)
        self.assertEqual(self.commands("valo-merge"), [])
        receipt = json.loads(
            self.receipts.read_text(encoding="utf-8").splitlines()[-1]
        )
        self.assertEqual(receipt["outcome"], "NEEDS_HUMAN")

    def test_merge_requires_json_merged_true(self):
        self.merge_payload = {"merged": False, "message": "not merged"}
        self.assertEqual(self.run_tick(), 1)
        receipts = [
            json.loads(line)
            for line in self.receipts.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(receipts[-1]["outcome"], "FAILED")


if __name__ == "__main__":
    unittest.main()
