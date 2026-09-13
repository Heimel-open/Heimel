from __future__ import annotations

import pytest

from valo_kernel import DivergenceError, check_postconditions
from valo_kernel.contracts import (
    CanonicalEvent,
    EventType,
    ExecutionPhase,
    utcnow,
)

from .conftest import entity_event


def _set_state(engine, entity_id: str, state: str) -> None:
    engine.append(
        CanonicalEvent(
            event_id=f"set-{entity_id}-{state}",
            event_type=EventType.ENTITY_UPDATED,
            tenant_id="tenant-a",
            subject=entity_id,
            source="kernel",
            effective_at=utcnow(),
            payload={"entity_id": entity_id, "state": state},
        )
    )


def test_expected_postcondition_holds(engine) -> None:
    engine.append(entity_event("tenant-a", "invoice-1", state="OPEN"))
    _set_state(engine, "invoice-1", "PAID")
    check_postconditions(engine.state(), expected={"invoice-1": "PAID"}, process_ref="p1")


def test_state_divergence_detected(engine) -> None:
    """External API said success, payment transferred, but the invoice is still
    OPEN. BARO detects the divergence; 'green while dead' is prevented."""
    engine.append(entity_event("tenant-a", "invoice-1", state="OPEN"))
    with pytest.raises(DivergenceError, match="divergence"):
        check_postconditions(engine.state(), expected={"invoice-1": "PAID"}, process_ref="p1")


def test_effect_verified_only_marks_verified(engine) -> None:
    engine.append(entity_event("tenant-a", "invoice-1", state="OPEN"))
    engine.append(
        CanonicalEvent(
            event_id="phase",
            event_type=EventType.EXECUTION_PHASE_UPDATED,
            tenant_id="tenant-a",
            subject="invoice-1",
            source="veritas",
            effective_at=utcnow(),
            payload={"process_ref": "p1", "phase": ExecutionPhase.EXECUTION_OBSERVED.value},
        )
    )
    assert engine.state().clocks["p1:phase"] == ExecutionPhase.EXECUTION_OBSERVED.value

    # The authoritative postcondition must never be marked verified by a bare
    # external success; BARO re-checks against actual state.
    with pytest.raises(DivergenceError):
        check_postconditions(engine.state(), expected={"invoice-1": "PAID"}, process_ref="p1")


def test_external_phases_move_forward_only() -> None:
    from valo_kernel import allow_external_phase_move

    assert allow_external_phase_move(ExecutionPhase.INTENDED, ExecutionPhase.AUTHORIZED)
    assert allow_external_phase_move(ExecutionPhase.EXECUTION_OBSERVED, ExecutionPhase.EFFECT_VERIFIED)
    assert not allow_external_phase_move(ExecutionPhase.EFFECT_VERIFIED, ExecutionPhase.INTENDED)
    assert not allow_external_phase_move(ExecutionPhase.AUTHORIZED, ExecutionPhase.AUTHORIZED)
