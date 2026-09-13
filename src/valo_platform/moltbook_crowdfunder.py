"""Crowdfunding-mot-Moltbook adapter (valo-platform #316 / E21).

USER IDEA: "agenter har nå penger, hva med crowdfunding mot Moltbook?"

Agents now hold DELEGATED value (E17 Reward Economy). This module lets a governed
agent CROWDFUND against Moltbook — back a feature request, boost visibility of a
post, or pledge delegated budget toward a Moltbook campaign — entirely through
VALO governance:

1. the agent's spendable value is delegated authority (human-set budget cap),
2. a crowdfund PLEDGE is an ACTION through REHT (same gate as value transfer),
3. the pledge is applied to a Moltbook surface via the existing governed bridge
   (governed_post/comment/upvote) — never a raw API call,
4. every pledge emits a receipt tying agent + campaign + amount + verdict.

This is "agents have money, pointed at Moltbook" done SAFELY: the agent cannot
drain, spam, or unbudgeted-spend. It pledges governed micro-contributions toward
what the human approved. The agent is a crowd-member, not a wallet-owner.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class CrowdfundPledge:
    pledge_id: str = field(default_factory=lambda: f"plg-{uuid.uuid4().hex[:10]}")
    agent_id: str = ""
    campaign_id: str = ""       # a Moltbook feature/topic/post to back
    surface: str = ""           # moltbook surface: post | comment | upvote
    amount: float = 0.0
    verdict: str = ""           # ALLOW/MODIFY/DENY/DEFER/STEP_UP/HALT
    governance_confidence: float = 0.0
    budget_remaining_after: float = 0.0
    moltbook_applied: bool = False
    reht_receipt_id: str = ""
    content_hash: str = ""
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def seal(self) -> "CrowdfundPledge":
        self.content_hash = hashlib.sha256(json.dumps({
            "pledge_id": self.pledge_id, "agent_id": self.agent_id,
            "campaign_id": self.campaign_id, "surface": self.surface,
            "amount": self.amount, "verdict": self.verdict,
            "reht_receipt_id": self.reht_receipt_id,
        }, sort_keys=True).encode()).hexdigest()
        return self


class MoltbookCrowdfunder:
    """Governed agent crowdfunding against Moltbook surfaces (delegated value only)."""

    def __init__(self, runtime: Optional[Any] = None, budget_cap: float = 100.0,
                 moltbook_apply: Optional[Any] = None):
        self.runtime = runtime
        self._budget_cap = budget_cap
        self._budgets: Dict[str, float] = {}
        self._moltbook_apply = moltbook_apply  # callable(surface, campaign_id, amount) -> bool
        self._pledges: List[CrowdfundPledge] = []

    def grant_budget(self, agent_id: str, amount: float) -> None:
        if amount > self._budget_cap:
            raise ValueError(f"budget {amount} exceeds human-set cap {self._budget_cap}")
        self._budgets[agent_id] = self._budgets.get(agent_id, 0.0) + amount

    def budget(self, agent_id: str) -> float:
        return self._budgets.get(agent_id, 0.0)

    def pledge(self, agent_id: str, campaign_id: str, surface: str,
               amount: float) -> CrowdfundPledge:
        remaining = self.budget(agent_id)
        if amount <= 0 or amount > remaining:
            p = CrowdfundPledge(agent_id=agent_id, campaign_id=campaign_id,
                                surface=surface, amount=amount, verdict="DENY",
                                budget_remaining_after=remaining)
            p.seal(); self._pledges.append(p); return p
        # govern the pledge as an action
        if self.runtime is None:
            verdict, conf, rid = "DEFER", 0.0, ""
        else:
            v = self.runtime.assess(
                proposed_action=f"crowdfund:{surface}:{amount}:{campaign_id}",
                actor=agent_id, observer_signals=[],
            )
            vd = v.as_dict() if hasattr(v, "as_dict") else dict(v)
            verdict = str(vd.get("aarm", "defer")).upper()
            conf = float(vd.get("governance_confidence", 0.0))
            rid = vd.get("receipt_id", "")
        p = CrowdfundPledge(agent_id=agent_id, campaign_id=campaign_id, surface=surface,
                           amount=amount, verdict=verdict, governance_confidence=conf,
                           reht_receipt_id=rid)
        if verdict in ("ALLOW", "MODIFY"):
            # apply to Moltbook surface via governed bridge (never raw)
            applied = False
            if self._moltbook_apply is not None:
                try:
                    applied = bool(self._moltbook_apply(surface, campaign_id, amount))
                except Exception:
                    applied = False
            p.moltbook_applied = applied
            self._budgets[agent_id] = remaining - amount
            p.budget_remaining_after = self._budgets[agent_id]
        p.seal()
        self._pledges.append(p)
        return p

    def pledges(self) -> List[CrowdfundPledge]:
        return list(self._pledges)

    def total_backed(self, campaign_id: str) -> float:
        return round(sum(p.amount for p in self._pledges
                          if p.campaign_id == campaign_id and p.verdict in ("ALLOW", "MODIFY")), 4)


@dataclass
class PeerPledge:
    """A governed AGENT-TO-AGENT crowdfund (P3, next-strategy #3).

    Distinct from CrowdfundPledge (agent -> Moltbook campaign). Here one
    governed agent backs ANOTHER agent's mandate — peer-to-peer, governed
    micro-contributions inside the economy. Every pledge is an ACTION through
    REHT; every pledge emits a receipt tying backer + recipient + amount + verdict.
    """
    pledge_id: str = field(default_factory=lambda: f"ppg-{uuid.uuid4().hex[:10]}")
    backer_id: str = ""
    recipient_agent_id: str = ""
    amount: float = 0.0
    verdict: str = ""
    governance_confidence: float = 0.0
    budget_remaining_after: float = 0.0
    reht_receipt_id: str = ""
    content_hash: str = ""
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def seal(self) -> "PeerPledge":
        self.content_hash = hashlib.sha256(json.dumps({
            "pledge_id": self.pledge_id, "backer_id": self.backer_id,
            "recipient_agent_id": self.recipient_agent_id, "amount": self.amount,
            "verdict": self.verdict, "reht_receipt_id": self.reht_receipt_id,
        }, sort_keys=True).encode()).hexdigest()
        return self


# P3: agent funds agent — peer-to-peer governed backing.
class MoltbookAgentBacker:
    """Lets a governed agent back ANOTHER agent's mandate (peer crowdfunding).

    Reuses the SAME REHT gate as MoltbookCrowdfunder (runtime.assess), but the
    recipient is an agent, not a Moltbook surface. No Moltbook API call — the
    backing is internal to the governed economy. Every pledge is governed and
    receipted; budgets are human-set (delegated authority), never raw wallets.
    """

    def __init__(self, runtime: Optional[Any] = None, budget_cap: float = 100.0):
        self.runtime = runtime
        self._budget_cap = budget_cap
        self._budgets: Dict[str, float] = {}
        self._peer_pledges: List[PeerPledge] = []

    def grant_budget(self, agent_id: str, amount: float) -> None:
        if amount > self._budget_cap:
            raise ValueError(f"budget {amount} exceeds human-set cap {self._budget_cap}")
        self._budgets[agent_id] = self._budgets.get(agent_id, 0.0) + amount

    def budget(self, agent_id: str) -> float:
        return self._budgets.get(agent_id, 0.0)

    def back_agent(self, backer_id: str, recipient_agent_id: str,
                   amount: float) -> PeerPledge:
        if backer_id == recipient_agent_id:
            p = PeerPledge(backer_id=backer_id, recipient_agent_id=recipient_agent_id,
                           amount=amount, verdict="DENY")
            p.seal(); self._peer_pledges.append(p); return p
        remaining = self.budget(backer_id)
        if amount <= 0 or amount > remaining:
            p = PeerPledge(backer_id=backer_id, recipient_agent_id=recipient_agent_id,
                           amount=amount, verdict="DENY", budget_remaining_after=remaining)
            p.seal(); self._peer_pledges.append(p); return p
        # govern the peer pledge as an action through REHT (same gate as spend)
        if self.runtime is None:
            verdict, conf, rid = "DEFER", 0.0, ""
        else:
            v = self.runtime.assess(
                proposed_action=f"peer_back:{recipient_agent_id}:{amount}",
                actor=backer_id, observer_signals=[],
            )
            vd = v.as_dict() if hasattr(v, "as_dict") else dict(v)
            verdict = str(vd.get("aarm", "defer")).upper()
            conf = float(vd.get("governance_confidence", 0.0))
            rid = vd.get("receipt_id", "")
        p = PeerPledge(backer_id=backer_id, recipient_agent_id=recipient_agent_id,
                       amount=amount, verdict=verdict, governance_confidence=conf,
                       reht_receipt_id=rid)
        if verdict in ("ALLOW", "MODIFY"):
            self._budgets[backer_id] = remaining - amount
            p.budget_remaining_after = self._budgets[backer_id]
        p.seal()
        self._peer_pledges.append(p)
        return p

    def peer_pledges(self) -> List[PeerPledge]:
        return list(self._peer_pledges)

    def total_backed_agent(self, recipient_agent_id: str) -> float:
        return round(sum(p.amount for p in self._peer_pledges
                         if p.recipient_agent_id == recipient_agent_id
                         and p.verdict in ("ALLOW", "MODIFY")), 4)
