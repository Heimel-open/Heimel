"""Generic governed incident-response Function.

The program is substrate-neutral. Shadow mode stops at a prepared action and
cannot WRITE. Live mode adds fresh REHT-backed authorization/execution and an
explicit post-state verification node.
"""

from __future__ import annotations

from dataclasses import dataclass

from valo_workflow_isa.contracts import (
    AuthorityRequirements,
    Determinism,
    EffectType,
    IdempotencyPolicy,
    NodeClass,
    NodePolicies,
    TypedRef,
    WorkflowEdge,
    WorkflowGraph,
    WorkflowNode,
)

from .compiler import validate_function_definition
from .contracts.common import (
    AutonomyLevel,
    FunctionStatus,
    IdempotencyRequirement,
    RiskClass,
)
from .contracts.function import (
    AuthorityRequirement,
    AutonomyProfile,
    EvidenceRequirement,
    FunctionDefinition,
    TypeRef,
)


@dataclass(frozen=True)
class GovernedIncidentProgram:
    definition: FunctionDefinition
    workflow_graph: WorkflowGraph
    shadow: bool


def build_governed_incident_program(*, shadow: bool = False) -> GovernedIncidentProgram:
    """Build and statically validate the generic incident-response program."""

    nodes = [
        WorkflowNode(
            id="preserve_evidence",
            opcode="VALIDATE_SCHEMA",
            node_class=NodeClass.COMPUTE,
            inputs=[TypedRef(name="observation", type="IncidentObservation")],
            outputs=[TypedRef(name="observation_verified", type="Verified<IncidentObservation>")],
            config={"schema": {"required": ["observation_id", "subject_ref", "symptoms"]}},
        ),
        WorkflowNode(
            id="classify",
            opcode="EVALUATE_RULE",
            node_class=NodeClass.DECIDE,
            inputs=[TypedRef(name="observation_verified", type="Verified<IncidentObservation>")],
            outputs=[TypedRef(name="classification", type="Candidate<IncidentClassification>")],
            determinism=Determinism.PROBABILISTIC,
            config={
                "rule": "true",
                "model": "incident-classifier",
                "model_version": "1",
                "source_context": "preserved-incident-evidence",
            },
        ),
        WorkflowNode(
            id="diagnose",
            opcode="RECONCILE",
            node_class=NodeClass.COMPUTE,
            inputs=[TypedRef(name="classification", type="Candidate<IncidentClassification>")],
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
        WorkflowEdge(source="preserve_evidence", target="classify"),
        WorkflowEdge(source="classify", target="diagnose"),
        WorkflowEdge(source="diagnose", target="prepare_remediation"),
    ]

    if shadow:
        terminal = "prepare_remediation"
        output_schema = {"action": "Candidate<Action>"}
        effects: list[str] = []
        risk = RiskClass.R2_OPERATIONAL
        autonomy = AutonomyProfile(
            allowed_autonomy_levels=[
                AutonomyLevel.OBSERVE,
                AutonomyLevel.DRAFT,
                AutonomyLevel.RECOMMEND,
            ],
            default_autonomy_level=AutonomyLevel.OBSERVE,
        )
        authority: list[AuthorityRequirement] = []
        idempotency = IdempotencyRequirement.NONE
        output_type = TypeRef(name="action", type="Candidate<Action>")
        function_id = "valo.incident.respond.shadow"
        name = "GOVERNED_INCIDENT_SHADOW"
    else:
        write_policy = NodePolicies(
            authority=AuthorityRequirements(
                capability="REMEDIATE", scope=["incident-subject"]
            ),
            idempotency=IdempotencyPolicy(
                require_key=True, verify_before_replay=True
            ),
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
                    config={
                        "action_type": "INCIDENT_REMEDIATION",
                        "capability": "REMEDIATE",
                    },
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
        terminal = "verify_poststate"
        output_schema = {"result": "VerifiedEffect<Action>"}
        effects = [
            EffectType.EXERCISE_AUTHORITY.value,
            EffectType.SAFETY_CRITICAL.value,
            EffectType.READ_EXTERNAL.value,
        ]
        risk = RiskClass.R5_SAFETY_CRITICAL
        autonomy = AutonomyProfile(
            allowed_autonomy_levels=[
                AutonomyLevel.HUMAN,
                AutonomyLevel.RECOMMEND,
                AutonomyLevel.STEP_UP,
            ],
            default_autonomy_level=AutonomyLevel.STEP_UP,
        )
        authority = [AuthorityRequirement(capability="REMEDIATE", scope=["*"])]
        idempotency = IdempotencyRequirement.VERIFY_BEFORE_REPLAY
        output_type = TypeRef(name="result", type="VerifiedEffect<Action>")
        function_id = "valo.incident.respond"
        name = "GOVERNED_INCIDENT_RESPONSE"

    workflow = WorkflowGraph(
        id=f"wf.{function_id}",
        version="1",
        input_schema={"observation": "IncidentObservation"},
        output_schema=output_schema,
        nodes=nodes,
        edges=edges,
        entry="preserve_evidence",
        terminal_states=[terminal],
        invariants=[
            "evidence_before_remediation",
            "probabilistic_classification_never_writes_directly",
            "one_prepared_remediation_per_execution",
            "live_remediation_requires_fresh_reht_authorization",
            "completion_requires_poststate_verification" if not shadow else "shadow_has_no_write",
        ],
    )
    definition = FunctionDefinition(
        function_id=function_id,
        name=name,
        version="1.0.0",
        input_type=TypeRef(name="observation", type="IncidentObservation"),
        output_type=output_type,
        workflow_ref=workflow.id,
        effects=effects,
        risk_class=risk,
        autonomy_profile=autonomy,
        authority_requirements=authority,
        evidence_requirements=[
            EvidenceRequirement(
                required_types=["IncidentObservation"], minimum_status="RECEIVED"
            )
        ],
        reversible=False,
        idempotency_requirement=idempotency,
        status=FunctionStatus.ACTIVE,
    )
    validate_function_definition(definition, workflow)
    return GovernedIncidentProgram(
        definition=definition, workflow_graph=workflow, shadow=shadow
    )

