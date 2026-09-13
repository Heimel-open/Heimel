from __future__ import annotations

from examples.demonstrator_1_electrician import build_graph as electrician_graph
from examples.demonstrator_2_public import build_graph as public_graph
from examples.demonstrator_3_onboarding import build_person_graph as onboarding_graph
from valo_function_fabric import build_stdlib
from valo_function_fabric.compiler import compile_function_graph
from valo_function_fabric.contracts import FunctionGraph


def _function_ids(fgraph: FunctionGraph) -> set[str]:
    return {call.function_ref.function_id for call in fgraph.nodes}


def test_cross_domain_primitives_reused_without_fork() -> None:
    """The SAME registered VERIFY_IDENTITY, APPROVE and NOTIFY are used across
    the electrician, public application and employee onboarding graphs — no
    domain copies the core implementation."""
    registry = build_stdlib()
    snapshot = registry.snapshot()

    graphs = {
        "electrician": electrician_graph(),
        "public": public_graph(),
        "onboarding": onboarding_graph(),
    }

    # compile all three
    for fgraph in graphs.values():
        compile_function_graph(fgraph, snapshot)

    used_verify = {name for name, g in graphs.items() if "valo.identity.verify_identity" in _function_ids(g)}
    used_approve = {name for name, g in graphs.items() if "valo.decision.approve" in _function_ids(g)}
    used_notify = {name for name, g in graphs.items() if "valo.communication.notify" in _function_ids(g)}

    assert used_verify == {"electrician", "public", "onboarding"}
    assert used_approve == {"electrician", "public", "onboarding"}
    assert used_notify == {"electrician", "public", "onboarding"}

    # the shared implementation is a single registered workflow — not forked
    verify_workflow = registry.graph_for(registry.resolve("valo.identity.verify_identity"))
    for fgraph in graphs.values():
        for call in fgraph.nodes:
            if call.function_ref.function_id == "valo.identity.verify_identity":
                resolved = registry.get(call.function_ref.identity)
                assert registry.graph_for(resolved).id == verify_workflow.id


def test_cross_domain_compile_is_deterministic() -> None:
    registry = build_stdlib()
    snapshot = registry.snapshot()
    g = electrician_graph()
    h1 = compile_function_graph(g, snapshot).compiled_graph_hash
    h2 = compile_function_graph(g, snapshot).compiled_graph_hash
    assert h1 == h2

