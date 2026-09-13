"""Mechanical consequence-runtime interlocks subordinate to REHT.

Nothing in this module can grant execution authority. The controls only narrow,
block, meter, bind, or receipt an already-authorized consequence path.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from threading import Lock
from typing import Any, Callable, Mapping, Protocol


class MechanicalBlock(RuntimeError):
    """A non-authoritative runtime interlock blocked progression."""


class ProbeDisposition(str, Enum):
    PASS = "PASS"
    OBSERVE = "OBSERVE"
    STEP_UP = "STEP_UP"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class ProbeResult:
    disposition: ProbeDisposition
    reason: str = ""
    evidence: Mapping[str, Any] = field(default_factory=dict)
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if self.execution_authority:
            raise ValueError("pre-commit probes cannot grant execution authority")


class PreCommitProbe(Protocol):
    def evaluate(
        self,
        action: Mapping[str, Any],
        execution_context: Mapping[str, Any],
    ) -> ProbeResult: ...


@dataclass(frozen=True)
class PostconditionResult:
    verified: bool
    reason: str = ""
    evidence: Mapping[str, Any] = field(default_factory=dict)
    authority_granted: bool = False

    def __post_init__(self) -> None:
        if self.authority_granted:
            raise ValueError("postcondition evidence cannot grant authority")


class PostconditionChecker(Protocol):
    def check(
        self,
        action: Mapping[str, Any],
        execution_context: Mapping[str, Any],
        effect_result: Any,
    ) -> PostconditionResult: ...


class RuntimeControlPlane:
    """Thread-safe global/scoped HALT and revocation latch.

    This is an independent mechanical stop surface. It never returns ALLOW and
    cannot create authority; absence of a block merely permits the request to
    continue to REHT and the remaining effect-boundary checks.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._halt_global = False
        self._halted_scopes: set[str] = set()
        self._revoked_authorities: set[str] = set()
        self._revoked_principals: set[str] = set()
        self._revoked_actors: set[str] = set()

    def halt_global(self) -> None:
        with self._lock:
            self._halt_global = True

    def resume_global(self) -> None:
        with self._lock:
            self._halt_global = False

    def halt_scope(self, scope: str) -> None:
        with self._lock:
            self._halted_scopes.add(str(scope))

    def resume_scope(self, scope: str) -> None:
        with self._lock:
            self._halted_scopes.discard(str(scope))

    def revoke_authority(self, authority_ref: str) -> None:
        with self._lock:
            self._revoked_authorities.add(str(authority_ref))

    def revoke_principal(self, principal_id: str) -> None:
        with self._lock:
            self._revoked_principals.add(str(principal_id))

    def revoke_actor(self, actor_id: str) -> None:
        with self._lock:
            self._revoked_actors.add(str(actor_id))

    def check(
        self,
        action: Mapping[str, Any],
        execution_context: Mapping[str, Any],
    ) -> str | None:
        scope = str(action.get("capability") or action.get("action_type") or "")
        actor = str(action.get("actor_id") or execution_context.get("actor_id") or "")
        principal = str(
            action.get("principal_id") or execution_context.get("principal_id") or ""
        )
        authority = str(
            execution_context.get("authority_state_id")
            or execution_context.get("authority_ref")
            or action.get("authority_ref")
            or ""
        )
        with self._lock:
            if self._halt_global:
                return "HALT_GLOBAL"
            if scope and scope in self._halted_scopes:
                return f"HALT_SCOPE:{scope}"
            if authority and authority in self._revoked_authorities:
                return f"REVOKED_AUTHORITY:{authority}"
            if principal and principal in self._revoked_principals:
                return f"REVOKED_PRINCIPAL:{principal}"
            if actor and actor in self._revoked_actors:
                return f"REVOKED_ACTOR:{actor}"
        return None


@dataclass(frozen=True)
class ResourceBudget:
    budget_id: str
    limits: Mapping[str, float]
    parent_id: str | None = None


@dataclass(frozen=True)
class ResourceReservation:
    reservation_id: str
    budget_id: str
    action_digest: str
    amounts: Mapping[str, float]


class ResourceBudgetLedger:
    """Atomic hierarchical resource reservation and consumption ledger.

    A child reservation is charged against the child and every ancestor. This
    prevents sibling budgets from jointly exceeding a shared parent ceiling.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._budgets: dict[str, ResourceBudget] = {}
        self._reserved_totals: dict[str, dict[str, float]] = {}
        self._consumed_totals: dict[str, dict[str, float]] = {}
        self._reservations: dict[str, ResourceReservation] = {}
        self._consumed_reservations: set[str] = set()
        self._permit_bindings: dict[str, str] = {}

    def _lineage(self, budget_id: str) -> tuple[str, ...]:
        lineage: list[str] = []
        seen: set[str] = set()
        current: str | None = budget_id
        while current is not None:
            if current in seen:
                raise ValueError("resource budget cycle detected")
            seen.add(current)
            budget = self._budgets.get(current)
            if budget is None:
                raise ValueError("budget missing")
            lineage.append(current)
            current = budget.parent_id
        return tuple(lineage)

    def register_budget(self, budget: ResourceBudget) -> None:
        with self._lock:
            if budget.budget_id in self._budgets:
                raise ValueError("budget already exists")
            normalized = {str(k): float(v) for k, v in budget.limits.items()}
            if any(value < 0 for value in normalized.values()):
                raise ValueError("resource limits must be non-negative")
            if budget.parent_id is not None:
                parent = self._budgets.get(budget.parent_id)
                if parent is None:
                    raise ValueError("parent budget missing")
                for resource, value in normalized.items():
                    if value > float(parent.limits.get(resource, 0.0)):
                        raise ValueError("child budget cannot widen parent resource limits")
            self._budgets[budget.budget_id] = ResourceBudget(
                budget_id=budget.budget_id,
                limits=normalized,
                parent_id=budget.parent_id,
            )
            self._reserved_totals[budget.budget_id] = {}
            self._consumed_totals[budget.budget_id] = {}

    def reserve(self, reservation: ResourceReservation) -> None:
        with self._lock:
            if reservation.reservation_id in self._reservations:
                raise ValueError("reservation already exists")
            if reservation.budget_id not in self._budgets:
                raise ValueError("budget missing")
            amounts = {str(k): float(v) for k, v in reservation.amounts.items()}
            if any(value < 0 for value in amounts.values()):
                raise ValueError("reservation amounts must be non-negative")
            lineage = self._lineage(reservation.budget_id)
            for budget_id in lineage:
                budget = self._budgets[budget_id]
                reserved = self._reserved_totals[budget_id]
                consumed = self._consumed_totals[budget_id]
                for resource, amount in amounts.items():
                    limit = float(budget.limits.get(resource, 0.0))
                    projected = (
                        reserved.get(resource, 0.0)
                        + consumed.get(resource, 0.0)
                        + amount
                    )
                    if projected > limit:
                        raise ValueError(
                            f"resource budget exceeded: {budget_id}:{resource}"
                        )
            for budget_id in lineage:
                reserved = self._reserved_totals[budget_id]
                for resource, amount in amounts.items():
                    reserved[resource] = reserved.get(resource, 0.0) + amount
            self._reservations[reservation.reservation_id] = ResourceReservation(
                reservation_id=reservation.reservation_id,
                budget_id=reservation.budget_id,
                action_digest=reservation.action_digest,
                amounts=amounts,
            )

    def consume_once(
        self,
        reservation_id: str,
        *,
        action_digest: str,
        permit_ref: str,
    ) -> bool:
        with self._lock:
            reservation = self._reservations.get(reservation_id)
            if reservation is None:
                raise MechanicalBlock("RESOURCE_RESERVATION_MISSING")
            if reservation.action_digest != action_digest:
                raise MechanicalBlock("RESOURCE_ACTION_BINDING_MISMATCH")
            if reservation_id in self._consumed_reservations:
                return False
            for budget_id in self._lineage(reservation.budget_id):
                reserved = self._reserved_totals[budget_id]
                consumed = self._consumed_totals[budget_id]
                for resource, amount in reservation.amounts.items():
                    reserved[resource] = reserved.get(resource, 0.0) - float(amount)
                    consumed[resource] = consumed.get(resource, 0.0) + float(amount)
            self._consumed_reservations.add(reservation_id)
            self._permit_bindings[reservation_id] = permit_ref
            return True

    def is_consumed(self, reservation_id: str) -> bool:
        with self._lock:
            return reservation_id in self._consumed_reservations


class ContainmentInterlock:
    """Deterministic containment/egress/path-binding verifier."""

    def check(
        self,
        action: Mapping[str, Any],
        execution_context: Mapping[str, Any],
    ) -> str | None:
        if not bool(action.get("containment_required", False)):
            return None
        observed = execution_context.get("containment")
        if not isinstance(observed, Mapping):
            return "CONTAINMENT_EVIDENCE_MISSING"
        if observed.get("status") != "VALID":
            return "CONTAINMENT_NOT_VALID"
        if observed.get("revoked") is True or observed.get("breached") is True:
            return "CONTAINMENT_BREACH_OR_REVOCATION"
        if observed.get("egress_mode") != "ADAPTER":
            return "DIRECT_EGRESS_FORBIDDEN"
        if observed.get("credential_lease_active") is not True:
            return "CREDENTIAL_LEASE_INACTIVE"
        if not observed.get("path_head_digest"):
            return "PATH_HEAD_BINDING_MISSING"

        expected = action.get("containment_binding", {})
        if not isinstance(expected, Mapping):
            return "CONTAINMENT_BINDING_INVALID"
        for field in (
            "runtime_id",
            "environment_digest",
            "egress_adapter",
            "credential_lease_id",
            "path_head_digest",
            "epoch",
        ):
            if field in expected and observed.get(field) != expected.get(field):
                return f"CONTAINMENT_BINDING_MISMATCH:{field}"
        return None


class _BoundaryProof:
    pass


_BOUNDARY_PROOF = _BoundaryProof()


class BoundaryEffect:
    """Effect callable mechanically invocable only by EffectBoundary."""

    def __init__(self, name: str, function: Callable[[dict[str, Any]], Any]) -> None:
        if not name:
            raise ValueError("effect name is required")
        self.name = name
        self._function = function

    @classmethod
    def seal(
        cls,
        name: str,
        function: Callable[[dict[str, Any]], Any],
    ) -> "BoundaryEffect":
        return cls(name=name, function=function)

    def invoke(self, action: dict[str, Any]) -> Any:
        raise MechanicalBlock("NO_DIRECT_EFFECT_PATH")

    def _invoke_from_boundary(
        self,
        action: dict[str, Any],
        proof: object,
    ) -> Any:
        if proof is not _BOUNDARY_PROOF:
            raise MechanicalBlock("NO_DIRECT_EFFECT_PATH")
        return self._function(copy.deepcopy(action))


@dataclass(frozen=True)
class ExecutionReceipt:
    receipt_id: str
    status: str
    action_digest: str
    execution_context_hash: str | None
    reht_decision: str | None
    clearance_ref: str | None
    permit_ref: str | None
    effect_name: str | None
    effect_result_digest: str | None
    reason: str | None
    created_at: str
    postconditions_verified: bool | None = None
    authority_granted: bool = False

    def __post_init__(self) -> None:
        if self.authority_granted:
            raise ValueError("execution receipts cannot grant authority")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ExecutionEvidenceSink(Protocol):
    def append(self, receipt: ExecutionReceipt) -> None: ...


class InMemoryExecutionEvidenceSink:
    """Process-local evidence sink for tests/development."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._receipts: list[ExecutionReceipt] = []

    def append(self, receipt: ExecutionReceipt) -> None:
        with self._lock:
            self._receipts.append(receipt)

    def receipts(self) -> list[ExecutionReceipt]:
        with self._lock:
            return list(self._receipts)


def canonical_digest(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_execution_receipt(
    *,
    status: str,
    action: Mapping[str, Any],
    execution_context_hash: str | None,
    reht_decision: str | None,
    clearance_ref: str | None,
    permit_ref: str | None,
    effect_name: str | None,
    effect_result: Any | None = None,
    reason: str | None = None,
    postconditions_verified: bool | None = None,
) -> ExecutionReceipt:
    created_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    core = {
        "status": status,
        "action_digest": canonical_digest(action),
        "execution_context_hash": execution_context_hash,
        "reht_decision": reht_decision,
        "clearance_ref": clearance_ref,
        "permit_ref": permit_ref,
        "effect_name": effect_name,
        "effect_result_digest": (
            canonical_digest(effect_result) if effect_result is not None else None
        ),
        "reason": reason,
        "created_at": created_at,
        "postconditions_verified": postconditions_verified,
        "authority_granted": False,
    }
    return ExecutionReceipt(
        receipt_id="sha256:" + canonical_digest(core),
        **core,
    )


__all__ = [
    "BoundaryEffect",
    "ContainmentInterlock",
    "ExecutionEvidenceSink",
    "ExecutionReceipt",
    "InMemoryExecutionEvidenceSink",
    "MechanicalBlock",
    "PostconditionChecker",
    "PostconditionResult",
    "PreCommitProbe",
    "ProbeDisposition",
    "ProbeResult",
    "ResourceBudget",
    "ResourceBudgetLedger",
    "ResourceReservation",
    "RuntimeControlPlane",
    "build_execution_receipt",
    "canonical_digest",
]
