"""Deterministic verified-outcome feedback for the next REHT decision.

Veritas evidence is input only. It cannot create, expand, or restore authority.
This module verifies the minimum WORM-backed execution-outcome contract and
projects it into a non-authoritative authority-state observation.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

VERITAS_WORM_OUTCOME_V1 = "VERITAS_WORM_OUTCOME_V1"
_VALID_OUTCOMES = {"succeeded", "failed", "partial", "blocked"}


def validate_verified_prior_outcome(
    outcome: dict[str, Any],
    *,
    expected_prior_permit_ref: str | None = None,
    acceptable_outcomes: set[str] | None = None,
) -> str | None:
    """Validate a prior execution outcome before REHT may rely on it.

    The record must already have been verified against Veritas WORM evidence.
    REHT does not perform semantic inference from the result; it only checks the
    deterministic bindings required by the current Action Contract.
    """
    if outcome.get("schema") != VERITAS_WORM_OUTCOME_V1:
        return "EA-09: prior execution outcome uses an unsupported evidence schema"
    if outcome.get("verified") is not True or outcome.get("worm_chain_verified") is not True:
        return "EA-09: prior execution outcome is not verified by an intact Veritas WORM chain"
    if outcome.get("authority_granted") is not False:
        return "EA-09: Veritas outcome attempted to carry authority"

    for name in (
        "execution_id",
        "permit_ref",
        "clearance_ref",
        "observation_package_ref",
        "observation_package_digest",
        "worm_entry_ref",
    ):
        value = outcome.get(name)
        if not isinstance(value, str) or not value:
            return f"EA-09: verified prior execution outcome is missing {name}"

    status = outcome.get("status")
    if status not in _VALID_OUTCOMES:
        return "EA-09: prior execution outcome has an invalid status"

    if expected_prior_permit_ref is not None and outcome.get("permit_ref") != expected_prior_permit_ref:
        return "EA-09: prior execution outcome does not match the causal permit"

    allowed = acceptable_outcomes or {"succeeded"}
    if status not in allowed:
        return f"EA-09: prior execution outcome {status!r} is not admissible for this action"
    return None


def bind_verified_outcome_state(
    execution_context: dict[str, Any],
    outcome: dict[str, Any],
) -> dict[str, Any]:
    """Return a new execution context containing outcome-derived state.

    The projection is deliberately non-authoritative. It records what Veritas
    proved happened; normal REHT authority, scope, purpose, freshness and EAR
    checks still decide whether the next action may execute.
    """
    error = validate_verified_prior_outcome(outcome, acceptable_outcomes=_VALID_OUTCOMES)
    if error:
        raise ValueError(error)

    result = deepcopy(execution_context)
    state = dict(result.get("authority_state") or {})
    state["verified_prior_execution"] = {
        "execution_id": outcome["execution_id"],
        "permit_ref": outcome["permit_ref"],
        "clearance_ref": outcome["clearance_ref"],
        "status": outcome["status"],
        "observation_package_ref": outcome["observation_package_ref"],
        "worm_entry_ref": outcome["worm_entry_ref"],
        "authority_granted": False,
    }
    result["authority_state"] = state
    result["prior_execution_outcome"] = deepcopy(outcome)
    return result
