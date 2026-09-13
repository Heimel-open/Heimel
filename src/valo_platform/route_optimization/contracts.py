"""Immutable planning contracts for action-frontier route optimization.

These objects propose route order and concurrency only. They never grant
authority, clearance, admissibility or execution permission.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.valo_platform.canonical import canonical_digest
from src.valo_platform.route_optimization.reason_codes import RouteReasonCode


def _constraint_key(item: object) -> str:
    if isinstance(item, RouteConstraint):
        return item.constraint_id
    return str(item.get("constraint_id", ""))


class RouteNodeKind(str, Enum):
    RETRIEVAL = "retrieval"
    CONTEXT = "context"
    MODEL = "model"
    TOOL = "tool"
    TRANSFORMATION = "transformation"
    EVALUATION = "evaluation"
    APPROVAL = "approval"
    EXECUTION = "execution"
    RECEIPT = "receipt"
    OUTCOME = "outcome"


class RouteEdgeKind(str, Enum):
    DEPENDENCY = "dependency"
    EVIDENCE = "evidence"
    AUTHORITY = "authority"
    POLICY = "policy"
    SEMANTIC = "semantic"
    EXECUTION_ORDER = "execution_order"
    RETRY = "retry"
    RECOVERY = "recovery"


class ConstraintKind(str, Enum):
    AUTHORITY = "authority"
    POLICY = "policy"
    MAL_ADMISSIBILITY = "mal_admissibility"
    EVIDENCE = "evidence"
    SEMANTIC_INTEGRITY = "semantic_integrity"
    CONSENT = "consent"
    PRIVACY = "privacy"
    BUDGET = "budget"
    DEADLINE = "deadline"
    RISK = "risk"
    REVERSIBILITY = "reversibility"
    HUMAN_CHECKPOINT = "human_checkpoint"
    EXECUTION_CAPABILITY = "execution_capability"


class SelectionStatus(str, Enum):
    SELECTED = "selected"
    NO_ROUTE = "no_route"


_REASON_BY_CONSTRAINT = {
    ConstraintKind.AUTHORITY: RouteReasonCode.ROUTE_AUTHORITY_INVALID,
    ConstraintKind.POLICY: RouteReasonCode.ROUTE_POLICY_INVALID,
    ConstraintKind.MAL_ADMISSIBILITY: RouteReasonCode.ROUTE_MAL_INADMISSIBLE,
    ConstraintKind.EVIDENCE: RouteReasonCode.ROUTE_EVIDENCE_INSUFFICIENT,
    ConstraintKind.SEMANTIC_INTEGRITY: RouteReasonCode.ROUTE_SEMANTIC_INTEGRITY_FAILED,
    ConstraintKind.CONSENT: RouteReasonCode.ROUTE_CONSENT_INVALID,
    ConstraintKind.PRIVACY: RouteReasonCode.ROUTE_PRIVACY_INVALID,
    ConstraintKind.BUDGET: RouteReasonCode.ROUTE_BUDGET_EXCEEDED,
    ConstraintKind.DEADLINE: RouteReasonCode.ROUTE_DEADLINE_UNREACHABLE,
    ConstraintKind.RISK: RouteReasonCode.ROUTE_RISK_EXCEEDED,
    ConstraintKind.REVERSIBILITY: RouteReasonCode.ROUTE_IRREVERSIBILITY_EXCEEDED,
    ConstraintKind.HUMAN_CHECKPOINT: RouteReasonCode.ROUTE_HUMAN_CHECKPOINT_MISSING,
    ConstraintKind.EXECUTION_CAPABILITY: RouteReasonCode.ROUTE_EXECUTION_CAPABILITY_MISSING,
}


class RouteConstraint(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    constraint_id: str
    kind: ConstraintKind
    satisfied: bool
    hard: bool = True
    evidence_refs: Tuple[str, ...] = ()
    detail: str = ""

    @field_validator("evidence_refs", mode="before")
    @classmethod
    def _sort_evidence(cls, value: object) -> object:
        if value is None:
            return ()
        return tuple(sorted(set(value)))

    @property
    def failure_reason(self) -> RouteReasonCode:
        return _REASON_BY_CONSTRAINT[self.kind]


class RouteEstimate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    execution_ms: int = Field(default=0, ge=0)
    queue_ms: int = Field(default=0, ge=0)
    human_wait_ms: int = Field(default=0, ge=0)
    expected_retry_ms: int = Field(default=0, ge=0)
    expected_rollback_ms: int = Field(default=0, ge=0)
    cost_microunits: int = Field(default=0, ge=0)
    risk_exposure: int = Field(default=0, ge=0, le=100)
    reversibility: int = Field(default=100, ge=0, le=100)
    evidence_strength: int = Field(default=0, ge=0, le=100)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_ref: str = "static"
    version: str = "1"

    @property
    def expected_duration_ms(self) -> int:
        return (
            self.execution_ms
            + self.queue_ms
            + self.human_wait_ms
            + self.expected_retry_ms
            + self.expected_rollback_ms
        )


class RouteNode(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    node_id: str
    kind: RouteNodeKind
    estimate: RouteEstimate = Field(default_factory=RouteEstimate)
    constraints: Tuple[RouteConstraint, ...] = ()
    evidence_refs: Tuple[str, ...] = ()
    owner_ref: str = ""
    owned_resources: Tuple[str, ...] = ()
    mandatory_governance: bool = False
    irreversible: bool = False

    @field_validator("constraints", mode="before")
    @classmethod
    def _sort_constraints(cls, value: object) -> object:
        if value is None:
            return ()
        return tuple(sorted(value, key=_constraint_key))

    @field_validator("evidence_refs", "owned_resources", mode="before")
    @classmethod
    def _sort_strings(cls, value: object) -> object:
        if value is None:
            return ()
        return tuple(sorted(set(value)))


class RouteEdge(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source: str
    target: str
    kind: RouteEdgeKind = RouteEdgeKind.DEPENDENCY
    required: bool = True
    max_traversals: int = Field(default=1, ge=1)


class RouteCandidate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate_id: str
    node_ids: Tuple[str, ...]
    constraints: Tuple[RouteConstraint, ...] = ()
    assumptions: Tuple[str, ...] = ()
    valid_until: Optional[datetime] = None

    @field_validator("node_ids", "assumptions", mode="before")
    @classmethod
    def _sort_strings(cls, value: object) -> object:
        if value is None:
            return ()
        return tuple(sorted(set(value)))

    @field_validator("constraints", mode="before")
    @classmethod
    def _sort_constraints(cls, value: object) -> object:
        if value is None:
            return ()
        return tuple(sorted(value, key=_constraint_key))

    @property
    def route_signature(self) -> str:
        return canonical_digest(
            {
                "node_ids": self.node_ids,
                "constraints": self.constraints,
                "assumptions": self.assumptions,
                "valid_until": self.valid_until,
            }
        )

    @property
    def fingerprint(self) -> str:
        return canonical_digest(self)


class RouteRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    route_request_id: str
    principal_id: str
    purpose_ref: str
    intent_digest: str
    semantic_state_digest: str
    target_outcome_ref: str
    current_state_digest: str
    authority_snapshot_hash: str
    policy_snapshot_hash: str
    context_snapshot_hash: str
    required_constraint_kinds: Tuple[ConstraintKind, ...] = ()
    budget_limit_microunits: Optional[int] = Field(default=None, ge=0)
    deadline_ms: Optional[int] = Field(default=None, ge=0)
    max_risk_exposure: Optional[int] = Field(default=None, ge=0, le=100)
    min_reversibility: Optional[int] = Field(default=None, ge=0, le=100)
    required_human_checkpoints: Tuple[str, ...] = ()
    as_of: datetime
    estimate_set_version: str = "1"

    @field_validator("required_constraint_kinds", mode="before")
    @classmethod
    def _sort_constraints(cls, value: object) -> object:
        if value is None:
            return ()
        return tuple(sorted(set(value), key=lambda item: str(getattr(item, "value", item))))

    @field_validator("required_human_checkpoints", mode="before")
    @classmethod
    def _sort_checkpoints(cls, value: object) -> object:
        if value is None:
            return ()
        return tuple(sorted(set(value)))

    @property
    def fingerprint(self) -> str:
        return canonical_digest(self)


class RouteMetrics(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    completion_ms: int = Field(ge=0)
    total_cost_microunits: int = Field(ge=0)
    max_risk_exposure: int = Field(ge=0, le=100)
    min_reversibility: int = Field(ge=0, le=100)
    min_evidence_strength: int = Field(ge=0, le=100)
    critical_path: Tuple[str, ...]
    parallel_groups: Tuple[Tuple[str, ...], ...]
    active_frontier: Tuple[str, ...]
    estimate_versions: Tuple[str, ...]


class PrunedCandidate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate_id: str
    reasons: Tuple[RouteReasonCode, ...]
    detail: str = ""
    dominated_by: Optional[str] = None


class RoutePivot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    pivot_id: str
    active_frontier: Tuple[str, ...]
    candidate_ids: Tuple[str, ...]


class RouteSelection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: SelectionStatus
    route_request_id: str
    selected_candidate_id: Optional[str] = None
    selected_node_ids: Tuple[str, ...] = ()
    active_frontier: Tuple[str, ...] = ()
    pivot_set: Tuple[RoutePivot, ...] = ()
    critical_path: Tuple[str, ...] = ()
    parallel_groups: Tuple[Tuple[str, ...], ...] = ()
    estimated_completion_ms: Optional[int] = Field(default=None, ge=0)
    estimated_total_cost_microunits: Optional[int] = Field(default=None, ge=0)
    max_risk_exposure: Optional[int] = Field(default=None, ge=0, le=100)
    min_reversibility: Optional[int] = Field(default=None, ge=0, le=100)
    min_evidence_strength: Optional[int] = Field(default=None, ge=0, le=100)
    estimate_versions: Tuple[str, ...] = ()
    assumptions: Tuple[str, ...] = ()
    pruned_candidates: Tuple[PrunedCandidate, ...] = ()
    blockers: Tuple[RouteReasonCode, ...] = ()
    valid_until: Optional[datetime] = None
    route_digest: Optional[str] = None

    @property
    def fingerprint(self) -> str:
        return canonical_digest(self.model_copy(update={"route_digest": None}))


__all__ = [
    "ConstraintKind",
    "PrunedCandidate",
    "RouteCandidate",
    "RouteConstraint",
    "RouteEdge",
    "RouteEdgeKind",
    "RouteEstimate",
    "RouteMetrics",
    "RouteNode",
    "RouteNodeKind",
    "RoutePivot",
    "RouteRequest",
    "RouteSelection",
    "SelectionStatus",
]
