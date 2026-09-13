"""Governed swarm-runtime contracts for the optional jcode harness.

This module models coordination only. It does not execute agents, grant authority,
merge code, deploy, or attest correctness. Parent workers may delegate bounded
missions to child workers, but authority never propagates through the swarm.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import PurePosixPath
from typing import Iterable


class JcodeSwarmGovernanceError(ValueError):
    pass


class InvalidChildDelegationError(JcodeSwarmGovernanceError):
    pass


class OwnedFileScopeError(JcodeSwarmGovernanceError):
    pass


class ParallelFileCollisionError(JcodeSwarmGovernanceError):
    pass


class ForbiddenDelegatedCapabilityError(JcodeSwarmGovernanceError):
    pass


_FORBIDDEN_CAPABILITY_PREFIXES = (
    "authority.",
    "reht.",
    "racs.",
    "governance.",
    "deploy",
    "merge",
    "external.execute",
)


@dataclass(frozen=True)
class ChildWorkerDelegation:
    parent_worker_id: str
    child_worker_id: str
    mission: str
    owned_files: tuple[str, ...]
    delegated_capabilities: tuple[str, ...]
    parent_scope_digest: str
    authority_effect: str = "none"
    inherits_parent_authority: bool = False
    requires_fresh_reht_clearance: bool = True
    self_development_allowed: bool = False

    def as_dict(self) -> dict:
        return {
            "parent_worker_id": self.parent_worker_id,
            "child_worker_id": self.child_worker_id,
            "mission": self.mission,
            "owned_files": list(self.owned_files),
            "delegated_capabilities": list(self.delegated_capabilities),
            "parent_scope_digest": self.parent_scope_digest,
            "authority_effect": self.authority_effect,
            "inherits_parent_authority": self.inherits_parent_authority,
            "requires_fresh_reht_clearance": self.requires_fresh_reht_clearance,
            "self_development_allowed": self.self_development_allowed,
        }


@dataclass(frozen=True)
class AgentCoordinationMessage:
    sender_worker_id: str
    recipient_refs: tuple[str, ...]
    mode: str
    message_type: str
    content_digest: str
    authority_effect: str = "none"
    creates_mandate: bool = False

    def as_dict(self) -> dict:
        return {
            "sender_worker_id": self.sender_worker_id,
            "recipient_refs": list(self.recipient_refs),
            "mode": self.mode,
            "message_type": self.message_type,
            "content_digest": self.content_digest,
            "authority_effect": self.authority_effect,
            "creates_mandate": self.creates_mandate,
        }


@dataclass(frozen=True)
class PersistentMemoryContext:
    memory_key: str
    content_digest: str
    provenance_ref: str
    freshness_ref: str
    status: str = "context_only"
    authority_effect: str = "none"
    can_authorize: bool = False

    def as_dict(self) -> dict:
        return {
            "memory_key": self.memory_key,
            "content_digest": self.content_digest,
            "provenance_ref": self.provenance_ref,
            "freshness_ref": self.freshness_ref,
            "status": self.status,
            "authority_effect": self.authority_effect,
            "can_authorize": self.can_authorize,
        }


def plan_child_delegation(
    parent_worker_id: str,
    child_worker_id: str,
    mission: str,
    *,
    parent_owned_files: Iterable[str],
    child_owned_files: Iterable[str],
    delegated_capabilities: Iterable[str] = (),
) -> ChildWorkerDelegation:
    """Create a bounded child mission without propagating parent authority."""
    parent_worker_id = _require_text(parent_worker_id, "parent_worker_id")
    child_worker_id = _require_text(child_worker_id, "child_worker_id")
    mission = _require_text(mission, "mission")
    if parent_worker_id == child_worker_id:
        raise InvalidChildDelegationError("child worker must differ from parent worker")

    parent_scope = _normalize_owned_files(parent_owned_files, "parent_owned_files")
    child_scope = _normalize_owned_files(child_owned_files, "child_owned_files")
    if not child_scope:
        raise OwnedFileScopeError("child worker must have an explicit owned-file scope")

    outside_parent_scope = sorted(set(child_scope) - set(parent_scope))
    if outside_parent_scope:
        raise OwnedFileScopeError(
            "child owned files exceed parent scope: " + ", ".join(outside_parent_scope)
        )

    capabilities = tuple(sorted({_require_text(c, "delegated capability") for c in delegated_capabilities}))
    forbidden = [c for c in capabilities if _is_forbidden_capability(c)]
    if forbidden:
        raise ForbiddenDelegatedCapabilityError(
            "child delegation cannot carry authority/promotion capability: "
            + ", ".join(forbidden)
        )

    return ChildWorkerDelegation(
        parent_worker_id=parent_worker_id,
        child_worker_id=child_worker_id,
        mission=mission,
        owned_files=child_scope,
        delegated_capabilities=capabilities,
        parent_scope_digest=_digest("\n".join(parent_scope)),
    )


def find_file_collisions(
    delegations: Iterable[ChildWorkerDelegation],
) -> dict[str, tuple[str, ...]]:
    """Return files claimed by more than one parallel child worker."""
    owners: dict[str, list[str]] = {}
    seen_workers: set[str] = set()
    for delegation in delegations:
        if delegation.child_worker_id in seen_workers:
            raise InvalidChildDelegationError(
                f"duplicate child worker id: {delegation.child_worker_id}"
            )
        seen_workers.add(delegation.child_worker_id)
        for path in delegation.owned_files:
            owners.setdefault(path, []).append(delegation.child_worker_id)
    return {
        path: tuple(sorted(worker_ids))
        for path, worker_ids in sorted(owners.items())
        if len(worker_ids) > 1
    }


def validate_parallel_delegations(
    delegations: Iterable[ChildWorkerDelegation],
) -> tuple[ChildWorkerDelegation, ...]:
    """Fail closed when parallel worker file ownership overlaps."""
    planned = tuple(delegations)
    collisions = find_file_collisions(planned)
    if collisions:
        details = "; ".join(
            f"{path}=>{','.join(worker_ids)}" for path, worker_ids in collisions.items()
        )
        raise ParallelFileCollisionError("parallel owned-file collision: " + details)
    return planned


def plan_coordination_message(
    sender_worker_id: str,
    body: str,
    *,
    recipient_refs: Iterable[str] = (),
    mode: str = "direct",
    message_type: str = "coordination",
) -> AgentCoordinationMessage:
    """Record message metadata without turning swarm messages into mandate."""
    sender_worker_id = _require_text(sender_worker_id, "sender_worker_id")
    body = _require_text(body, "body")
    message_type = _require_text(message_type, "message_type")
    if mode not in {"direct", "broadcast"}:
        raise JcodeSwarmGovernanceError("mode must be direct or broadcast")

    recipients = tuple(sorted({_require_text(r, "recipient_ref") for r in recipient_refs}))
    if mode == "direct" and not recipients:
        raise JcodeSwarmGovernanceError("direct messages require at least one recipient")
    if mode == "broadcast":
        recipients = ("*",)

    return AgentCoordinationMessage(
        sender_worker_id=sender_worker_id,
        recipient_refs=recipients,
        mode=mode,
        message_type=message_type,
        content_digest=_digest(body),
    )


def bind_persistent_memory(
    memory_key: str,
    content: str,
    *,
    provenance_ref: str,
    freshness_ref: str,
) -> PersistentMemoryContext:
    """Bind persistent memory as provenance-bearing context, never authority."""
    return PersistentMemoryContext(
        memory_key=_require_text(memory_key, "memory_key"),
        content_digest=_digest(_require_text(content, "content")),
        provenance_ref=_require_text(provenance_ref, "provenance_ref"),
        freshness_ref=_require_text(freshness_ref, "freshness_ref"),
    )


def _normalize_owned_files(paths: Iterable[str], field: str) -> tuple[str, ...]:
    normalized: set[str] = set()
    for raw in paths:
        path = _require_text(raw, field).replace("\\", "/")
        parsed = PurePosixPath(path)
        if parsed.is_absolute() or ".." in parsed.parts or path.startswith(".git/"):
            raise OwnedFileScopeError(f"invalid owned-file path: {path}")
        normalized.add(str(parsed))
    return tuple(sorted(normalized))


def _is_forbidden_capability(capability: str) -> bool:
    return any(
        capability == prefix or capability.startswith(prefix)
        for prefix in _FORBIDDEN_CAPABILITY_PREFIXES
    )


def _require_text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise JcodeSwarmGovernanceError(f"{field} must be non-empty text")
    return value.strip()


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
