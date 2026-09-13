#!/usr/bin/env python3
"""Check that an agent profile update is allowed by the proof bundle.

This is a lightweight stand-in for VACS-gated profile updates. It enforces the
same core rule: no profile-changing action without authority, budget, receipt,
no revocation and no open contest.
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
        raise SystemExit("usage: check_profile_update_gate.py PROFILE.yaml")

    profile_path = Path(sys.argv[1])
    base = profile_path.parent
    profile = load_yaml(profile_path)
    errors = []

    revocation = load_yaml(base / profile["revocation"]["revocation_registry"])
    contest = load_yaml(base / profile["accountability"]["contestability_file"])
    budget = load_yaml(base / profile["budget"]["budget_file"])

    if profile["revocation"].get("revoked"):
        errors.append("profile is revoked")
    if revocation.get("revoked_agents"):
        errors.append("agent has revocation records")
    if contest.get("open_contests"):
        errors.append("profile has open contests")

    budget_grant = budget["budget_grant"]
    if budget_grant["budget_remaining"] < 0:
        errors.append("budget remaining is negative")
    if budget_grant["budget_spent"] > budget_grant["budget_granted"]:
        errors.append("budget spent exceeds grant")
    if not budget_grant.get("spend_requires_receipt"):
        errors.append("budget spend does not require receipt")

    if not profile["session_control"].get("session_bound_required"):
        errors.append("session-bound control is disabled")
    if not profile["controls"].get("receipt") == "required":
        errors.append("profile does not require receipts")

    if errors:
        for error in errors:
            print(f"DENY: {error}")
        raise SystemExit(1)

    print("ALLOW: profile update gate passed")


if __name__ == "__main__":
    main()
