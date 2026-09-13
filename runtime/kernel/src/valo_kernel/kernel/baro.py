from __future__ import annotations

from ..contracts.common import ExecutionPhase
from ..world.state import WorldState
from .errors import DivergenceError


def check_postconditions(
    state: WorldState,
    *,
    expected: dict[str, str],
    process_ref: str,
) -> None:
    """BARO check: expected postcondition vs actually observed state. On
    mismatch the kernel raises DivergenceError and never marks the postcondition
    as verified. Example: expected invoice.status=PAID while the invoice is
    still OPEN is divergence — 'green while dead' is prevented."""

    for entity_id, expected_state in expected.items():
        entity = state.entities.get(entity_id)
        actual = entity.state if entity is not None else None
        if actual != expected_state:
            raise DivergenceError(
                f"state divergence for {entity_id}: expected {expected_state}, "
                f"got {actual or 'missing'}"
            )

    phase = state.clocks.get(f"{process_ref}:phase")
    if phase == ExecutionPhase.EFFECT_VERIFIED.value:
        raise DivergenceError(f"process {process_ref} already marked effect verified")
