import hashlib
import importlib.machinery
import importlib.util
import os
import pathlib
import sys
import tempfile
import textwrap
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
LOADER = importlib.machinery.SourceFileLoader(
    "valo_egress_gate", str(ROOT / "bin" / "valo-egress-gate")
)
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
gate = importlib.util.module_from_spec(SPEC)
sys.modules[LOADER.name] = gate
LOADER.exec_module(gate)


EMPTY_BODY_SHA256 = hashlib.sha256(b"").hexdigest()


class GovernedEgressTests(unittest.TestCase):
    def request(self):
        metadata = {
            "method": "POST",
            "url": "https://api.example.test/v1/actions",
            "header_names": ["Content-Type", "Authorization"],
            "body_sha256": EMPTY_BODY_SHA256,
            "body_size_bytes": 0,
            "content_type": "application/json",
            "websocket": False,
        }
        digest = gate.request_digest(metadata)
        return {
            "contract": gate.REQUEST_CONTRACT,
            "request_id": "req-1",
            "mission_id": "mission-1",
            "principal_id": "agent-1",
            "authority_grant_id": "grant-1",
            "request": {**metadata, "request_digest": digest},
            "transport": {
                "adapter": "crabtrap",
                "static_rule_decision": "NO_MATCH",
                "judge_decision": "ALLOW",
            },
            "governance": {
                "vaig": {
                    "evaluation_id": "vaig-1",
                    "request_digest": digest,
                    "status": "PASS",
                },
                "reht": {
                    "clearance_id": "reht-1",
                    "request_digest": digest,
                    "status": "CLEARED",
                },
                "racs": {
                    "decision_id": "racs-1",
                    "request_digest": digest,
                    "decision": "ALLOW",
                },
            },
        }

    def authorize_request(self):
        payload = self.request()
        payload["contract"] = gate.AUTHORIZE_CONTRACT
        payload.pop("governance")
        return payload

    def test_racs_allow_with_bound_artifacts_allows(self):
        result = gate.evaluate(self.request())
        self.assertEqual(result["decision"], "ALLOW")
        self.assertEqual(result["reason_code"], "RACS_ALLOW")
        self.assertNotIn("headers", result)
        self.assertNotIn("body", result)

    def test_transport_allow_and_judge_allow_cannot_bypass_reht(self):
        payload = self.request()
        payload["transport"]["static_rule_decision"] = "ALLOW"
        payload["governance"]["reht"]["status"] = "NOT_CLEARED"
        result = gate.evaluate(payload)
        self.assertEqual(result["decision"], "DENY")
        self.assertEqual(result["reason_code"], "REHT_NOT_CLEARED")

    def test_static_deny_blocks_before_governance_artifacts(self):
        payload = self.request()
        payload["transport"]["static_rule_decision"] = "DENY"
        payload["governance"] = {}
        result = gate.evaluate(payload)
        self.assertEqual(result["decision"], "DENY")
        self.assertEqual(result["reason_code"], "TRANSPORT_STATIC_DENY")

    def test_crabtrap_judge_is_advisory_only(self):
        payload = self.request()
        payload["transport"]["judge_decision"] = "DENY"
        result = gate.evaluate(payload)
        self.assertEqual(result["decision"], "ALLOW")
        self.assertEqual(result["transport_advisory"]["judge_decision"], "DENY")

    def test_request_binding_mismatch_is_rejected(self):
        payload = self.request()
        payload["governance"]["racs"]["request_digest"] = "0" * 64
        with self.assertRaises(gate.ProtocolError):
            gate.evaluate(payload)

    def test_vaig_fail_blocks_forwarding(self):
        payload = self.request()
        payload["governance"]["vaig"]["status"] = "FAIL"
        result = gate.evaluate(payload)
        self.assertEqual(result["decision"], "DENY")
        self.assertEqual(result["reason_code"], "VAIG_FAIL")

    def test_step_up_blocks_forwarding(self):
        payload = self.request()
        payload["governance"]["racs"]["decision"] = "STEP_UP"
        result = gate.evaluate(payload)
        self.assertEqual(result["decision"], "DENY")
        self.assertEqual(result["reason_code"], "RACS_STEP_UP")

    def test_modify_requires_new_digest(self):
        payload = self.request()
        payload["governance"]["racs"]["decision"] = "MODIFY"
        payload["governance"]["racs"]["replacement_request_digest"] = "f" * 64
        result = gate.evaluate(payload)
        self.assertEqual(result["decision"], "MODIFY")
        self.assertEqual(result["replacement_request_digest"], "f" * 64)

    def test_websocket_is_denied_in_v1(self):
        payload = self.request()
        payload["request"]["websocket"] = True
        payload["request"]["request_digest"] = gate.request_digest(payload["request"])
        result = gate.evaluate(payload)
        self.assertEqual(result["decision"], "DENY")
        self.assertEqual(result["reason_code"], "WEBSOCKET_FRAMES_UNGOVERNED")

    def test_url_credentials_are_rejected(self):
        payload = self.request()
        payload["request"]["url"] = "https://user@example.test/"
        with self.assertRaises(gate.ProtocolError):
            gate.evaluate(payload)

    def test_authorize_invokes_broker_with_metadata_not_body(self):
        script = textwrap.dedent(
            """
            import json, sys
            query = json.load(sys.stdin)
            assert query["contract"] == "valo.governed-egress.governance-query.v1"
            assert "body" not in query["request"]
            digest = query["request"]["request_digest"]
            json.dump({"governance": {
                "vaig": {"evaluation_id": "v", "request_digest": digest, "status": "PASS"},
                "reht": {"clearance_id": "r", "request_digest": digest, "status": "CLEARED"},
                "racs": {"decision_id": "d", "request_digest": digest, "decision": "ALLOW"}
            }}, sys.stdout)
            """
        )
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "broker.py"
            path.write_text(script, encoding="utf-8")
            env = {"VALO_EGRESS_GOVERNANCE_COMMAND": f"{sys.executable} {path}"}
            with mock.patch.dict(os.environ, env, clear=False):
                result = gate.authorize(self.authorize_request())
        self.assertEqual(result["decision"], "ALLOW")
        self.assertEqual(result["reason_code"], "RACS_ALLOW")

    def test_authorize_fails_closed_without_broker(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(gate.GovernanceUnavailable):
                gate.authorize(self.authorize_request())

    def test_authorize_static_deny_does_not_need_broker(self):
        payload = self.authorize_request()
        payload["transport"]["static_rule_decision"] = "DENY"
        with mock.patch.dict(os.environ, {}, clear=True):
            result = gate.authorize(payload)
        self.assertEqual(result["decision"], "DENY")
        self.assertEqual(result["reason_code"], "TRANSPORT_STATIC_DENY")


if __name__ == "__main__":
    unittest.main()
