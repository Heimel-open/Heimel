"""
Governed action proposal (#143) — proposes actions wrapped in a RACS-style action envelope.

The OS builds action proposals as RACS-compatible action envelopes and sends them
to REHT (admissibility authority) and VAIG (integrity signals) for evaluation.

The OS NEVER executes locally. Execution is owned by REHT / VALO Harness.

Design:
  - Reuses the RACS action envelope schema shape from spec (actor, target,
    requested_effect, authority_context, policy_context, evidence_package,
    environment_state, risk_context, expires_at).
  - Proposal is sent to REHT/VAIG stubs (simple callbacks) for evaluation.
  - The `governed_propose` function wraps proposal + evaluation into a single
    result — but NEVER proceeds to execution.

Canonical rules:
  - REHT sole admissibility authority — OS proposes, never decides/executes.
  - Canonical types from RACS are reused (action envelope schema shape).
  - C0/α/τ are env vars only, never hardcoded.
"""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


# ------------------------------------------------------------------
# RACS action envelope shape — mirrors spec/action-envelope.schema.json
# ------------------------------------------------------------------

@dataclass
class ActionEnvelope:
    """A RACS-compatible action envelope.

    Required fields (mirroring RACS spec):
      racs_version, action_id, action_type, actor, target,
      requested_effect, authority_context, policy_context,
      evidence_package, environment_state, created_at.

    Optional: risk_context, expires_at.
    """
    racs_version: str = "1.0"
    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_type: str = ""
    actor: Dict[str, Any] = field(default_factory=dict)
    target: Dict[str, Any] = field(default_factory=dict)
    requested_effect: Dict[str, Any] = field(default_factory=dict)
    authority_context: Dict[str, Any] = field(default_factory=dict)
    policy_context: Dict[str, Any] = field(default_factory=dict)
    evidence_package: Dict[str, Any] = field(default_factory=dict)
    environment_state: Dict[str, Any] = field(default_factory=dict)
    risk_context: Optional[Dict[str, Any]] = None
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "racs_version": self.racs_version,
            "action_id": self.action_id,
            "action_type": self.action_type,
            "actor": self.actor,
            "target": self.target,
            "requested_effect": self.requested_effect,
            "authority_context": self.authority_context,
            "policy_context": self.policy_context,
            "evidence_package": self.evidence_package,
            "environment_state": self.environment_state,
            "created_at": self.created_at,
        }
        if self.risk_context is not None:
            result["risk_context"] = self.risk_context
        if self.expires_at is not None:
            result["expires_at"] = self.expires_at
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActionEnvelope":
        return cls(
            racs_version=data.get("racs_version", "1.0"),
            action_id=data.get("action_id", str(uuid.uuid4())),
            action_type=data.get("action_type", ""),
            actor=data.get("actor", {}),
            target=data.get("target", {}),
            requested_effect=data.get("requested_effect", {}),
            authority_context=data.get("authority_context", {}),
            policy_context=data.get("policy_context", {}),
            evidence_package=data.get("evidence_package", {}),
            environment_state=data.get("environment_state", {}),
            risk_context=data.get("risk_context"),
            created_at=data.get("created_at", time.time()),
            expires_at=data.get("expires_at"),
        )


# ------------------------------------------------------------------
# Evaluation result types (from VAIG/REHT)
# ------------------------------------------------------------------

VAIG_VERDICT = Optional[Dict[str, Any]]  # e.g. {"result": "ALLOW", "confidence": 0.92}
REHT_VERDICT = Optional[Dict[str, Any]]  # e.g. {"admissible": True, "clearance_id": "clr_abc"}


@dataclass
class GovernanceResult:
    """Result of a governed proposal — envelope + evaluations, NO execution."""

    envelope: ActionEnvelope
    vaig_evaluation: VAIG_VERDICT = None
    reht_evaluation: REHT_VERDICT = None
    errors: List[str] = field(default_factory=list)

    @property
    def can_execute(self) -> bool:
        """Check if the proposal received ALLOW from VAIG and ADMISSIBLE from REHT.

        IMPORTANT: This is an informational property only. It does NOT grant
        execution authority. The OS never executes — only REHT/Harness may.

        Consistency rule (audit finding #3, requirement 4): a REHT verdict whose
        ``state`` is ``INADMISSIBLE`` must never be treated as executable, even if
        its scalar ``admissible`` flag is spuriously ``True``. The two signals must
        agree; otherwise the verdict is internally inconsistent and fails closed.
        """
        if self.vaig_evaluation is None or self.reht_evaluation is None:
            return False
        vaig_ok = self.vaig_evaluation.get("result") == "ALLOW"
        reht_ok = self.reht_evaluation.get("admissible") is True
        reht_state = self.reht_evaluation.get("state")
        if reht_state is not None and reht_state == "INADMISSIBLE":
            # State/admissible contradiction must fail closed, never open.
            reht_ok = False
        return vaig_ok and reht_ok


# ------------------------------------------------------------------
# Governance proposal function
# ------------------------------------------------------------------
#
# Default evaluator stubs — simple pass-through that record the proposal.
# In production, these would call the actual VAIG and REHT services via
# `RehtClient` (see reht_client.py).
#
def _default_vaig_evaluator(envelope: ActionEnvelope) -> VAIG_VERDICT:
    """Default VAIG evaluator — FAIL-CLOSED.

    Returns DENY by default. The OS must be wired to a real VAIG service
    (via RehtClient / vaig_evaluator) before any action can be admissible.
    A pass-through ALLOW here would let every proposal bypass integrity
    evaluation (audit finding: VAIG stub returned ALLOW unconditionally,
    so can_execute was always True once REHT said admissible).
    """
    return {
        "result": "DENY",
        "confidence": 0.0,
        "reason": "no_vaig_configured",
        "evaluated_at": time.time(),
        "action_id": envelope.action_id,
    }


def _default_reht_evaluator(envelope: ActionEnvelope) -> REHT_VERDICT:
    """Default REHT evaluator — FAIL-CLOSED when no authority is connected."""
    return {
        "state": "INDETERMINATE",
        "admissible": False,
        "clearance_id": None,
        "reasons": ["no_reht_configured"],
        "evaluated_at": time.time(),
        "action_id": envelope.action_id,
    }


def governed_propose(
    action_type: str,
    actor: Dict[str, Any],
    target: Dict[str, Any],
    requested_effect: Dict[str, Any],
    authority_context: Dict[str, Any],
    policy_context: Optional[Dict[str, Any]] = None,
    evidence_package: Optional[Dict[str, Any]] = None,
    environment_state: Optional[Dict[str, Any]] = None,
    risk_context: Optional[Dict[str, Any]] = None,
    expires_in: Optional[float] = None,
    vaig_evaluator: Callable[[ActionEnvelope], VAIG_VERDICT] = _default_vaig_evaluator,
    reht_evaluator: Callable[[ActionEnvelope], REHT_VERDICT] = _default_reht_evaluator,
) -> GovernanceResult:
    """Build a RACS action envelope and send it to VAIG and REHT for evaluation.

    Returns a GovernanceResult with the envelope and both evaluations.
    The OS NEVER executes — this function only proposes and evaluates.
    """
    envelope = ActionEnvelope(
        action_type=action_type,
        actor=actor,
        target=target,
        requested_effect=requested_effect,
        authority_context=authority_context,
        policy_context=policy_context or {},
        evidence_package=evidence_package or {},
        environment_state=environment_state or {},
        risk_context=risk_context,
        expires_at=(time.time() + expires_in) if expires_in is not None else None,
    )

    errors: List[str] = []

    # Send to VAIG for integrity evaluation
    try:
        vaig_result = vaig_evaluator(envelope)
    except Exception as e:
        vaig_result = None
        errors.append(f"VAIG evaluation failed: {e}")

    # Send to REHT for admissibility evaluation
    try:
        reht_result = reht_evaluator(envelope)
    except Exception as e:
        reht_result = None
        errors.append(f"REHT evaluation failed: {e}")

    return GovernanceResult(
        envelope=envelope,
        vaig_evaluation=vaig_result,
        reht_evaluation=reht_result,
        errors=errors,
    )


# ------------------------------------------------------------------
# REHT evaluator adapter — wraps RehtClient as a callable evaluator
# ------------------------------------------------------------------


def _make_reht_evaluator(
    client: "RehtClient",  # type: ignore[name-defined]  # noqa: F821
) -> Callable[[ActionEnvelope], REHT_VERDICT]:
    """Wrap a ``RehtClient`` instance into a callable evaluator.

    Returns a function that accepts an ``ActionEnvelope`` and returns
    a ``REHT_VERDICT`` dict compatible with ``governed_propose()``.
    """

    def evaluator(envelope: ActionEnvelope) -> REHT_VERDICT:
        verdict = client.evaluate(envelope)
        gc = verdict.governance_clearance
        return {
            "admissible": verdict.admissible,
            "state": verdict.state,
            "score": verdict.score,
            "reasons": verdict.reasons,
            "governance_clearance": gc,
            "clearance_id": gc.get("clearance_id") if gc else None,
            "policy_applied": verdict.policy_applied,
            "evaluated_at": time.time(),
            "action_id": envelope.action_id,
        }

    return evaluator


# ------------------------------------------------------------------
# PAIOS propose_action — primary entry point for governed proposals
# ------------------------------------------------------------------

_ADMISSIBLE_STATE = "ADMISSIBLE"


def propose_action(
    action_type: str,
    actor: Dict[str, Any],
    target: Dict[str, Any],
    requested_effect: Dict[str, Any],
    authority_context: Dict[str, Any],
    policy_context: Optional[Dict[str, Any]] = None,
    evidence_package: Optional[Dict[str, Any]] = None,
    environment_state: Optional[Dict[str, Any]] = None,
    risk_context: Optional[Dict[str, Any]] = None,
    expires_in: Optional[float] = None,
    vaig_evaluator: Optional[Callable[[ActionEnvelope], VAIG_VERDICT]] = None,
    reht_client: Optional["RehtClient"] = None,  # type: ignore[name-defined]  # noqa: F821
    memory: Optional["CanonicalMemory"] = None,  # type: ignore[name-defined]  # noqa: F821
    maturity_model: Optional["MaturityModel"] = None,  # type: ignore[name-defined]  # noqa: F821
) -> GovernanceResult:
    """Build a RACS action envelope, evaluate via REHT, record verdict.

    This is the primary PAIOS entry point for governed action proposals.
    The OS proposes → REHT decides. The OS NEVER executes.

    Workflow:
      1. Build a RACS-compatible ``ActionEnvelope`` (via ``governed_propose``).
      2. Send it to the ``RehtClient`` for admissibility evaluation.
      3. Record the verdict in canonical memory (if ``memory`` is provided).
      4. If ADMISSIBLE and ``PAIOS_REHT_ADMISSIBILITY_PROVEN=1`` env is set,
         and a ``maturity_model`` is at L2, attempt L2→L3 advance.
      5. If INADMISSIBLE the proposal is blocked (recorded, not executed).

    Args:
        reht_client: A ``RehtClient`` instance. If ``None``, a default
            client is created (falls back to env-var or in-process).
        memory: Optional ``CanonicalMemory`` instance for recording
            the proposal verdict.
        maturity_model: Optional ``MaturityModel`` instance. When provided
            and the verdict is ADMISSIBLE with ``PAIOS_REHT_ADMISSIBILITY_PROVEN=1``,
            L2→L3 advance is attempted.

    Returns:
        A ``GovernanceResult`` with the envelope + evaluations.

    Raises:
        ``RehtClientError`` if the REHT client is not configured.
        ``assert_no_execution`` is still enforced — no execution path exists.
    """
    # Lazy import to avoid circular dependencies and keep optional
    from paios.boundaries import assert_no_execution
    from paios.reht_client import RehtClient

    client = reht_client or RehtClient()

    # Build the envelope via governed_propose with the REHT client adapter
    # and the (optionally supplied) VAIG evaluator. If no vaig_evaluator is
    # given, governed_propose falls back to the FAIL-CLOSED default VAIG
    # evaluator (DENY) — never a pass-through ALLOW.
    result = governed_propose(
        action_type=action_type,
        actor=actor,
        target=target,
        requested_effect=requested_effect,
        authority_context=authority_context,
        policy_context=policy_context,
        evidence_package=evidence_package,
        environment_state=environment_state,
        risk_context=risk_context,
        expires_in=expires_in,
        vaig_evaluator=vaig_evaluator if vaig_evaluator is not None else _default_vaig_evaluator,
        reht_evaluator=_make_reht_evaluator(client),
    )

    # --- Record the verdict in canonical memory ---
    if memory is not None and result.reht_evaluation is not None:
        from paios.memory import MemoryRecord, MemoryType

        memory.store(
            MemoryRecord(
                id=f"proposal_{result.envelope.action_id[:8]}",
                type=MemoryType.GOVERNANCE_SIGNAL,
                content={
                    "action_type": result.envelope.action_type,
                    "action_id": result.envelope.action_id,
                    "reht_evaluation": result.reht_evaluation,
                    "vaig_evaluation": result.vaig_evaluation,
                    "can_execute": result.can_execute,
                },
                provenance="paios:proposal",
            )
        )

    # --- Maturity gating (L2→L3) ---
    # Advance only when the proposal is genuinely admissible: BOTH VAIG (ALLOW)
    # and REHT (admissible) must agree. Using only the REHT state would let a
    # fail-open VAIG bypass the gate. can_execute already encodes the AND of
    # both evaluators, so gate on it.
    if (
        maturity_model is not None
        and result.can_execute
        and result.reht_evaluation is not None
    ):
        state = result.reht_evaluation.get("state", "")
        if state == _ADMISSIBLE_STATE and os.environ.get(
            "PAIOS_REHT_ADMISSIBILITY_PROVEN", "0"
        ) == "1":
            from paios.maturity import MaturityLevel

            # Only attempt advance if at L2 and conditions are satisfied
            if (
                maturity_model.current == MaturityLevel.L2_STEERED_RECS
                and maturity_model.can_advance()
            ):
                maturity_model.advance(signal="reht_admissibility_proven")

    # --- Assert no execution boundary ---
    assert_no_execution(
        context=(
            f"Proposal complete for action_type={action_type}, "
            f"action_id={result.envelope.action_id}. "
            f"PAIOS proposes. REHT/Harness executes."
        ),
        raise_on_call=False,
    )

    return result
