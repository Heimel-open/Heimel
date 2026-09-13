"""Deterministic CPU-only falsification of late HALT windows.

Inject HALT from inside permit/resource consumption, after the normal post-REHT
runtime check has already passed. No external effect may run afterward.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any

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


def _action(index: int, *, resource: bool = False) -> dict[str, Any]:
    action: dict[str, Any] = {
        "action_id": f"action:late-stop:{index}",
        "action_type": "WRITE",
        "capability": "WRITE",
        "target": "target:1",
        "actor_id": "actor:1",
    }
    if resource:
        action.update(
            resource_bounds_required=True,
            resource_reservation_id=f"reservation:late-stop:{index}",
        )
    return action


def _context(_: dict[str, Any]) -> dict[str, Any]:
    return {"state": "READY", "actor_id": "actor:1"}


class _Allow:
    def __init__(self, permit_ref: str) -> None:
        self.permit_ref = permit_ref

    def authorize(self, execution_context, action_contract) -> DecisionResult:
        return DecisionResult(
            decision="ALLOW",
            clearance_ref=f"clearance:{self.permit_ref}",
            permit_ref=self.permit_ref,
            execution_context_hash=_digest(execution_context),
        )


def run(iterations: int) -> dict[str, object]:
    if iterations < 1:
        raise ValueError("iterations must be positive")
    started = time.perf_counter()
    failures: list[dict[str, object]] = []
    permit_blocks = 0
    resource_blocks = 0

    for index in range(iterations):
        control = RuntimeControlPlane()
        permit_ref = f"permit:late-stop:permit:{index}"

        class HaltingPermitStore(InMemoryPermitStore):
            def consume_once(self, ref: str) -> bool:
                consumed = super().consume_once(ref)
                if consumed:
                    control.halt_global()
                return consumed

        store = HaltingPermitStore()
        calls: list[str] = []
        boundary = EffectBoundary.for_development(store, runtime_control=control)
        try:
            boundary.commit(
                reht=_Allow(permit_ref),
                context_factory=_context,
                action_contract=_action(index),
                effect=BoundaryEffect.seal(
                    "late-stop-effect",
                    lambda _: calls.append("EFFECT"),
                ),
            )
        except EffectDenied as exc:
            if "HALT_GLOBAL" in str(exc) and not calls and store.is_consumed(permit_ref):
                permit_blocks += 1
            else:
                failures.append({"family": "permit", "index": index, "error": str(exc)})
        else:
            failures.append({"family": "permit", "index": index, "error": "effect crossed HALT"})

    for index in range(iterations):
        control = RuntimeControlPlane()
        permit_ref = f"permit:late-stop:resource:{index}"
        action = _action(index, resource=True)

        class HaltingLedger(ResourceBudgetLedger):
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

        ledger = HaltingLedger()
        ledger.register_budget(ResourceBudget(f"budget:{index}", {"units": 1.0}))
        ledger.reserve(
            ResourceReservation(
                reservation_id=f"reservation:late-stop:{index}",
                budget_id=f"budget:{index}",
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
        try:
            boundary.commit(
                reht=_Allow(permit_ref),
                context_factory=_context,
                action_contract=action,
                effect=BoundaryEffect.seal(
                    "late-stop-effect",
                    lambda _: calls.append("EFFECT"),
                ),
            )
        except EffectDenied as exc:
            if (
                "HALT_GLOBAL" in str(exc)
                and not calls
                and store.is_consumed(permit_ref)
                and ledger.is_consumed(f"reservation:late-stop:{index}")
            ):
                resource_blocks += 1
            else:
                failures.append({"family": "resource", "index": index, "error": str(exc)})
        else:
            failures.append({"family": "resource", "index": index, "error": "effect crossed HALT"})

    return {
        "schema": "valo.reht.late-runtime-stop-falsification.v1",
        "iterations_per_family": iterations,
        "permit_consumption_late_halt_blocks": permit_blocks,
        "resource_consumption_late_halt_blocks": resource_blocks,
        "unsafe_effects": 0 if not failures else None,
        "cpu_only": True,
        "external_api_cost": 0,
        "failures": failures,
        "classification": "PASS" if not failures else "FAIL",
        "provider_side_fencing_verified": False,
        "elapsed_seconds": round(time.perf_counter() - started, 6),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=10000)
    parser.add_argument(
        "--output",
        default="validation/results/late_runtime_stop_falsification.json",
    )
    args = parser.parse_args()
    payload = run(args.iterations)
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    print(rendered)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered + "\n", encoding="utf-8")
    if payload["classification"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
