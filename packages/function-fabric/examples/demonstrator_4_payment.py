"""Demonstrator 4: Payment — PAY_OBLIGATION.

Proves the Function Graph compiles to a Workflow ISA graph AND that external
execution success is NOT a verified payment outcome. The compiled graph is run
through the Workflow ISA runtime: the Gateway reports success, but BARO finds
the expected postcondition (payment VERIFIED) did not arise — the workflow
does NOT complete.

FF contract: PAY outputs VerifiedEffect<Payment>; GatewaySuccess<Payment> is
insufficient.
"""

from __future__ import annotations

from valo_workflow_isa import RuntimeEngine, WorkflowStatus
from valo_workflow_isa.testing import (
    DictKernel,
    FakeBaro,
    FakeGateway,
    FakeReht,
    FakeVeritas,
)

from valo_function_fabric import build_stdlib
from valo_function_fabric.compiler import compile_function_graph
from valo_function_fabric.contracts import FunctionCall, FunctionGraph, FunctionRef


def build_graph() -> FunctionGraph:
    return FunctionGraph(
        graph_id="graph.demo.pay_obligation", version="1",
        inputs={"payment": "PaymentRequest"},
        outputs={"payment_result": "VerifiedEffect<Payment>"},
        nodes=[
            FunctionCall(id="pay", function_ref=FunctionRef(function_id="valo.finance.pay", version="1.0.0"), input_bindings={"payment": "payment"}, output_bindings={"payment_result": "payment_result"}),
        ],
        edges=[], entry_nodes=["pay"], terminal_nodes=["pay"],
    )


def run() -> dict:
    registry = build_stdlib()
    snapshot = registry.snapshot()
    fgraph = build_graph()
    compiled = compile_function_graph(fgraph, snapshot)

    kernel = DictKernel()
    kernel.register_entity("payment")
    kernel.register_identity("id-agent", "agent-a", verified=True)
    kernel.grant_authority("agent-a", "PAY", ["payment"])

    # external API answers success; observed reality still shows payment OPEN
    gateway = FakeGateway(success=True)
    veritas = FakeVeritas(observed={"payment": "OPEN"})
    baro = FakeBaro()

    engine = RuntimeEngine(kernel, FakeReht(), gateway, veritas, baro, tenant_id="tenant-a")
    instance = engine.start(compiled.workflow_graph, {"payment": {"id": "p-1"}})

    assert instance.status != WorkflowStatus.COMPLETED, "external success alone must not complete a payment"
    assert instance.status == WorkflowStatus.FAILED
    return {
        "compiled_graph_hash": compiled.compiled_graph_hash,
        "registry_snapshot_hash": compiled.registry_snapshot_hash,
        "status": instance.status.value,
        "postcondition": "postcondition" in str(instance.errors),
    }


def test_demonstrator_4_payment() -> None:
    result = run()
    assert result["status"] == "FAILED"
    assert result["postcondition"] is True


if __name__ == "__main__":
    print(run())

