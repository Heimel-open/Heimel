from datetime import UTC, datetime, timedelta
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from local_runtime import EvidenceRecordingFailed, LocalRuntime


def test_effect_without_evidence_is_not_admitted_as_success(monkeypatch):
    runtime = LocalRuntime()
    aid = runtime.submit({
        "type": "payment",
        "actor_id": "agent-1",
        "target": "merchant-1",
        "payload": {"amount": 10, "currency": "EUR"},
    })
    runtime.grant(aid)
    now = datetime(2026, 9, 14, tzinfo=UTC)
    permit = runtime.authorize(aid, now=now)

    def fail_record(*_args, **_kwargs):
        raise OSError("simulated evidence store failure")

    monkeypatch.setattr(runtime, "_record_receipt", fail_record)

    with pytest.raises(EvidenceRecordingFailed):
        runtime.execute(aid, permit, now=now + timedelta(seconds=1))

    result = runtime.result(aid)
    replay = runtime.replay(aid)
    kinds = [event.kind for event in replay["events"]]

    assert result.status == "FAILURE"
    assert result.receipt_ref is None
    assert replay["state"] == "EFFECT_OCCURRED_UNATTESTED"
    assert replay["receipt"] is None
    assert "EFFECT_EXECUTED" in kinds
    assert "EVIDENCE_FAILED" in kinds
    assert "EVIDENCE_RECORDED" not in kinds
