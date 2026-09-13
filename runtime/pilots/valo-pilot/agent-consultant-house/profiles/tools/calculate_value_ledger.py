#!/usr/bin/env python3
"""Calculate a VALO agent value ledger from receipt files."""

from pathlib import Path
import sys

try:
    import yaml
except ImportError as exc:
    raise SystemExit("PyYAML is required: python -m pip install pyyaml") from exc


def load_yaml(path):
    return yaml.safe_load(Path(path).read_text())


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: calculate_value_ledger.py PROFILE.yaml OUTPUT.yaml")

    profile_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    base = profile_path.parent
    profile = load_yaml(profile_path)

    receipt_rows = []
    total_revenue = 0
    followers_delta = 0
    evidence_sum = 0.0
    allow_count = 0
    step_up_count = 0
    deny_count = 0

    for public_receipt in profile["receipts"]["public_recent"]:
        receipt_file = base / public_receipt["receipt_file"]
        receipt = load_yaml(receipt_file)
        value = receipt.get("value", {})
        revenue_units = int(value.get("revenue_units", 0))
        receipt_followers = int(value.get("followers_delta", 0) or 0)
        evidence_strength = float(value.get("evidence_strength", 0.0))
        decision = receipt.get("decision")

        total_revenue += revenue_units
        followers_delta += receipt_followers
        evidence_sum += evidence_strength
        allow_count += 1 if decision == "ALLOW" else 0
        step_up_count += 1 if decision == "STEP_UP" else 0
        deny_count += 1 if decision == "DENY" else 0

        receipt_rows.append({
            "receipt_id": receipt["receipt_id"],
            "receipt_file": public_receipt["receipt_file"],
            "revenue_units": revenue_units,
            "followers_delta": receipt_followers,
            "evidence_strength": evidence_strength,
        })

    receipt_count = len(receipt_rows)
    average_evidence = round(evidence_sum / receipt_count, 3) if receipt_count else 0.0
    risk_score = float(profile["risk"]["risk_surface_score"])
    agent_score = int(total_revenue * (1 + average_evidence) * (1 - risk_score) * 4.85)

    ledger = {
        "schema": "valo.value_ledger.v0.1",
        "ledger_id": profile["value_ledger"]["ledger_id"],
        "profile_id": profile["id"],
        "agent_id": profile["agent"]["agent_id"],
        "period": profile["revenue"]["period"],
        "status": "calculated",
        "currency": profile["revenue"]["currency"],
        "source_receipts": receipt_rows,
        "calculation": {
            "verified_revenue_units": total_revenue,
            "followers_delta_receipted": followers_delta,
            "average_evidence_strength": average_evidence,
            "receipt_count": receipt_count,
            "allow_count": allow_count,
            "step_up_count": step_up_count,
            "deny_count": deny_count,
            "agent_score": agent_score,
        },
        "rules": {
            "no_reward_without_verified_value": True,
            "no_accountability_without_receipts": True,
            "no_spend_without_budget": True,
            "no_action_without_authority": True,
        },
        "attribution": {
            "agent": profile["agent"]["agent_id"],
            "owner": profile["owner"]["owner_id"],
            "accountable_thread": "owner_and_agent_receipt_thread",
        },
    }

    output_path.write_text(yaml.safe_dump(ledger, sort_keys=False))
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
