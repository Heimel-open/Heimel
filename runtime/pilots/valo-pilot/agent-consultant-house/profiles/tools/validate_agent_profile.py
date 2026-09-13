#!/usr/bin/env python3
"""Validate an agent.valo.id profile proof bundle.

Prototype validator. Checks cross-file references and basic arithmetic without
requiring jsonschema. Use schema validation in CI later.
"""

from pathlib import Path
import sys

try:
    import yaml
except ImportError as exc:
    raise SystemExit("PyYAML is required: python -m pip install pyyaml") from exc


def load_yaml(path):
    return yaml.safe_load(Path(path).read_text())


def require_file(base, relative_path, errors):
    path = base / relative_path
    if not relative_path:
        errors.append("missing file path")
    elif not path.exists():
        errors.append(f"missing file: {relative_path}")
    return path


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: validate_agent_profile.py PROFILE.yaml")

    profile_path = Path(sys.argv[1])
    base = profile_path.parent
    profile = load_yaml(profile_path)
    errors = []

    if profile.get("schema") != "valo.agent_profile.v0.1":
        errors.append("profile schema must be valo.agent_profile.v0.1")

    require_file(base, profile.get("schema_file", ""), errors)
    require_file(base, profile["registry"]["registry_file"], errors)
    require_file(base, profile["registry"]["revocation_registry"], errors)
    require_file(base, profile["registry"]["contestability_record"], errors)
    require_file(base, profile["delegation"]["budget_file"], errors)
    require_file(base, profile["revenue"]["ledger_file"], errors)
    require_file(base, profile["reputation"]["rep_receipt"], errors)
    require_file(base, profile["risk"]["risk_receipt"], errors)

    receipt_total = 0
    for receipt in profile["receipts"]["public_recent"]:
        receipt_path = require_file(base, receipt["receipt_file"], errors)
        if receipt_path.exists():
            receipt_doc = load_yaml(receipt_path)
            if receipt_doc.get("receipt_id") != receipt["receipt_id"]:
                errors.append(f"receipt id mismatch: {receipt['receipt_id']}")
            receipt_total += receipt_doc.get("value", {}).get("revenue_units", 0)

    claimed = profile["revenue"]["verified_amount"]
    if receipt_total != claimed:
        errors.append(f"revenue mismatch: receipts={receipt_total} profile={claimed}")

    budget_path = base / profile["budget"]["budget_file"]
    if budget_path.exists():
        budget = load_yaml(budget_path)
        grant = budget["budget_grant"]
        if grant["budget_granted"] - grant["budget_spent"] != grant["budget_remaining"]:
            errors.append("budget arithmetic mismatch")
        spend_total = sum(item.get("amount", 0) for item in budget.get("spend_receipts", []))
        if spend_total != grant["budget_spent"]:
            errors.append(f"budget spend mismatch: receipts={spend_total} budget_spent={grant['budget_spent']}")

    registry_path = base / profile["registry"]["registry_file"]
    if registry_path.exists():
        registry = load_yaml(registry_path)
        matching = [agent for agent in registry.get("agents", []) if agent.get("agent_id") == profile["agent"]["agent_id"]]
        if not matching:
            errors.append("agent missing from registry")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)

    print("agent profile proof bundle valid")


if __name__ == "__main__":
    main()
