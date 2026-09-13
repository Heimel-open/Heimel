from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

from edge_substrate import (  # noqa: E402
    ACTUATE,
    ADMISSIBLE,
    ADMISSIBLE_TO_EGRESS_GATE,
    ADMISSIBLE_TO_REHT,
    NETWORK_EGRESS,
    OBSERVE,
    REFUSED,
    EdgeSubstrateError,
    assess_edge_substrate,
    manifest_from_dict,
    request_from_dict,
)


def valid_manifest(**overrides):
    data = {
        "runtime_id": "edge-rp2040-01",
        "runtime_family": "micropython",
        "board_family": "rp2040",
        "firmware_version": "1.20.0",
        "owner_id": "factory-edge",
        "device_identity": "device:edge-rp2040-01",
        "capabilities": [
            "gpio", "i2c", "spi", "json", "hashlib", "network", "tls",
            "cloud-egress", "actuate",
        ],
        "access_scopes": ["sensor:temperature", "actuator:relay"],
        "data_scopes": ["telemetry:temperature"],
        "verification_refs": ["test://edge-rp2040-01/preflight"],
        "network_validated": True,
        "tls_available": True,
        "audit_ref": "veritas://edge-rp2040-01",
        "authority_effect": "none",
    }
    data.update(overrides)
    return manifest_from_dict(data)


def request(action=OBSERVE, **overrides):
    data = {
        "action": action,
        "purpose": "edge admission test",
        "required_capabilities": [],
        "requested_access_scopes": [],
        "requested_data_scopes": [],
        "sensitive_data": False,
        "cloud_required": False,
        "evidence_refs": [],
    }
    data.update(overrides)
    return request_from_dict(data)


class EdgeSubstrateTests(unittest.TestCase):
    def test_observation_is_admissible_but_non_authorizing(self):
        decision = assess_edge_substrate(
            valid_manifest(),
            request(required_capabilities=["gpio"]),
        )
        self.assertEqual(decision.status, ADMISSIBLE)
        self.assertEqual(decision.authority_effect, "none")
        self.assertEqual(decision.next_boundary, "observation")

    def test_replay_digest_is_deterministic(self):
        manifest = valid_manifest()
        admission = request(required_capabilities=["gpio"])
        first = assess_edge_substrate(manifest, admission)
        second = assess_edge_substrate(manifest, admission)
        self.assertEqual(first.replay_digest, second.replay_digest)

    def test_network_egress_requires_verified_network(self):
        manifest = valid_manifest(
            capabilities=["gpio"],
            network_validated=False,
            tls_available=False,
        )
        decision = assess_edge_substrate(
            manifest,
            request(NETWORK_EGRESS, evidence_refs=["receipt://network-request"]),
        )
        self.assertEqual(decision.status, REFUSED)
        self.assertIn("network path has not been verified", " ".join(decision.reasons))

    def test_sensitive_egress_requires_tls(self):
        manifest = valid_manifest(
            capabilities=["network", "cloud-egress"],
            network_validated=True,
            tls_available=False,
        )
        decision = assess_edge_substrate(
            manifest,
            request(
                NETWORK_EGRESS,
                sensitive_data=True,
                evidence_refs=["receipt://sensitive-egress"],
            ),
        )
        self.assertEqual(decision.status, REFUSED)
        self.assertIn("TLS", " ".join(decision.reasons))

    def test_network_egress_routes_to_governed_egress(self):
        decision = assess_edge_substrate(
            valid_manifest(),
            request(
                NETWORK_EGRESS,
                sensitive_data=True,
                cloud_required=True,
                required_capabilities=["json"],
                evidence_refs=["receipt://egress-request"],
            ),
        )
        self.assertEqual(decision.status, ADMISSIBLE_TO_EGRESS_GATE)
        self.assertEqual(decision.next_boundary, "governed-egress")
        self.assertEqual(decision.authority_effect, "none")

    def test_scope_expansion_is_refused(self):
        decision = assess_edge_substrate(
            valid_manifest(),
            request(
                requested_access_scopes=["actuator:unknown"],
                requested_data_scopes=["telemetry:private"],
            ),
        )
        self.assertEqual(decision.status, REFUSED)
        self.assertGreaterEqual(len(decision.reasons), 2)

    def test_actuation_never_becomes_authorized_here(self):
        decision = assess_edge_substrate(
            valid_manifest(),
            request(
                ACTUATE,
                required_capabilities=["actuate"],
                requested_access_scopes=["actuator:relay"],
                evidence_refs=["receipt://actuation-intent"],
            ),
        )
        self.assertEqual(decision.status, ADMISSIBLE_TO_REHT)
        self.assertEqual(decision.next_boundary, "fresh-reht")
        self.assertEqual(decision.authority_effect, "none")

    def test_consequence_bearing_request_requires_evidence(self):
        decision = assess_edge_substrate(
            valid_manifest(),
            request(NETWORK_EGRESS),
        )
        self.assertEqual(decision.status, REFUSED)
        self.assertIn("request evidence", " ".join(decision.reasons))

    def test_manifest_requires_owner_identity_firmware_and_audit(self):
        with self.assertRaises(EdgeSubstrateError):
            valid_manifest(owner_id="")
        with self.assertRaises(EdgeSubstrateError):
            valid_manifest(device_identity="")
        with self.assertRaises(EdgeSubstrateError):
            valid_manifest(firmware_version="")
        with self.assertRaises(EdgeSubstrateError):
            valid_manifest(audit_ref="")

    def test_manifest_cannot_claim_authority(self):
        with self.assertRaises(EdgeSubstrateError):
            valid_manifest(authority_effect="allow")

    def test_raw_secrets_are_rejected(self):
        data = {
            "action": OBSERVE,
            "purpose": "bad input",
            "password": "not-allowed",
        }
        with self.assertRaises(EdgeSubstrateError):
            request_from_dict(data)

    def test_verified_network_requires_declared_network_capability(self):
        with self.assertRaises(EdgeSubstrateError):
            valid_manifest(
                capabilities=["gpio"],
                network_validated=True,
                tls_available=False,
            )

    def test_verified_tls_requires_declared_tls_capability(self):
        with self.assertRaises(EdgeSubstrateError):
            valid_manifest(
                capabilities=["network"],
                network_validated=True,
                tls_available=True,
            )

    def test_unknown_fields_fail_closed(self):
        with self.assertRaises(EdgeSubstrateError):
            valid_manifest(extra="nope")


if __name__ == "__main__":
    unittest.main()
