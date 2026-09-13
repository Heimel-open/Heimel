"""
VACS session security tests.

Covers the first recovered VAIG Fidelity primitives: session keys, receipt HMAC
verification, revocation, rotation, and capability extension caps.
"""

import os
import sys

import pytest

sys.path.insert(0, "../src")

from capability_extension import (  # noqa: E402
    CapabilityExtensionCapExceeded,
    CapabilityExtensionTracker,
)
from receipt import ACSReceiptGenerator, Decision  # noqa: E402
from session_key import (  # noqa: E402
    SessionKeyManager,
    derive_session_key,
    sign_session_payload,
    verify_session_payload,
)


def test_different_sessions_produce_different_keys():
    secret = os.urandom(32)
    assert derive_session_key(secret, "session-a") != derive_session_key(secret, "session-b")


def test_same_session_derivation_is_deterministic():
    secret = os.urandom(32)
    assert derive_session_key(secret, "session-a") == derive_session_key(secret, "session-a")


def test_session_key_is_32_bytes():
    assert len(derive_session_key(os.urandom(32), "session-a")) == 32


def test_short_fleet_secret_rejected():
    with pytest.raises(ValueError):
        SessionKeyManager(b"short")


def test_manager_returns_key_and_key_id():
    manager = SessionKeyManager.generate()
    key, key_id = manager.derive("session-abcdef")
    assert len(key) == 32
    assert key_id == "session-abcd"


def test_revoked_key_id_is_rejected():
    manager = SessionKeyManager.generate()
    _, key_id = manager.derive("session-abcdef")
    manager.revoke(key_id)
    with pytest.raises(ValueError, match="revoked"):
        manager.derive("session-abcdef")


def test_revocation_list_propagates():
    manager_a = SessionKeyManager.generate()
    manager_b = SessionKeyManager(manager_a.fleet_secret)
    _, key_id = manager_a.derive("session-abcdef")
    manager_a.revoke(key_id)
    manager_b.apply_revocation_list(manager_a.revoked_key_ids())
    assert manager_b.is_revoked(key_id)


def test_rotation_changes_fleet_secret():
    manager = SessionKeyManager.generate()
    old_secret = manager.fleet_secret
    manager.rotate(os.urandom(32))
    assert manager.fleet_secret != old_secret


def test_hmac_payload_verifies_with_correct_session_key():
    key = derive_session_key(os.urandom(32), "session-a")
    payload = '{"decision":"ALLOW","packet_id":"pkt-1"}'
    signature = sign_session_payload(key, payload)
    assert verify_session_payload(key, payload, signature)


def test_hmac_payload_fails_with_wrong_session_key():
    key = derive_session_key(os.urandom(32), "session-a")
    wrong_key = derive_session_key(os.urandom(32), "session-b")
    payload = '{"decision":"ALLOW","packet_id":"pkt-1"}'
    signature = sign_session_payload(key, payload)
    assert not verify_session_payload(wrong_key, payload, signature)


def test_session_bound_receipt_verifies_with_correct_key():
    manager = SessionKeyManager.generate()
    session_key, key_id = manager.derive("session-abcdef")
    receipt_generator = ACSReceiptGenerator()
    packet = {
        "packet_id": "pkt-1",
        "intent": {"action": "modify", "target": "record-1"},
        "evidence": {"sources": []},
        "policy": {"max_risk_level": "medium"},
    }

    receipt = receipt_generator.generate_session_bound(
        packet=packet,
        decision=Decision.ALLOW,
        session_id="session-abcdef",
        key_id=key_id,
        session_key=session_key,
        previous_state_hash="prev",
        proposed_state_hash="next",
    )

    assert receipt["session_id"] == "session-abcdef"
    assert receipt["key_id"] == key_id
    assert receipt["session_signature_alg"] == "hmac-sha256"
    assert receipt_generator.verify_session_bound(receipt, session_key)
    assert not receipt_generator.verify_session_bound(receipt, os.urandom(32))


def test_narrowing_capability_extension_is_not_scope_broadening():
    tracker = CapabilityExtensionTracker("session-a", ["read_docs"], cap=5)
    event = tracker.request_extension("read_docs:project/public")
    assert event.scope_broadening is False
    assert event.extension_index == 1


def test_broadening_capability_extension_is_flagged():
    tracker = CapabilityExtensionTracker("session-a", ["read_docs"], cap=5)
    event = tracker.request_extension("network.egress")
    assert event.scope_broadening is True


def test_capability_extension_cap_is_enforced():
    tracker = CapabilityExtensionTracker("session-a", ["read"], cap=2)
    tracker.request_extension("write")
    tracker.request_extension("delete")
    with pytest.raises(CapabilityExtensionCapExceeded):
        tracker.request_extension("network.egress")


def test_capability_extension_summary():
    tracker = CapabilityExtensionTracker("session-a", ["read"], cap=5)
    tracker.request_extension("write")
    summary = tracker.summary()
    assert summary["extensions_used"] == 1
    assert summary["remaining"] == 4
    assert summary["scope_broadening_count"] == 1
    assert "write" in summary["current_capabilities"]