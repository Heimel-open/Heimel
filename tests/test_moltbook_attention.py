"""Unit tests — Moltbook Attention (P1, next-strategy #1).

Verifies:
- a governed agent's boost request routes through REHT (reuses #257 bridge)
- boost is attested (ALLOW) only when VALO says ALLOW
- missing identity -> no boost attested (HALT)
- dry_run=True never transmits (boost_applied=False)
- admissible_visibility_score returns the governed verdict, no transmit
"""

from __future__ import annotations

from src.valo_platform.moltbook_attention import (
    governed_boost,
    admissible_visibility_score,
)
from src.valo_platform.integrations.bridges.moltbook_bridge import MoltbookDecision


def _valid_profile() -> dict:
    """A profile that satisfies the bridge's hard gates + REHT authority.

    Mirrors tests/test_moltbook_bridge.py _profile(): a healthy 'ok' signal
    is required for REHT to return ALLOW (no signal -> defer/deny).
    """
    from src.valo_platform.reht_preaction_runtime import RehtPreActionRuntime
    from src.valo_platform.authority_registry import (
        AuthorityRegistry, Actor, ActorKind, ExecutionAuthorityLevel,
    )
    registry = AuthorityRegistry()
    registry.register(Actor("agent-1", ActorKind.AI, ExecutionAuthorityLevel.OBSERVE))
    registry.register(Actor("owner-1", ActorKind.HUMAN, ExecutionAuthorityLevel.GOVERN))
    registry.delegate("owner-1", "agent-1", ["*"], ExecutionAuthorityLevel.EXECUTE_BOUNDED)
    RehtPreActionRuntime(registry=registry)
    return {
        "agent": {"agent_id": "agent-1"},
        "owner": {"owner_id": "owner-1"},
        "delegation": {"delegation_id": "del-1"},
        "budget": {
            "budget_id": "bud-1",
            "budget_grant": {"budget_remaining": 10.0, "currency": "receipted_units"},
        },
        "signals": [{"source": "s", "disposition": "ok", "confidence": 0.95}],
        "signals_sources": ["s"],
    }


def test_boost_attested_when_allowed():
    profile = _valid_profile()
    res = governed_boost(profile=profile, surface="public_safe_distribution",
                         weight=1.0, dry_run=True)
    assert res["governed"] is True
    assert res["decision"] == "allow"
    assert res["boost_applied"] is False  # dry_run -> never transmit
    assert "moltbook_attestation" in res
    assert res["moltbook_attestation"]["request"]["action_type"] == "boost"
    assert res["valo_receipt_id"]


def test_boost_blocked_without_identity():
    # profile missing agent/owner -> bridge HALT, no boost attested
    profile = {"agent": {}, "owner": {}, "delegation": {}, "budget": {}, "signals": []}
    res = governed_boost(profile=profile, surface="public_safe_distribution",
                         weight=1.0, dry_run=True)
    assert res["governed"] is False
    assert res["decision"] == MoltbookDecision.HALT.value
    assert res["boost_applied"] is False


def test_dry_run_never_transmits():
    profile = _valid_profile()
    # even on ALLOW, dry_run=True must NOT mark boost as applied
    res = governed_boost(profile=profile, surface="public_safe_distribution",
                         weight=2.0, dry_run=True)
    assert res["dry_run"] is True
    assert res["boost_applied"] is False


def test_admissible_visibility_score_no_transmit():
    profile = _valid_profile()
    score = admissible_visibility_score(profile=profile, surface="public_safe_distribution")
    assert "decision" in score
    assert score["boost_applied"] is False
    assert "moltbook_attestation" in score or "valo_receipt_id" in score
