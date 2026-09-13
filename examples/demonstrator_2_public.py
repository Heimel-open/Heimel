"""Demonstrator 2: Public Application — PROCESS_APPLICATION.

The same VERIFY/REGISTER/EVIDENCE/APPROVE/NOTIFY primitives are reused from
the electrician domain: VERIFY_IDENTITY -> REGISTER -> REQUEST_EVIDENCE ->
VERIFY_EVIDENCE -> CHECK_ELIGIBILITY -> PREPARE_DECISION -> APPROVE ->
ISSUE_DECISION -> NOTIFY.

ISSUE_DECISION is a stub Function over the workflow contract (Public pack adds
the specific decision contract later).
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


def build_graph() -> FunctionGraph:
    return FunctionGraph(
        graph_id="graph.demo.process_application", version="1",
        inputs={
            "identity": "IdentityCandidate",
            "request": "Request",
            "registration": "Registration",
            "request_evidence": "EvidenceRequest",
            "evidence": "Evidence",
            "criteria": "EligibilityCriteria",
            "approval": "ApprovalRequest",
            "decision": "Registration",
            "notification": "Notification",
        },
        outputs={"done": "Acknowledged<Message>"},
        nodes=[
            FunctionCall(id="verify_identity", function_ref=FunctionRef(function_id="valo.identity.verify_identity", version="1.0.0"), input_bindings={"candidate": "identity"}, output_bindings={"identity": "verified"}),
            FunctionCall(id="register", function_ref=FunctionRef(function_id="valo.lifecycle.register", version="1.0.0"), input_bindings={"registration": "registration"}, output_bindings={"registered": "registered"}),
            FunctionCall(id="request_evidence", function_ref=FunctionRef(function_id="valo.evidence.request", version="1.0.0"), input_bindings={"request": "request_evidence"}, output_bindings={"evidence": "requested"}),
            FunctionCall(id="verify_evidence", function_ref=FunctionRef(function_id="valo.evidence.verify", version="1.0.0"), input_bindings={"evidence_in": "evidence"}, output_bindings={"evidence": "admitted"}),
            FunctionCall(id="check_eligibility", function_ref=FunctionRef(function_id="valo.qualification.check_eligibility", version="1.0.0"), input_bindings={"criteria": "criteria"}, output_bindings={"result": "eligible"}),
            FunctionCall(id="approve", function_ref=FunctionRef(function_id="valo.decision.approve", version="1.0.0"), input_bindings={"approval": "approval"}, output_bindings={"attestation": "approved"}),
            FunctionCall(id="issue_decision", function_ref=FunctionRef(function_id="valo.lifecycle.register", version="1.0.0"), input_bindings={"registration": "decision"}, output_bindings={"registered": "issued"}),
            FunctionCall(id="notify", function_ref=FunctionRef(function_id="valo.communication.notify", version="1.0.0"), input_bindings={"notification": "notification"}, output_bindings={"ack": "done"}),
        ],
        edges=[
            FunctionEdge(source="verify_identity", target="register"),
            FunctionEdge(source="register", target="request_evidence"),
            FunctionEdge(source="request_evidence", target="verify_evidence"),
            FunctionEdge(source="verify_evidence", target="check_eligibility"),
            FunctionEdge(source="check_eligibility", target="approve"),
            FunctionEdge(source="approve", target="issue_decision"),
            FunctionEdge(source="issue_decision", target="notify"),
        ],
        entry_nodes=["verify_identity"],
        terminal_nodes=["notify"],
    )


def run() -> dict:
    registry = build_stdlib()
    snapshot = registry.snapshot()
    fgraph = build_graph()
    compiled = compile_function_graph(fgraph, snapshot)
    used = {call.function_ref.function_id for call in fgraph.nodes}
    return {
        "graph_id": fgraph.graph_id,
        "compiled_graph_hash": compiled.compiled_graph_hash,
        "reuses_verify_identity": "valo.identity.verify_identity" in used,
        "reuses_notify": "valo.communication.notify" in used,
        "nodes": len(compiled.workflow_graph.nodes),
    }


def test_demonstrator_2_public_application() -> None:
    result = run()
    assert result["reuses_verify_identity"] is True
    assert result["reuses_notify"] is True


if __name__ == "__main__":
    print(run())
