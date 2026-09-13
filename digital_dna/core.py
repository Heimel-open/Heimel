"""Digital DNA primitives for identity continuity research.

Epistemic status: implementation_claim.
This module does not establish truth, standing, authority, or permission to act.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from typing import Any, Mapping


MISSING = object()


def _canonical(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return {key: _canonical(item) for key, item in asdict(value).items()}
    if isinstance(value, Mapping):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (set, frozenset)):
        return sorted(
            (_canonical(item) for item in value),
            key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=False),
        )
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    return value


def canonical_json(value: Any) -> str:
    """Return a stable JSON encoding suitable for hashing."""
    return json.dumps(
        _canonical(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def digest(value: Any) -> str:
    """SHA-256 digest of the canonical representation."""
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def get_path(state: Mapping[str, Any], path: str) -> Any:
    """Resolve a dotted path from a nested mapping."""
    current: Any = state
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return MISSING
        current = current[part]
    return current


class ContinuityDecision(str, Enum):
    CONTINUES = "CONTINUES"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BREAK = "BREAK"
    INDETERMINATE = "INDETERMINATE"


class MemoryStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DORMANT = "DORMANT"
    DISPUTED = "DISPUTED"
    SUPERSEDED = "SUPERSEDED"
    REVOKED = "REVOKED"


class PairOperator(str, Enum):
    EQUAL = "EQUAL"
    NUMERIC_DELTA_LTE = "NUMERIC_DELTA_LTE"


class StateOperator(str, Enum):
    EQUAL = "EQUAL"
    NOT_EQUAL = "NOT_EQUAL"
    EXISTS = "EXISTS"
    IN = "IN"
    LTE = "LTE"
    GTE = "GTE"


@dataclass(frozen=True)
class EquivalenceRule:
    """A deterministic rule for the identity-equivalence relation (~)."""

    path: str
    operator: PairOperator = PairOperator.EQUAL
    tolerance: float | None = None


@dataclass(frozen=True)
class StateRule:
    """A deterministic predicate over the proposed state."""

    path: str
    operator: StateOperator
    expected: Any = None


@dataclass(frozen=True)
class MemoryRecord:
    """A content-addressed memory reference; payload storage remains external."""

    memory_id: str
    content_digest: str
    status: MemoryStatus
    predecessor_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class DigitalDNAManifest:
    """Executable S/T/~/I/C continuity contract."""

    identity_id: str
    version: str
    state_space_id: str
    required_state_paths: tuple[str, ...] = ()
    allowed_transformations: frozenset[str] = frozenset()
    equivalence_rules: tuple[EquivalenceRule, ...] = ()
    invariants: tuple[StateRule, ...] = ()
    collapse_conditions: tuple[StateRule, ...] = ()
    authorized_amenders: frozenset[str] = frozenset()
    parent_manifest_digest: str | None = None

    def manifest_digest(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class IdentityTransition:
    """A proposed movement from one represented identity state to the next."""

    transition_id: str
    transformation: str
    before_state: Mapping[str, Any]
    after_state: Mapping[str, Any]
    observed_at: str
    evidence_digests: tuple[str, ...] = ()
    memory_records: tuple[MemoryRecord, ...] = ()
    proposes_protected_amendment: bool = False
    amendment_authority: str | None = None
    proposed_manifest_digest: str | None = None

    def transition_digest(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class Evaluation:
    decision: ContinuityDecision
    reasons: tuple[str, ...]
    manifest_digest: str
    transition_digest: str


@dataclass(frozen=True)
class ContinuityReceipt:
    """Hash-chainable evidence of one continuity evaluation."""

    identity_id: str
    manifest_digest: str
    transition_digest: str
    previous_state_digest: str
    proposed_state_digest: str
    memory_root_digest: str
    decision: ContinuityDecision
    reasons: tuple[str, ...]
    observed_at: str
    previous_receipt_digest: str | None = None

    @classmethod
    def from_evaluation(
        cls,
        manifest: DigitalDNAManifest,
        transition: IdentityTransition,
        evaluation: Evaluation,
        previous_receipt_digest: str | None = None,
    ) -> "ContinuityReceipt":
        return cls(
            identity_id=manifest.identity_id,
            manifest_digest=evaluation.manifest_digest,
            transition_digest=evaluation.transition_digest,
            previous_state_digest=digest(transition.before_state),
            proposed_state_digest=digest(transition.after_state),
            memory_root_digest=digest(transition.memory_records),
            decision=evaluation.decision,
            reasons=evaluation.reasons,
            observed_at=transition.observed_at,
            previous_receipt_digest=previous_receipt_digest,
        )

    def receipt_digest(self) -> str:
        return digest(self)
