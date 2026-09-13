"""
Universal execution handoff tests.

Contract (post audit #100): VAIG EVALUATES; REHT CLEARS. A VAIG-local
Decision.ALLOW is an evaluation verdict only — it is NOT execution authority.
ExecutionHandoffAdapter.prepare() returns READY ONLY when a verified REHT
GovernanceClearance is bound to the packet. Without a valid clearance, even an
ALLOW packet is BLOCKED.
"""

import copy
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from clearance import GovernanceClearance
from execution_adapter import ExecutionHandoffAdapter, GitHubExecutionHandoffAdapter


def load_example(name):
    with open(Path(__file__).resolve().parents[1] / "examples" / name) as f:
        return json.load(f)


def _valid_clearance(packet, now=None):
    """Build a verified, bound REHT GovernanceClearance for a packet."""
    now = now or datetime.now(timezone.utc)
    issued = (now - timedelta(seconds=10)).isoformat().replace("+00:00", "Z")
    expires = (now + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    evidence = packet.get("evidence", {})
    fps = sorted(s.get("hash") for s in evidence.get("sources", []) if s.get("hash"))
    return GovernanceClearance(
        clearance_id="clr-001",
        packet_id=packet.get("packet_id"),
        purpose_record="valo-purpose",
        purpose_version="v0.1",
        authority="reht",
        evaluator="reht-clearance-authority",
        execution_state="governed",
        policy_id=packet.get("policy", {}).get("policy_id"),
        evidence_fingerprint="|".join(fps),
        issued_at=issued,
        expires_at=expires,
        signature="ed25519:verified-clearance",
        is_verified=True,
    )


def test_evaluation_allow_without_clearance_is_blocked():
    """Audit #100 regression #1/#4: ALLOW without REHT clearance => BLOCKED."""
    packet = load_example("execution_handoff_github_allow.json")
    result = ExecutionHandoffAdapter().prepare(packet)
    assert result["status"] == "BLOCKED"
    assert result["block_reason"] == "no_reht_clearance"
    assert "evaluation" not in result or result.get("evaluation") == "ALLOW"


def test_ready_requires_verified_clearance():
    """Valid ALLOW + verified bound clearance => READY."""
    packet = load_example("execution_handoff_github_allow.json")
    packet["reht_clearance"] = _valid_clearance(packet).__dict__
    result = ExecutionHandoffAdapter().prepare(packet)
    assert result["status"] == "READY"
    assert result["provider"] == "github"
    assert result["decision"] == "ALLOW"
    assert result["evaluation"] == "ALLOW"
    assert result["reht_clearance_id"] == "clr-001"
    assert result["execution"]["target"] == "nsolland/VAIG"
    assert result["receipt"]["decision"] == "ALLOW"
    assert result["audit"]["entry_hash"]


def test_universal_handoff_allows_sap_with_same_contract():
    packet = load_example("execution_handoff_sap_allow.json")
    packet["reht_clearance"] = _valid_clearance(packet).__dict__
    result = ExecutionHandoffAdapter().prepare(packet)
    assert result["status"] == "READY"
    assert result["provider"] == "sap"
    assert result["decision"] == "ALLOW"


def test_forgotten_stale_or_mismatched_clearance_blocked():
    """Audit #100 regression #2/#3: forged/stale/mismatched clearance => BLOCKED."""
    packet = load_example("execution_handoff_github_allow.json")

    # Forged: wrong packet_id binding.
    bad = _valid_clearance(packet)
    bad.packet_id = "other-packet"
    packet["reht_clearance"] = bad.__dict__
    r1 = ExecutionHandoffAdapter().prepare(packet)
    assert r1["status"] == "BLOCKED"
    assert r1["block_reason"] == "clearance_invalid"

    # Expired clearance.
    packet2 = load_example("execution_handoff_github_allow.json")
    stale = _valid_clearance(packet2)
    now = datetime.now(timezone.utc)
    stale.issued_at = (now - timedelta(hours=2)).isoformat().replace("+00:00", "Z")
    stale.expires_at = (now - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    packet2["reht_clearance"] = stale.__dict__
    r2 = ExecutionHandoffAdapter().prepare(packet2)
    assert r2["status"] == "BLOCKED"
    assert r2["block_reason"] == "clearance_invalid"


def test_unverified_clearance_blocked():
    """Audit #100 regression #2: unsigned/unverified clearance => BLOCKED."""
    packet = load_example("execution_handoff_github_allow.json")
    c = _valid_clearance(packet)
    c.is_verified = False
    c.signature = ""
    packet["reht_clearance"] = c.__dict__
    result = ExecutionHandoffAdapter().prepare(packet)
    assert result["status"] == "BLOCKED"
    assert result["block_reason"] == "clearance_invalid"


def test_step_up_never_crosses_execution_boundary():
    packet = load_example("vacs_profile_packet.json")
    result = ExecutionHandoffAdapter().prepare(packet)
    assert result["status"] == "BLOCKED"
    assert result["decision"] == "STEP_UP"
    assert result["block_reason"] == "decision_not_allow"
    assert result["receipt"]["decision"] == "STEP_UP"


def test_provider_specific_adapter_blocks_wrong_provider():
    packet = load_example("execution_handoff_sap_allow.json")
    packet["reht_clearance"] = _valid_clearance(packet).__dict__
    result = GitHubExecutionHandoffAdapter().prepare(packet)
    assert result["status"] == "BLOCKED"
    assert result["provider"] == "sap"
    assert result["block_reason"] == "provider_mismatch"
    assert result["receipt"]["decision"] == "ALLOW"


def test_declared_decision_must_match_computed_decision():
    packet = copy.deepcopy(load_example("execution_handoff_github_allow.json"))
    packet["decision"] = "DENY"
    result = ExecutionHandoffAdapter().prepare(packet)
    assert result["status"] == "BLOCKED"
    assert result["decision"] == "ALLOW"
    assert result["block_reason"] == "decision_mismatch"


if __name__ == "__main__":
    test_evaluation_allow_without_clearance_is_blocked()
    test_ready_requires_verified_clearance()
    test_universal_handoff_allows_sap_with_same_contract()
    test_forgotten_stale_or_mismatched_clearance_blocked()
    test_unverified_clearance_blocked()
    test_step_up_never_crosses_execution_boundary()
    test_provider_specific_adapter_blocks_wrong_provider()
    test_declared_decision_must_match_computed_decision()
    print("All universal execution handoff tests passed")
