from datetime import UTC, datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from local_runtime import ConsequenceDenied, LocalRuntime
from metering import default_billable_executed_consequence, governed_consequence_event


def action(amount=10):
    return {
        "type": "payment",
        "actor_id": "agent-1",
        "target": "merchant-1",
        "payload": {"amount": amount, "currency": "EUR"},
    }


def test_success_projects_one_stable_billable_consequence_event():
    runtime = LocalRuntime()
    aid = runtime.submit(action())
    runtime.grant(aid)
    now = datetime(2026, 9, 14, tzinfo=UTC)
    permit = runtime.authorize(aid, now=now)
    runtime.execute(aid, permit, now=now)

    first = governed_consequence_event(runtime, aid, tenant_or_organization="org-1")
    second = governed_consequence_event(runtime, aid, tenant_or_organization="org-1")

    assert first["event_id"] == second["event_id"]
    assert first["decision"] == "ALLOW"
    assert first["enforcement_result"] == "EXECUTED"
    assert first["outcome_state"] == "SUCCESS"
    assert first["evidence_reference"]
    assert default_billable_executed_consequence(first)


def test_deny_is_governed_event_but_not_executed_or_billable_by_default():
    runtime = LocalRuntime()
    aid = runtime.submit(action())

    try:
        runtime.authorize(aid, now=datetime(2026, 9, 14, tzinfo=UTC))
    except ConsequenceDenied:
        pass
    else:
        raise AssertionError("expected consequence denial")

    event = governed_consequence_event(runtime, aid)

    assert event["decision"] == "DENY"
    assert event["enforcement_result"] == "NOT_ATTEMPTED"
    assert event["outcome_state"] == "NONE"
    assert event["evidence_reference"] is None
    assert not default_billable_executed_consequence(event)
