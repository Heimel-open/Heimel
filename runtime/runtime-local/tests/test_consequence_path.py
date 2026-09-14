from datetime import UTC, datetime, timedelta
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from local_runtime import ConsequenceDenied, ConsequenceRejected, LocalRuntime


def action(amount=10):
    return {
        "type": "payment",
        "actor_id": "agent-1",
        "target": "merchant-1",
        "payload": {"amount": amount, "currency": "EUR"},
    }


def test_pending_action_cannot_report_success():
    runtime = LocalRuntime()
    aid = runtime.submit(action())

    result = runtime.result(aid)

    assert result.status == "FAILURE"
    assert result.receipt_ref is None
    assert result.error.startswith("NOT_EXECUTED")


def test_deny_cannot_become_effect():
    runtime = LocalRuntime()
    aid = runtime.submit(action())

    with pytest.raises(ConsequenceDenied):
        runtime.authorize(aid, now=datetime(2026, 9, 14, tzinfo=UTC))

    assert runtime.result(aid).status == "FAILURE"
    assert runtime.receipt(aid) is None
    assert "EFFECT_EXECUTED" not in [e.kind for e in runtime.stream(aid)]


def test_allow_requires_permit_and_records_evidence():
    runtime = LocalRuntime()
    aid = runtime.submit(action())
    runtime.grant(aid)
    now = datetime(2026, 9, 14, tzinfo=UTC)

    permit = runtime.authorize(aid, now=now)
    result = runtime.execute(aid, permit, now=now + timedelta(seconds=1))

    assert result.status == "SUCCESS"
    assert result.receipt_ref is not None
    receipt = runtime.receipt(aid)
    assert receipt is not None
    assert receipt.receipt_id == result.receipt_ref
    kinds = [e.kind for e in runtime.stream(aid)]
    assert kinds.index("DECISION") < kinds.index("PERMIT_CONSUMED")
    assert kinds.index("PERMIT_CONSUMED") < kinds.index("EFFECT_EXECUTED")
    assert kinds.index("EFFECT_EXECUTED") < kinds.index("EVIDENCE_RECORDED")


def test_revocation_after_authorization_stops_effect():
    runtime = LocalRuntime()
    aid = runtime.submit(action())
    runtime.grant(aid)
    now = datetime(2026, 9, 14, tzinfo=UTC)
    permit = runtime.authorize(aid, now=now)

    runtime.revoke(aid)

    with pytest.raises(ConsequenceRejected, match="authority state changed"):
        runtime.execute(aid, permit, now=now + timedelta(seconds=1))
    assert runtime.receipt(aid) is None
    assert "EFFECT_EXECUTED" not in [e.kind for e in runtime.stream(aid)]


def test_expired_permit_stops_effect():
    runtime = LocalRuntime()
    aid = runtime.submit(action())
    runtime.grant(aid)
    now = datetime(2026, 9, 14, tzinfo=UTC)
    permit = runtime.authorize(aid, now=now, ttl_seconds=1)

    with pytest.raises(ConsequenceRejected, match="permit expired"):
        runtime.execute(aid, permit, now=now + timedelta(seconds=2))
    assert runtime.receipt(aid) is None


def test_effect_mismatch_stops_effect():
    runtime = LocalRuntime()
    aid = runtime.submit(action(amount=10))
    runtime.grant(aid)
    now = datetime(2026, 9, 14, tzinfo=UTC)
    permit = runtime.authorize(aid, now=now)

    with pytest.raises(ConsequenceRejected, match="exact effect"):
        runtime.execute(
            aid,
            permit,
            now=now + timedelta(seconds=1),
            effect=action(amount=11),
        )
    assert runtime.receipt(aid) is None


def test_permit_replay_stops_second_effect():
    runtime = LocalRuntime()
    aid = runtime.submit(action())
    runtime.grant(aid)
    now = datetime(2026, 9, 14, tzinfo=UTC)
    permit = runtime.authorize(aid, now=now)

    first = runtime.execute(aid, permit, now=now + timedelta(seconds=1))
    assert first.status == "SUCCESS"

    with pytest.raises(ConsequenceRejected, match="already consumed"):
        runtime.execute(aid, permit, now=now + timedelta(seconds=2))


def test_replay_binds_effect_decision_enforcement_and_evidence():
    runtime = LocalRuntime()
    aid = runtime.submit(action())
    runtime.grant(aid)
    now = datetime(2026, 9, 14, tzinfo=UTC)
    permit = runtime.authorize(aid, now=now)
    runtime.execute(aid, permit, now=now + timedelta(seconds=1))

    replay = runtime.replay(aid)

    assert replay["state"] == "EXECUTED"
    assert replay["receipt"] is not None
    kinds = [e.kind for e in replay["events"]]
    for required in ("ACTION_REQUESTED", "DECISION", "PERMIT_CONSUMED", "EFFECT_EXECUTED", "EVIDENCE_RECORDED"):
        assert required in kinds
