from __future__ import annotations

from datetime import datetime
from typing import Any

from ..contracts.common import canonical_digest, utcnow
from ..contracts.events import CanonicalEvent
from ..contracts.workspace import WorkspaceExecutionBinding
from ..world.state import WorldState
from .errors import ExecutionContextError
from .workspace import changed_dependencies


def build_execution_context(
    state: WorldState,
    *,
    actor: str,
    capability: str,
    target: str,
    requested_transition: CanonicalEvent,
    identity_id: str | None = None,
    purpose_id: str | None = None,
    moment: datetime | None = None,
    event_position: int = 0,
    execution_nonce: str | None = None,
    workspace_binding: WorkspaceExecutionBinding | None = None,
) -> dict[str, Any]:
    """Build the complete execution context delivered to REHT. The kernel
    authorizes nothing; REHT remains the sole authorization boundary.

    Fail-closed: an actor without a verified execution identity cannot act."""
    moment = moment or utcnow()
    if event_position < 0:
        raise ExecutionContextError("execution event position cannot be negative")
    execution_nonce = (
        execution_nonce
        or requested_transition.idempotency_key
        or requested_transition.event_id
    )
    if not execution_nonce:
        raise ExecutionContextError("execution nonce is required")

    current_state_root = state.root_hash()
    if workspace_binding is not None:
        if workspace_binding.tenant_id != state.tenant_id:
            raise ExecutionContextError(
                "workspace tenant differs from current Kernel state"
            )
        if moment < workspace_binding.conformed_at:
            raise ExecutionContextError("workspace conformance is in the future")
        if moment >= workspace_binding.workspace_expires_at:
            raise ExecutionContextError("workspace expired after conformance")
        if event_position < workspace_binding.source_event_position:
            raise ExecutionContextError(
                "execution event position predates the governed projection"
            )
        action = workspace_binding.proposed_action
        if action.capability != capability or action.target != target:
            raise ExecutionContextError(
                "execution request differs from conformed proposed action"
            )
        if purpose_id != action.purpose_id:
            raise ExecutionContextError(
                "execution purpose differs from conformed proposed action"
            )
        changed = changed_dependencies(workspace_binding.dependencies, state)
        if changed:
            raise ExecutionContextError(
                "workspace relevant state changed after conformance: "
                + ", ".join(changed)
            )
        if workspace_binding.dependency_digest != canonical_digest(
            [item.model_dump(mode="json") for item in workspace_binding.dependencies]
        ):
            raise ExecutionContextError("workspace dependency binding is invalid")

    actor_entity = state.entities.get(actor)
    if actor_entity is None:
        raise ExecutionContextError(f"unknown actor entity: {actor}")

    # Fail closed: every executable actor must carry an explicit active and
    # verified execution identity. There is no type-based bypass — an
    # unverified ServiceIdentity is not executable either. If identity_id is
    # given it must be the actor's; otherwise the actor must have exactly one
    # active verified claim in state.
    if identity_id is not None:
        claim = state.identities.get(identity_id)
        if claim is None or claim.entity_id != actor or not claim.is_active(moment):
            raise ExecutionContextError(
                "actor has no active verified execution identity"
            )
    else:
        matches = [
            c
            for c in state.identities.values()
            if c.entity_id == actor and c.is_active(moment)
        ]
        if len(matches) != 1:
            raise ExecutionContextError(
                "actor has no unique active verified execution identity; "
                "free-form text identity is not executable"
            )
        claim = matches[0]
        identity_id = claim.identity_id

    authorities = [
        a
        for a in state.authorities.values()
        if a.principal == actor and a.capability == capability and a.is_active(moment)
    ]

    delegations = [
        d
        for d in state.delegations.values()
        if d.delegate == actor and d.is_active(moment)
    ]

    purpose = state.purposes.get(purpose_id) if purpose_id else None

    rights = [
        r for r in state.rights.values() if r.holder == actor and r.is_active(moment)
    ]
    obligations = [
        o
        for o in state.obligations.values()
        if o.obligated_party == actor and o.is_open(moment)
    ]

    contracts = [
        c
        for c in state.contracts.values()
        if actor in c.parties and c.status == "SIGNED"
    ]

    constraints = [
        c for c in state.constraints.values() if c.subject in (actor, target)
    ]

    evidence = [e for e in state.evidence.values() if e.subject in (actor, target)]

    target_entity = state.entities.get(target)

    return {
        "tenant_id": state.tenant_id,
        "actor": actor,
        "identity": identity_id,
        "authority": [a.model_dump(mode="json") for a in authorities],
        "delegation": [d.model_dump(mode="json") for d in delegations],
        "purpose": purpose.model_dump(mode="json") if purpose else None,
        "rights": [r.model_dump(mode="json") for r in rights],
        "obligations": [o.model_dump(mode="json") for o in obligations],
        "current_state": target_entity.model_dump(mode="json")
        if target_entity
        else None,
        "evidence": [e.model_dump(mode="json") for e in evidence],
        "contracts": [c.model_dump(mode="json") for c in contracts],
        "constraints": [c.model_dump(mode="json") for c in constraints],
        "time": {"now": moment.isoformat()},
        "state_ref": (
            workspace_binding.dependency_digest
            if workspace_binding is not None
            else current_state_root
        ),
        "state_root": current_state_root,
        "sequence": event_position,
        "execution_nonce": execution_nonce,
        "workspace_binding": (
            workspace_binding.model_dump(mode="json")
            if workspace_binding is not None
            else None
        ),
        "requested_transition": requested_transition.model_dump(mode="json"),
    }
