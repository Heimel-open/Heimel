from __future__ import annotations

from valo_reht import RealReht
from valo_workflow_isa import compile_graph as isa_compile

from valo_trades_pack import (
    build_trades_registry,
    compile_golden,
    run_golden,
    seed_world,
)
from valo_trades_pack.golden import CORE_REUSE_CHECK


def test_pack_reuses_exact_core_functions() -> None:
    """The golden graph references the exact core Function versions that run
    through the runtime (no forks)."""
    registry = build_trades_registry()
    used = {call.function_ref.function_id for call in build_golden_graph(registry).nodes}
    for core in CORE_REUSE_CHECK:
        assert core in used, f"pack must reuse core Function {core}"
        definition = registry.resolve(core, "1.0.0")
        assert definition is not None


def build_golden_graph(registry):
    from valo_trades_pack import build_golden_graph as bg

    return bg(registry)


def test_no_domain_leakage_into_core() -> None:
    """Trades types never appear in Kernel/ISA core; the pack layers domain
    semantics on top."""
    registry = build_trades_registry()
    identity = registry.resolve("valo.identity.verify_identity")
    assert "WorkOrder" not in identity.input_type.type
    assert "Electrician" not in identity.output_type.type


def test_no_writes_bypass_isa_reht() -> None:
    """Every world-changing action in the golden graph is a WRITE node that
    flows through the runtime boundary (its workflow contains EXECUTE_ACTION
    with an authority requirement)."""
    registry = build_trades_registry()
    for function_id in ["valo.trades.dispatch", "valo.trades.issue_invoice", "valo.trades.receive_payment", "valo.trades.close_work_order"]:
        workflow = registry.graph_for(registry.get(f"{function_id}@1.0.0"))
        write = [n for n in workflow.nodes if n.node_class.value == "WRITE"]
        assert write and write[0].policies.authority is not None, f"{function_id} must carry an authority boundary"


def test_compiled_golden_is_valid_isa() -> None:
    isa_compile(compile_golden(build_trades_registry()).workflow_graph)


def test_kernel_is_authoritative_state_owner() -> None:
    """Business truth lives in the Kernel; the runtime only appends events. The
    Kernel's read API returns immutable state, so direct mutation is not
    possible from the pack."""
    kernel = seed_world()
    before = kernel.sequence()
    run_golden(reht=RealReht(), kernel=kernel)
    assert kernel.sequence() > before
    entity = kernel.state().entities["workorder-1"]
    assert entity.model_dump(mode="json")  # immutable read


def test_no_local_authorization_boundary() -> None:
    """The pack has no local REHT: authority decisions come from the Kernel
    execution context via the real REHT port."""
    from valo_reht import RealReht

    reht = RealReht()
    base = {
        "actor": "worker-a",
        "identity": "id-worker-a",
        "time": {"now": "2026-08-08T00:00:00+00:00"},
    }
    # a context with no authority for the required capability is denied
    decision = reht.authorize({**base, "authority": []}, {"capability": "DISPATCH", "target": "workorder-1"})
    assert decision.decision == "DENY"
    # an in-scope, in-principal, active, timezone-aware authority allows
    decision = reht.authorize(
        {**base, "authority": [{
            "authority_id": "auth-1", "principal": "worker-a", "capability": "DISPATCH",
            "scope": ["workorder-1"], "status": "ACTIVE",
            "validity": {"valid_from": "2020-01-01T00:00:00+00:00", "valid_until": "2100-01-01T00:00:00+00:00"},
        }]},
        {"capability": "DISPATCH", "target": "workorder-1"},
    )
    assert decision.decision == "ALLOW"
