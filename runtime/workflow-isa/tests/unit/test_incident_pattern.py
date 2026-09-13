from valo_workflow_isa.contracts import NodeClass
from valo_workflow_isa.patterns import (
    IncidentPatternMode,
    build_governed_incident_graph,
)


def test_shadow_pattern_compiles_without_write_nodes() -> None:
    graph = build_governed_incident_graph(IncidentPatternMode.SHADOW)
    assert graph.terminal_states == ["prepare_remediation", "evidence_halt"]
    assert all(node.node_class is not NodeClass.WRITE for node in graph.nodes)
    assert graph.output_schema == {"action": "Candidate<Action>"}


def test_live_pattern_has_single_governed_remediation_and_poststate_verification() -> None:
    graph = build_governed_incident_graph(IncidentPatternMode.LIVE)
    node_map = graph.node_map()
    writes = [node for node in graph.nodes if node.node_class is NodeClass.WRITE]

    assert [node.id for node in writes] == [
        "authorize_remediation",
        "execute_remediation",
    ]
    assert node_map["authorize_remediation"].policies.authority.require_fresh_context is True
    assert node_map["execute_remediation"].policies.idempotency.verify_before_replay is True
    assert node_map["verify_poststate"].opcode == "VERIFY_EXECUTION"
    assert "verify_poststate" in graph.terminal_states


def test_unhealthy_evidence_has_explicit_halt_path() -> None:
    graph = build_governed_incident_graph(IncidentPatternMode.LIVE)
    halt_edges = [edge for edge in graph.edges if edge.target == "evidence_halt"]
    assert len(halt_edges) == 1
    assert halt_edges[0].condition == "evidence_gate.approved == false"
    assert graph.node_map()["evidence_halt"].opcode == "HALT"


def test_severity_is_classified_before_diagnosis_and_never_writes_directly() -> None:
    graph = build_governed_incident_graph(IncidentPatternMode.LIVE)
    node_map = graph.node_map()
    assert node_map["classify_severity"].determinism.value == "PROBABILISTIC"
    assert node_map["diagnose"].opcode == "RECONCILE"
    assert any(
        edge.source == "classify_severity" and edge.target == "diagnose"
        for edge in graph.edges
    )
    assert not any(
        edge.source == "classify_severity"
        and node_map[edge.target].node_class is NodeClass.WRITE
        for edge in graph.edges
    )


def test_pattern_is_substrate_neutral() -> None:
    for mode in IncidentPatternMode:
        serialized = build_governed_incident_graph(mode).model_dump_json().lower()
        assert "kubernetes" not in serialized
        assert "kubectl" not in serialized
