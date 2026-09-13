"""CPU-only falsification of multi-host runtime-control/resource assumptions."""

from __future__ import annotations

import argparse
import json
import time

from valo_reht.consistency import ConsistencyScope, DeploymentTopology
from valo_reht.effect_boundary import EffectBoundary
from valo_reht.runtime_interlocks import (
    ResourceBudget,
    ResourceBudgetLedger,
    ResourceReservation,
    RuntimeControlPlane,
    canonical_digest,
)


class _UnusedEvidenceSink:
    def close(self, receipt):
        raise AssertionError("construction-only probe")


class _DistributedPermitStore:
    production_safe = True
    consistency_scope = ConsistencyScope.DISTRIBUTED_CONSENSUS

    def consume_once(self, permit_ref: str) -> bool:
        raise AssertionError("construction-only probe")

    def is_consumed(self, permit_ref: str) -> bool:
        raise AssertionError("construction-only probe")


class _DistributedJournal:
    production_safe = True
    consistency_scope = ConsistencyScope.DISTRIBUTED_CONSENSUS

    def open_intent(self, **kwargs) -> bool:
        raise AssertionError("construction-only probe")

    def mark_effect_invoking(self, permit_ref: str) -> None:
        raise AssertionError("construction-only probe")

    def mark_receipt_ready(self, permit_ref: str, receipt) -> None:
        raise AssertionError("construction-only probe")

    def mark_evidence_closing(self, permit_ref: str) -> None:
        raise AssertionError("construction-only probe")

    def mark_closed(self, permit_ref: str, closure) -> None:
        raise AssertionError("construction-only probe")

    def get(self, permit_ref: str):
        raise AssertionError("construction-only probe")


class _DistributedRuntimeControl:
    consistency_scope = ConsistencyScope.DISTRIBUTED_CONSENSUS

    def check(self, action, execution_context):
        return None


class _DistributedResourceLedger:
    consistency_scope = ConsistencyScope.DISTRIBUTED_CONSENSUS

    def consume_once(self, reservation_id: str, *, action_digest: str, permit_ref: str) -> bool:
        raise AssertionError("construction-only probe")


def run() -> dict[str, object]:
    started = time.perf_counter()

    host_a_control = RuntimeControlPlane()
    host_b_control = RuntimeControlPlane()
    host_a_control.halt_global()
    halt_a = host_a_control.check({}, {})
    halt_b = host_b_control.check({}, {})
    lost_halt_confirmed = halt_a == "HALT_GLOBAL" and halt_b is None

    digest = canonical_digest({"action": "same-global-budget"})
    host_a_ledger = ResourceBudgetLedger()
    host_b_ledger = ResourceBudgetLedger()
    budget_accepts = 0
    for ledger in (host_a_ledger, host_b_ledger):
        ledger.register_budget(ResourceBudget("global", {"units": 100.0}))
        ledger.reserve(
            ResourceReservation(
                reservation_id="reservation:full",
                budget_id="global",
                action_digest=digest,
                amounts={"units": 100.0},
            )
        )
        if ledger.consume_once(
            "reservation:full",
            action_digest=digest,
            permit_ref="permit:global",
        ):
            budget_accepts += 1
    oversubscription_confirmed = budget_accepts == 2

    runtime_gate_error = None
    try:
        EffectBoundary(
            _DistributedPermitStore(),
            evidence_sink=_UnusedEvidenceSink(),
            execution_journal=_DistributedJournal(),
            deployment_topology=DeploymentTopology.MULTI_HOST,
        )
    except ValueError as exc:
        runtime_gate_error = str(exc)

    resource_gate_error = None
    try:
        EffectBoundary(
            _DistributedPermitStore(),
            evidence_sink=_UnusedEvidenceSink(),
            execution_journal=_DistributedJournal(),
            runtime_control=_DistributedRuntimeControl(),  # type: ignore[arg-type]
            deployment_topology=DeploymentTopology.MULTI_HOST,
        )
    except ValueError as exc:
        resource_gate_error = str(exc)

    complete_contract = EffectBoundary(
        _DistributedPermitStore(),
        evidence_sink=_UnusedEvidenceSink(),
        execution_journal=_DistributedJournal(),
        runtime_control=_DistributedRuntimeControl(),  # type: ignore[arg-type]
        resource_ledger=_DistributedResourceLedger(),  # type: ignore[arg-type]
        deployment_topology=DeploymentTopology.MULTI_HOST,
    )

    guard_present = bool(
        runtime_gate_error
        and "distributed-consensus runtime control" in runtime_gate_error
        and resource_gate_error
        and "distributed-consensus resource ledger" in resource_gate_error
        and complete_contract.deployment_topology is DeploymentTopology.MULTI_HOST
    )

    return {
        "schema": "valo.reht.multi-host-interlock-falsification.v1",
        "cpu_only": True,
        "external_api_cost": 0,
        "host_a_halt": halt_a,
        "host_b_halt": halt_b,
        "process_local_halt_loss_confirmed": lost_halt_confirmed,
        "independent_full_budget_consumptions": budget_accepts,
        "conceptual_global_limit": 100.0,
        "conceptual_combined_consumption": 200.0 if oversubscription_confirmed else None,
        "process_local_resource_oversubscription_confirmed": oversubscription_confirmed,
        "runtime_gate_error": runtime_gate_error,
        "resource_gate_error": resource_gate_error,
        "complete_distributed_contract_constructible": (
            complete_contract.deployment_topology is DeploymentTopology.MULTI_HOST
        ),
        "distributed_implementations_verified": False,
        "classification": (
            "LIMITATIONS_CONFIRMED_AND_GUARD_PRESENT"
            if lost_halt_confirmed and oversubscription_confirmed and guard_present
            else "FAIL"
        ),
        "elapsed_seconds": round(time.perf_counter() - started, 6),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="validation/results/multi_host_interlock_falsification.json",
    )
    args = parser.parse_args()
    payload = run()
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    print(rendered)
    with open(args.output, "w", encoding="utf-8") as handle:
        handle.write(rendered + "\n")
    if payload["classification"] == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
