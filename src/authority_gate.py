"""Legacy delegation-evaluation compatibility surface.

This module does not grant execution authority. It evaluates whether a request
appears compatible with a stored delegation snapshot and emits a bounded
recommendation only. REHT remains the sole execution-authorization boundary.

Compatibility vocabulary is retained (ALLOW / STEP_UP / DEFER / DENY / HALT),
but every result is explicitly non-authoritative:

    execution_authority = False
    requires_reht_clearance = True

An ``ALLOW`` from this module therefore means only "delegation checks passed";
it MUST NOT be interpreted as permission to execute.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
import hashlib
import json
from typing import Dict, List, Optional


def _utcnow() -> datetime:
    """Return naive UTC for compatibility with persisted legacy timestamps."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AuthorityDecision(str, Enum):
    """Compatibility recommendation vocabulary; never execution authority."""

    ALLOW = "ALLOW"
    STEP_UP = "STEP_UP"
    DEFER = "DEFER"
    DENY = "DENY"
    HALT = "HALT"


PolicyDecision = AuthorityDecision


@dataclass
class AuthorityDelegation:
    """Legacy delegation snapshot used as evaluation evidence."""

    delegator_id: str
    delegator_role: str
    delegatee_id: str
    scope: str
    policy_id: str
    max_value: Optional[float] = None
    max_cost: Optional[float] = None
    valid_from: datetime = field(default_factory=_utcnow)
    valid_until: datetime = field(default_factory=lambda: _utcnow() + timedelta(days=365))
    context_constraints: Dict[str, List[str]] = field(default_factory=dict)
    requires_audit_trail: bool = True
    emergency_escalation_threshold: Optional[float] = None

    def is_current(self) -> bool:
        now = _utcnow()
        return self.valid_from <= now <= self.valid_until

    def matches_context(self, context: Dict[str, str]) -> bool:
        for key, allowed_values in self.context_constraints.items():
            if key in context and context[key] not in allowed_values:
                return False
        return True


@dataclass
class ExecutionRequest:
    """Legacy request shape evaluated before a later REHT clearance step."""

    action_id: str
    action_type: str
    actor: str
    on_behalf_of: Optional[str] = None
    decision_value: Optional[float] = None
    decision_cost: Optional[float] = None
    context: Dict[str, str] = field(default_factory=dict)
    policy_version: Optional[str] = None
    timestamp: datetime = field(default_factory=_utcnow)
    metadata: Dict = field(default_factory=dict)


@dataclass
class AuthorityPolicy:
    """Legacy evaluation policy; does not establish execution authority."""

    require_explicit_delegation: bool = True
    require_context_match: bool = True
    max_escalation_depth: int = 3
    audit_trail_required: bool = True
    emergency_override_enabled: bool = False
    default_escalation_threshold: Optional[float] = None


@dataclass
class AuthorityCheckResult:
    """Non-authoritative delegation evaluation result.

    ``proof_hash`` is an integrity hash over the evaluation record only. It is
    not a clearance, permit, capability token, or authorization proof.
    """

    decision: AuthorityDecision
    delegator: str
    delegatee: str
    scope: str
    reasoning: str
    checked_at: datetime = field(default_factory=_utcnow)
    violations: List[str] = field(default_factory=list)
    proof_hash: str = ""
    execution_authority: bool = False
    requires_reht_clearance: bool = True

    def __post_init__(self) -> None:
        if self.execution_authority:
            raise ValueError("VAIG legacy authority evaluation cannot grant execution authority")
        if not self.requires_reht_clearance:
            raise ValueError("VAIG legacy authority evaluation must require REHT clearance")

    @property
    def can_execute(self) -> bool:
        """Hard compatibility guard: this object can never authorize execution."""
        return False

    def compute_proof(self) -> str:
        payload = {
            "decision": self.decision.value,
            "delegator": self.delegator,
            "delegatee": self.delegatee,
            "scope": self.scope,
            "timestamp": self.checked_at.isoformat(),
            "reasoning": self.reasoning,
            "execution_authority": False,
            "requires_reht_clearance": True,
        }
        proof_json = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(proof_json.encode()).hexdigest()


class AuthorityStore(ABC):
    """Storage interface for legacy delegation snapshots."""

    @abstractmethod
    def get_delegation(self, delegatee_id: str, scope: str) -> Optional[AuthorityDelegation]:
        pass

    @abstractmethod
    def create_delegation(self, delegation: AuthorityDelegation) -> str:
        pass

    @abstractmethod
    def revoke_delegation(self, delegation_id: str) -> bool:
        pass

    @abstractmethod
    def update_delegation(self, delegation_id: str, updates: Dict) -> bool:
        pass

    @abstractmethod
    def list_active_delegations(self, delegatee_id: str) -> List[AuthorityDelegation]:
        pass


class InMemoryAuthorityStore(AuthorityStore):
    """Development/test store for delegation evidence."""

    def __init__(self):
        self._delegations: Dict[str, AuthorityDelegation] = {}
        self._id_counter = 0
        self._revoked_ids: set[str] = set()

    def get_delegation(self, delegatee_id: str, scope: str) -> Optional[AuthorityDelegation]:
        for delegation_id, delegation in self._delegations.items():
            if delegation_id in self._revoked_ids:
                continue
            if delegation.delegatee_id == delegatee_id and delegation.scope == scope:
                return delegation
        return None

    def create_delegation(self, delegation: AuthorityDelegation) -> str:
        self._id_counter += 1
        delegation_id = f"auth_{self._id_counter}"
        self._delegations[delegation_id] = delegation
        return delegation_id

    def revoke_delegation(self, delegation_id: str) -> bool:
        if delegation_id not in self._delegations:
            return False
        self._revoked_ids.add(delegation_id)
        self._delegations[delegation_id].valid_until = _utcnow()
        return True

    def update_delegation(self, delegation_id: str, updates: Dict) -> bool:
        if delegation_id not in self._delegations:
            return False
        for key, value in updates.items():
            if hasattr(self._delegations[delegation_id], key):
                setattr(self._delegations[delegation_id], key, value)
        return True

    def list_active_delegations(self, delegatee_id: str) -> List[AuthorityDelegation]:
        return [
            delegation
            for delegation_id, delegation in self._delegations.items()
            if delegation_id not in self._revoked_ids
            and delegation.delegatee_id == delegatee_id
            and delegation.is_current()
        ]


class AuthorityGate:
    """Backward-compatible delegation evaluator.

    The historical class name is retained for imports. ``check_authority`` only
    evaluates delegation evidence and never grants execution authority.
    """

    def __init__(
        self,
        authority_store: Optional[AuthorityStore] = None,
        policy: Optional[AuthorityPolicy] = None,
    ):
        self.store = authority_store or InMemoryAuthorityStore()
        self.policy = policy or AuthorityPolicy()
        self.decision_log: List[AuthorityCheckResult] = []

    def _result(
        self,
        *,
        decision: AuthorityDecision,
        delegator: str,
        delegatee: str,
        scope: str,
        reasoning: str,
        violations: Optional[List[str]] = None,
    ) -> AuthorityCheckResult:
        result = AuthorityCheckResult(
            decision=decision,
            delegator=delegator,
            delegatee=delegatee,
            scope=scope,
            reasoning=reasoning,
            violations=list(violations or []),
        )
        result.proof_hash = result.compute_proof()
        self.decision_log.append(result)
        return result

    def check_authority(self, request: ExecutionRequest) -> AuthorityCheckResult:
        """Evaluate delegation compatibility; REHT clearance is still required."""
        delegation = self.store.get_delegation(request.actor, request.action_type)
        if not delegation:
            return self._result(
                decision=AuthorityDecision.DENY,
                delegator="unknown",
                delegatee=request.actor,
                scope=request.action_type,
                reasoning="No active delegation found",
                violations=[
                    f"No active delegation found for {request.actor} to perform {request.action_type}"
                ],
            )

        if not delegation.is_current():
            return self._result(
                decision=AuthorityDecision.DENY,
                delegator=delegation.delegator_id,
                delegatee=request.actor,
                scope=request.action_type,
                reasoning="Delegation expired",
                violations=[
                    f"Delegation from {delegation.delegator_id} expired on {delegation.valid_until}"
                ],
            )

        if not delegation.matches_context(request.context):
            return self._result(
                decision=AuthorityDecision.DENY,
                delegator=delegation.delegator_id,
                delegatee=request.actor,
                scope=request.action_type,
                reasoning="Context violation",
                violations=[
                    f"Request context {request.context} violates delegation constraints"
                ],
            )

        if (
            delegation.emergency_escalation_threshold is not None
            and request.decision_value is not None
            and request.decision_value > delegation.emergency_escalation_threshold
        ):
            return self._result(
                decision=AuthorityDecision.HALT,
                delegator=delegation.delegator_id,
                delegatee=request.actor,
                scope=request.action_type,
                reasoning="Emergency threshold exceeded, halt and escalate",
                violations=[
                    f"Decision value {request.decision_value} exceeds emergency threshold"
                ],
            )

        if (
            delegation.max_value is not None
            and request.decision_value is not None
            and request.decision_value > delegation.max_value
        ):
            return self._result(
                decision=AuthorityDecision.STEP_UP,
                delegator=delegation.delegator_id,
                delegatee=request.actor,
                scope=request.action_type,
                reasoning="Value exceeds limit, escalation required",
                violations=[
                    f"Decision value {request.decision_value} exceeds limit {delegation.max_value}"
                ],
            )

        if (
            delegation.max_cost is not None
            and request.decision_cost is not None
            and request.decision_cost > delegation.max_cost
        ):
            return self._result(
                decision=AuthorityDecision.DEFER,
                delegator=delegation.delegator_id,
                delegatee=request.actor,
                scope=request.action_type,
                reasoning="Cost exceeds budget allocation, requires approval",
                violations=[
                    f"Execution cost {request.decision_cost} exceeds limit {delegation.max_cost}"
                ],
            )

        return self._result(
            decision=AuthorityDecision.ALLOW,
            delegator=delegation.delegator_id,
            delegatee=request.actor,
            scope=request.action_type,
            reasoning=(
                "Delegation evaluation passed under policy "
                f"{delegation.policy_id}; REHT clearance remains required"
            ),
        )

    def create_delegation(
        self,
        delegator_id: str,
        delegator_role: str,
        delegatee_id: str,
        scope: str,
        policy_id: str,
        max_value: Optional[float] = None,
        max_cost: Optional[float] = None,
        context_constraints: Optional[Dict[str, List[str]]] = None,
        valid_days: int = 365,
    ) -> str:
        delegation = AuthorityDelegation(
            delegator_id=delegator_id,
            delegator_role=delegator_role,
            delegatee_id=delegatee_id,
            scope=scope,
            policy_id=policy_id,
            max_value=max_value,
            max_cost=max_cost,
            valid_until=_utcnow() + timedelta(days=valid_days),
            context_constraints=context_constraints or {},
        )
        return self.store.create_delegation(delegation)

    def get_decision_log(self) -> List[AuthorityCheckResult]:
        return self.decision_log.copy()

    def get_delegation_status(self, delegatee_id: str) -> Dict:
        delegations = self.store.list_active_delegations(delegatee_id)
        return {
            "delegatee": delegatee_id,
            "active_delegations": len(delegations),
            "scopes": [d.scope for d in delegations],
            "delegators": list({d.delegator_id for d in delegations}),
            "execution_authority": False,
            "requires_reht_clearance": True,
        }
