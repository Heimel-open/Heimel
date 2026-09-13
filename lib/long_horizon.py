"""Long-horizon harness patterns for VALO Factory (#52).

Adopts resumability, isolated child contexts, judge-fork review, memory
compaction and sandbox-lifecycle patterns from Google ADK Long Horizon into
VALO Factory, WITHOUT a Google ADK runtime dependency and WITHOUT authority
leakage.

Hard boundary: VAIG evaluates; REHT authorizes consequence-bearing execution;
RACS expresses the decision. Harness state, memory, judges, sandboxes,
providers and resumability never grant authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ChildContextRef:
    """A scoped, isolated child execution context."""

    context_id: str
    parent_id: str
    purpose: str
    workspace_ref: str
    created_at: datetime = field(default_factory=_utcnow)


@dataclass(frozen=True)
class MemoryChunk:
    """A compacted, versioned memory slice."""

    chunk_id: str
    scope_id: str
    content_digest: str
    version: int = 1
    supersedes: str | None = None


@dataclass(frozen=True)
class CheckpointRef:
    """A resumable checkpoint (state snapshot, no authority)."""

    checkpoint_id: str
    run_id: str
    step: int
    state_digest: str
    captured_at: datetime = field(default_factory=_utcnow)


@dataclass
class SandboxLifecycleState:
    """Lifecycle of a sandbox: created -> active -> sealed -> reaped.

    Mutable lifecycle state; not a canonical immutable contract.
    """

    sandbox_id: str
    workspace_ref: str
    state: str = "created"  # created | active | sealed | reaped
    sealed_at: datetime | None = None
    reaped_at: datetime | None = None


@dataclass(frozen=True)
class JudgeForkReview:
    """Independent judge-fork review of a candidate.

    Advisory: the review evaluates; it never authorizes, clears or executes.
    """

    review_id: str
    candidate_id: str
    judge_ref: str
    verdict: str  # pass | fail | uncertain
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)


class LongHorizonHarness:
    """Deterministic, resumable long-horizon harness (no authority)."""

    def __init__(self) -> None:
        self._checkpoints: dict[str, CheckpointRef] = {}
        self._children: dict[str, ChildContextRef] = {}
        self._memory: dict[str, MemoryChunk] = {}
        self._sandboxes: dict[str, SandboxLifecycleState] = {}
        self._reviews: list[JudgeForkReview] = []

    # --- Resumability -----------------------------------------------------

    def checkpoint(self, run_id: str, step: int, state: Mapping[str, Any]) -> CheckpointRef:
        ref = CheckpointRef(
            checkpoint_id=f"cp-{run_id}-{step}",
            run_id=run_id,
            step=step,
            state_digest=_digest(state),
        )
        self._checkpoints[ref.checkpoint_id] = ref
        return ref

    def resume_from(self, run_id: str, step: int) -> CheckpointRef | None:
        return self._checkpoints.get(f"cp-{run_id}-{step}")

    # --- Isolated child contexts ------------------------------------------

    def spawn_child(self, parent_id: str, purpose: str, workspace_ref: str) -> ChildContextRef:
        ref = ChildContextRef(
            context_id=f"ctx-{len(self._children) + 1}",
            parent_id=parent_id,
            purpose=purpose,
            workspace_ref=workspace_ref,
        )
        self._children[ref.context_id] = ref
        return ref

    def child(self, context_id: str) -> ChildContextRef | None:
        return self._children.get(context_id)

    # --- Memory compaction -------------------------------------------------

    def compact_memory(self, scope_id: str, content_digest: str) -> MemoryChunk:
        prior = [c for c in self._memory.values() if c.scope_id == scope_id]
        version = max((c.version for c in prior), default=0) + 1
        chunk = MemoryChunk(
            chunk_id=f"mem-{scope_id}-{version}",
            scope_id=scope_id,
            content_digest=content_digest,
            version=version,
            supersedes=prior[-1].chunk_id if prior else None,
        )
        self._memory[chunk.chunk_id] = chunk
        return chunk

    def memory_for(self, scope_id: str) -> list[MemoryChunk]:
        return [c for c in self._memory.values() if c.scope_id == scope_id]

    # --- Sandbox lifecycle -------------------------------------------------

    def create_sandbox(self, workspace_ref: str) -> SandboxLifecycleState:
        sb = SandboxLifecycleState(
            sandbox_id=f"sandbox-{len(self._sandboxes) + 1}",
            workspace_ref=workspace_ref,
            state="created",
        )
        self._sandboxes[sb.sandbox_id] = sb
        return sb

    def transition_sandbox(self, sandbox_id: str, target: str) -> SandboxLifecycleState:
        allowed = {"created": {"active"}, "active": {"sealed"},
                   "sealed": {"reaped"}}
        sb = self._sandboxes[sandbox_id]
        if target not in allowed.get(sb.state, set()):
            raise ValueError(f"illegal sandbox transition {sb.state} -> {target}")
        sb.state = target
        now = _utcnow()
        if target == "sealed":
            sb.sealed_at = now
        elif target == "reaped":
            sb.reaped_at = now
        return sb

    # --- Judge-fork review -------------------------------------------------

    def record_review(self, review: JudgeForkReview) -> None:
        self._reviews.append(review)

    def reviews_for(self, candidate_id: str) -> list[JudgeForkReview]:
        return [r for r in self._reviews if r.candidate_id == candidate_id]

    # --- No authority surface ---------------------------------------------

    @property
    def has_authority_surface(self) -> bool:
        return False


def _digest(payload: Mapping[str, Any]) -> str:
    import hashlib
    import json

    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


__all__ = [
    "CheckpointRef",
    "ChildContextRef",
    "JudgeForkReview",
    "LongHorizonHarness",
    "MemoryChunk",
    "SandboxLifecycleState",
]
