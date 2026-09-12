"""Demonstrator 3: Employee Onboarding — ONBOARD_PERSON.

Uses the REGISTERED valo.lifecycle.onboard composite (same VERIFY_IDENTITY /
CHECK_ELIGIBILITY / VERIFY_EVIDENCE / REGISTER / ALLOCATE / NOTIFY primitives)
and additionally runs the ONBOARD_PERSON FunctionGraph built from the same
core Functions, proving cross-domain reuse without a fork.
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


def build_person_graph() -> FunctionGraph:
    return FunctionGraph(
        graph_id="graph.demo.onboard_person", version="1",
        inputs={
            "identity": "IdentityCandidate",
            "evidence": "Evidence",
            "criteria": "EligibilityCriteria",
            "approval": "ApprovalRequest",
            "registration": "Registration",
            "demand": "AllocationDemand",
            "notification": "Notification",
        },
        outputs={"done": "Acknowledged<Message>"},
        nodes=[
            FunctionCall(id="verify_identity", function_ref=FunctionRef(function_id="valo.identity.verify_identity", version="1.0.0"), input_bindings={"candidate": "identity"}, output_bindings={"identity": "verified"}),
            FunctionCall(id="verify_evidence", function_ref=FunctionRef(function_id="valo.evidence.verify", version="1.0.0"), input_bindings={"evidence_in": "evidence"}, output_bindings={"evidence": "admitted"}),
            FunctionCall(id="check_eligibility", function_ref=FunctionRef(function_id="valo.qualification.check_eligibility", version="1.0.0"), input_bindings={"criteria": "criteria"}, output_bindings={"result": "eligible"}),
            FunctionCall(id="approve", function_ref=FunctionRef(function_id="valo.decision.approve", version="1.0.0"), input_bindings={"approval": "approval"}, output_bindings={"attestation": "approved"}),
            FunctionCall(id="register", function_ref=FunctionRef(function_id="valo.lifecycle.register", version="1.0.0"), input_bindings={"registration": "registration"}, output_bindings={"registered": "registered"}),
            FunctionCall(id="allocate", function_ref=FunctionRef(function_id="valo.resource.allocate", version="1.0.0"), input_bindings={"demand": "demand"}, output_bindings={"allocation": "allocated"}),
            FunctionCall(id="notify", function_ref=FunctionRef(function_id="valo.communication.notify", version="1.0.0"), input_bindings={"notification": "notification"}, output_bindings={"ack": "done"}),
        ],
        edges=[
            FunctionEdge(source="verify_identity", target="verify_evidence"),
            FunctionEdge(source="verify_evidence", target="check_eligibility"),
            FunctionEdge(source="check_eligibility", target="approve"),
            FunctionEdge(source="approve", target="register"),
            FunctionEdge(source="approve", target="allocate"),
            FunctionEdge(source="register", target="notify"),
            FunctionEdge(source="allocate", target="notify"),
        ],
        entry_nodes=["verify_identity"],
        terminal_nodes=["notify"],
    )


def run() -> dict:
    registry = build_stdlib()
    snapshot = registry.snapshot()

    # 1. the registered composite
    onboard_def = registry.get("valo.lifecycle.onboard@1.0.0")
    onboard_graph = registry.graph_for(onboard_def)
    onboard_node_count = len(onboard_graph.nodes)

    # 2. the ONBOARD_PERSON FunctionGraph built from the same core Functions
    fgraph = build_person_graph()
    compiled = compile_function_graph(fgraph, snapshot)
    used = {call.function_ref.function_id for call in fgraph.nodes}
    return {
        "onboard_composite_nodes": onboard_node_count,
        "person_graph_nodes": len(compiled.workflow_graph.nodes),
        "reuses_verify_identity": "valo.identity.verify_identity" in used,
        "reuses_approve": "valo.decision.approve" in used,
        "reuses_notify": "valo.communication.notify" in used,
    }


def test_demonstrator_3_onboarding() -> None:
    result = run()
    assert result["reuses_verify_identity"] is True
    assert result["reuses_approve"] is True
    assert result["reuses_notify"] is True


if __name__ == "__main__":
    print(run())

