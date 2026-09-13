"""Demonstrator 4: external execution mismatch.

REHT ALLOWs. The Gateway sends the handling. The external API answers success.
Veritas observes the result. BARO finds that the expected postcondition did not
arise: payment transferred but invoice.status is still OPEN. The kernel must
never mark the postcondition as verified. Result: EXCEPTION (divergence). This
prevents 'green while dead'.
"""

from __future__ import annotations

from valo_kernel import DivergenceError, KernelEngine, check_postconditions
from valo_kernel.contracts import (
    CanonicalEvent,
    EntityType,
    EventType,
    ExecutionPhase,
    utcnow,
)


def run() -> dict:
    tenant = "demo-4"
    engine = KernelEngine(tenant)
    now = utcnow()
    prov = {"source_type": "system", "source_id": "bootstrap", "source_system": "valo-kernel"}

    engine.append(
        CanonicalEvent(
            event_id="entity-invoice",
            event_type=EventType.ENTITY_REGISTERED,
            tenant_id=tenant,
            subject="invoice-1",
            source="kernel",
            effective_at=now,
            payload={"entity": {"entity_id": "invoice-1", "entity_type": EntityType.ACCOUNT, "tenant_id": tenant, "state": "OPEN", "provenance": prov}},
        )
    )

    # external execution lifecycle: INTENDED -> AUTHORIZED -> EXECUTION_REQUESTED
    for phase, ref in [
        (ExecutionPhase.INTENDED, "intended"),
        (ExecutionPhase.AUTHORIZED, "authorized"),
        (ExecutionPhase.EXECUTION_REQUESTED, "requested"),
        (ExecutionPhase.EXECUTION_OBSERVED, "observed"),
    ]:
        engine.append(
            CanonicalEvent(
                event_id=f"phase-{ref}",
                event_type=EventType.EXECUTION_PHASE_UPDATED,
                tenant_id=tenant,
                subject="invoice-1",
                source="veritas",
                effective_at=now,
                payload={"process_ref": "pay-p1", "phase": phase.value},
            )
        )

    # external API answered success, payment transferred, but the invoice is
    # still OPEN in the world model. The observed reality is the state itself.

    # BARO checks the expected postcondition against observed reality.
    try:
        check_postconditions(engine.state(), expected={"invoice-1": "PAID"}, process_ref="pay-p1")
        raise AssertionError("BARO must detect the divergence")
    except DivergenceError as exc:
        divergence = str(exc)

    # the kernel never records EFFECT_VERIFIED for this process
    assert engine.state().clocks.get("pay-p1:phase") == ExecutionPhase.EXECUTION_OBSERVED.value

    return {"divergence": divergence, "phase": engine.state().clocks["pay-p1:phase"]}


def test_demonstrator_4_external_mismatch() -> None:
    result = run()
    assert "divergence" in result["divergence"]
    assert result["phase"] == ExecutionPhase.EXECUTION_OBSERVED.value


if __name__ == "__main__":
    print(run())
