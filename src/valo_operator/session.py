"""Operator session boundary.

A session is the EXPLICIT identity context of an Operator submission: who
(actor + verified identity), in which tenant, for which purpose, under which
delegation, and whether a step-up was granted. The Operator validates the
session against Kernel truth BEFORE anything runs; the session never carries
authority — it names the principal the boundary will evaluate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OperatorSession(BaseModel):
    """Explicit identity context for a submission. `step_up` marks that a
    human explicitly escalated a rights-impacting action; it never grants
    authority by itself."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tenant_id: str = Field(min_length=1)
    actor: str = Field(min_length=1)
    identity_id: str | None = None
    purpose_id: str | None = None
    delegation_ref: str | None = None
    step_up: bool = False


def validate_session(kernel: Any, session: OperatorSession) -> list[str]:
    """Deterministic session validation against Kernel truth. Returns the list
    of violations (empty == valid). Never authorizes; it only confirms the
    principal exists and is properly identified in this tenant."""
    state = kernel.state()
    violations: list[str] = []

    if session.tenant_id != state.tenant_id:
        violations.append(f"tenant mismatch: session {session.tenant_id} != kernel {state.tenant_id}")

    if session.actor not in state.entities:
        violations.append(f"unknown actor entity: {session.actor}")

    if session.identity_id is not None:
        claim = state.identities.get(session.identity_id)
        if claim is None:
            violations.append(f"unknown identity: {session.identity_id}")
        elif claim.entity_id != session.actor:
            violations.append(f"identity {session.identity_id} does not belong to actor {session.actor}")
        elif not claim.is_active():
            violations.append(f"identity {session.identity_id} is not active")
    else:
        matches = [c for c in state.identities.values() if c.entity_id == session.actor and c.is_active()]
        if len(matches) != 1:
            violations.append(f"actor {session.actor} has no unique active verified identity")

    if session.purpose_id is not None:
        purpose = state.purposes.get(session.purpose_id)
        if purpose is None:
            violations.append(f"unknown purpose: {session.purpose_id}")
        elif not purpose.validity.is_active_at(state.clock()):
            violations.append(f"purpose {session.purpose_id} is not active")

    if session.delegation_ref is not None:
        delegation = state.delegations.get(session.delegation_ref)
        if delegation is None:
            violations.append(f"unknown delegation: {session.delegation_ref}")
        elif not delegation.is_active(None):
            violations.append(f"delegation {session.delegation_ref} is not active")

    return violations


@dataclass
class SessionStatus:
    valid: bool
    violations: list[str] = field(default_factory=list)
