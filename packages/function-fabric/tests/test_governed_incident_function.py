from valo_workflow_isa.contracts import NodeClass

from valo_function_fabric.contracts.common import AutonomyLevel, IdempotencyRequirement
from valo_function_fabric.incident import build_governed_incident_program


def test_shadow_incident_program_has_no_write_path() -> None:
    program = build_governed_incident_program(shadow=True)
    graph = program.workflow_graph

    assert program.definition.function_id == "valo.incident.respond.shadow"
    assert all(node.node_class is not NodeClass.WRITE for node in graph.nodes)
    assert graph.terminal_states == ["prepare_remediation"]
    assert graph.output_schema == {"action": "Candidate<Action>"}
    assert program.definition.authority_requirements == []
    assert program.definition.effects == []


def test_live_incident_program_enforces_authorize_execute_verify_boundary() -> None:
    program = build_governed_incident_program(shadow=False)
    graph = program.workflow_graph
    node_map = graph.node_map()

    assert [
        node_map[name].opcode
        for name in (
            "prepare_remediation",
            "authorize_remediation",
            "execute_remediation",
            "verify_poststate",
        )
    ] == [
        "PREPARE_ACTION",
        "AUTHORIZE_ACTION",
        "EXECUTE_ACTION",
        "VERIFY_EXECUTION",
    ]
    assert node_map["authorize_remediation"].policies.authority is not None
    assert node_map["execute_remediation"].policies.authority is not None
    assert node_map["execute_remediation"].policies.idempotency.verify_before_replay is True
    assert graph.terminal_states == ["verify_poststate"]
    assert program.definition.idempotency_requirement is IdempotencyRequirement.VERIFY_BEFORE_REPLAY
    assert AutonomyLevel.AUTO_EXECUTE not in program.definition.autonomy_profile.allowed_autonomy_levels


def test_probabilistic_classification_is_reconciled_before_any_write() -> None:
    graph = build_governed_incident_program(shadow=False).workflow_graph
    node_map = graph.node_map()

    assert node_map["classify"].determinism.value == "PROBABILISTIC"
    assert node_map["diagnose"].opcode == "RECONCILE"
    direct_write_edges = [
        edge
        for edge in graph.edges
        if edge.source == "classify" and node_map[edge.target].node_class is NodeClass.WRITE
    ]
    assert direct_write_edges == []


def test_program_is_substrate_neutral() -> None:
    for shadow in (True, False):
        program = build_governed_incident_program(shadow=shadow)
        serialized = program.workflow_graph.model_dump_json().lower()
        assert "kubernetes" not in serialized
        assert "kubectl" not in serialized

