from datetime import UTC, datetime
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evidence_admissibility import EvidenceAdmissibilityDecision, EvidenceRecord
from local_runtime import ConsequenceDenied, LocalRuntime


def _required_action():
    return {
        "type": "payment",
        "actor_id": "agent-1",
        "target": "merchant-1",
        "payload": {"amount": 10, "currency": "EUR"},
        "evidence_requirement": "REQUIRED",
    }


def _evidence(*, sufficiency="SUFFICIENT", content_hash=None, derivation_hash=None):
    return EvidenceRecord(
        source_ref="cas://source-1",
        content_hash=content_hash or "sha256:" + "a" * 64,
        read_ref="bytes:0-128",
        derivation_hash=derivation_hash or "sha256:" + "b" * 64,
        evaluator_id="heimel-evidence",
        evaluator_version="1",
        sufficiency=sufficiency,
    )


def test_required_evidence_fail_closes_before_authorization():
    runtime = LocalRuntime()
    aid = runtime.submit(_required_action())
    runtime.grant(aid)

    with pytest.raises(ConsequenceDenied, match="evidence .*admissible"):
        runtime.authorize(aid, now=datetime(2026, 9, 18, tzinfo=UTC))

    replay = runtime.replay(aid)
    assert replay["state"] == "DENIED"
    assert replay["evidence_admissibility"].decision is EvidenceAdmissibilityDecision.INSUFFICIENT
    assert any(event.kind == "EVIDENCE_ADMISSIBILITY" for event in replay["events"])


def test_admissible_evidence_is_bound_into_authorization():
    runtime = LocalRuntime()
    aid = runtime.submit(_required_action())
    runtime.grant(aid)

    evidence_result = runtime.evaluate_evidence(aid, _evidence())
    permit = runtime.authorize(aid, now=datetime(2026, 9, 18, tzinfo=UTC))

    assert evidence_result.decision is EvidenceAdmissibilityDecision.ADMIT
    assert evidence_result.derivation_receipt is not None
    assert permit.reht_ref.startswith("sha256:")
    decision_events = [event for event in runtime.stream(aid) if event.kind == "DECISION"]
    assert decision_events[-1].payload["derivation_receipt"] == evidence_result.derivation_receipt


def test_insufficient_evidence_cannot_be_promoted_by_authority_grant():
    runtime = LocalRuntime()
    aid = runtime.submit(_required_action())
    runtime.grant(aid)

    result = runtime.evaluate_evidence(aid, _evidence(sufficiency="INSUFFICIENT"))
    assert result.decision is EvidenceAdmissibilityDecision.INSUFFICIENT

    with pytest.raises(ConsequenceDenied, match="evidence .*admissible"):
        runtime.authorize(aid, now=datetime(2026, 9, 18, tzinfo=UTC))


@pytest.mark.parametrize(
    ("content_hash", "derivation_hash"),
    [
        ("sha256:", "sha256:" + "b" * 64),
        ("sha256:not-a-digest", "sha256:" + "b" * 64),
        ("sha256:" + "a" * 63, "sha256:" + "b" * 64),
        ("sha256:" + "a" * 65, "sha256:" + "b" * 64),
        ("sha256:" + "g" * 64, "sha256:" + "b" * 64),
        ("sha256:" + "a" * 64, "sha256:"),
        ("sha256:" + "a" * 64, "sha256:not-a-digest"),
        ("sha256:" + "a" * 64, "sha256:" + "g" * 64),
    ],
)
def test_malformed_required_evidence_digest_is_refused(content_hash, derivation_hash):
    runtime = LocalRuntime()
    aid = runtime.submit(_required_action())
    runtime.grant(aid)

    result = runtime.evaluate_evidence(
        aid,
        _evidence(content_hash=content_hash, derivation_hash=derivation_hash),
    )
    assert result.decision is EvidenceAdmissibilityDecision.REFUSE
    assert result.reason == "unsupported_evidence_digest"

    with pytest.raises(ConsequenceDenied, match="evidence .*admissible"):
        runtime.authorize(aid, now=datetime(2026, 9, 18, tzinfo=UTC))
