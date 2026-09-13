"""Demonstrator: Public Application Golden Path — the COMPILED
PROCESS_PUBLIC_APPLICATION graph runs through the Workflow ISA Runtime against
Kernel-owned state and the REHT/RACS/Gateway/Veritas/BARO ports. No local REHT,
no parallel state machine, no separate shadow path."""

from __future__ import annotations

from valo_reht import RealReht
from valo_workflow_isa import compile_graph as isa_compile

from valo_public_pack import (
    build_public_registry,
    compile_golden,
    explain,
    provenance,
    replay,
    run_golden,
    seed_world,
)


def run() -> dict:
    registry = build_public_registry()
    compiled = compile_golden(registry)
    isa_compile(compiled.workflow_graph)  # valid Workflow ISA

    kernel = seed_world()
    result = run_golden(reht=RealReht(), kernel=kernel)

    assert result.case_state == "CLOSED", f"golden path must close, got {result.case_state}"
    assert result.instance_status == "COMPLETED"
    assert result.gateway_executions >= 6, "world-changing actions must flow through the Gateway"

    shadow_kernel = seed_world()
    shadow = run_golden(reht=RealReht(), kernel=shadow_kernel, shadow=True)
    assert shadow.instance_status == "COMPLETED", "shadow must run the full path"
    assert shadow.case_state == "RECEIVED", "shadow must not write kernel state"
    assert shadow.economics["gateway_executions"] == 0
    assert shadow.economics["proposed_kernel_events"] > 0

    exp = explain(kernel, result.case_state)
    rep = replay(kernel, result.case_state)
    prov = provenance(kernel)

    return {
        "compiled_graph_hash": compiled.compiled_graph_hash,
        "final_state": result.case_state,
        "instance_status": result.instance_status,
        "gateway_executions": result.gateway_executions,
        "explain_decision_ready": exp["decision_ready"],
        "replay_matches": rep["matches_original"],
        "event_chain_integrity": prov["event_chain_integrity"],
        "shadow_no_writes": shadow.economics["gateway_executions"] == 0,
    }


def test_demonstrator_golden_path() -> None:
    result = run()
    assert result["final_state"] == "CLOSED"
    assert result["instance_status"] == "COMPLETED"
    assert result["replay_matches"] is True
    assert result["event_chain_integrity"] is True
    assert result["shadow_no_writes"] is True


if __name__ == "__main__":
    print(run())
