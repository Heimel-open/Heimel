#!/usr/bin/env python3
"""Offline public proof of the complete local Heimel consequence path."""
from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime" / "runtime-local"
sys.path.insert(0, str(RUNTIME))

from local_runtime import ConsequenceDenied, ConsequenceRejected, LocalRuntime  # noqa: E402
from metering import default_billable_executed_consequence, governed_consequence_event  # noqa: E402


def effect(amount: int) -> dict[str, object]:
    return {
        "type": "payment",
        "actor_id": "public-e2e-agent",
        "target": "public-e2e-merchant",
        "payload": {"amount": amount, "currency": "EUR"},
    }


def main() -> int:
    now = datetime(2026, 9, 14, 12, 0, tzinfo=UTC)
    runtime = LocalRuntime()

    allowed_id = runtime.submit(effect(10))
    runtime.grant(allowed_id)
    allowed_permit = runtime.authorize(allowed_id, now=now)
    allowed_result = runtime.execute(allowed_id, allowed_permit, now=now)
    allowed_replay = runtime.replay(allowed_id)
    allowed_meter = governed_consequence_event(runtime, allowed_id, tenant_or_organization="public-e2e")

    assert allowed_result.status == "SUCCESS"
    assert allowed_result.receipt_ref
    assert allowed_replay["state"] == "EXECUTED"
    assert allowed_replay["receipt"] is not None
    assert default_billable_executed_consequence(allowed_meter)

    revoked_id = runtime.submit(effect(20))
    runtime.grant(revoked_id)
    stale_permit = runtime.authorize(revoked_id, now=now)
    runtime.revoke(revoked_id)
    try:
        runtime.execute(revoked_id, stale_permit, now=now)
    except ConsequenceRejected:
        pass
    else:
        raise AssertionError("revoked authority allowed a stale permit to execute")

    assert runtime.receipt(revoked_id) is None
    assert "EFFECT_EXECUTED" not in [event.kind for event in runtime.stream(revoked_id)]

    denied_id = runtime.submit(effect(30))
    try:
        runtime.authorize(denied_id, now=now)
    except ConsequenceDenied:
        pass
    else:
        raise AssertionError("unauthorized effect was not denied")

    denied_meter = governed_consequence_event(runtime, denied_id, tenant_or_organization="public-e2e")
    assert denied_meter["decision"] == "DENY"
    assert denied_meter["enforcement_result"] == "NOT_ATTEMPTED"
    assert denied_meter["outcome_state"] == "NONE"
    assert denied_meter["evidence_reference"] is None
    assert not default_billable_executed_consequence(denied_meter)

    replayed_meter = governed_consequence_event(runtime, allowed_id, tenant_or_organization="public-e2e")
    assert replayed_meter["event_id"] == allowed_meter["event_id"]

    proof = {
        "status": "PASS",
        "network_required": False,
        "commercial_entitlement_required": False,
        "allow": {
            "result": allowed_result.status,
            "receipt": allowed_result.receipt_ref,
            "meter_event": allowed_meter["event_id"],
            "billable_by_default": True,
        },
        "revocation": {
            "stale_permit_rejected": True,
            "effect_occurred": False,
        },
        "deny": {
            "decision": denied_meter["decision"],
            "effect_occurred": False,
            "billable_by_default": False,
        },
        "replay": {
            "same_meter_event_id": True,
            "receipt_preserved": True,
        },
    }
    print(json.dumps(proof, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
