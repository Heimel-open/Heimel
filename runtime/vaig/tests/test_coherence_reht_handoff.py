import copy
import sys
from pathlib import Path

import pytest

from vaig.coherence_evaluation import CoherenceEvaluationResultV1, EvaluationStatus
from vaig.reht_handoff import (
    COHERENCE_EVIDENCE_KEY,
    bind_coherence_result,
    read_coherence_binding,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "vacs" / "src"))
from receipt import ACSReceiptGenerator, Decision


def _result(status=EvaluationStatus.PASS):
    reasons = () if status is EvaluationStatus.PASS else ("TEST_BLOCK",)
    return CoherenceEvaluationResultV1(
        status=status,
        reason_codes=reasons,
        input_digest="sha256:" + "a" * 64,
        replay_packet_digest="sha256:" + "b" * 64,
    )


def _packet():
    return {
        "packet_id": "pkt-1",
        "intent": {"action": "read", "target": "report"},
        "evidence": {"sources": [{"hash": "sha256:source"}]},
        "policy": {"policy_id": "p-1"},
    }


def test_pass_result_binds_without_mutating_original_packet():
    packet = _packet()
    bound = bind_coherence_result(packet, _result())

    assert COHERENCE_EVIDENCE_KEY not in packet["evidence"]
    binding = read_coherence_binding(bound)
    assert binding is not None
    assert binding.status is EvaluationStatus.PASS
    assert binding.execution_authority is False
    assert binding.requires_reht_clearance is True
    assert binding.can_execute is False


def test_open_or_fail_cannot_be_promoted_into_reht_handoff():
    with pytest.raises(ValueError, match="must PASS"):
        bind_coherence_result(_packet(), _result(EvaluationStatus.OPEN))
    with pytest.raises(ValueError, match="must PASS"):
        bind_coherence_result(_packet(), _result(EvaluationStatus.FAIL))


def test_non_pass_can_be_bound_only_for_audit_packet():
    bound = bind_coherence_result(
        _packet(),
        _result(EvaluationStatus.OPEN),
        require_pass=False,
    )
    binding = read_coherence_binding(bound)
    assert binding is not None
    assert binding.status is EvaluationStatus.OPEN
    assert binding.can_execute is False


def test_binding_digest_detects_tampering():
    bound = bind_coherence_result(_packet(), _result())
    tampered = copy.deepcopy(bound)
    tampered["evidence"][COHERENCE_EVIDENCE_KEY]["result"]["status"] = "OPEN"

    with pytest.raises(ValueError, match="result_digest mismatch"):
        read_coherence_binding(tampered)


def test_acs_receipt_exposes_and_hash_binds_coherence_result():
    generator = ACSReceiptGenerator()
    plain = generator.generate(_packet(), Decision.ALLOW)
    bound_packet = bind_coherence_result(_packet(), _result())
    bound = generator.generate(bound_packet, Decision.ALLOW)
    binding = read_coherence_binding(bound_packet)

    assert binding is not None
    assert bound["vaig_coherence_result_digest"] == binding.result_digest
    assert bound["vaig_coherence_status"] == "PASS"
    assert bound["input_hash"] != plain["input_hash"]
    assert bound["signature"] != plain["signature"]


def test_session_receipt_signature_covers_coherence_fields():
    generator = ACSReceiptGenerator()
    packet = bind_coherence_result(_packet(), _result())
    receipt = generator.generate_session_bound(
        packet,
        Decision.ALLOW,
        session_id="session-1",
        key_id="key-1",
        session_key=b"secret",
    )
    assert generator.verify_session_bound(receipt, b"secret") is True

    tampered = copy.deepcopy(receipt)
    tampered["vaig_coherence_status"] = "OPEN"
    assert generator.verify_session_bound(tampered, b"secret") is False
