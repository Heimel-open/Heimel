"""Tests for #316 Crowdfunding-mot-Moltbook adapter (E21)."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "valo_platform"))

from moltbook_crowdfunder import MoltbookCrowdfunder, CrowdfundPledge


class _FakeVerdict:
    def __init__(self, aarm, conf=0.9, rid="rcpt-x"):
        self.aarm = aarm
        self.governance_confidence = conf
        self.receipt_id = rid
    def as_dict(self):
        return {"aarm": self.aarm, "governance_confidence": self.governance_confidence,
                "receipt_id": self.receipt_id, "verdict": self.aarm}


class _FakeRuntime:
    def __init__(self, policy):
        self.policy = policy
    def assess(self, proposed_action="", actor="", observer_signals=None):
        for substr, aarm in self.policy.items():
            if substr in proposed_action:
                return _FakeVerdict(aarm)
        return _FakeVerdict("deny")


def test_grant_budget_respects_cap():
    c = MoltbookCrowdfunder(budget_cap=50.0)
    c.grant_budget("a1", 30.0)
    assert c.budget("a1") == 30.0
    try:
        c.grant_budget("a1", 100.0)
        assert False
    except ValueError:
        pass


def test_allowed_pledge_backs_campaign_and_applies():
    applied = []
    c = MoltbookCrowdfunder(runtime=_FakeRuntime({"crowdfund": "allow"}),
                            moltbook_apply=lambda s, cid, amt: (applied.append((s, cid, amt)) or True))
    c.grant_budget("a1", 100.0)
    p = c.pledge("a1", "feat-dark-mode", "upvote", 40.0)
    assert isinstance(p, CrowdfundPledge)
    assert p.verdict == "ALLOW"
    assert p.moltbook_applied is True
    assert c.budget("a1") == 60.0
    assert applied == [("upvote", "feat-dark-mode", 40.0)]


def test_insufficient_budget_denies():
    c = MoltbookCrowdfunder(runtime=_FakeRuntime({"crowdfund": "allow"}))
    c.grant_budget("a1", 10.0)
    p = c.pledge("a1", "feat-x", "post", 50.0)
    assert p.verdict == "DENY"
    assert p.moltbook_applied is False
    assert c.budget("a1") == 10.0


def test_reht_deny_blocks_pledge():
    c = MoltbookCrowdfunder(runtime=_FakeRuntime({"crowdfund": "deny"}))
    c.grant_budget("a1", 100.0)
    p = c.pledge("a1", "feat-x", "post", 40.0)
    assert p.verdict == "DENY"
    assert p.moltbook_applied is False


def test_no_runtime_defers():
    c = MoltbookCrowdfunder(runtime=None)
    c.grant_budget("a1", 100.0)
    p = c.pledge("a1", "feat-x", "upvote", 40.0)
    assert p.verdict == "DEFER"
    assert p.moltbook_applied is False


def test_total_backed_aggregates():
    c = MoltbookCrowdfunder(runtime=_FakeRuntime({"crowdfund": "allow"}))
    c.grant_budget("a1", 100.0)
    c.pledge("a1", "feat-x", "upvote", 10.0)
    c.pledge("a1", "feat-x", "post", 20.0)
    c.pledge("a1", "feat-y", "upvote", 5.0)
    assert c.total_backed("feat-x") == 30.0


def test_pledge_has_receipt_and_hash():
    c = MoltbookCrowdfunder(runtime=_FakeRuntime({"crowdfund": "allow"}))
    c.grant_budget("a1", 100.0)
    p = c.pledge("a1", "feat-x", "upvote", 10.0)
    assert p.content_hash
    assert p.reht_receipt_id == "rcpt-x"
