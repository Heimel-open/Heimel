"""Deterministic approver-authority validation for EAR human gates."""

from __future__ import annotations

from datetime import datetime
from typing import Any

APPROVER_AUTHORITY_V1 = "APPROVER_AUTHORITY_V1"
INDEPENDENT_APPROVER_GATES = {"human_approval", "dual_control"}
_PROHIBITED_EXECUTION_OUTPUTS = {
    "allow",
    "allowed",
    "authorized",
    "authorization",
    "decision",
    "permit",
    "permit_ref",
    "clearance_ref",
    "execution_authority_granted",
}


def validate_approver_authority_gate(
    attestation: dict[str, Any],
    *,
    gate_type: str,
    execution_actor: str,
    action: dict[str, Any],
    action_hash: str,
    now: datetime,
) -> str | None:
    """Validate that every independent gate approver has current approval authority.

    Approval authority is only a gate condition. This function never creates or
    expands the execution authority evaluated by REHT.
    """
    if gate_type not in INDEPENDENT_APPROVER_GATES:
        return None

    required_capability = action.get("required_approver_capability")
    if not isinstance(required_capability, str) or not required_capability.strip():
        return "EA-11: independent gate lacks required_approver_capability policy"
    if attestation.get("approval_capability") != required_capability:
        return "EA-11: gate approval capability does not match the action policy"

    approvers = attestation.get("approver_actors")
    if (
        not isinstance(approvers, list)
        or not approvers
        or any(not isinstance(item, str) or not item for item in approvers)
    ):
        return "EA-11: independent gate lacks explicit approver actors"
    if len(set(approvers)) != len(approvers) or execution_actor in set(approvers):
        return "EA-11: independent gate approvers are not independent and distinct"
    if gate_type == "dual_control" and len(approvers) < 2:
        return "EA-11: dual-control gate requires at least two distinct independent approvers"

    facts = attestation.get("approver_authorities")
    if not isinstance(facts, list) or not facts:
        return "EA-11: independent gate lacks verified approver authority facts"
    if len(facts) != len(approvers):
        return "EA-11: approver authority facts do not exactly cover gate approvers"

    target = action.get("target")
    purpose_id = action.get("purpose_id")
    fact_actors: list[str] = []
    authority_refs: list[str] = []

    for fact in facts:
        if not isinstance(fact, dict):
            return "EA-11: approver authority fact is malformed"
        if fact.get("schema") != APPROVER_AUTHORITY_V1:
            return "EA-11: approver authority fact uses an unsupported schema"
        if fact.get("verified") is not True:
            return "EA-11: approver authority fact is not verified"
        if any(str(key).lower() in _PROHIBITED_EXECUTION_OUTPUTS for key in fact):
            return "EA-11: approver authority fact attempted to carry execution authority"

        actor = fact.get("approver_actor")
        if not isinstance(actor, str) or not actor:
            return "EA-11: approver authority fact is missing approver_actor"
        if actor not in approvers or actor == execution_actor:
            return "EA-11: approver authority fact is not bound to an independent gate approver"
        fact_actors.append(actor)

        authority_ref = fact.get("authority_ref")
        if not isinstance(authority_ref, str) or not authority_ref:
            return "EA-11: approver authority fact is missing authority_ref"
        authority_refs.append(authority_ref)

        if fact.get("capability") != required_capability:
            return "EA-11: approver authority capability does not match the action policy"
        if fact.get("action_contract_hash") != action_hash:
            return "EA-11: approver authority is not bound to the exact action contract"
        if fact.get("target_ref") != target:
            return "EA-11: approver authority is not bound to the action target"
        if fact.get("purpose_id") != purpose_id:
            return "EA-11: approver authority is not bound to the action purpose"

        for field in ("source", "evidence_ref"):
            value = fact.get(field)
            if not isinstance(value, str) or not value:
                return f"EA-11: approver authority fact is missing {field}"

        observed_at = _parse_aware(fact.get("observed_at"))
        valid_until = _parse_aware(fact.get("valid_until"))
        if observed_at is None or valid_until is None:
            return "EA-11: approver authority validity cannot be proven"
        if observed_at > now or valid_until <= now or valid_until <= observed_at:
            return "EA-11: approver authority is future-dated, expired, or malformed"

    if set(fact_actors) != set(approvers) or len(set(fact_actors)) != len(fact_actors):
        return "EA-11: approver authority facts do not exactly cover gate approvers"
    if len(set(authority_refs)) != len(authority_refs):
        return "EA-11: approver authority references are not distinct"
    return None


def _parse_aware(raw: Any) -> datetime | None:
    if not isinstance(raw, str) or not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return None
    return parsed
