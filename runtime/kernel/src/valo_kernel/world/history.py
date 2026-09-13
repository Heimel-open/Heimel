from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from ..contracts.events import CanonicalEvent
from ..kernel.integrity import verify_chain
from .state import WorldState


def _replay_events(
    events: list[CanonicalEvent],
    initial: WorldState | None = None,
    reduce_fn: Callable[[WorldState, CanonicalEvent], WorldState] | None = None,
) -> WorldState:
    if reduce_fn is None:
        from ..kernel.reducers import reduce

        reduce_fn = reduce
    if initial is not None:
        state = initial.model_copy(deep=True)
    else:
        state = WorldState(tenant_id=events[0].tenant_id if events else "default")
    for event in events:
        state = reduce_fn(state, event)
    return state


def replay(
    events: list[CanonicalEvent],
    initial: WorldState | None = None,
    reduce_fn: Callable[[WorldState, CanonicalEvent], WorldState] | None = None,
) -> WorldState:
    """Deterministically rebuild state from an event stream. The same stream
    always produces the same state. LLMs are never required for replay."""
    verify_chain(events)
    return _replay_events(events, initial=initial, reduce_fn=reduce_fn)


def replay_at(
    events: list[CanonicalEvent],
    moment: datetime,
    initial: WorldState | None = None,
    reduce_fn: Callable[[WorldState, CanonicalEvent], WorldState] | None = None,
) -> WorldState:
    """RECORDED bitemporal semantics: reconstruct the world as it was known
    (recorded) up to `moment` — filtering on event.timestamp."""
    verify_chain(events)
    applicable = [e for e in events if e.timestamp <= moment]
    return _replay_events(applicable, initial=initial, reduce_fn=reduce_fn)


def state_effective_at(
    events: list[CanonicalEvent],
    moment: datetime,
    initial: WorldState | None = None,
    reduce_fn: Callable[[WorldState, CanonicalEvent], WorldState] | None = None,
) -> WorldState:
    """EFFECTIVE bitemporal semantics: reconstruct the world as it was actually
    in effect at `moment` — filtering on event.effective_at. Corrections and
    backdated events (effective_at in the past) apply for any moment at or after
    their effective time. Distinct from `replay_at` (recorded-by-T)."""
    verify_chain(events)
    applicable = [e for e in events if e.effective_at <= moment]
    return _replay_events(applicable, initial=initial, reduce_fn=reduce_fn)
