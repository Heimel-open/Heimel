# ruff: noqa: C408
"""Registered Health Operations Pack Functions.

The registry expresses what may be requested. It does not authorize anything;
write Functions still cross Workflow ISA -> REHT -> deterministic binding ->
Gateway/Veritas through Operator.
"""

from __future__ import annotations

from valo_function_fabric.compiler import validate_function_definition
from valo_function_fabric.contracts import (
    AuthorityRequirement,
    AutonomyLevel,
    AutonomyProfile,
    IdempotencyRequirement,
    RiskClass,
    TypeRef,
)
from valo_function_fabric.registry import FunctionRegistry
from valo_function_fabric.stdlib import build_stdlib
from valo_function_fabric.stdlib.helpers import leaf_definition, leaf_workflow, register_leaf
from valo_function_fabric.types import workflow_type
from valo_workflow_isa.contracts import AuthorityRequirements as IsaAuthority
from valo_workflow_isa.contracts import (
    EffectType,
    NodeClass,
    NodePolicies,
    TypedRef,
    WorkflowEdge,
    WorkflowGraph,
    WorkflowNode,
)
from valo_workflow_isa.contracts import IdempotencyPolicy as IsaIdempotency

_DRAFT = AutonomyProfile(
    allowed_autonomy_levels=[
        AutonomyLevel.HUMAN,
        AutonomyLevel.OBSERVE,
        AutonomyLevel.DRAFT,
        AutonomyLevel.RECOMMEND,
        AutonomyLevel.STEP_UP,
    ],
    default_autonomy_level=AutonomyLevel.DRAFT,
)
_STEP_UP = AutonomyProfile(
    allowed_autonomy_levels=[AutonomyLevel.HUMAN, AutonomyLevel.RECOMMEND, AutonomyLevel.STEP_UP],
    default_autonomy_level=AutonomyLevel.STEP_UP,
)
_AUTO = AutonomyProfile(
    allowed_autonomy_levels=[
        AutonomyLevel.HUMAN,
        AutonomyLevel.RECOMMEND,
        AutonomyLevel.STEP_UP,
        AutonomyLevel.AUTO_EXECUTE,
    ],
    default_autonomy_level=AutonomyLevel.AUTO_EXECUTE,
)


def _t(name: str, type_expr: str) -> TypeRef:
    return TypeRef(name=name, type=type_expr)


_PURE = [
    dict(
        fid="valo.health.create_note_draft",
        name="HEALTH_CREATE_NOTE_DRAFT",
        opcode="RECONCILE",
        node_class=NodeClass.COMPUTE,
        inp=("conversation", "HealthConversationRefV1"),
        outp=("candidate", "CandidateClinicalRecordV1"),
        risk=RiskClass.R2_OPERATIONAL,
        autonomy=_DRAFT,
    ),
    dict(
        fid="valo.health.lookup_appointment_availability",
        name="HEALTH_LOOKUP_APPOINTMENT_AVAILABILITY",
        opcode="RECONCILE",
        node_class=NodeClass.COMPUTE,
        inp=("context", "PatientContextV1"),
        outp=("availability", "AppointmentAvailability"),
        risk=RiskClass.R1_REVERSIBLE_ADMINISTRATIVE,
        autonomy=_AUTO,
    ),
]

_WRITE = [
    dict(
        fid="valo.health.approve_note_draft",
        name="HEALTH_APPROVE_NOTE_DRAFT",
        inp=("review", "ClinicalReviewAttestationV1"),
        outp=("approved", "Approved<CandidateClinicalRecordV1>"),
        capability="CLINICAL_REVIEW",
        actor="clinician-1",
        identity_id="id-clinician-1",
        target="health-record-1",
        action_type="APPROVE_NOTE_DRAFT",
        state="NOTE_APPROVED",
        postconditions={"review_recorded": True},
        risk=RiskClass.R4_RIGHTS_IMPACTING,
        autonomy=_STEP_UP,
        idempotency=IdempotencyRequirement.REQUIRED,
    ),
    dict(
        fid="valo.health.commit_clinical_note",
        name="HEALTH_COMMIT_CLINICAL_NOTE",
        inp=("candidate", "CandidateClinicalRecordV1"),
        outp=("record", "VerifiedEffect<ClinicalRecord>"),
        capability="CLINICAL_RECORD_WRITE",
        actor="clinician-1",
        identity_id="id-clinician-1",
        target="health-record-1",
        action_type="COMMIT_CLINICAL_NOTE",
        state="NOTE_COMMITTED",
        postconditions={"clinical_record_committed": True},
        risk=RiskClass.R4_RIGHTS_IMPACTING,
        autonomy=_STEP_UP,
        idempotency=IdempotencyRequirement.VERIFY_BEFORE_REPLAY,
    ),
    dict(
        fid="valo.health.book_appointment",
        name="HEALTH_BOOK_APPOINTMENT",
        inp=("action", "CandidateHealthActionV1"),
        outp=("appointment", "VerifiedEffect<AppointmentStateV1>"),
        capability="APPOINTMENT_ADMIN",
        actor="health-admin-1",
        identity_id="id-health-admin-1",
        target="appointment-1",
        action_type="BOOK_APPOINTMENT",
        state="BOOKED",
        postconditions={"appointment_booked": True},
        risk=RiskClass.R2_OPERATIONAL,
        autonomy=_AUTO,
        idempotency=IdempotencyRequirement.VERIFY_BEFORE_REPLAY,
    ),
    dict(
        fid="valo.health.reschedule_appointment",
        name="HEALTH_RESCHEDULE_APPOINTMENT",
        inp=("action", "CandidateHealthActionV1"),
        outp=("appointment", "VerifiedEffect<AppointmentStateV1>"),
        capability="APPOINTMENT_ADMIN",
        actor="health-admin-1",
        identity_id="id-health-admin-1",
        target="appointment-1",
        action_type="RESCHEDULE_APPOINTMENT",
        state="RESCHEDULED",
        postconditions={"appointment_rescheduled": True},
        risk=RiskClass.R2_OPERATIONAL,
        autonomy=_AUTO,
        idempotency=IdempotencyRequirement.VERIFY_BEFORE_REPLAY,
    ),
    dict(
        fid="valo.health.cancel_appointment",
        name="HEALTH_CANCEL_APPOINTMENT",
        inp=("action", "CandidateHealthActionV1"),
        outp=("appointment", "VerifiedEffect<AppointmentStateV1>"),
        capability="APPOINTMENT_ADMIN",
        actor="health-admin-1",
        identity_id="id-health-admin-1",
        target="appointment-1",
        action_type="CANCEL_APPOINTMENT",
        state="CANCELLED",
        postconditions={"appointment_cancelled": True},
        risk=RiskClass.R2_OPERATIONAL,
        autonomy=_AUTO,
        idempotency=IdempotencyRequirement.VERIFY_BEFORE_REPLAY,
    ),
    dict(
        fid="valo.health.capture_renewal_request",
        name="HEALTH_CAPTURE_RENEWAL_REQUEST",
        inp=("action", "CandidateHealthActionV1"),
        outp=("renewal", "PrescriptionRenewalRequestV1"),
        capability="RENEWAL_INTAKE",
        actor="health-system-1",
        identity_id="id-health-system-1",
        target="renewal-1",
        action_type="CAPTURE_RENEWAL_REQUEST",
        state="CAPTURED",
        postconditions={"renewal_request_captured": True},
        risk=RiskClass.R2_OPERATIONAL,
        autonomy=_AUTO,
        idempotency=IdempotencyRequirement.REQUIRED,
    ),
    dict(
        fid="valo.health.route_renewal_request",
        name="HEALTH_ROUTE_RENEWAL_REQUEST",
        inp=("renewal", "PrescriptionRenewalRequestV1"),
        outp=("routed", "Routed<PrescriptionRenewalRequestV1>"),
        capability="RENEWAL_ROUTING",
        actor="health-system-1",
        identity_id="id-health-system-1",
        target="renewal-1",
        action_type="ROUTE_RENEWAL_REQUEST",
        state="ROUTED",
        postconditions={"renewal_request_routed": True},
        risk=RiskClass.R2_OPERATIONAL,
        autonomy=_AUTO,
        idempotency=IdempotencyRequirement.VERIFY_BEFORE_REPLAY,
    ),
    dict(
        fid="valo.health.request_clinical_review",
        name="HEALTH_REQUEST_CLINICAL_REVIEW",
        inp=("renewal", "PrescriptionRenewalRequestV1"),
        outp=("review", "ClinicalReviewRequested"),
        capability="CLINICAL_REVIEW_REQUEST",
        actor="health-system-1",
        identity_id="id-health-system-1",
        target="renewal-1",
        action_type="REQUEST_CLINICAL_REVIEW",
        state="CLINICAL_REVIEW_REQUESTED",
        postconditions={"clinical_review_requested": True},
        risk=RiskClass.R3_FINANCIAL_LEGAL,
        autonomy=_STEP_UP,
        idempotency=IdempotencyRequirement.REQUIRED,
    ),
    dict(
        fid="valo.health.record_clinician_decision",
        name="HEALTH_RECORD_CLINICIAN_DECISION",
        inp=("renewal", "PrescriptionRenewalRequestV1"),
        outp=("decision", "Recorded<ClinicianDecision>"),
        capability="CLINICAL_DECISION_RECORD",
        actor="clinician-1",
        identity_id="id-clinician-1",
        target="renewal-1",
        action_type="RECORD_CLINICIAN_DECISION",
        state="CLINICIAN_DECISION_RECORDED",
        postconditions={"clinician_decision_recorded": True},
        risk=RiskClass.R5_SAFETY_CRITICAL,
        autonomy=_STEP_UP,
        idempotency=IdempotencyRequirement.REQUIRED,
    ),
    dict(
        fid="valo.health.notify_patient",
        name="HEALTH_NOTIFY_PATIENT",
        inp=("action", "CandidateHealthActionV1"),
        outp=("notification", "Acknowledged<PatientMessage>"),
        capability="PATIENT_COMMUNICATION",
        actor="health-system-1",
        identity_id="id-health-system-1",
        target="renewal-1",
        action_type="NOTIFY_PATIENT",
        state="PATIENT_NOTIFIED",
        postconditions={"patient_notified": True},
        risk=RiskClass.R2_OPERATIONAL,
        autonomy=_STEP_UP,
        idempotency=IdempotencyRequirement.VERIFY_BEFORE_REPLAY,
    ),
]

RESERVED_FUNCTION_IDS = ("valo.health.execute_authorized_prescription_action",)


def build_health_registry() -> FunctionRegistry:
    registry = build_stdlib()
    for spec in _PURE:
        _register_pure(registry, spec)
    for spec in _WRITE:
        _register_write(registry, spec)
    return registry


def health_function_ids() -> tuple[str, ...]:
    return tuple(sorted([spec["fid"] for spec in _PURE] + [spec["fid"] for spec in _WRITE]))


def _register_pure(registry: FunctionRegistry, spec: dict) -> None:
    graph_id = f"wf.{spec['fid']}"
    input_ref = _t(spec["inp"][0], spec["inp"][1])
    output_ref = _t(spec["outp"][0], spec["outp"][1])
    workflow = leaf_workflow(
        graph_id,
        node_id="run",
        opcode=spec["opcode"],
        node_class=spec["node_class"],
        input_refs=[input_ref],
        output_refs=[output_ref],
        effect=EffectType.PURE,
        capability=None,
        config={},
    )
    definition = leaf_definition(
        spec["fid"],
        spec["name"],
        "1.0.0",
        input_type=input_ref,
        output_type=output_ref,
        workflow_graph=workflow,
        effects=["PURE"],
        risk=spec["risk"],
        autonomy=spec["autonomy"],
    )
    register_leaf(registry, definition, workflow)


def _register_write(registry: FunctionRegistry, spec: dict) -> None:
    graph_id = f"wf.{spec['fid']}"
    config = {
        "target": spec["target"],
        "actor": spec["actor"],
        "identity_id": spec["identity_id"],
        "action_type": spec["action_type"],
        "capability": spec["capability"],
        "kernel_event_type": "HEALTH_TRANSITION",
        "postconditions": spec["postconditions"],
        "requested_transition": {"state": spec["state"]},
    }
    input_ref = _t(spec["inp"][0], spec["inp"][1])
    output_ref = _t(spec["outp"][0], spec["outp"][1])
    input_node_ref = TypedRef(name=input_ref.name, type=workflow_type(input_ref.type))
    output_node_ref = TypedRef(name=output_ref.name, type=workflow_type(output_ref.type))
    idempotency = spec.get("idempotency", IdempotencyRequirement.NONE)
    prepare = WorkflowNode(
        id="prepare",
        opcode="PREPARE_ACTION",
        node_class=NodeClass.COMPUTE,
        inputs=[input_node_ref],
        outputs=[TypedRef(name="action", type="any")],
        effect_type=EffectType.PURE,
        policies=NodePolicies(authority=IsaAuthority(capability=spec["capability"], scope=[])),
        config=config,
    )
    execute = WorkflowNode(
        id="execute",
        opcode="EXECUTE_ACTION",
        node_class=NodeClass.WRITE,
        inputs=[TypedRef(name="action", type="any")],
        outputs=[output_node_ref],
        effect_type=EffectType.WRITE_INTERNAL,
        policies=NodePolicies(
            authority=IsaAuthority(capability=spec["capability"], scope=[]),
            idempotency=IsaIdempotency(require_key=True)
            if idempotency != IdempotencyRequirement.NONE
            else IsaIdempotency(),
        ),
        config=config,
    )
    workflow = WorkflowGraph(
        id=graph_id,
        version="1",
        input_schema={input_node_ref.name: input_node_ref.type},
        output_schema={output_node_ref.name: output_node_ref.type},
        nodes=[prepare, execute],
        edges=[WorkflowEdge(source="prepare", target="execute")],
        entry="prepare",
        terminal_states=["execute"],
    )
    definition = leaf_definition(
        spec["fid"],
        spec["name"],
        "1.0.0",
        input_type=input_ref,
        output_type=output_ref,
        workflow_graph=workflow,
        effects=["WRITE_INTERNAL"],
        risk=spec["risk"],
        autonomy=spec["autonomy"],
        authority=[AuthorityRequirement(capability=spec["capability"], scope=["*"])],
        idempotency=idempotency,
    )
    validate_function_definition(definition, workflow)
    registry.register(definition, workflow)
