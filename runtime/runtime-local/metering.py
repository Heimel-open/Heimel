"""Canonical local projection for Heimel governed-consequence metering.

This module turns the existing governed consequence evidence into one stable event.
It does not decide billing. Commercial contracts select which event outcomes are
billable; replaying the same action produces the same event_id.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Optional


def _digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def governed_consequence_event(
    runtime: Any,
    action_id: str,
    *,
    tenant_or_organization: Optional[str] = None,
) -> dict[str, object]:
    """Project one action's governed consequence state into the canonical meter event."""
    replay = runtime.replay(action_id)
    events = list(replay["events"])
    decision_event = next((event for event in reversed(events) if event.kind == "DECISION"), None)
    if decision_event is None:
        raise ValueError("action has no governed consequence decision")

    decision = str(decision_event.payload["decision"])
    effect_executed = any(event.kind == "EFFECT_EXECUTED" for event in events)
    evidence_failed = any(event.kind == "EVIDENCE_FAILED" for event in events)
    receipt = replay.get("receipt")

    if effect_executed:
        enforcement_result = "EXECUTED"
    elif decision == "ALLOW":
        enforcement_result = "NOT_ATTEMPTED"
    else:
        enforcement_result = "NOT_ATTEMPTED"

    if evidence_failed or replay.get("state") == "EFFECT_OCCURRED_UNATTESTED":
        outcome_state = "EFFECT_OCCURRED_UNATTESTED"
    elif receipt is not None:
        outcome_state = str(receipt.outcome)
    else:
        outcome_state = "NONE"

    action = runtime._require_action(action_id)["action"]
    occurred_at = (
        receipt.recorded_at.isoformat()
        if receipt is not None
        else decision_event.timestamp.replace("Z", "+00:00")
    )
    authority_revision = decision_event.payload.get("authority_revision")
    if authority_revision is None and receipt is not None:
        authority_revision = receipt.authority_revision

    identity = {
        "action_id": action_id,
        "effect_digest": replay["effect_digest"],
        "decision": decision,
        "enforcement_result": enforcement_result,
        "outcome_state": outcome_state,
        "authority_revision": authority_revision,
        "evidence_reference": receipt.receipt_id if receipt is not None else None,
    }

    return {
        "schema_version": 1,
        "event_id": _digest(identity),
        "action_id": action_id,
        "tenant_or_organization": tenant_or_organization,
        "effect_digest": replay["effect_digest"],
        "effect_type": action.get("type"),
        "decision": decision,
        "enforcement_result": enforcement_result,
        "outcome_state": outcome_state,
        "authority_revision": authority_revision,
        "evidence_reference": receipt.receipt_id if receipt is not None else None,
        "occurred_at": occurred_at,
    }


def default_billable_executed_consequence(event: dict[str, object]) -> bool:
    """Default commercial filter: only successfully executed consequences are billable."""
    return (
        event.get("decision") == "ALLOW"
        and event.get("enforcement_result") == "EXECUTED"
        and event.get("outcome_state") == "SUCCESS"
        and event.get("evidence_reference") is not None
    )
