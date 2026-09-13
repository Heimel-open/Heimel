"""
ACS v0.1 Tests
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evidence_gap import ACSEvidenceGapAnalyzer
from hashlog import ACSHashLog
from policy_engine import ACSPolicyEngine, Decision
from receipt import ACSReceiptGenerator
from validator import ACSValidator


def load_example(name):
    with open(Path(__file__).resolve().parents[1] / "examples" / name) as f:
        return json.load(f)


def test_validator():
    v = ACSValidator()

    packet = load_example("allow.json")
    assert v.validate(packet) is True
    assert len(v.get_errors()) == 0

    bad = packet.copy()
    bad["confidence"] = 1.5
    assert v.validate(bad) is False
    assert "Confidence must be 0-1" in str(v.get_errors())

    bad_source = json.loads(json.dumps(packet))
    bad_source["evidence"]["sources"][0]["type"] = "unsupported"
    assert v.validate(bad_source) is False
    assert "Invalid evidence source" in str(v.get_errors())

    print("Validator tests passed")


def test_policy_engine():
    pe = ACSPolicyEngine()

    assert pe.evaluate(load_example("allow.json")) == Decision.ALLOW
    assert pe.evaluate(load_example("modify.json")) == Decision.MODIFY
    assert pe.evaluate(load_example("defer.json")) == Decision.DEFER
    assert pe.evaluate(load_example("deny.json")) == Decision.DENY
    assert pe.evaluate(load_example("step_up.json")) == Decision.STEP_UP
    assert pe.evaluate(load_example("halt.json")) == Decision.HALT

    print("Policy engine tests passed")


def test_receipt():
    rg = ACSReceiptGenerator()
    packet = load_example("allow.json")

    receipt = rg.generate(packet, Decision.ALLOW)
    assert "receipt_id" in receipt
    assert receipt["decision"] == "ALLOW"
    assert receipt["action_hash"].startswith("sha256:")

    print("Receipt tests passed")


def test_hashlog():
    hl = ACSHashLog()
    rg = ACSReceiptGenerator()
    packet = load_example("allow.json")

    receipt = rg.generate(packet, Decision.ALLOW)
    entry = hl.append(receipt)

    assert hl.get_length() == 1
    assert hl.verify_chain() is True
    assert "entry_hash" in entry

    print("Hash log tests passed")


def test_evidence_gap():
    ega = ACSEvidenceGapAnalyzer()

    assert ega.calculate(load_example("allow.json")) == 0.0
    assert ega.calculate(load_example("defer.json")) == 0.67
    assert ega.calculate(load_example("deny.json")) == 0.33

    print("Evidence gap tests passed")


def test_full_pipeline():
    v = ACSValidator()
    pe = ACSPolicyEngine()
    rg = ACSReceiptGenerator()
    hl = ACSHashLog()
    ega = ACSEvidenceGapAnalyzer()

    examples = [
        "allow.json",
        "modify.json",
        "defer.json",
        "deny.json",
        "step_up.json",
        "halt.json",
    ]

    for example in examples:
        packet = load_example(example)
        packet["evidence"]["evidence_gap"] = ega.calculate(packet)

        assert v.validate(packet) is True, v.get_errors()
        decision = pe.evaluate(packet)
        assert packet["decision"] == decision.value
        receipt = rg.generate(packet, decision)
        entry = hl.append(receipt)

        assert "entry_hash" in entry

    assert hl.get_length() == 6
    assert hl.verify_chain() is True

    print("Full pipeline tests passed")


if __name__ == "__main__":
    test_validator()
    test_policy_engine()
    test_receipt()
    test_hashlog()
    test_evidence_gap()
    test_full_pipeline()
    print("\nAll ACS v0.1 tests passed")
