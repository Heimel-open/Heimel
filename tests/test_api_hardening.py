"""API hardening: evidence validation and audit endpoints must not fabricate."""

import os

from fastapi.testclient import TestClient

from vaig.api import app
from vaig.worm import WORMLog


def _client():
    return TestClient(app)


def test_evidence_validate_reflects_rrp_state():
    client = _client()
    resp = client.post(
        "/api/v1/evidence/validate",
        json={"condition_type": "mfa_verified", "condition_value": True},
    )
    payload = resp.json()
    assert payload["validation_state"] == "VALIDATED"
    assert payload["admissible"] is True
    assert payload["fresh"] is True
    assert payload["payload_digest"].startswith("sha256:")
    assert payload["confidence"] >= 0.0

    missing = client.post(
        "/api/v1/evidence/validate",
        json={"condition_type": "mfa_verified", "condition_value": None},
    )
    assert missing.json()["validation_state"] == "INSUFFICIENT"
    assert missing.json()["admissible"] is False


def test_audit_log_no_entries_is_honest(tmp_path):
    log_path = str(tmp_path / "empty_audit.jsonl")
    os.environ["VAIG_WORM_LOG"] = log_path
    try:
        resp = _client().get("/api/v1/audit/log")
        payload = resp.json()
        assert payload["count"] == 0
        assert payload["entries"] == []
        assert payload["chain_integrity"] == "no_entries"
    finally:
        del os.environ["VAIG_WORM_LOG"]


def test_audit_log_returns_real_chain(tmp_path):
    log_path = str(tmp_path / "real_audit.jsonl")
    worm = WORMLog(log_path)
    worm.append("evt-1", {"action": "authorize"})
    worm.append("evt-2", {"action": "evidence_validate"})
    os.environ["VAIG_WORM_LOG"] = log_path
    try:
        resp = _client().get("/api/v1/audit/log")
        payload = resp.json()
        assert payload["count"] == 2
        assert [e["entry_id"] for e in payload["entries"]] == ["evt-1", "evt-2"]
        assert all(e["hash"] for e in payload["entries"])
        assert payload["chain_integrity"] == "verified"
        assert payload["entries"][1]["previous_hash"] == payload["entries"][0]["hash"]
    finally:
        del os.environ["VAIG_WORM_LOG"]


def test_verify_chain_no_entries_is_honest(tmp_path):
    os.environ["VAIG_WORM_LOG"] = str(tmp_path / "missing.jsonl")
    try:
        resp = _client().get("/api/v1/audit/verify-chain")
        payload = resp.json()
        assert payload["chain_status"] == "no_entries"
        assert payload["total_entries"] == 0
    finally:
        del os.environ["VAIG_WORM_LOG"]
