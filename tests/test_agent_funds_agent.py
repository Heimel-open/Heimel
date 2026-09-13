"""Unit tests — Agent-funds-agent (P3, next-strategy #3).

Verifies:
- a governed agent can back ANOTHER agent (peer crowdfunding)
- self-backing is denied
- over-budget backing is denied
- every peer pledge routes through REHT (verdict + receipt id recorded)
- budget is debited only on ALLOW/MODIFY

Uses the same FakeRuntime contract as test_moltbook_crowdfunder.py (the
crowdfunder modules accept an abstract runtime with
assess(proposed_action, actor, observer_signals) -> {aarm, receipt_id, ...}).
"""

from __future__ import annotations

from types import SimpleNamespace

from src.valo_platform.moltbook_crowdfunder import MoltbookAgentBacker


class _FakeRuntime:
    def __init__(self, verdicts: dict):
        self._v = verdicts  # proposed_action substring -> aarm verdict

    def assess(self, proposed_action="", actor="", observer_signals=None):
        aarm = "defer"
        for key, val in self._v.items():
            if key in proposed_action:
                aarm = val
                break
        return SimpleNamespace(
            as_dict=lambda: {
                "aarm": aarm,
                "receipt_id": f"rcpt-{abs(hash(proposed_action)) % 100000}",
                "governance_confidence": 0.9 if aarm in ("allow", "modify") else 0.0,
            })


def _backer(verdict="allow", cap=100.0):
    b = MoltbookAgentBacker(runtime=_FakeRuntime({"peer_back": verdict}),
                             budget_cap=cap)
    b.grant_budget("backer-1", 50.0)
    return b


def test_agent_backs_another_agent():
    b = _backer("allow")
    p = b.back_agent("backer-1", "recipient-2", 10.0)
    assert p.verdict in ("ALLOW", "MODIFY")
    assert p.reht_receipt_id
    assert p.budget_remaining_after == 40.0
    assert b.total_backed_agent("recipient-2") == 10.0


def test_self_backing_denied():
    b = _backer("allow")
    p = b.back_agent("backer-1", "backer-1", 10.0)
    assert p.verdict == "DENY"
    assert b.budget("backer-1") == 50.0  # unchanged


def test_over_budget_denied():
    b = _backer("allow")
    p = b.back_agent("backer-1", "recipient-2", 999.0)
    assert p.verdict == "DENY"
    assert p.budget_remaining_after == 50.0


def test_peer_pledge_routes_through_reht():
    b = _backer("allow")
    p = b.back_agent("backer-1", "recipient-2", 5.0)
    assert p.reht_receipt_id  # governed, not raw
    assert p.content_hash  # sealed
    assert p.verdict in ("ALLOW", "MODIFY")
