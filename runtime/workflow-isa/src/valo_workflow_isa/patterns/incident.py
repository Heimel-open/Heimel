"""Generic governed incident workflow pattern.

Domain adapters supply observations and evidence-source health. The pattern
preserves evidence, fails closed on unhealthy required observation sources,
keeps probabilistic classification away from WRITE, and in live mode requires
authorization, execution, and post-state verification.
"""

from __future__ import annotations

from enum import Enum

from ..compiler import compile_graph
from ..contracts.common import (
    ControlOpcode,
    Determinism,
    EdgeType,
    EffectType,
    NodeClass,
)
from ..contracts.graph import WorkflowEdge, WorkflowGraph
from ..contracts.node import TypedRef, WorkflowNode
from ..contracts.policy import AuthorityRequirements, IdempotencyPolicy, NodePolicies


class IncidentPatternMode(str, Enum):
    SHADOW = "SHADOW"
    LIVE = "LIVE"


def build_governed_incident_graph(
    mode: IncidentPatternMode = IncidentPatternMode.LIVE,
) -> WorkflowGraph:
    nodes = [
        WorkflowNode(
            id="preserve_evidence",
            opcode="VALIDATE_SCHEMA",
            node_class=NodeClass.COMPUTE,
            inputs=[TypedRef(name="observation", type="IncidentObservation")],
            outputs=[
                TypedRef(
                    name="observation_verified", type="Verified<IncidentObservation>"
                )
            ],
            config={"schema": {"required": ["observation_id", "subject_ref", "symptoms"]}},
        ),
        WorkflowNode(
            id="evidence_gate",
            opcode="EVALUATE_RULE",
            node_class=NodeClass.DECIDE,
            inputs=[
                TypedRef(
                    name="observation_verified", type="Verified<IncidentObservation>"
                ),
                TypedRef(name="evidence_sources_healthy", type="bool"),
            ],
            outputs=[TypedRef(name="evidence_gate", type="EvidenceGate")],
            config={"rule": "evidence_sources_healthy"},
        ),
        WorkflowNode(
            id="evidence_halt",
            opcode=ControlOpcode.HALT.value,
            node_class=NodeClass.COMPUTE,
            config={"reason": "required incident evidence source unavailable or unhealthy"},
        ),
        WorkflowNode(
            id="classify_severity",
            opcode="EVALUATE_RULE",
            node_class=NodeClass.DECIDE,
            inputs=[
                TypedRef(
                    name="observation_verified", type="Verified<IncidentObservation>"
                )
            ],
            outputs=[
                TypedRef(
                    name="severity", type="Candidate<IncidentSeverityAssessment>"
                )
            ],
            determinism=Determinism.PROBABILISTIC,
            config={
                "rule": "true",
                "model": "incident-severity-classifier",
                "model_version": "1",
                "source_context": "preserved-incident-evidence",
            },
        ),
        WorkflowNode(
            id="diagnose",
            opcode="RECONCILE",
            node_class=NodeClass.COMPUTE,
            inputs=[
                TypedRef(
                    name="severity", type="Candidate<IncidentSeverityAssessment>"
                )
            ],
            outputs=[TypedRef(name="diagnosis", type="Verified<IncidentDiagnosis>")],
        ),
        WorkflowNode(
            id="prepare_remediation",
            opcode="PREPARE_ACTION",
            node_class=NodeClass.COMPUTE,
            inputs=[TypedRef(name="diagnosis", type="Verified<IncidentDiagnosis>")],
            outputs=[TypedRef(name="action", type="Candidate<Action>")],
            config={
                "action_type": "INCIDENT_REMEDIATION",
                "capability": "REMEDIATE",
                "kernel_event_type": "INCIDENT_REMEDIATION_OBSERVED",
            },
        ),
    ]
    edges = [
        WorkflowEdge(source="preserve_evidence", target="evidence_gate"),
        WorkflowEdge(
            source="evidence_gate",
            target="classify_severity",
            edge_type=EdgeType.TRUE,
            condition="evidence_gate.approved == true",
        ),
        WorkflowEdge(
            source="evidence_gate",
            target="evidence_halt",
            edge_type=EdgeType.FALSE,
            condition="evidence_gate.approved == false",
        ),
        WorkflowEdge(source="classify_severity", target="diagnose"),
        WorkflowEdge(source="diagnose", target="prepare_remediation"),
    ]

    if mode is IncidentPatternMode.SHADOW:
        graph = WorkflowGraph(
            id="valo.pattern.governed-incident.shadow",
            version="1",
            input_schema={
                "observation": "IncidentObservation",
                "evidence_sources_healthy": "bool",
            },
            output_schema={"action": "Candidate<Action>"},
            nodes=nodes,
            edges=edges,
            invariants=[
                "evidence_before_action",
                "unhealthy_required_evidence_halts",
                "severity_classified_before_root_cause_is_required",
                "shadow_contains_no_write",
            ],
            entry="preserve_evidence",
            terminal_states=["prepare_remediation", "evidence_halt"],
        )
        compile_graph(graph)
        return graph

    write_policy = NodePolicies(
        authority=AuthorityRequirements(
            capability="REMEDIATE", scope=["incident-subject"], require_fresh_context=True
        ),
        idempotency=IdempotencyPolicy(require_key=True, verify_before_replay=True),
    )
    nodes.extend(
        [
            WorkflowNode(
                id="authorize_remediation",
                opcode="AUTHORIZE_ACTION",
                node_class=NodeClass.WRITE,
                effect_type=EffectType.EXERCISE_AUTHORITY,
                inputs=[TypedRef(name="action", type="Candidate<Action>")],
                outputs=[TypedRef(name="authorized", type="Authorized<Action>")],
                policies=write_policy,
                config={"action_type": "INCIDENT_REMEDIATION", "capability": "REMEDIATE"},
            ),
            WorkflowNode(
                id="execute_remediation",
                opcode="EXECUTE_ACTION",
                node_class=NodeClass.WRITE,
                effect_type=EffectType.SAFETY_CRITICAL,
                inputs=[TypedRef(name="authorized", type="Authorized<Action>")],
                outputs=[TypedRef(name="executed", type="Confirmed<Action>")],
                policies=write_policy,
                config={
                    "action_type": "INCIDENT_REMEDIATION",
                    "capability": "REMEDIATE",
                    "kernel_event_type": "INCIDENT_REMEDIATION_OBSERVED",
                },
            ),
            WorkflowNode(
                id="verify_poststate",
                opcode="VERIFY_EXECUTION",
                node_class=NodeClass.READ,
                effect_type=EffectType.READ_EXTERNAL,
                inputs=[TypedRef(name="executed", type="Confirmed<Action>")],
                outputs=[TypedRef(name="result", type="VerifiedEffect<Action>")],
            ),
        ]
    )
    edges.extend(
        [
            WorkflowEdge(source="prepare_remediation", target="authorize_remediation"),
            WorkflowEdge(source="authorize_remediation", target="execute_remediation"),
            WorkflowEdge(source="execute_remediation", target="verify_poststate"),
        ]
    )
    graph = WorkflowGraph(
        id="valo.pattern.governed-incident.live",
        version="1",
        input_schema={
            "observation": "IncidentObservation",
            "evidence_sources_healthy": "bool",
        },
        output_schema={"result": "VerifiedEffect<Action>"},
        nodes=nodes,
        edges=edges,
        invariants=[
            "evidence_before_action",
            "unhealthy_required_evidence_halts",
            "severity_classified_before_root_cause_is_required",
            "probabilistic_classification_never_writes_directly",
            "one_consequence_bearing_remediation_per_execution",
            "fresh_reht_authorization_before_execution",
            "completion_requires_verified_poststate",
        ],
        entry="preserve_evidence",
        terminal_states=["verify_poststate", "evidence_halt"],
    )
    compile_graph(graph)
    return graph
