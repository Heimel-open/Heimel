"""Executable REHT-native Execution Authorization Requirements v1.

The validator is deterministic and generic. It consumes only authority-bearing
execution context plus the concrete action contract. It does not evaluate the
world, discover policy, or manufacture authority.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from .approver_authority import (
    INDEPENDENT_APPROVER_GATES,
    validate_approver_authority_gate,
)
from .outcome_feedback import validate_verified_prior_outcome

EAR_V1 = "EAR_V1"
EAR_GATE_V1 = "EAR_GATE_V1"
EAR_GOVERNANCE_GATE_V1 = "EAR_GOVERNANCE_GATE_V1"
_VALID_IMPACTS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
_HIGH_IMPACTS = {"HIGH", "CRITICAL"}
_ACCEPTABLE_REALITY = {"MATCH", "VERIFIED"}
_HUMAN_GOVERNANCE_GATES = {"human_approval", "dual_control"}
_VALID_REVIEW_RESULTS = {"YES", "NO", "PARTLY"}
_GATE_REF_FIELDS = {
    "human_approval": "human_approval_ref",
    "dual_control": "dual_control_ref",
    "confirmation": "confirmation_ref",
    "step_up": "step_up_ref",
    "delay": "delay_gate_ref",
}


def validate_execution_requirements(
    execution_context: dict[str, Any],
    action_contract: dict[str, Any],
    authority: dict[str, Any],
) -> str | None:
    """Return the first violated EAR v1 invariant, otherwise ``None``.

    EAR v1 is opt-in so existing action contracts keep their frozen behaviour.
    Once selected, every applicable check fails closed.
    """
    if action_contract.get("execution_authorization_profile") != EAR_V1:
        return None

    error = _causal_continuity(execution_context, action_contract)
    if error:
        return error

    error = _authority_drift(execution_context)
    if error:
        return error

    error = _multi_hop(execution_context)
    if error:
        return error

    error = _temporary_authority(authority)
    if error:
        return error

    error = _purpose_binding(execution_context, action_contract, authority)
    if error:
        return error

    error = _required_evidence(execution_context, action_contract)
    if error:
        return error

    error = _reality_validation(execution_context, action_contract)
    if error:
        return error

    error = _verified_prior_outcome(execution_context, action_contract)
    if error:
        return error

    error = _impact_and_gates(execution_context, action_contract)
    if error:
        return error

    error = _replay_resistance(execution_context)
    if error:
        return error

    return _resource_bounds(action_contract)


def _causal_continuity(ctx: dict[str, Any], action: dict[str, Any]) -> str | None:
    expected_state = action.get("state_ref")
    if expected_state is not None and ctx.get("state_ref") != expected_state:
        return "EA-04: causal continuity broken (authorized state does not match execution state)"
    return None


def _authority_drift(ctx: dict[str, Any]) -> str | None:
    state = ctx.get("authority_state") or {}
    if state.get("drift_detected") is True:
        return "EA-05: authority drift detected; executable authority is non-existent"
    attested = state.get("attested_surface_hash")
    current = state.get("current_surface_hash")
    if attested is not None and current is not None and attested != current:
        return "EA-05: authority surface differs from attested state"
    return None


def _multi_hop(ctx: dict[str, Any]) -> str | None:
    causal = ctx.get("causal") or {}
    hop_depth = causal.get("hop_depth", 0)
    if not isinstance(hop_depth, int) or isinstance(hop_depth, bool) or hop_depth < 0:
        return "EA-06: invalid causal hop depth"
    if hop_depth > 0 and (
        not causal.get("prior_permit_ref") or causal.get("reauthorized") is not True
    ):
        return "EA-06: side-effecting hop lacks independent reauthorization"
    return None


def _temporary_authority(authority: dict[str, Any]) -> str | None:
    if authority.get("temporary") is not True:
        return None
    validity = authority.get("validity") or {}
    if not validity.get("valid_until"):
        return "EA-07: temporary authority has no explicit expiry"
    scope = authority.get("scope") or []
    if not scope or "*" in scope:
        return "EA-07: temporary authority must have bounded scope"
    return None


def _purpose_binding(
    ctx: dict[str, Any], action: dict[str, Any], authority: dict[str, Any]
) -> str | None:
    """Require deterministic purpose binding for consequential execution.

    Purpose is risk-based rather than universal. HIGH/CRITICAL, irreversible,
    or explicitly purpose-required side effects must bind to a current Kernel
    Purpose object and an exact purpose restriction on the authority grant.
    This remains safe even when identity is valid but compromised or spoofed.
    """
    if action.get("side_effecting") is not True:
        return None

    impact = action.get("impact")
    purpose_required = (
        action.get("requires_purpose") is True
        or impact in _HIGH_IMPACTS
        or action.get("reversible") is False
    )
    if not purpose_required:
        return None

    purpose_id = action.get("purpose_id")
    if not isinstance(purpose_id, str) or not purpose_id.strip():
        return "EA-03: consequential action lacks an explicit purpose_id"

    purpose = ctx.get("purpose")
    if not isinstance(purpose, dict) or purpose.get("purpose_id") != purpose_id:
        return "EA-03: execution context does not carry the exact registered purpose"

    basis = purpose.get("basis")
    if not isinstance(basis, str) or not basis.strip():
        return "EA-03: registered purpose lacks a legitimate basis reference"

    action_type = action.get("action_type")
    permitted_actions = purpose.get("permitted_actions")
    if not isinstance(action_type, str) or not action_type:
        return "EA-03: purpose-bound action lacks an action_type"
    if not isinstance(permitted_actions, list) or action_type not in permitted_actions:
        return "EA-03: registered purpose does not permit this action type"

    target = action.get("target")
    purpose_scope = purpose.get("scope")
    if target:
        if not isinstance(purpose_scope, list) or not purpose_scope:
            return "EA-03: registered purpose has no explicit target scope"
        if "*" not in purpose_scope and target not in purpose_scope:
            return "EA-03: action target is outside the registered purpose scope"

    validity = purpose.get("validity")
    if not isinstance(validity, dict):
        return "EA-03: registered purpose lacks a validity window"
    now = _parse_aware((ctx.get("time") or {}).get("now"))
    valid_from = _parse_aware(validity.get("valid_from"))
    valid_until = _parse_aware(validity.get("valid_until"))
    if now is None or valid_from is None or valid_until is None:
        return "EA-03: purpose validity cannot be proven"
    if not (valid_from <= now < valid_until):
        return "EA-03: registered purpose is not active at execution time"

    authority_constraints = authority.get("constraints") or {}
    if authority_constraints.get("purpose_id") != purpose_id:
        return "EA-03: authority is not explicitly bound to the required purpose"

    return None


def _required_evidence(ctx: dict[str, Any], action: dict[str, Any]) -> str | None:
    if action.get("requires_evidence") is not True:
        return None
    evidence = ctx.get("evidence") or {}
    if (
        evidence.get("status") != "VALID"
        or evidence.get("fresh") is not True
        or not evidence.get("evidence_ref")
    ):
        return "EA-08: required evidence is incomplete, stale, inadmissible, or unverifiable"
    return None


def _reality_validation(ctx: dict[str, Any], action: dict[str, Any]) -> str | None:
    if action.get("requires_reality_validation") is not True:
        return None
    reality = ctx.get("reality_validation") or {}
    if reality.get("status") not in _ACCEPTABLE_REALITY or not reality.get(
        "evidence_ref"
    ):
        return "EA-09: required reality validation does not verify the current state"
    return None


def _verified_prior_outcome(ctx: dict[str, Any], action: dict[str, Any]) -> str | None:
    if action.get("requires_verified_prior_outcome") is not True:
        return None
    outcome = ctx.get("prior_execution_outcome")
    if not isinstance(outcome, dict):
        return "EA-09: required verified prior execution outcome is absent"
    causal = ctx.get("causal") or {}
    expected = action.get("expected_prior_permit_ref") or causal.get("prior_permit_ref")
    configured = action.get("acceptable_prior_outcomes")
    acceptable: set[str] | None = None
    if configured is not None:
        if (
            not isinstance(configured, list)
            or not configured
            or not all(isinstance(item, str) for item in configured)
        ):
            return "EA-09: acceptable prior outcome policy is malformed"
        acceptable = set(configured)
    return validate_verified_prior_outcome(
        outcome,
        expected_prior_permit_ref=expected,
        acceptable_outcomes=acceptable,
    )


def _impact_and_gates(ctx: dict[str, Any], action: dict[str, Any]) -> str | None:
    if action.get("side_effecting") is not True:
        return None
    impact = action.get("impact")
    reversible = action.get("reversible")
    if impact not in _VALID_IMPACTS or not isinstance(reversible, bool):
        return "EA-10: side-effecting action lacks deterministic impact/reversibility classification"

    governance_profile = action.get("governance_gate_profile")
    if governance_profile not in {None, EAR_GOVERNANCE_GATE_V1}:
        return "EA-11: unsupported governance gate profile"
    governance_profile_selected = governance_profile == EAR_GOVERNANCE_GATE_V1

    if (
        impact not in _HIGH_IMPACTS
        and reversible is not False
        and not governance_profile_selected
    ):
        return None

    required_gate_types = action.get("required_gate_types")
    if (
        not isinstance(required_gate_types, list)
        or not required_gate_types
        or any(
            not isinstance(item, str) or item not in _GATE_REF_FIELDS
            for item in required_gate_types
        )
        or len(set(required_gate_types)) != len(required_gate_types)
    ):
        return "EA-11: protected action lacks a valid explicit required_gate_types policy"

    if governance_profile_selected and not any(
        gate_type in _HUMAN_GOVERNANCE_GATES for gate_type in required_gate_types
    ):
        return "EA-11: governance gate profile requires human approval or dual control"

    gates = ctx.get("gates")
    attestations = ctx.get("gate_attestations")
    if not isinstance(gates, dict) or not isinstance(attestations, dict):
        return "EA-11: protected action lacks gate references or verified gate attestations"

    action_hash = _digest(action)
    for gate_type in required_gate_types:
        ref_field = _GATE_REF_FIELDS[gate_type]
        gate_ref = gates.get(ref_field)
        if not isinstance(gate_ref, str) or not gate_ref:
            return f"EA-11: required gate {gate_type!r} is absent"
        attestation = attestations.get(gate_ref)
        error = _validate_gate_attestation(
            attestation,
            gate_type=gate_type,
            gate_ref=gate_ref,
            ctx=ctx,
            action=action,
            action_hash=action_hash,
        )
        if error:
            return error
    return None


def _validate_gate_attestation(
    attestation: Any,
    *,
    gate_type: str,
    gate_ref: str,
    ctx: dict[str, Any],
    action: dict[str, Any],
    action_hash: str,
) -> str | None:
    if not isinstance(attestation, dict):
        return f"EA-11: required gate {gate_type!r} lacks a typed attestation"
    if attestation.get("schema") != EAR_GATE_V1:
        return "EA-11: gate attestation uses an unsupported schema"
    if (
        attestation.get("gate_type") != gate_type
        or attestation.get("gate_ref") != gate_ref
    ):
        return "EA-11: gate attestation does not match the required gate"
    if attestation.get("verified") is not True:
        return "EA-11: gate attestation is not verified"
    if attestation.get("authority_granted") is not False:
        return "EA-11: gate attestation attempted to carry authority"

    actor = ctx.get("actor")
    if attestation.get("subject_actor") != actor:
        return "EA-11: gate attestation is not bound to the execution actor"
    if attestation.get("action_contract_hash") != action_hash:
        return "EA-11: gate attestation is not bound to the exact action contract"

    execution_nonce = ctx.get("execution_nonce")
    if not isinstance(execution_nonce, str) or not execution_nonce:
        return "EA-11: current execution nonce cannot be proven for protected gate"
    if attestation.get("execution_nonce") != execution_nonce:
        return "EA-11: gate attestation is not bound to the current execution nonce"

    for field in ("source", "evidence_ref"):
        value = attestation.get(field)
        if not isinstance(value, str) or not value:
            return f"EA-11: gate attestation is missing {field}"

    now = _parse_aware((ctx.get("time") or {}).get("now"))
    observed_at = _parse_aware(attestation.get("observed_at"))
    valid_until = _parse_aware(attestation.get("valid_until"))
    if now is None or observed_at is None or valid_until is None:
        return "EA-11: gate attestation validity cannot be proven"
    if observed_at > now or valid_until <= now or valid_until <= observed_at:
        return "EA-11: gate attestation is future-dated, expired, or malformed"

    if gate_type in INDEPENDENT_APPROVER_GATES:
        error = validate_approver_authority_gate(
            attestation,
            gate_type=gate_type,
            execution_actor=actor,
            action=action,
            action_hash=action_hash,
            now=now,
        )
        if error:
            return error

    return _validate_governance_gate_profile(
        attestation,
        gate_type=gate_type,
        action=action,
    )


def _validate_governance_gate_profile(
    attestation: dict[str, Any],
    *,
    gate_type: str,
    action: dict[str, Any],
) -> str | None:
    """Validate the optional human/organizational gate-completeness profile.

    The profile does not define substantive policy and cannot grant authority.
    It only makes the human review boundary explicit and machine-checkable.
    """
    profile = action.get("governance_gate_profile")
    if profile != EAR_GOVERNANCE_GATE_V1 or gate_type not in _HUMAN_GOVERNANCE_GATES:
        return None

    trigger_ref = attestation.get("trigger_ref")
    if not isinstance(trigger_ref, str) or not trigger_ref.strip():
        return "EA-11: governance gate lacks an explicit trigger_ref"

    criteria_results = attestation.get("criteria_results")
    if not isinstance(criteria_results, list) or not criteria_results:
        return "EA-11: governance gate lacks explicit criteria results"

    seen: set[str] = set()
    for item in criteria_results:
        if not isinstance(item, dict):
            return "EA-11: governance gate criteria results are malformed"
        criterion_ref = item.get("criterion_ref")
        result = item.get("result")
        if not isinstance(criterion_ref, str) or not criterion_ref.strip():
            return "EA-11: governance gate criterion lacks criterion_ref"
        if criterion_ref in seen:
            return "EA-11: governance gate contains duplicate criterion_ref"
        seen.add(criterion_ref)
        if result not in _VALID_REVIEW_RESULTS:
            return "EA-11: governance gate criterion uses an unsupported review result"
        if result != "YES":
            return "EA-11: governance gate review is not fully affirmative"

    if attestation.get("decision") != "APPROVE":
        return "EA-11: governance gate lacks an explicit positive decision"

    for field in ("escalation_ref", "record_ref"):
        value = attestation.get(field)
        if not isinstance(value, str) or not value.strip():
            return f"EA-11: governance gate is missing {field}"

    return None


def _replay_resistance(ctx: dict[str, Any]) -> str | None:
    sequence = ctx.get("sequence")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 0:
        return "EA-14: missing or invalid execution sequence"
    nonce = ctx.get("execution_nonce")
    if not isinstance(nonce, str) or not nonce:
        return "EA-14: missing execution nonce"
    return None


def _resource_bounds(action: dict[str, Any]) -> str | None:
    if action.get("resource_limits_required") is not True:
        return None
    limits = action.get("resource_limits")
    if not isinstance(limits, dict) or not limits:
        return "EA-18: required resource bounds are absent"
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


def _digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
