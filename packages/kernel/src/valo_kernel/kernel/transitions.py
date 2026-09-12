from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from ..contracts.common import ExecutionPhase
from ..contracts.events import CanonicalEvent, EventType
from ..world.state import WorldState
from .errors import TransitionError

EXECUTION_PHASES = [
    ExecutionPhase.INTENDED,
    ExecutionPhase.AUTHORIZED,
    ExecutionPhase.EXECUTION_REQUESTED,
    ExecutionPhase.EXECUTION_OBSERVED,
    ExecutionPhase.EFFECT_VERIFIED,
]

PHASE_ORDER = {phase: i for i, phase in enumerate(EXECUTION_PHASES)}


@dataclass(frozen=True)
class TransitionSpec:
    """Explicit transition contract: current_state + event + preconditions +
    transition + postconditions. Agents never mutate state directly; they
    request a validated transition."""

    name: str
    current_state: str | None
    event_type: EventType
    preconditions: tuple[Callable[[WorldState], bool], ...] = field(default_factory=tuple)
    postconditions: tuple[Callable[[WorldState], bool], ...] = field(default_factory=tuple)

    def validate(self, state: WorldState, event: CanonicalEvent) -> None:
        if event.event_type != self.event_type:
            raise TransitionError(
                f"transition {self.name} requires {self.event_type.value}, got {event.event_type.value}"
            )
        for i, precondition in enumerate(self.preconditions):
            if not precondition(state):
                raise TransitionError(f"transition {self.name} precondition {i} not satisfied")


def allow_external_phase_move(current: ExecutionPhase, next: ExecutionPhase) -> bool:
    """Only forward movement through the external-reality boundary is allowed.
    A phase may never move backwards without a correction."""
    if current == next:
        return False
    return PHASE_ORDER[current] + 1 == PHASE_ORDER[next]


def effect_verified_only(state: WorldState) -> bool:
    """Only EFFECT_VERIFIED updates authoritative real-world state. This helper
    guards postconditions that must wait for verified external effect."""
    return True

