"""Read-only operator views. The operator NEVER mutates Kernel state; every
projection is derived from the append-only event stream / immutable state
snapshot the Kernel returns. No state machine, no write path here."""

from __future__ import annotations

from typing import Any

from valo_kernel import KernelEngine
from valo_kernel.contracts.common import utcnow


def kernel_views(kernel: KernelEngine) -> dict[str, Any]:
    """Deterministic read-only projections over the Kernel v1 world state."""
    state = kernel.state()
    return {
        "entities": {
            eid: {
                "type": entity.entity_type.value,
                "state": entity.state,
                "attributes": entity.attributes,
            }
            for eid, entity in state.entities.items()
        },
        "authorities": [
            {
                "authority_id": a.authority_id,
                "principal": a.principal,
                "capability": a.capability,
                "scope": a.scope,
                "constraints": a.constraints,
                "status": a.status,
                "basis": a.basis,
            }
            for a in state.authorities.values()
        ],
        "rights": [
            {"right_id": r.right_id, "holder": r.holder, "right_type": r.right_type, "object": r.object}
            for r in state.rights.values()
        ],
        "reservations": [
            {"reservation_id": r.reservation_id, "resource_id": r.resource_id, "holder": r.holder, "status": r.status}
            for r in state.reservations.values()
        ],
        "events": [
            {"type": e.event_type.value, "subject": e.subject, "actor": e.actor}
            for e in kernel.events()
        ],
        "event_count": kernel.sequence(),
        "time": {"now": _clock(state).isoformat()},
    }


def _clock(state: Any) -> Any:
    values = list(state.clocks.values())
    return max(values) if values else utcnow()


def entities_by_state(kernel: KernelEngine) -> dict[str, list[str]]:
    state = kernel.state()
    by_state: dict[str, list[str]] = {}
    for eid, entity in state.entities.items():
        by_state.setdefault(entity.state, []).append(eid)
    return by_state
