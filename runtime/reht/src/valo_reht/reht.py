"""Real REHT — the authorization boundary of VALO, as a separate component.

REHT (Rights, Effects and Home-Title) is the SOLE authorization boundary. The
Kernel v1 produces a fresh execution context; this package decides ALLOW,
STEP_UP or DENY by re-validating every authorization-relevant field of the
authority and the action, and returns a deterministic decision artifact.

The package is generic: it knows nothing about any domain. The packs carry
their own deterministic pre-execution domain admissibility; REHT carries only
the authorization decision. No pack-specific REHT code may live here.

STEP_UP is not a substitute for missing authority. It is available only after
identity, active authority, capability, scope, constraints and purpose already
match the exact action. It expresses that execution remains inadmissible until
a named higher-assurance requirement is satisfied. STEP_UP never emits a
clearance or execution permit.

The authoritative decision plane is exactly ``ALLOW`` | ``STEP_UP`` | ``DENY``.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from .confidential_execution import validate_confidential_execution_continuity
from .contracts import DecisionResult, RehtPort
from .execution_requirements import EAR_V1, validate_execution_requirements
from .governed_workspace import (
    Ed25519KernelExecutionContextVerifier,
    validate_governed_workspace_context,
)


class RealReht(RehtPort):
    """Deterministic REHT over fresh Kernel context and one exact action."""

    def __init__(
        self,
        *,
        kernel_context_verifier: Ed25519KernelExecutionContextVerifier | None = None,
        clock: Callable[[], datetime] | None = None,
        max_workspace_context_age: timedelta = timedelta(seconds=5),
        max_workspace_future_skew: timedelta = timedelta(seconds=1),
    ) -> None:
        if max_workspace_context_age < timedelta(0) or max_workspace_future_skew < timedelta(0):
            raise ValueError("workspace context freshness bounds cannot be negative")
        self.decisions: list[DecisionResult] = []
        self._kernel_context_verifier = kernel_context_verifier
        self._clock = clock or (lambda: datetime.now(UTC))
        self._max_workspace_context_age = max_workspace_context_age
        self._max_workspace_future_skew = max_workspace_future_skew

    def authorize(
        self,
        execution_context: dict[str, Any],
        action_contract: dict[str, Any],
    ) -> DecisionResult:
        capability = action_contract.get("capability")
        target = action_contract.get("target")
        required_constraints = action_contract.get("constraints") or {}
        required_purpose = action_contract.get("purpose_id")
        actor = execution_context.get("actor")

        context_now = _moment(execution_context)
        if context_now is None:
            return self._decide(
                "DENY",
                reason="malformed execution context time (freshness cannot be proven)",
                ctx=execution_context,
            )

        workspace_present = execution_context.get("workspace_binding") is not None
        workspace_required = action_contract.get("governed_workspace_required") is True
        now = context_now
        if workspace_present or workspace_required:
            try:
                authorization_time = self._clock()
                validate_governed_workspace_context(
                    execution_context,
                    action_contract,
                    verifier=self._kernel_context_verifier,
                    authorization_time=authorization_time,
                    max_context_age=self._max_workspace_context_age,
                    max_future_skew=self._max_workspace_future_skew,
                )
                if authorization_time.tzinfo is None or authorization_time.utcoffset() is None:
                    raise ValueError("REHT authorization clock must be timezone-aware")
                now = authorization_time.astimezone(UTC)
            except Exception as exc:
                return self._decide(
                    "DENY",
                    reason=f"governed workspace validation failed: {exc}",
                    ctx=execution_context,
                )

        if not execution_context.get("identity"):
            return self._decide(
                "DENY",
                reason="no verified execution identity",
                ctx=execution_context,
            )

        authorities = execution_context.get("authority") or []
        if not authorities:
            return self._decide(
                "DENY",
                reason=f"no active authority for {capability}",
                ctx=execution_context,
            )

        invariant_error: str | None = None
        for authority in authorities:
            if authority.get("principal") != actor:
                continue
            if authority.get("capability") != capability:
                continue
            if not _active(authority, now):
                continue
            scope = authority.get("scope") or []
            if target and scope and "*" not in scope and target not in scope:
                continue
            if required_constraints and not _satisfies(
                authority.get("constraints") or {},
                required_constraints,
            ):
                continue
            if required_purpose and not _purpose_ok(authority, required_purpose):
                continue

            if action_contract.get("execution_authorization_profile") == EAR_V1:
                error = validate_execution_requirements(
                    execution_context,
                    action_contract,
                    authority,
                )
                if error:
                    invariant_error = error
                    continue
                error = validate_confidential_execution_continuity(
                    execution_context,
                    action_contract,
                )
                if error:
                    invariant_error = error
                    continue

            step_up_reason = _step_up_reason(action_contract)
            if step_up_reason is not None:
                return self._decide(
                    "STEP_UP",
                    reason=step_up_reason,
                    ctx=execution_context,
                    action_contract=action_contract,
                )

            return self._decide(
                "ALLOW",
                authority=authority,
                ctx=execution_context,
                action_contract=action_contract,
            )

        return self._decide(
            "DENY",
            reason=(
                invariant_error
                or f"no active authority in scope for {capability}@{target}"
            ),
            ctx=execution_context,
        )

    def _decide(
        self,
        decision: str,
        *,
        reason: str | None = None,
        ctx: dict[str, Any] | None = None,
        authority: dict[str, Any] | None = None,
        action_contract: dict[str, Any] | None = None,
    ) -> DecisionResult:
        result = DecisionResult(
            decision=decision,
            reason=reason,
            clearance_ref=None,
            permit_ref=None,
            execution_context_hash=_digest(ctx) if ctx else None,
        )
        if decision == "ALLOW" and authority is not None:
            artifact = _artifact(authority, action_contract or {}, ctx or {})
            result = DecisionResult(
                decision="ALLOW",
                clearance_ref=artifact["clearance_ref"],
                permit_ref=artifact["permit_ref"],
                execution_context_hash=artifact["ctx_hash"],
                reason=None,
            )
        self.decisions.append(result)
        return result


def _step_up_reason(action_contract: dict[str, Any]) -> str | None:
    """Return a deterministic reason for an explicit higher-assurance gate.

    STEP_UP is opt-in data on the exact action contract. This function does not
    infer authority from ambiguity and therefore cannot widen capability or
    scope. A malformed declaration fails closed as DENY at the caller only by
    not producing STEP_UP; schemas should reject malformed contracts earlier.
    """
    requirement = action_contract.get("step_up")
    if requirement is True:
        return "higher-assurance authorization required before execution"
    if not isinstance(requirement, dict) or requirement.get("required") is not True:
        return None

    reason = requirement.get("reason")
    if isinstance(reason, str) and reason.strip():
        return reason.strip()
    return "higher-assurance authorization required before execution"


def _moment(execution_context: dict[str, Any]) -> datetime | None:
    """Require a parseable, timezone-aware context time."""
    raw = execution_context.get("time", {}).get("now")
    if not raw:
        return None
    return _parse_aware(raw)


def _parse_aware(raw: Any) -> datetime | None:
    if not isinstance(raw, str) or not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except (ValueError, TypeError):
        return None
    if parsed.tzinfo is None:
        return None
    return parsed


def _active(authority: dict[str, Any], now: datetime) -> bool:
    """An authority is active only inside its valid non-revoked window."""
    if authority.get("status") == "REVOKED":
        return False
    validity = authority.get("validity") or {}
    for key, comparator in (
        ("valid_from", _after),
        ("valid_until", _at_or_before),
    ):
        raw = validity.get(key)
        if raw is None:
            continue
        parsed = _parse_aware(raw)
        if parsed is None:
            return False
        if comparator(parsed, now):
            return False
    revoked_at = authority.get("revoked_at")
    if revoked_at:
        parsed = _parse_aware(revoked_at)
        if parsed is None or parsed <= now:
            return False
    return True


def _after(value: datetime, now: datetime) -> bool:
    return value > now


def _at_or_before(value: datetime, now: datetime) -> bool:
    return value <= now


def _satisfies(
    authority_constraints: dict[str, Any],
    required: dict[str, Any],
) -> bool:
    return all(
        authority_constraints.get(key) == value
        for key, value in required.items()
    )


def _purpose_ok(authority: dict[str, Any], required_purpose: str) -> bool:
    constraints = authority.get("constraints") or {}
    exact = constraints.get("purpose_id")
    if exact is not None:
        return exact == required_purpose

    permitted = constraints.get("purposes")
    if permitted is None:
        return True
    if isinstance(permitted, str):
        return permitted == required_purpose
    if isinstance(permitted, (list, tuple, set)):
        return required_purpose in permitted
    return False


def _digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _artifact(
    authority: dict[str, Any],
    action_contract: dict[str, Any],
    ctx: dict[str, Any],
) -> dict[str, str]:
    """Bind clearance/permit refs to the full exact action and Kernel context."""
    ctx_hash = _digest(ctx)
    action_contract_hash = _digest(action_contract)
    artifact_digest = _digest(
        {
            "authority_id": authority.get("authority_id"),
            "capability": action_contract.get("capability"),
            "target": action_contract.get("target"),
            "ctx_hash": ctx_hash,
            "action_contract_hash": action_contract_hash,
        }
    )
    return {
        "clearance_ref": f"clearance:{artifact_digest[:12]}",
        "permit_ref": f"permit:{artifact_digest[:12]}",
        "ctx_hash": ctx_hash,
        "action_contract_hash": action_contract_hash,
    }
