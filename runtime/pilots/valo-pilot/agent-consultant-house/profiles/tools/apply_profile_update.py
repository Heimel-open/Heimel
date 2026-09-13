#!/usr/bin/env python3
"""Gate profile-changing writes behind signed profile_update receipts.

This prototype does not mutate the profile. It answers the operational question:
would a profile write be allowed with the current authority, contestability,
revocation, budget and signed receipt state?
"""

from pathlib import Path
import sys

try:
    import yaml
except ImportError as exc:
    raise SystemExit("PyYAML is required: python -m pip install pyyaml") from exc


def load_yaml(path):
    return yaml.safe_load(Path(path).read_text())


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: apply_profile_update.py PROFILE.yaml")

    profile_path = Path(sys.argv[1])
    base = profile_path.parent
    profile = load_yaml(profile_path)
    errors = []

    revocation = load_yaml(base / profile["revocation"]["revocation_registry"])
    contest = load_yaml(base / profile["accountability"]["contestability_file"])
    budget = load_yaml(base / profile["budget"]["budget_file"])

    if profile["revocation"].get("revoked") or revocation.get("revoked_agents"):
        errors.append("profile write denied: revoked authority or agent")
    if contest.get("open_contests"):
        errors.append("profile write denied: open contest")

    grant = budget["budget_grant"]
    if grant["budget_spent"] > grant["budget_granted"]:
        errors.append("profile write denied: budget exceeded")

    update_receipts = []
    for entry in profile["receipts"]["public_recent"]:
        receipt = load_yaml(base / entry["receipt_file"])
        if receipt.get("action", {}).get("type") == "profile_update":
            update_receipts.append(receipt)

    if not update_receipts:
        errors.append("profile write denied: no profile_update receipt")

    for receipt in update_receipts:
        verification = receipt.get("verification", {})
        authority = receipt.get("authority", {})
        if receipt.get("decision") != "ALLOW":
            errors.append(f"profile write denied: update receipt {receipt['receipt_id']} is not ALLOW")
        if not authority.get("session_bound") or not authority.get("session_id"):
            errors.append(f"profile write denied: update receipt {receipt['receipt_id']} is not session-bound")
        if verification.get("signature_status") not in {"demo_signed", "production_signed"}:
            errors.append(f"profile write denied: update receipt {receipt['receipt_id']} has unsigned status")
        if verification.get("signature", "").startswith("sample-") or not verification.get("signature"):
            errors.append(f"profile write denied: update receipt {receipt['receipt_id']} has invalid signature")

    if errors:
        for error in errors:
            print(f"DENY: {error}")
        raise SystemExit(1)

    print("ALLOW: signed profile update gate passed")


if __name__ == "__main__":
    main()
