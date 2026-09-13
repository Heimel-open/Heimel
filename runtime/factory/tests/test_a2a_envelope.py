import copy
import importlib.machinery
import importlib.util
import pathlib
import sys
import unittest
from datetime import datetime, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
LOADER = importlib.machinery.SourceFileLoader(
    "valo_a2a_envelope", str(ROOT / "bin" / "valo-a2a-envelope")
)
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
a2a = importlib.util.module_from_spec(SPEC)
sys.modules[LOADER.name] = a2a
LOADER.exec_module(a2a)

D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64
D4 = "4" * 64
D5 = "5" * 64
NOW = datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc)


class GovernedA2AEnvelopeTests(unittest.TestCase):
    def envelope(self):
        value = {
            "contract": a2a.CONTRACT,
            "envelope_id": "a2a-env-1",
            "a2a_version": a2a.A2A_VERSION,
            "extension_uri": a2a.EXTENSION_URI,
            "operation": "SEND_MESSAGE",
            "source": {
                "principal_id": "principal-human-1",
                "agent_id": "agent-procurement",
                "agent_card_digest": D1,
            },
            "target": {
                "agent_id": "agent-supplier",
                "agent_card_url": "https://supplier.example/.well-known/agent-card.json",
                "agent_card_digest": D2,
                "selected_interface": "HTTP+JSON",
                "trust_basis": "SIGNED_AGENT_CARD",
                "signature_verified": True,
                "retrieved_at": "2026-07-27T11:55:00Z",
                "mal_profile_id": "mal-agent-supplier-v1",
            },
            "mandate": {
                "authority_grant_id": "grant-1",
                "delegation_chain_digest": D3,
                "purpose_digest": D4,
                "scope": ["supplier.quote.request"],
                "constraints": {
                    "maximum_quote_count": 3,
                    "data_classification": "INTERNAL",
                },
                "consequence_class": "MEDIUM",
                "reversibility": "REVERSIBLE",
                "issued_at": "2026-07-27T11:50:00Z",
                "expires_at": "2026-07-27T13:50:00Z",
                "max_delegation_depth": 0,
                "redelegation_allowed": False,
                "revocation_registry_ref": "revocations://factory/a2a",
            },
            "payload": {
                "a2a_payload_digest": D5,
                "message_id": "message-1",
                "context_id": "context-1",
                "content_types": ["application/json"],
                "maximum_artifact_bytes": 1048576,
            },
        }
        digest = a2a.compute_action_digest(value)
        value["action_digest"] = digest
        value["governance"] = {
            "vaig": {
                "evaluation_id": "vaig-1",
                "action_digest": digest,
                "status": "PASS",
            },
            "reht": {
                "clearance_id": "reht-1",
                "action_digest": digest,
                "status": "CLEARED",
            },
            "racs": {
                "decision_id": "racs-1",
                "action_digest": digest,
                "decision": "ALLOW",
            },
        }
        return value

    def test_bound_allow_is_transmittable(self):
        result = a2a.validate(self.envelope(), now=NOW)
        self.assertTrue(result["transmittable"])
        self.assertEqual(result["reason"], "RACS_ALLOW")

    def test_agent_card_and_transport_do_not_bypass_reht(self):
        value = self.envelope()
        value["governance"]["reht"]["status"] = "NOT_CLEARED"
        result = a2a.validate(value, now=NOW)
        self.assertFalse(result["transmittable"])

    def test_governance_must_bind_exact_action(self):
        value = self.envelope()
        value["governance"]["racs"]["action_digest"] = "0" * 64
        with self.assertRaises(a2a.EnvelopeError):
            a2a.validate(value, now=NOW)

    def test_action_mutation_is_detected(self):
        value = self.envelope()
        value["payload"]["message_id"] = "message-mutated"
        with self.assertRaises(a2a.EnvelopeError):
            a2a.validate(value, now=NOW)

    def test_signed_agent_card_requires_signature_verification(self):
        value = self.envelope()
        value["target"]["signature_verified"] = False
        with self.assertRaises(a2a.EnvelopeError):
            a2a.validate(value, now=NOW)

    def test_raw_credentials_are_forbidden(self):
        value = self.envelope()
        value["mandate"]["constraints"]["api_key"] = "secret-value"
        with self.assertRaises(a2a.EnvelopeError):
            a2a.validate(value, now=NOW)

    def test_modify_blocks_original_and_requires_new_digest(self):
        value = self.envelope()
        value["governance"]["racs"]["decision"] = "MODIFY"
        value["governance"]["racs"]["replacement_action_digest"] = "f" * 64
        result = a2a.validate(value, now=NOW)
        self.assertFalse(result["transmittable"])
        self.assertEqual(result["reason"], "RACS_MODIFY")

    def test_expired_mandate_is_rejected(self):
        value = self.envelope()
        value["mandate"]["expires_at"] = "2026-07-27T11:59:00Z"
        value["action_digest"] = a2a.compute_action_digest(value)
        for artifact in value["governance"].values():
            artifact["action_digest"] = value["action_digest"]
        with self.assertRaises(a2a.EnvelopeError):
            a2a.validate(value, now=NOW)

    def test_no_redelegation_requires_zero_depth(self):
        value = self.envelope()
        value["mandate"]["max_delegation_depth"] = 1
        value["action_digest"] = a2a.compute_action_digest(value)
        for artifact in value["governance"].values():
            artifact["action_digest"] = value["action_digest"]
        with self.assertRaises(a2a.EnvelopeError):
            a2a.validate(value, now=NOW)


if __name__ == "__main__":
    unittest.main()
