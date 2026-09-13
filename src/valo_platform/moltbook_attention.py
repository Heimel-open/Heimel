"""
Moltbook Attention — governed visibility (valo-platform P1, next-strategy #1).

PILLAR 1 of the VALO x Moltbook execution roadmap: attention is EARNED by
admissible behaviour, not bought. A governed agent can request a Moltbook
visibility boost; the request is governed by VALO's RehtPreActionRuntime BEFORE
any boost is attested. On ALLOW, VALO emits a Moltbook-compatible attestation
("this agent is admissible -> boost eligible") — Moltbook applies the boost only
if VALO says ALLOW.

This module REUSES the existing governed runtime + receipt surface from
moltbook_bridge.py (#257). It does NOT redefine the bridge, the receipt schema,
or the authority layer. It adds one governed surface: `boost`.

IP-SAFE (same rules as #257):
  - NO Moltbook API keys, NO external network calls. The profile is a LOCAL
    dict/YAML. VALO NEVER fetches Moltbook.
  - Only the public governed runtime surface is used.
  - dry_run=True by default: attest + return the payload, never transmit.

Per Index #219 / architecture red lines:
  - VAIG evaluates, REHT clears. This module is a REHT-governed action surface.
  - No decision authority here — REHT decides; we attest + record.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.valo_platform.integrations.bridges.moltbook_bridge import (
    MoltbookDecision,
    MoltbookGovernedAction,
    govern_moltbook_action,
)


# Boost is a governed action through the SAME gate as spend/post/comment.
_BOOST_ACTION_CLASS = "moltbook_boost"
_BOOST_RISK_TIER = "low"


def governed_boost(*, profile: Dict[str, Any], surface: str, weight: float = 1.0,
                   dry_run: bool = True, tenant_id: Optional[str] = None,
                   economy=None) -> Dict[str, Any]:
    """Govern a Moltbook VISIBILITY BOOST request through VALO.

    Flow:
      1. govern_moltbook_action() -> VALO verdict + signed receipt (reuses #257).
      2. if result != ALLOW -> return governed result (no boost attested).
      3. else emit a Moltbook-compatible 'admissible visibility' attestation.

    `dry_run=True` (default): we attest + return the payload but NEVER call
    Moltbook. The caller transmits only if it holds the (separate) Moltbook
    client and VALO said ALLOW.

    Returns a dict carrying the governed action + the boost attestation,
    mirroring the shape of moltbook_bridge.governed_post().
    """
    # Boost is metered in the same delegated-value units as spend.
    action = govern_moltbook_action(
        profile=profile, surface=surface, amount=weight,
        tenant_id=tenant_id, economy=economy)

    if action.result != MoltbookDecision.ALLOW:
        return {
            "governed": False,
            "boost_applied": False,
            "decision": action.result.value,
            "reason": action.reason,
            "valo_receipt_id": action.valo_receipt_id,
            "moltbook_receipt": action.as_moltbook_receipt(),
        }

    # VALO authorized the boost -> build the admissible-visibility attestation.
    boost_receipt = action.as_moltbook_receipt()
    boost_receipt["request"] = {
        "action_type": "boost",
        "action_surface": surface,
        "weight": weight,
        "purpose": "moltbook_governed_visibility",
    }
    boost_receipt["controls"]["surface_allowed"] = True
    boost_receipt["decision"]["result"] = "ALLOW"
    boost_receipt["decision"]["reason"] = "valo_allow_visibility"

    return {
        "governed": True,
        "boost_applied": (not dry_run),
        "dry_run": dry_run,
        "decision": "allow",
        "valo_receipt_id": action.valo_receipt_id,
        "moltbook_attestation": boost_receipt,
    }


# Convenience: score an agent's admissible-standing for ranking (no transmit).
def admissible_visibility_score(profile: Dict[str, Any], surface: str,
                                 weight: float = 1.0) -> Dict[str, Any]:
    """Return the governed boost decision WITHOUT any Moltbook call.

    Used by a ranking hook to prefer governed agents in the feed. Pure
    attestation: VALO attests admissibility; Moltbook reads the verdict.
    """
    return governed_boost(
        profile=profile, surface=surface, weight=weight, dry_run=True)
