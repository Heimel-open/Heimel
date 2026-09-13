#!/usr/bin/env python3
"""Calculate the visible BARO risk surface for an agent profile.

Prototype calculator. It derives a deterministic risk surface from declared
profile categories, blocked surfaces, receipt decisions and receipt deltas.
"""

from pathlib import Path
import sys

try:
    import yaml
except ImportError as exc:
    raise SystemExit("PyYAML is required: python -m pip install pyyaml") from exc

BASE_CATEGORY_SCORES = {
    "reputation": 0.21,
    "governance_advice": 0.28,
    "public_content": 0.19,
    "strategy_output": 0.29,
}


def load_yaml(path):
    return yaml.safe_load(Path(path).read_text())


def risk_level(score):
    if score < 0.2:
        return "low"
    if score < 0.35:
        return "low_to_medium"
    if score < 0.6:
        return "medium"
    return "high"


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: calculate_baro_risk.py PROFILE.yaml OUTPUT.yaml")

    profile_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    base = profile_path.parent
    profile = load_yaml(profile_path)

    categories = {
        category: BASE_CATEGORY_SCORES.get(category, 0.25)
        for category in profile["risk"].get("risk_categories", [])
    }
    category_mean = round(sum(categories.values()) / max(len(categories), 1), 3)

    source_receipts = []
    step_up_count = 0
    for entry in profile["receipts"]["public_recent"]:
        receipt = load_yaml(base / entry["receipt_file"])
        decision = receipt.get("decision")
        if decision == "STEP_UP":
            step_up_count += 1
        source_receipts.append({
            "receipt_id": receipt["receipt_id"],
            "risk_delta": receipt.get("risk", {}).get("baro_risk_delta", 0),
            "decision": decision,
        })

    # The public profile score is category-first. STEP_UP decisions stay visible
    # through source_receipts and controls instead of being hidden in one number.
    score = category_mean

    doc = {
        "schema": "valo.baro_risk_profile.v0.1",
        "risk_id": "research_01_baro_risk",
        "profile_id": profile["id"],
        "agent_id": profile["agent"]["agent_id"],
        "source": "BARO",
        "status": "prototype_calculated",
        "risk_surface_score": score,
        "risk_level": risk_level(score),
        "visible_to_public_profile": True,
        "risk_categories": categories,
        "blocked_risk_categories": {
            category: "blocked" for category in profile["risk"].get("blocked_risk_categories", [])
        },
        "source_receipts": source_receipts,
        "controls": {
            "baro_route": "WATCH" if step_up_count else "PASS",
            "step_up_required_for_high_risk": True,
            "human_face_media_blocked": "human_face_media" in profile.get("blocked_surfaces", []),
            "fake_human_persona_blocked": "fake_human_persona" in profile.get("blocked_surfaces", []),
            "unreceipted_revenue_claims_blocked": "unreceipted_revenue_claims" in profile.get("blocked_surfaces", []),
        },
        "calculation_note": (
            "Prototype BARO risk surface is derived from the allowed/blocked surface map, "
            "recent receipt decisions, and risk deltas. It is not yet connected to live BARO runtime signals."
        ),
    }

    output_path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    print(f"BARO risk surface written: {output_path}")


if __name__ == "__main__":
    main()
