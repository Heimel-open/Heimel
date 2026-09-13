"""
VACS adapter handoff tests.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from adapter import VACSExecutionHandoffBuilder, VACSExecutionHandoffError


def load_packet(name):
    with open(Path(__file__).resolve().parents[1] / "examples" / name) as f:
        return json.load(f)


def test_builds_github_handoff_for_allowed_vacs_packet():
    packet = load_packet("vacs_github_handoff_packet.json")
    handoff = VACSExecutionHandoffBuilder().build(packet, "github", "pull_request")

    assert handoff["handoff_version"] == "vacs-handoff-v0.1"
    assert handoff["adapter"] == "github"
    assert handoff["method"] == "pull_request"
    assert handoff["decision"] == "ALLOW"
    assert handoff["intent"]["target"] == "repo:nsolland/VAIG"
    assert handoff["receipt_required"] is True


def test_blocks_handoff_when_decision_is_not_allow():
    packet = load_packet("vacs_profile_packet.json")

    try:
        VACSExecutionHandoffBuilder().build(packet, "github", "pull_request")
        assert False, "Expected handoff error"
    except VACSExecutionHandoffError as exc:
        assert "decision == ALLOW" in str(exc)


def test_blocks_handoff_without_receipt_path():
    packet = load_packet("vacs_github_handoff_packet.json")

    try:
        VACSExecutionHandoffBuilder().build(packet, "github", "pull_request", receipt_path_available=False)
        assert False, "Expected handoff error"
    except VACSExecutionHandoffError as exc:
        assert "receipt path" in str(exc)


def test_blocks_unsupported_adapter_method():
    packet = load_packet("vacs_github_handoff_packet.json")

    try:
        VACSExecutionHandoffBuilder().build(packet, "github", "delete_branch")
        assert False, "Expected handoff error"
    except VACSExecutionHandoffError as exc:
        assert "Unsupported method" in str(exc)


if __name__ == "__main__":
    test_builds_github_handoff_for_allowed_vacs_packet()
    test_blocks_handoff_when_decision_is_not_allow()
    test_blocks_handoff_without_receipt_path()
    test_blocks_unsupported_adapter_method()
    print("All VACS adapter handoff tests passed")
