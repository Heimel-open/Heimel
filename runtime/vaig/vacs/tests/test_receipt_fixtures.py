"""
ACS receipt fixture tests.
"""

import json
from pathlib import Path


REQUIRED = {"receipt_id", "packet_id", "action_hash", "input_hash", "policy_hash", "decision", "timestamp"}
EXPECTED_DECISIONS = {"ALLOW", "MODIFY", "DEFER", "DENY", "STEP_UP", "HALT"}


def test_receipt_fixtures_cover_all_decisions():
    fixture_dir = Path(__file__).resolve().parents[1] / "fixtures" / "receipts"
    receipts = []

    for path in fixture_dir.glob("*_receipt.json"):
        with path.open() as f:
            receipt = json.load(f)
        assert REQUIRED.issubset(receipt.keys()), path.name
        assert receipt["action_hash"].startswith("sha256:"), path.name
        assert receipt["input_hash"].startswith("sha256:"), path.name
        assert receipt["policy_hash"].startswith("sha256:"), path.name
        receipts.append(receipt)

    assert {receipt["decision"] for receipt in receipts} == EXPECTED_DECISIONS


if __name__ == "__main__":
    test_receipt_fixtures_cover_all_decisions()
    print("All ACS receipt fixtures passed")
