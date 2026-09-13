"""Demonstrator 1: Electrician — BOOK_SERVICE_JOB.

Proves the same core Functions compose into a real booking program:
VERIFY_IDENTITY -> REGISTER -> CLASSIFY -> MATCH_RESOURCE -> SCHEDULE
-> PRICE -> APPROVE -> RESERVE_RESOURCE -> NOTIFY.

Not a full electrician platform: the point is the Function Graph compiles to a
valid Workflow ISA graph with pinned versions and a deterministic hash.
"""

from __future__ import annotations

from valo_function_fabric import build_stdlib
from valo_function_fabric.compiler import compile_function_graph
from valo_function_fabric.contracts import (
    FunctionCall,
    FunctionEdge,
    FunctionGraph,
    FunctionRef,
)
from valo_function_fabric.simulation import simulate


def build_graph() -> FunctionGraph:
    return FunctionGraph(
        graph_id="graph.demo.book_service_job", version="1",
        inputs={
            "identity": "IdentityCandidate",
            "request": "Request",
            "registration": "Registration",
            "requirement": "ResourceRequirement",
            "schedule": "ScheduleRequirement",
            "scope": "PriceScope",
            "approval": "ApprovalRequest",
            "resource": "Candidate<Resource>",
            "notification": "Notification",
        },
        outputs={"done": "Acknowledged<Message>"},
        nodes=[
            FunctionCall(id="verify_identity", function_ref=FunctionRef(function_id="valo.identity.verify_identity", version="1.0.0"), input_bindings={"candidate": "identity"}, output_bindings={"identity": "verified"}),
            FunctionCall(id="register", function_ref=FunctionRef(function_id="valo.lifecycle.register", version="1.0.0"), input_bindings={"registration": "registration"}, output_bindings={"registered": "registered"}),
            FunctionCall(id="classify", function_ref=FunctionRef(function_id="valo.intake.classify", version="1.0.0"), input_bindings={"request": "request"}, output_bindings={"classification": "classified"}),
            FunctionCall(id="match", function_ref=FunctionRef(function_id="valo.resource.match", version="1.0.0"), input_bindings={"requirement": "requirement"}, output_bindings={"candidates": "matched"}),
            FunctionCall(id="schedule", function_ref=FunctionRef(function_id="valo.coordination.schedule", version="1.0.0"), input_bindings={"requirement": "schedule"}, output_bindings={"booking": "booked"}),
            FunctionCall(id="price", function_ref=FunctionRef(function_id="valo.finance.price", version="1.0.0"), input_bindings={"scope": "scope"}, output_bindings={"price": "priced"}),
            FunctionCall(id="approve", function_ref=FunctionRef(function_id="valo.decision.approve", version="1.0.0"), input_bindings={"approval": "approval"}, output_bindings={"attestation": "approved"}),
            FunctionCall(id="reserve", function_ref=FunctionRef(function_id="valo.resource.reserve", version="1.0.0"), input_bindings={"resource": "resource"}, output_bindings={"reservation": "reserved"}),
            FunctionCall(id="notify", function_ref=FunctionRef(function_id="valo.communication.notify", version="1.0.0"), input_bindings={"notification": "notification"}, output_bindings={"ack": "done"}),
        ],
        edges=[
            FunctionEdge(source="verify_identity", target="register"),
            FunctionEdge(source="register", target="classify"),
            FunctionEdge(source="classify", target="match"),
            FunctionEdge(source="match", target="schedule"),
            FunctionEdge(source="schedule", target="price"),
            FunctionEdge(source="price", target="approve"),
            FunctionEdge(source="approve", target="reserve"),
            FunctionEdge(source="reserve", target="notify"),
        ],
        entry_nodes=["verify_identity"],
        terminal_nodes=["notify"],
    )


def run() -> dict:
    registry = build_stdlib()
    snapshot = registry.snapshot()
    fgraph = build_graph()
    compiled = compile_function_graph(fgraph, snapshot)
    report = simulate(fgraph, snapshot, registry)
    assert compiled.workflow_graph is not None
    assert report.expected_writes, "BOOK_SERVICE_JOB must contain WRITE steps (RESERVE)"
    return {
        "graph_id": fgraph.graph_id,
        "compiled_graph_hash": compiled.compiled_graph_hash,
        "registry_snapshot_hash": compiled.registry_snapshot_hash,
        "nodes": len(compiled.workflow_graph.nodes),
        "risk": report.risk,
        "writes": [w["effect"] for w in report.expected_writes],
    }


def test_demonstrator_1_electrician() -> None:
    result = run()
    assert result["graph_id"] == "graph.demo.book_service_job"
    assert "ALLOCATE_RESOURCE" in result["writes"]


if __name__ == "__main__":
    print(run())
