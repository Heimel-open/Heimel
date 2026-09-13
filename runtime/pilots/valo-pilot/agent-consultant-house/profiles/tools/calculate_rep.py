#!/usr/bin/env python3
"""Calculate prototype VALO REP from profile, value ledger and BARO risk."""

from pathlib import Path
import sys

try:
    import yaml
except ImportError as exc:
    raise SystemExit("PyYAML is required: python -m pip install pyyaml") from exc


def load_yaml(path):
    return yaml.safe_load(Path(path).read_text())


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def main():
    if len(sys.argv) != 4:
        raise SystemExit("usage: calculate_rep.py PROFILE.yaml VALUE_LEDGER.yaml OUTPUT.yaml")

    profile_path = Path(sys.argv[1])
    ledger_path = Path(sys.argv[2])
    output_path = Path(sys.argv[3])
    profile = load_yaml(profile_path)
    ledger = load_yaml(ledger_path)

    calc = ledger["calculation"]
    receipt_count = int(calc["receipt_count"])
    allow_count = int(calc["allow_count"])
    step_up_count = int(calc["step_up_count"])
    deny_count = int(calc["deny_count"])
    evidence = float(calc["average_evidence_strength"])
    risk = float(profile["risk"]["risk_surface_score"])
    revenue = int(calc["verified_revenue_units"])
    followers_delta = int(calc["followers_delta_receipted"])

    receipt_success = (allow_count + step_up_count) / receipt_count if receipt_count else 0.0
    risk_adjustment = 1.0 - risk
    value_signal = clamp((revenue / 10000.0) + (followers_delta / 1000.0))
    safe_escalation = step_up_count / receipt_count if receipt_count else 0.0
    deny_penalty = min(0.25, deny_count * 0.05)

    score = (
        evidence * 0.35
        + receipt_success * 0.25
        + risk_adjustment * 0.20
        + value_signal * 0.15
        + safe_escalation * 0.05
        - deny_penalty
    )
    score = round(clamp(score), 3)

    rep = {
        "schema": "valo.rep_calculation.v0.1",
        "rep_id": "research_01_rep_v0_1",
        "profile_id": profile["id"],
        "agent_id": profile["agent"]["agent_id"],
        "status": "calculated",
        "rep_score": score,
        "inputs": {
            "receipt_count": receipt_count,
            "allow_count": allow_count,
            "step_up_count": step_up_count,
            "deny_count": deny_count,
            "verified_revenue_units": revenue,
            "evidence_strength_average": evidence,
            "baro_risk_surface_score": risk,
            "followers": profile["agent_dna"]["followers"],
            "followers_delta_receipted": followers_delta,
        },
        "formula_v0_1": {
            "description": "Prototype REP weights receipt-backed value, evidence strength, safe escalation, and risk-adjusted public trust.",
            "weights": {
                "evidence_strength": 0.35,
                "receipt_success": 0.25,
                "risk_adjustment": 0.20,
                "value_signal": 0.15,
                "safe_escalation": 0.05,
            },
            "computed_score": score,
        },
        "risk_adjustment": {
            "source_file": profile["risk"]["risk_receipt"],
            "score": risk,
            "treatment": "lower_risk_increases_rep",
        },
        "receipt_sources": [r["receipt_file"] for r in profile["receipts"]["public_recent"]],
        "rules": {
            "receipt_backed_only": True,
            "step_up_counts_as_safety_when_authority_preserved": True,
            "unreceipted_claims_excluded": True,
            "contested_receipts_require_recalculation": True,
        },
    }

    output_path.write_text(yaml.safe_dump(rep, sort_keys=False))
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
