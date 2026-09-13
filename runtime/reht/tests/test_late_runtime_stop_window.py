from __future__ import annotations

import hashlib
import json
from typing import Any

import pytest

from valo_reht import (
    BoundaryEffect,
    EffectBoundary,
    EffectDenied,
    InMemoryPermitStore,
    ResourceBudget,
    ResourceBudgetLedger,
    ResourceReservation,
    RuntimeControlPlane,
)
from valo_reht.contracts import DecisionResult
from valo_reht.runtime_interlocks import canonical_digest


def _digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _action(**extra: Any) -> dict[str, Any]:
    action = {
        "action_id": "action:late-stop",
        "action_type": "WRITE",
        "capability": "WRITE",
        "target": "target:1",
        "actor_id": "actor:1",
    }
    action.update(extra)
    return action


def _context(_: dict[str, Any]) -> dict[str, Any]:
    return {"state": "READY", "actor_id": "actor:1"}


class _Allow:
    def authorize(self, execution_context, action_contract) -> DecisionResult:
        return DecisionResult(
            decision="ALLOW",
            clearance_ref="clearance:late-stop",
            permit_ref="permit:late-stop",
            execution_context_hash=_digest(execution_context),
        )


def test_halt_injected_after_permit_consume_is_terminal_before_effect() -> None:
    control = RuntimeControlPlane()

    class HaltingPermitStore(InMemoryPermitStore):
        def consume_once(self, permit_ref: str) -> bool:
            consumed = super().consume_once(permit_ref)
            if consumed:
                control.halt_global()
            return consumed

    store = HaltingPermitStore()
    calls: list[str] = []
    boundary = EffectBoundary.for_development(store, runtime_control=control)

    with pytest.raises(EffectDenied, match="HALT_GLOBAL") as excinfo:
        boundary.commit(
            reht=_Allow(),
            context_factory=_context,
            action_contract=_action(),
            effect=BoundaryEffect.seal(
                "late-stop-effect",
                lambda _: calls.append("EFFECT"),
            ),
        )

    assert calls == []
    assert store.is_consumed("permit:late-stop") is True
    assert excinfo.value.receipt is not None
    assert excinfo.value.receipt.status == "BLOCKED"
    assert excinfo.value.receipt.reason == "HALT_GLOBAL"


def test_halt_injected_during_resource_consume_is_terminal_before_effect() -> None:
    control = RuntimeControlPlane()
    action = _action(
        resource_bounds_required=True,
        resource_reservation_id="reservation:late-stop",
    )

    class HaltingResourceLedger(ResourceBudgetLedger):
        def consume_once(
            self,
            reservation_id: str,
            *,
            action_digest: str,
            permit_ref: str,
        ) -> bool:
            consumed = super().consume_once(
                reservation_id,
                action_digest=action_digest,
                permit_ref=permit_ref,
            )
            if consumed:
                control.halt_global()
            return consumed

    ledger = HaltingResourceLedger()
    ledger.register_budget(ResourceBudget("budget:late-stop", {"units": 1.0}))
    ledger.reserve(
        ResourceReservation(
            reservation_id="reservation:late-stop",
            budget_id="budget:late-stop",
            action_digest=canonical_digest(action),
            amounts={"units": 1.0},
        )
    )
    store = InMemoryPermitStore()
    calls: list[str] = []
    boundary = EffectBoundary.for_development(
        store,
        runtime_control=control,
        resource_ledger=ledger,
    )

    with pytest.raises(EffectDenied, match="HALT_GLOBAL"):
        boundary.commit(
            reht=_Allow(),
            context_factory=_context,
            action_contract=action,
            effect=BoundaryEffect.seal(
                "late-stop-effect",
                lambda _: calls.append("EFFECT"),
            ),
        )

    assert calls == []
    assert store.is_consumed("permit:late-stop") is True
    assert ledger.is_consumed("reservation:late-stop") is True
