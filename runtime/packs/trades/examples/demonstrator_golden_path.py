"""Demonstrator: EV Charger Golden Path — the COMPILED graph runs through the
Workflow ISA Runtime against Kernel-owned state and the real
REHT/RACS/Gateway/Veritas/BARO ports. No local REHT, no parallel state machine,
no separate shadow path."""

from __future__ import annotations

from valo_reht import RealReht

from valo_trades_pack import (
    build_trades_registry,
    compile_golden,
    run_golden,
    seed_world,
)


def run() -> dict:
    registry = build_trades_registry()
    compiled = compile_golden(registry)
    from valo_workflow_isa import compile_graph as isa_compile

    isa_compile(compiled.workflow_graph)  # valid Workflow ISA

    kernel = seed_world()
    result = run_golden(reht=RealReht(), kernel=kernel)

    assert result.workorder_state == "CLOSED", f"golden path must close, got {result.workorder_state}"
    assert result.instance_status == "COMPLETED", f"instance must complete, got {result.instance_status}"
    assert result.gateway_executions >= 8, "writes must flow through the Gateway"
    assert all(d["decision"] == "ALLOW" for d in result.reht_decisions), "happy path must be authorized"

    # shadow: the SAME compiled graph, writes disabled -> kernel unchanged
    shadow_kernel = seed_world()
    shadow = run_golden(reht=RealReht(), kernel=shadow_kernel, shadow=True)
    assert shadow.instance_status == "COMPLETED", "shadow must run the full path"
    assert shadow.workorder_state == "NEW", "shadow must not write kernel state"
    assert shadow.economics["gateway_executions"] == 0, "shadow must not execute externally"
    assert shadow.economics["proposed_kernel_events"] > 0, "shadow must propose the writes"

    return {
        "compiled_graph_hash": compiled.compiled_graph_hash,
        "final_state": result.workorder_state,
        "instance_status": result.instance_status,
        "kernel_events": result.kernel_events,
        "gateway_executions": result.gateway_executions,
        "reht_authorizations": len(result.reht_decisions),
        "shadow_no_writes": shadow.economics["gateway_executions"] == 0,
    }


def test_demonstrator_golden_path() -> None:
    result = run()
    assert result["final_state"] == "CLOSED"
    assert result["instance_status"] == "COMPLETED"
    assert result["shadow_no_writes"] is True


if __name__ == "__main__":
    print(run())
