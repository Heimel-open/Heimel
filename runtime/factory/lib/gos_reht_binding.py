"""GOS-001E: deterministic binding of Governance OS to REHT and RACS runtime.

Canonical anchor: ``nsolland/Index`` PR #483
(``research/tracks/execution-governance/2026-07-27-governance-os-ai-board-control-system.md``).

This module builds a deterministic *binding/context* layer only. It assembles a
REHT-context from purpose, intent, hierarchy, active authority path, active
weights, evidence validity, cumulative exposure and revalidation triggers and
maps the result deterministically to a RACS outcome. It never changes REHT or
RACS semantics and it never grants execution authority.

Mechanical invariant: a RACS result produced here is an *outcome mapping*
(``ALLOW`` / ``DEFER`` / ``STEP_UP`` / ``DENY``), not an execution permit. The
engine exposes no ``authorize`` / ``execute`` / ``clear`` surface and
``AUTHORITY_EFFECT`` is always ``"none"``.

Binding rules (deterministic, in evaluation order):

* when a prior clearance is supplied, it is revalidated against the current
  context first; changed mandate/evidence/assumptions invalidate it
  (``DEFER``, decisive gate ``revalidation``);
* unknown mandatory state anywhere -> never ``ALLOW`` (``DEFER``/``STEP_UP``);
* reserved action -> ``STEP_UP`` when human elevation is enabled, otherwise
  ``DENY``;
* purpose not bound / mandate scope violation / authority path revoked /
  cumulative exposure exceeded -> ``DENY``;
* stale or invalid evidence/assumptions, or expired/suspended mandate ->
  ``DEFER``.

Clearance, execution and outcome receipts stay separate. Every receipt
identifies the decisive gates, the active profiles and the provenance chain.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "gos-reht-binding-v1"
AUTHORITY_EFFECT = "none"

# RACS outcome mapping produced by this binding layer. Deterministic only;
# it never grants execution authority.
RACS_OUTCOMES = ("ALLOW", "DEFER", "STEP_UP", "DENY")

# Revalidation outcomes for prior clearance records.
REVALIDATED_CLEARED = "CLEARED"
REVALIDATED_STALE = "INVALIDATED_STALE"

# Gate names (decisive gates are reported on every result and receipt).
GATE_FAIL_CLOSED = "fail_closed_state"
GATE_RESERVED_ACTION = "reserved_action"
GATE_PURPOSE_BOUND = "purpose_bound"
GATE_MANDATE_VALID = "mandate_valid"
GATE_AUTHORITY_PATH_ACTIVE = "authority_path_active"
GATE_EVIDENCE_VALID = "evidence_valid"
GATE_ASSUMPTIONS_VALID = "assumptions_valid"
GATE_REVALIDATION = "revalidation"
GATE_CUMULATIVE_EXPOSURE = "cumulative_exposure"

# Known state vocabularies. Anything outside them is an unknown mandatory
# state and must fail closed (never ALLOW).
KNOWN_EVIDENCE_STATES = frozenset({"valid", "invalidated", "stale", "expired", "not_active"})
KNOWN_ASSUMPTION_STATES = frozenset({"valid", "invalidated", "stale", "expired", "not_active"})
KNOWN_MANDATE_STATES = frozenset({"active", "revoked", "suspended", "expired"})
KNOWN_AUTHORITY_STATES = frozenset({"active", "revoked", "suspended", "expired"})


class GosRehtBindingError(ValueError):
    """Base error for GOS -> REHT/RACS binding contract violations."""


class MissingClearanceError(GosRehtBindingError):
    """An execution/outcome receipt referenced an unknown clearance."""


class MissingExecutionError(GosRehtBindingError):
    """An outcome receipt referenced an unknown execution."""


class ReceiptChainOrderError(GosRehtBindingError):
    """Receipts must stay separate and reference a valid predecessor."""


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _require_nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GosRehtBindingError(f"{name} must be a non-empty string")
    return value.strip()


# ---------------------------------------------------------------------------
# Deterministic models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GovernancePurpose:
    """Constitutional purpose. Immutable; binds every intent below it."""

    purpose_id: str
    content_digest: str
    version: int = 1

    def __post_init__(self) -> None:
        _require_nonempty(self.purpose_id, "purpose_id")
        _require_nonempty(self.content_digest, "content_digest")
        if self.version < 1:
            raise GosRehtBindingError("purpose version must be >= 1")

    def digest(self) -> str:
        return digest({
            "purpose_id": self.purpose_id,
            "content_digest": self.content_digest,
            "version": self.version,
        })


@dataclass(frozen=True)
class BoardIntent:
    """Board intent: binds purpose, scope, assumptions and reserved actions."""

    intent_id: str
    purpose_ref: str
    description: str
    reserved_actions: tuple[str, ...] = field(default_factory=tuple)
    assumptions: tuple[str, ...] = field(default_factory=tuple)
    scope_actions: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _require_nonempty(self.intent_id, "intent_id")
        _require_nonempty(self.purpose_ref, "purpose_ref")
        _require_nonempty(self.description, "description")
        object.__setattr__(self, "reserved_actions", tuple(self.reserved_actions))
        object.__setattr__(self, "assumptions", tuple(self.assumptions))
        object.__setattr__(self, "scope_actions", tuple(self.scope_actions))

    def digest(self) -> str:
        return digest({
            "intent_id": self.intent_id,
            "purpose_ref": self.purpose_ref,
            "description": self.description,
            "reserved_actions": self.reserved_actions,
            "assumptions": self.assumptions,
            "scope_actions": self.scope_actions,
        })


@dataclass(frozen=True)
class EnterpriseMandate:
    """Narrow enterprise mandate granted by a principal to a grantee."""

    mandate_id: str
    principal: str
    grantee: str
    scope_actions: tuple[str, ...] = field(default_factory=tuple)
    assumptions: tuple[str, ...] = field(default_factory=tuple)
    state: str = "active"
    valid_until: datetime | None = None

    def __post_init__(self) -> None:
        _require_nonempty(self.mandate_id, "mandate_id")
        _require_nonempty(self.principal, "principal")
        _require_nonempty(self.grantee, "grantee")
        object.__setattr__(self, "scope_actions", tuple(self.scope_actions))
        object.__setattr__(self, "assumptions", tuple(self.assumptions))
        # State is NOT validated here: the binding engine is the deterministic
        # boundary that must fail closed on unknown mandatory state.
        if self.state not in KNOWN_MANDATE_STATES and not isinstance(self.state, str):
            raise GosRehtBindingError("mandate state must be a string")

    def digest(self) -> str:
        return digest({
            "mandate_id": self.mandate_id,
            "principal": self.principal,
            "grantee": self.grantee,
            "scope_actions": self.scope_actions,
            "assumptions": self.assumptions,
            "state": self.state,
        })


@dataclass(frozen=True)
class DelegationNode:
    """One delegation on the active authority path (may only narrow scope)."""

    delegation_id: str
    granter: str
    grantee: str
    authority_scope: tuple[str, ...] = field(default_factory=tuple)
    weight_pct: int = 100
    exposure_units: int = 0
    state: str = "active"
    valid_until: datetime | None = None

    def __post_init__(self) -> None:
        _require_nonempty(self.delegation_id, "delegation_id")
        _require_nonempty(self.granter, "granter")
        _require_nonempty(self.grantee, "grantee")
        object.__setattr__(self, "authority_scope", tuple(self.authority_scope))
        if self.weight_pct < 0 or self.weight_pct > 100:
            raise GosRehtBindingError("weight_pct must be within 0..100")
        if self.exposure_units < 0:
            raise GosRehtBindingError("exposure_units must be >= 0")
        if not isinstance(self.state, str):
            raise GosRehtBindingError("delegation state must be a string")

    @property
    def weighted_exposure_units(self) -> int:
        return self.exposure_units * self.weight_pct // 100

    def digest(self) -> str:
        return digest({
            "delegation_id": self.delegation_id,
            "granter": self.granter,
            "grantee": self.grantee,
            "authority_scope": self.authority_scope,
            "weight_pct": self.weight_pct,
            "exposure_units": self.exposure_units,
            "state": self.state,
        })


@dataclass(frozen=True)
class EvidenceItem:
    """Evidence validity artifact. Evidence is never an instruction surface."""

    evidence_id: str
    state: str
    content_digest: str
    mandatory: bool = False

    def __post_init__(self) -> None:
        _require_nonempty(self.evidence_id, "evidence_id")
        _require_nonempty(self.content_digest, "content_digest")
        if not isinstance(self.state, str):
            raise GosRehtBindingError("evidence state must be a string")

    def digest(self) -> str:
        return digest({
            "evidence_id": self.evidence_id,
            "state": self.state,
            "content_digest": self.content_digest,
            "mandatory": self.mandatory,
        })


@dataclass(frozen=True)
class Assumption:
    """An assumption with a validity state and invalidation trigger."""

    assumption_id: str
    state: str
    content_digest: str
    mandatory: bool = True

    def __post_init__(self) -> None:
        _require_nonempty(self.assumption_id, "assumption_id")
        _require_nonempty(self.content_digest, "content_digest")
        if not isinstance(self.state, str):
            raise GosRehtBindingError("assumption state must be a string")

    def digest(self) -> str:
        return digest({
            "assumption_id": self.assumption_id,
            "state": self.state,
            "content_digest": self.content_digest,
            "mandatory": self.mandatory,
        })


@dataclass(frozen=True)
class ActiveProfile:
    """An active production profile and its decision weights."""

    profile_id: str
    content_digest: str
    weights: tuple[tuple[str, int], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _require_nonempty(self.profile_id, "profile_id")
        _require_nonempty(self.content_digest, "content_digest")
        object.__setattr__(self, "weights", tuple(self.weights))

    def digest(self) -> str:
        return digest({
            "profile_id": self.profile_id,
            "content_digest": self.content_digest,
            "weights": list(self.weights),
        })


@dataclass(frozen=True)
class HumanRatification:
    """Human ratification of one reserved action."""

    ratification_id: str
    action_digest: str
    ratified_by: str
    purpose_ref: str

    def __post_init__(self) -> None:
        _require_nonempty(self.ratification_id, "ratification_id")
        _require_nonempty(self.action_digest, "action_digest")
        _require_nonempty(self.ratified_by, "ratified_by")
        _require_nonempty(self.purpose_ref, "purpose_ref")

    def digest(self) -> str:
        return digest({
            "ratification_id": self.ratification_id,
            "action_digest": self.action_digest,
            "ratified_by": self.ratified_by,
            "purpose_ref": self.purpose_ref,
        })


@dataclass(frozen=True)
class RehtContext:
    """Assembled REHT context: everything REHT needs immediately before a
    consequence, bound into one deterministic artifact."""

    purpose: GovernancePurpose
    intent: BoardIntent
    mandate: EnterpriseMandate
    delegation_path: tuple[DelegationNode, ...] = field(default_factory=tuple)
    evidence: tuple[EvidenceItem, ...] = field(default_factory=tuple)
    assumptions: tuple[Assumption, ...] = field(default_factory=tuple)
    active_profiles: tuple[ActiveProfile, ...] = field(default_factory=tuple)
    ratifications: tuple[HumanRatification, ...] = field(default_factory=tuple)
    exposure_limit_units: int = 0
    elevation_enabled: bool = False
    agent: str = ""

    def __post_init__(self) -> None:
        _require_nonempty(self.agent, "agent")
        if self.exposure_limit_units < 0:
            raise GosRehtBindingError("exposure_limit_units must be >= 0")
        object.__setattr__(self, "delegation_path", tuple(self.delegation_path))
        object.__setattr__(self, "evidence", tuple(self.evidence))
        object.__setattr__(self, "assumptions", tuple(self.assumptions))
        object.__setattr__(self, "active_profiles", tuple(self.active_profiles))
        object.__setattr__(self, "ratifications", tuple(self.ratifications))
        # Purpose binding is NOT enforced here: the engine's ``purpose_bound``
        # gate is the deterministic enforcement point.

    @property
    def mandate_digest(self) -> str:
        return self.mandate.digest()

    @property
    def evidence_digest(self) -> str:
        return digest([item.digest() for item in self.evidence])

    @property
    def assumptions_digest(self) -> str:
        return digest([item.digest() for item in self.assumptions])

    @property
    def provenance_chain(self) -> tuple[str, ...]:
        return (
            self.purpose.purpose_id,
            self.intent.intent_id,
            self.mandate.mandate_id,
            *[node.delegation_id for node in self.delegation_path],
            self.agent,
        )

    @property
    def active_profile_ids(self) -> tuple[str, ...]:
        return tuple(profile.profile_id for profile in self.active_profiles)

    @property
    def cumulative_exposure_units(self) -> int:
        return sum(
            node.weighted_exposure_units for node in self.delegation_path
        )

    @property
    def authority_path_valid(self) -> bool:
        """Chain integrity plus strict no-widening across the delegation tree."""
        nodes = self.delegation_path
        if not nodes:
            return False
        if nodes[0].granter != self.mandate.principal:
            return False
        if nodes[-1].grantee != self.agent:
            return False
        for previous, node in zip(nodes, nodes[1:]):
            if previous.grantee != node.granter:
                return False
            if not set(node.authority_scope).issubset(set(previous.authority_scope)):
                return False
        return True

    def context_digest(self) -> str:
        return digest({
            "schema": SCHEMA_VERSION,
            "purpose": self.purpose.digest(),
            "intent": self.intent.digest(),
            "mandate": self.mandate.digest(),
            "delegation_path": [node.digest() for node in self.delegation_path],
            "evidence": [item.digest() for item in self.evidence],
            "assumptions": [item.digest() for item in self.assumptions],
            "active_profiles": [profile.digest() for profile in self.active_profiles],
            "ratifications": [r.digest() for r in self.ratifications],
            "exposure_limit_units": self.exposure_limit_units,
            "elevation_enabled": self.elevation_enabled,
            "agent": self.agent,
        })


@dataclass(frozen=True)
class ClearanceRecord:
    """Prior clearance bound to the exact context that produced it."""

    clearance_id: str
    action_digest: str
    context_digest: str
    mandate_digest: str
    evidence_digest: str
    assumptions_digest: str
    decisive_gates: tuple[str, ...] = field(default_factory=tuple)
    active_profiles: tuple[str, ...] = field(default_factory=tuple)
    provenance_chain: tuple[str, ...] = field(default_factory=tuple)

    def digest(self) -> str:
        return digest({
            "clearance_id": self.clearance_id,
            "action_digest": self.action_digest,
            "context_digest": self.context_digest,
            "mandate_digest": self.mandate_digest,
            "evidence_digest": self.evidence_digest,
            "assumptions_digest": self.assumptions_digest,
            "decisive_gates": self.decisive_gates,
            "active_profiles": self.active_profiles,
            "provenance_chain": self.provenance_chain,
        })


@dataclass(frozen=True)
class RevalidationRecord:
    """Result of revalidating a prior clearance against the current context."""

    clearance_ref: str
    status: str  # CLEARED | INVALIDATED_STALE
    changed: tuple[str, ...] = field(default_factory=tuple)
    context_digest: str = ""

    def digest(self) -> str:
        return digest({
            "clearance_ref": self.clearance_ref,
            "status": self.status,
            "changed": self.changed,
            "context_digest": self.context_digest,
        })


@dataclass(frozen=True)
class BindingResult:
    """Deterministic RACS outcome mapping for one action.

    This is an outcome mapping, never an execution permit.
    """

    action_digest: str
    racs_outcome: str
    decisive_gates: tuple[str, ...]
    active_profiles: tuple[str, ...]
    provenance_chain: tuple[str, ...]
    cumulative_exposure_units: int
    exposure_limit_units: int
    clearance_receipt_ref: str = ""
    revalidation: RevalidationRecord | None = None
    reason: str = ""

    def digest(self) -> str:
        return digest({
            "action_digest": self.action_digest,
            "racs_outcome": self.racs_outcome,
            "decisive_gates": self.decisive_gates,
            "active_profiles": self.active_profiles,
            "provenance_chain": self.provenance_chain,
            "cumulative_exposure_units": self.cumulative_exposure_units,
            "exposure_limit_units": self.exposure_limit_units,
            "clearance_receipt_ref": self.clearance_receipt_ref,
            "reason": self.reason,
        })


@dataclass(frozen=True)
class ClearanceReceipt:
    """Clearance receipt. Separate from execution and outcome receipts."""

    receipt_id: str
    action_digest: str
    context_digest: str
    racs_outcome: str
    decisive_gates: tuple[str, ...]
    active_profiles: tuple[str, ...]
    provenance_chain: tuple[str, ...]
    receipt_kind: str = "clearance"

    def digest(self) -> str:
        return digest({
            "receipt_kind": self.receipt_kind,
            "receipt_id": self.receipt_id,
            "action_digest": self.action_digest,
            "context_digest": self.context_digest,
            "racs_outcome": self.racs_outcome,
            "decisive_gates": self.decisive_gates,
            "active_profiles": self.active_profiles,
            "provenance_chain": self.provenance_chain,
        })


@dataclass(frozen=True)
class ExecutionReceipt:
    """Execution receipt. References one clearance; never merged with it."""

    receipt_id: str
    clearance_receipt_ref: str
    action_digest: str
    decisive_gates: tuple[str, ...]
    active_profiles: tuple[str, ...]
    provenance_chain: tuple[str, ...]
    receipt_kind: str = "execution"

    def digest(self) -> str:
        return digest({
            "receipt_kind": self.receipt_kind,
            "receipt_id": self.receipt_id,
            "clearance_receipt_ref": self.clearance_receipt_ref,
            "action_digest": self.action_digest,
            "decisive_gates": self.decisive_gates,
            "active_profiles": self.active_profiles,
            "provenance_chain": self.provenance_chain,
        })


@dataclass(frozen=True)
class OutcomeReceipt:
    """Outcome receipt. References one execution; stays separate from it."""

    receipt_id: str
    execution_receipt_ref: str
    clearance_receipt_ref: str
    action_digest: str
    realized: str
    decisive_gates: tuple[str, ...]
    active_profiles: tuple[str, ...]
    provenance_chain: tuple[str, ...]
    receipt_kind: str = "outcome"

    def digest(self) -> str:
        return digest({
            "receipt_kind": self.receipt_kind,
            "receipt_id": self.receipt_id,
            "execution_receipt_ref": self.execution_receipt_ref,
            "clearance_receipt_ref": self.clearance_receipt_ref,
            "action_digest": self.action_digest,
            "realized": self.realized,
            "decisive_gates": self.decisive_gates,
            "active_profiles": self.active_profiles,
            "provenance_chain": self.provenance_chain,
        })


# ---------------------------------------------------------------------------
# Deterministic engine
# ---------------------------------------------------------------------------


class GosRehtBindingEngine:
    """Deterministic GOS -> REHT -> RACS binding engine.

    The engine only maps governance inputs to a RACS outcome and issues
    separate clearance/execution/outcome receipts. It exposes no authority or
    execution surface.
    """

    def __init__(self) -> None:
        self._clearances: dict[str, ClearanceRecord] = {}
        self._stale_clearances: dict[str, RevalidationRecord] = {}
        self._clearance_receipts: dict[str, ClearanceReceipt] = {}
        self._execution_receipts: dict[str, ExecutionReceipt] = {}
        self._outcome_receipts: dict[str, OutcomeReceipt] = {}
        self._decisions: list[BindingResult] = []

    @staticmethod
    def assemble_context(
        *,
        purpose: GovernancePurpose,
        intent: BoardIntent,
        mandate: EnterpriseMandate,
        delegation_path: Sequence[DelegationNode] = (),
        evidence: Sequence[EvidenceItem] = (),
        assumptions: Sequence[Assumption] = (),
        active_profiles: Sequence[ActiveProfile] = (),
        ratifications: Sequence[HumanRatification] = (),
        exposure_limit_units: int = 0,
        elevation_enabled: bool = False,
        agent: str = "",
    ) -> RehtContext:
        """Assemble a REHT-context from its deterministic components."""
        return RehtContext(
            purpose=purpose,
            intent=intent,
            mandate=mandate,
            delegation_path=tuple(delegation_path),
            evidence=tuple(evidence),
            assumptions=tuple(assumptions),
            active_profiles=tuple(active_profiles),
            ratifications=tuple(ratifications),
            exposure_limit_units=exposure_limit_units,
            elevation_enabled=elevation_enabled,
            agent=agent,
        )

    # -- revalidation ------------------------------------------------------

    def revalidate_clearance(
        self, clearance_id: str, context: RehtContext
    ) -> RevalidationRecord:
        """Revalidate a prior clearance against the current context.

        Changed mandate, evidence or assumptions invalidate the prior clearance
        (it becomes stale); it can never be silently reused.
        """
        record = self._clearances.get(clearance_id)
        if record is None:
            raise MissingClearanceError(f"unknown clearance {clearance_id!r}")

        changed: list[str] = []
        if record.mandate_digest != context.mandate_digest:
            changed.append("mandate")
        if record.evidence_digest != context.evidence_digest:
            changed.append("evidence")
        if record.assumptions_digest != context.assumptions_digest:
            changed.append("assumptions")

        status = REVALIDATED_STALE if changed else REVALIDATED_CLEARED
        result = RevalidationRecord(
            clearance_ref=clearance_id,
            status=status,
            changed=tuple(changed),
            context_digest=context.context_digest(),
        )
        if status == REVALIDATED_STALE:
            self._stale_clearances[clearance_id] = result
        return result

    # -- evaluation --------------------------------------------------------

    def evaluate(
        self,
        action: Mapping[str, Any],
        context: RehtContext,
        *,
        prior_clearance_id: str | None = None,
    ) -> BindingResult:
        """Map one exact action against the REHT-context to a RACS outcome.

        The result is a deterministic outcome mapping (ALLOW/DEFER/STEP_UP/
        DENY), never an execution permit. On ALLOW a clearance record and a
        clearance receipt are issued.
        """
        action_digest = digest(action)

        revalidation = None
        if prior_clearance_id is not None:
            revalidation = self.revalidate_clearance(prior_clearance_id, context)
            if revalidation.status == REVALIDATED_STALE:
                return self._result(
                    action_digest, "DEFER", (GATE_REVALIDATION,), context,
                    revalidation=revalidation,
                    reason="prior clearance invalidated by changed "
                           "mandate/evidence/assumptions",
                )

        # 1. Unknown mandatory state fails closed (never ALLOW).
        if self._has_unknown_state(context):
            outcome = "STEP_UP" if context.elevation_enabled else "DEFER"
            return self._result(
                action_digest, outcome, (GATE_FAIL_CLOSED,), context,
                revalidation=revalidation,
                reason="unknown mandatory state cannot ALLOW",
            )

        # 2. Reserved action -> STEP_UP or DENY.
        if self._action_reserved(action, context):
            if self._human_ratified(action, context):
                pass  # human ratification permits proceeding
            elif context.elevation_enabled:
                return self._result(
                    action_digest, "STEP_UP", (GATE_RESERVED_ACTION,), context,
                    revalidation=revalidation,
                    reason="reserved action requires human elevation",
                )
            else:
                return self._result(
                    action_digest, "DENY", (GATE_RESERVED_ACTION,), context,
                    revalidation=revalidation,
                    reason="reserved action denied without elevation path",
                )

        # 3. Purpose must be bound.
        if context.intent.purpose_ref != context.purpose.purpose_id:
            return self._result(
                action_digest, "DENY", (GATE_PURPOSE_BOUND,), context,
                revalidation=revalidation,
                reason="intent is not bound to the constitutional purpose",
            )

        # 4. Mandate valid.
        mandate_outcome = self._mandate_gate(action, context)
        if mandate_outcome != "ALLOW":
            return self._result(
                action_digest, mandate_outcome, (GATE_MANDATE_VALID,), context,
                revalidation=revalidation,
                reason=self._mandate_reason(action, context),
            )

        # 5. Authority path active (chain integrity + no widening + state).
        authority_outcome = self._authority_gate(context)
        if authority_outcome != "ALLOW":
            return self._result(
                action_digest, authority_outcome,
                (GATE_AUTHORITY_PATH_ACTIVE,), context,
                revalidation=revalidation,
                reason="active authority path is not valid",
            )

        # 6. Mandatory evidence valid.
        if not self._evidence_valid(context):
            return self._result(
                action_digest, "DEFER", (GATE_EVIDENCE_VALID,), context,
                revalidation=revalidation,
                reason="mandatory evidence is stale, invalid or expired",
            )

        # 7. Mandatory assumptions valid.
        if not self._assumptions_valid(context):
            return self._result(
                action_digest, "DEFER", (GATE_ASSUMPTIONS_VALID,), context,
                revalidation=revalidation,
                reason="mandatory assumptions are stale, invalid or expired",
            )

        # 8. Cumulative delegation-tree exposure must stay within the limit.
        exposure = context.cumulative_exposure_units
        if exposure > context.exposure_limit_units:
            return self._result(
                action_digest, "DENY", (GATE_CUMULATIVE_EXPOSURE,), context,
                revalidation=revalidation,
                reason="cumulative delegation-tree exposure exceeds limit",
            )

        # 9. ALLOW: issue clearance record + separate clearance receipt.
        gates = [
            GATE_PURPOSE_BOUND,
            GATE_MANDATE_VALID,
            GATE_AUTHORITY_PATH_ACTIVE,
            GATE_EVIDENCE_VALID,
            GATE_ASSUMPTIONS_VALID,
            GATE_CUMULATIVE_EXPOSURE,
        ]
        if self._action_reserved(action, context):
            gates.insert(0, GATE_RESERVED_ACTION)
        gates = tuple(gates)
        clearance = ClearanceRecord(
            clearance_id=f"clr-{action_digest[:24]}-{len(self._clearances) + 1}",
            action_digest=action_digest,
            context_digest=context.context_digest(),
            mandate_digest=context.mandate_digest,
            evidence_digest=context.evidence_digest,
            assumptions_digest=context.assumptions_digest,
            decisive_gates=gates,
            active_profiles=context.active_profile_ids,
            provenance_chain=context.provenance_chain,
        )
        self._clearances[clearance.clearance_id] = clearance
        receipt = ClearanceReceipt(
            receipt_id=clearance.clearance_id,
            action_digest=action_digest,
            context_digest=clearance.context_digest,
            racs_outcome="ALLOW",
            decisive_gates=clearance.decisive_gates,
            active_profiles=clearance.active_profiles,
            provenance_chain=clearance.provenance_chain,
        )
        self._clearance_receipts[receipt.receipt_id] = receipt
        return self._result(
            action_digest, "ALLOW", gates, context,
            revalidation=revalidation,
            clearance_receipt_ref=receipt.receipt_id,
            reason="all binding gates satisfied",
        )

    # -- receipt issuance --------------------------------------------------

    def record_execution(
        self, action_digest: str, clearance_receipt_ref: str
    ) -> ExecutionReceipt:
        """Issue a separate execution receipt referencing one clearance."""
        clearance = self._clearance_receipts.get(clearance_receipt_ref)
        if clearance is None:
            raise MissingClearanceError(
                f"execution requires a clearance receipt, missing "
                f"{clearance_receipt_ref!r}"
            )
        if clearance.action_digest != action_digest:
            raise ReceiptChainOrderError(
                "execution must reference the exact cleared action"
            )
        if clearance.racs_outcome != "ALLOW":
            raise ReceiptChainOrderError("only ALLOW may proceed to execution")
        receipt = ExecutionReceipt(
            receipt_id=f"exe-{action_digest[:24]}-{len(self._execution_receipts) + 1}",
            clearance_receipt_ref=clearance_receipt_ref,
            action_digest=action_digest,
            decisive_gates=clearance.decisive_gates,
            active_profiles=clearance.active_profiles,
            provenance_chain=clearance.provenance_chain,
        )
        self._execution_receipts[receipt.receipt_id] = receipt
        return receipt

    def record_outcome(
        self,
        execution_receipt_ref: str,
        *,
        realized: str,
    ) -> OutcomeReceipt:
        """Issue a separate outcome receipt referencing one execution."""
        execution = self._execution_receipts.get(execution_receipt_ref)
        if execution is None:
            raise MissingExecutionError(
                f"outcome requires an execution receipt, missing "
                f"{execution_receipt_ref!r}"
            )
        receipt = OutcomeReceipt(
            receipt_id=f"out-{execution.action_digest[:24]}-"
                       f"{len(self._outcome_receipts) + 1}",
            execution_receipt_ref=execution_receipt_ref,
            clearance_receipt_ref=execution.clearance_receipt_ref,
            action_digest=execution.action_digest,
            realized=realized,
            decisive_gates=execution.decisive_gates,
            active_profiles=execution.active_profiles,
            provenance_chain=execution.provenance_chain,
        )
        self._outcome_receipts[receipt.receipt_id] = receipt
        return receipt

    # -- gate helpers ------------------------------------------------------

    def _result(
        self,
        action_digest: str,
        outcome: str,
        decisive_gates: Sequence[str],
        context: RehtContext,
        *,
        revalidation: RevalidationRecord | None = None,
        clearance_receipt_ref: str = "",
        reason: str = "",
    ) -> BindingResult:
        result = BindingResult(
            action_digest=action_digest,
            racs_outcome=outcome,
            decisive_gates=tuple(decisive_gates),
            active_profiles=context.active_profile_ids,
            provenance_chain=context.provenance_chain,
            cumulative_exposure_units=context.cumulative_exposure_units,
            exposure_limit_units=context.exposure_limit_units,
            clearance_receipt_ref=clearance_receipt_ref,
            revalidation=revalidation,
            reason=reason,
        )
        self._decisions.append(result)
        return result

    @staticmethod
    def _action_name(action: Mapping[str, Any]) -> str:
        name = action.get("action")
        return _require_nonempty(name, "action.name")

    @staticmethod
    def _has_unknown_state(context: RehtContext) -> bool:
        if context.mandate.state not in KNOWN_MANDATE_STATES:
            return True
        if any(node.state not in KNOWN_AUTHORITY_STATES
               for node in context.delegation_path):
            return True
        if any(item.state not in KNOWN_EVIDENCE_STATES
               for item in context.evidence):
            return True
        if any(item.state not in KNOWN_ASSUMPTION_STATES
               for item in context.assumptions):
            return True
        return False

    @classmethod
    def _action_reserved(cls, action: Mapping[str, Any], context: RehtContext) -> bool:
        return cls._action_name(action) in context.intent.reserved_actions

    @classmethod
    def _human_ratified(cls, action: Mapping[str, Any], context: RehtContext) -> bool:
        return any(
            r.action_digest == digest(action)
            and r.purpose_ref == context.purpose.purpose_id
            for r in context.ratifications
        )

    @classmethod
    def _mandate_gate(cls, action: Mapping[str, Any], context: RehtContext) -> str:
        mandate = context.mandate
        if mandate.state == "revoked":
            return "DENY"
        if mandate.state in ("suspended", "expired"):
            return "DEFER"
        if mandate.grantee != context.agent:
            return "DENY"
        if mandate.scope_actions and cls._action_name(action) not in mandate.scope_actions:
            return "DENY"
        return "ALLOW"

    @classmethod
    def _mandate_reason(cls, action: Mapping[str, Any], context: RehtContext) -> str:
        mandate = context.mandate
        if mandate.state == "revoked":
            return "mandate revoked"
        if mandate.state in ("suspended", "expired"):
            return "mandate not active"
        if mandate.grantee != context.agent:
            return "mandate not granted to the acting agent"
        if mandate.scope_actions and cls._action_name(action) not in mandate.scope_actions:
            return "action outside mandate scope (no widening)"
        return "mandate gate failed"

    @staticmethod
    def _authority_gate(context: RehtContext) -> str:
        nodes = context.delegation_path
        if not context.authority_path_valid:
            return "DENY"
        for node in nodes:
            if node.state == "revoked":
                return "DENY"
            if node.state in ("suspended", "expired"):
                return "DEFER"
        return "ALLOW"

    @staticmethod
    def _evidence_valid(context: RehtContext) -> bool:
        return all(
            item.state == "valid" for item in context.evidence if item.mandatory
        )

    @staticmethod
    def _assumptions_valid(context: RehtContext) -> bool:
        return all(
            item.state == "valid" for item in context.assumptions if item.mandatory
        )

    # -- inspection --------------------------------------------------------

    @property
    def has_authority_surface(self) -> bool:
        return False

    @property
    def has_execution_surface(self) -> bool:
        return False

    @property
    def decision_count(self) -> int:
        return len(self._decisions)

    @property
    def clearance_count(self) -> int:
        return len(self._clearances)

    @property
    def execution_count(self) -> int:
        return len(self._execution_receipts)

    @property
    def outcome_count(self) -> int:
        return len(self._outcome_receipts)

    @property
    def stale_clearances(self) -> tuple[RevalidationRecord, ...]:
        return tuple(sorted(
            self._stale_clearances.values(),
            key=lambda record: record.clearance_ref,
        ))


__all__ = [
    "AUTHORITY_EFFECT",
    "Assumption",
    "BindingResult",
    "BoardIntent",
    "ClearanceReceipt",
    "ClearanceRecord",
    "DelegationNode",
    "EnterpriseMandate",
    "EvidenceItem",
    "ExecutionReceipt",
    "GATE_ASSUMPTIONS_VALID",
    "GATE_AUTHORITY_PATH_ACTIVE",
    "GATE_CUMULATIVE_EXPOSURE",
    "GATE_EVIDENCE_VALID",
    "GATE_FAIL_CLOSED",
    "GATE_MANDATE_VALID",
    "GATE_PURPOSE_BOUND",
    "GATE_RESERVED_ACTION",
    "GATE_REVALIDATION",
    "GosRehtBindingEngine",
    "GosRehtBindingError",
    "GovernancePurpose",
    "HumanRatification",
    "KNOWN_ASSUMPTION_STATES",
    "KNOWN_AUTHORITY_STATES",
    "KNOWN_EVIDENCE_STATES",
    "KNOWN_MANDATE_STATES",
    "MissingClearanceError",
    "MissingExecutionError",
    "OutcomeReceipt",
    "RACS_OUTCOMES",
    "REVALIDATED_CLEARED",
    "REVALIDATED_STALE",
    "RehtContext",
    "ReceiptChainOrderError",
    "RevalidationRecord",
    "SCHEMA_VERSION",
    "canonical_json",
    "digest",
]
