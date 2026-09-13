import importlib.machinery
import importlib.util
import json
import os
import pathlib
import sys
import tempfile
import textwrap
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
LOADER = importlib.machinery.SourceFileLoader(
    "valo_egress_governance_broker", str(ROOT / "bin" / "valo-egress-governance-broker")
)
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
broker = importlib.util.module_from_spec(SPEC)
sys.modules[LOADER.name] = broker
LOADER.exec_module(broker)


class GovernanceBrokerTests(unittest.TestCase):
    def query(self):
        return {
            "contract": broker.QUERY_CONTRACT,
            "request_id": "req-1",
            "mission_id": "mission-1",
            "principal_id": "agent-1",
            "authority_grant_id": "grant-1",
            "request": {
                "method": "POST",
                "url": "https://api.example.test/v1/actions",
                "header_names": ["content-type"],
                "body_sha256": "0" * 64,
                "body_size_bytes": 0,
                "content_type": "application/json",
                "websocket": False,
                "request_digest": "a" * 64,
            },
            "transport": {
                "adapter": "crabtrap",
                "static_rule_decision": "NO_MATCH",
                "judge_decision": "ALLOW",
            },
        }

    def stage_script(self, directory: str, stage: str, output: dict):
        path = pathlib.Path(directory) / f"{stage}.py"
        path.write_text(
            textwrap.dedent(
                f"""
                import json, sys
                payload = json.load(sys.stdin)
                assert payload["contract"] == "valo.governed-egress.stage-query.v1"
                assert payload["stage"] == {stage!r}
                json.dump({output!r}, sys.stdout)
                """
            ),
            encoding="utf-8",
        )
        return f"{sys.executable} {path}"

    def test_broker_runs_stages_in_order_and_returns_bound_artifacts(self):
        digest = "a" * 64
        with tempfile.TemporaryDirectory() as directory:
            env = {
                "VALO_EGRESS_VAIG_COMMAND": self.stage_script(directory, "vaig", {
                    "evaluation_id": "v-1", "request_digest": digest, "status": "PASS"
                }),
                "VALO_EGRESS_REHT_COMMAND": self.stage_script(directory, "reht", {
                    "clearance_id": "r-1", "request_digest": digest, "status": "CLEARED"
                }),
                "VALO_EGRESS_RACS_COMMAND": self.stage_script(directory, "racs", {
                    "decision_id": "d-1", "request_digest": digest, "decision": "ALLOW"
                }),
            }
            with mock.patch.dict(os.environ, env, clear=True):
                result = broker.broker(self.query())
        self.assertEqual(result["governance"]["vaig"]["status"], "PASS")
        self.assertEqual(result["governance"]["reht"]["status"], "CLEARED")
        self.assertEqual(result["governance"]["racs"]["decision"], "ALLOW")

    def test_digest_mismatch_fails_closed(self):
        digest = "a" * 64
        with tempfile.TemporaryDirectory() as directory:
            env = {
                "VALO_EGRESS_VAIG_COMMAND": self.stage_script(directory, "vaig", {
                    "evaluation_id": "v-1", "request_digest": "b" * 64, "status": "PASS"
                }),
                "VALO_EGRESS_REHT_COMMAND": self.stage_script(directory, "reht", {
                    "clearance_id": "r-1", "request_digest": digest, "status": "CLEARED"
                }),
                "VALO_EGRESS_RACS_COMMAND": self.stage_script(directory, "racs", {
                    "decision_id": "d-1", "request_digest": digest, "decision": "ALLOW"
                }),
            }
            with mock.patch.dict(os.environ, env, clear=True):
                with self.assertRaises(broker.BrokerError):
                    broker.broker(self.query())

    def test_missing_stage_command_fails_closed(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(broker.BrokerError):
                broker.broker(self.query())

    def test_modify_requires_distinct_replacement_digest(self):
        digest = "a" * 64
        with tempfile.TemporaryDirectory() as directory:
            env = {
                "VALO_EGRESS_VAIG_COMMAND": self.stage_script(directory, "vaig", {
                    "evaluation_id": "v-1", "request_digest": digest, "status": "PASS"
                }),
                "VALO_EGRESS_REHT_COMMAND": self.stage_script(directory, "reht", {
                    "clearance_id": "r-1", "request_digest": digest, "status": "CLEARED"
                }),
                "VALO_EGRESS_RACS_COMMAND": self.stage_script(directory, "racs", {
                    "decision_id": "d-1", "request_digest": digest, "decision": "MODIFY",
                    "replacement_request_digest": digest
                }),
            }
            with mock.patch.dict(os.environ, env, clear=True):
                with self.assertRaises(broker.BrokerError):
                    broker.broker(self.query())


if __name__ == "__main__":
    unittest.main()
