"""
VACS profile v0.1 tests.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from policy_engine import ACSPolicyEngine, Decision
from profile import VACSProfileValidator


def load_profile_packet():
    with open(Path(__file__).resolve().parents[1] / "examples" / "vacs_profile_packet.json") as f:
        return json.load(f)


def test_vacs_profile_validates_authority_envelope():
    packet = load_profile_packet()
    validator = VACSProfileValidator()

    assert validator.validate(packet) is True, validator.get_errors()


def test_vacs_profile_requires_target_inside_boundary():
    packet = load_profile_packet()
    packet["boundary"]["resources"] = ["another_account"]
    validator = VACSProfileValidator()

    assert validator.validate(packet) is False
    assert "boundary resources" in str(validator.get_errors())


def test_vacs_profile_requires_signoff_when_policy_requires_it():
    packet = load_profile_packet()
    packet["principal"]["human_signoff"] = {"required": False}
    validator = VACSProfileValidator()

    assert validator.validate(packet) is False
    assert "Policy requires signoff" in str(validator.get_errors())


def test_vacs_profile_requires_hard_signoff_fields():
    packet = load_profile_packet()
    del packet["principal"]["human_signoff"]["signature"]
    validator = VACSProfileValidator()

    assert validator.validate(packet) is False
    assert "signature" in str(validator.get_errors())


def test_vacs_profile_rejects_revoked_signoff():
    packet = load_profile_packet()
    packet["principal"]["human_signoff"]["status"] = "revoked"
    validator = VACSProfileValidator()

    assert validator.validate(packet) is False
    assert "revoked" in str(validator.get_errors())


def test_vacs_profile_requires_policy_hash():
    packet = load_profile_packet()
    packet["policy"]["policy_hash"] = "not-a-hash"
    validator = VACSProfileValidator()

    assert validator.validate(packet) is False
    assert "policy_hash" in str(validator.get_errors())


def test_vacs_profile_does_not_add_decision_primitives():
    packet = load_profile_packet()
    decision = ACSPolicyEngine().evaluate(packet)

    assert decision == Decision.STEP_UP
    assert packet["decision"] == "STEP_UP"
    assert packet["decision"] != "DEGRADE"


if __name__ == "__main__":
    test_vacs_profile_validates_authority_envelope()
    test_vacs_profile_requires_target_inside_boundary()
    test_vacs_profile_requires_signoff_when_policy_requires_it()
    test_vacs_profile_requires_hard_signoff_fields()
    test_vacs_profile_rejects_revoked_signoff()
    test_vacs_profile_requires_policy_hash()
    test_vacs_profile_does_not_add_decision_primitives()
    print("All VACS profile v0.1 tests passed")
