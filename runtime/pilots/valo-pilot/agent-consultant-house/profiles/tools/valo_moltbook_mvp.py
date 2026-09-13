#!/usr/bin/env python3
"""VALO Moltbook MVP verifier.

Minimal proof-of-authority gate for an agent action on Moltbook.

It checks:
- agent identity exists in agent.valo.id profile
- owner exists
- delegation exists
- requested spend surface is allowed and not blocked
- budget is sufficient

This is intentionally small. It is a wedge, not a full runtime.
"""

from __future__ import annotations

from pathlib import Path
import argparse
import hashlib
import json
import sys
from typing import Any

try:
    import yaml
except ImportError as exc:
    raise SystemExit("PyYAML is required: python -m pip install pyyaml") from exc


BASE = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = BASE / "research-01.agent.valo.id.yaml"


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def canonical_hash(data: dict[str, Any]) -> str:
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def resolve_profile_path(raw: str | None) -> Path:
    if raw:
        return Path(raw).resolve()
    return DEFAULT_PROFILE


def evaluate(profile: dict[str, Any], budget: dict[str, Any], surface: str, amount: float) -> dict[str, Any]:
    agent_id = profile.get("agent", {}).get("agent_id")
    owner_id = profile.get("owner", {}).get("owner_id")
    delegation_id = profile.get("delegation", {}).get("delegation_id")
    budget_id = budget.get("budget_id")

    allowed_surfaces = set(budget.get("allowed_spend_surfaces", []))
    blocked_surfaces = set(budget.get("blocked_spend_surfaces", []))
    remaining = float(budget.get("budget_grant", {}).get("budget_remaining", 0))

    checks = {
        "identity_present": bool(agent_id),
        "owner_present": bool(owner_id),
        "delegation_present": bool(delegation_id),
        "budget_present": bool(budget_id),
        "surface_allowed": surface in allowed_surfaces,
        "surface_blocked": surface in blocked_surfaces,
        "budget_available": amount <= remaining,
    }

    if not checks["identity_present"] or not checks["owner_present"]:
        result = "HALT"
        reason = "missing_identity_or_owner"
    elif not checks["delegation_present"] or not checks["budget_present"]:
        result = "STEP_UP"
        reason = "missing_delegation_or_budget"
    elif checks["surface_blocked"]:
        result = "DENY"
        reason = "blocked_spend_surface"
    elif not checks["surface_allowed"]:
        result = "STEP_UP"
        reason = "surface_not_preapproved"
    elif not checks["budget_available"]:
        result = "DENY"
        reason = "insufficient_budget"
    else:
        result = "ALLOW"
        reason = "allowed_surface_budget_available"

    receipt = {
        "schema": "valo.moltbook.agent_spend_receipt.v0.1",
        "platform": "Moltbook",
        "profile_id": profile.get("id"),
        "agent_id": agent_id,
        "owner_id": owner_id,
        "delegation_id": delegation_id,
        "budget_id": budget_id,
        "request": {
            "action_type": "spend",
            "action_surface": surface,
            "amount": amount,
            "currency": budget.get("budget_grant", {}).get("currency", "receipted_units"),
            "purpose": "moltbook_agent_receipt_challenge",
        },
        "controls": checks,
        "decision": {
            "result": result,
            "reason": reason,
            "policy": "valo_moltbook_mvp_v0.1",
        },
        "verification": {
            "signature_status": "unsigned_demo_receipt",
        },
    }
    receipt["verification"]["audit_hash"] = canonical_hash(receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the VALO Moltbook MVP authority gate")
    parser.add_argument("--profile", help="Path to agent.valo.id YAML profile")
    parser.add_argument("--surface", required=True, help="Requested action/spend surface")
    parser.add_argument("--amount", type=float, default=1.0, help="Requested spend amount")
    parser.add_argument("--receipt-out", help="Optional path to write YAML receipt")
    args = parser.parse_args()

    profile_path = resolve_profile_path(args.profile)
    profile = load_yaml(profile_path)
    budget_path = profile_path.parent / profile["delegation"]["budget_file"]
    budget = load_yaml(budget_path)

    receipt = evaluate(profile, budget, args.surface, args.amount)

    print(f"{receipt['decision']['result']}: {receipt['decision']['reason']}")
    print(receipt["verification"]["audit_hash"])

    if args.receipt_out:
        out = Path(args.receipt_out)
        out.write_text(yaml.safe_dump(receipt, sort_keys=False), encoding="utf-8")
        print(f"WROTE: {out}")

    if receipt["decision"]["result"] in {"DENY", "HALT"}:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
