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
from valo_function_fabric.stdlib.helpers import (
    leaf_definition,
    leaf_workflow,
    register_leaf,
)
from valo_function_fabric.types import workflow_type
from valo_workflow_isa.contracts import (
    AuthorityRequirements as IsaAuthority,
)
from valo_workflow_isa.contracts import (
    EffectType,
    NodeClass,
    NodePolicies,
    TypedRef,
    WorkflowEdge,
    WorkflowGraph,
    WorkflowNode,
)
from valo_workflow_isa.contracts import (
    IdempotencyPolicy as IsaIdempotency,
)

_STEP_UP = AutonomyProfile(
    allowed_autonomy_levels=[AutonomyLevel.HUMAN, AutonomyLevel.RECOMMEND, AutonomyLevel.STEP_UP],
    default_autonomy_level=AutonomyLevel.STEP_UP,
)
_AUTO = AutonomyProfile(
    allowed_autonomy_levels=[AutonomyLevel.HUMAN, AutonomyLevel.RECOMMEND, AutonomyLevel.STEP_UP, AutonomyLevel.AUTO_EXECUTE],
    default_autonomy_level=AutonomyLevel.AUTO_EXECUTE,
)


def _t(name: str, type_expr: str) -> TypeRef:
    return TypeRef(name=name, type=type_expr)


def build_public_registry() -> FunctionRegistry:
    registry = build_stdlib()
    for spec in _PURE:
        _register_pure(registry, spec)
    for spec in _WRITE:
        _register_write(registry, spec)
    return registry


_PURE = [
    # DecisionContext is assembled by an accumulating chain: every control
    # Function takes the previous context and yields the enriched context. The
    # terminal context can ONLY be produced by PREPARE_PUBLIC_DECISION, and
    # ISSUE_PUBLIC_DECISION consumes a DecisionContext — it cannot compile or
    # run on a bare Case.
    dict(fid="valo.public.verify_representation", name="VERIFY_REPRESENTATION", opcode="RECONCILE", node_class=NodeClass.COMPUTE,
         inp=("case", "Case"), outp=("context", "DecisionContext"), risk=RiskClass.R2_OPERATIONAL, autonomy=_STEP_UP),
    dict(fid="valo.public.resolve_purpose", name="RESOLVE_PURPOSE", opcode="RECONCILE", node_class=NodeClass.COMPUTE,
         inp=("context", "DecisionContext"), outp=("context", "DecisionContext"), risk=RiskClass.R1_REVERSIBLE_ADMINISTRATIVE, autonomy=_AUTO),
    dict(fid="valo.public.resolve_legal_basis", name="RESOLVE_LEGAL_BASIS", opcode="RECONCILE", node_class=NodeClass.COMPUTE,
         inp=("context", "DecisionContext"), outp=("context", "DecisionContext"), risk=RiskClass.R2_OPERATIONAL, autonomy=_AUTO),
    dict(fid="valo.public.resolve_competence", name="RESOLVE_COMPETENCE", opcode="RECONCILE", node_class=NodeClass.COMPUTE,
         inp=("context", "DecisionContext"), outp=("context", "DecisionContext"), risk=RiskClass.R2_OPERATIONAL, autonomy=_AUTO),
    dict(fid="valo.public.establish_case_facts", name="ESTABLISH_CASE_FACTS", opcode="RECONCILE", node_class=NodeClass.COMPUTE,
         inp=("context", "DecisionContext"), outp=("context", "DecisionContext"), risk=RiskClass.R2_OPERATIONAL, autonomy=_AUTO),
    dict(fid="valo.public.check_eligibility", name="CHECK_ELIGIBILITY", opcode="RECONCILE", node_class=NodeClass.COMPUTE,
         inp=("context", "DecisionContext"), outp=("context", "DecisionContext"), risk=RiskClass.R2_OPERATIONAL, autonomy=_AUTO),
    dict(fid="valo.public.check_procedural_requirements", name="CHECK_PROCEDURAL_REQUIREMENTS", opcode="RECONCILE", node_class=NodeClass.COMPUTE,
         inp=("context", "DecisionContext"), outp=("context", "DecisionContext"), risk=RiskClass.R2_OPERATIONAL, autonomy=_AUTO),
    dict(fid="valo.public.check_conflict_of_interest", name="CHECK_CONFLICT_OF_INTEREST", opcode="RECONCILE", node_class=NodeClass.COMPUTE,
         inp=("context", "DecisionContext"), outp=("context", "DecisionContext"), risk=RiskClass.R2_OPERATIONAL, autonomy=_AUTO),
    dict(fid="valo.public.prepare_public_decision", name="PREPARE_PUBLIC_DECISION", opcode="RECONCILE", node_class=NodeClass.COMPUTE,
         inp=("context", "DecisionContext"), outp=("context", "DecisionContext"), risk=RiskClass.R2_OPERATIONAL, autonomy=_STEP_UP),
    dict(fid="valo.public.verify_delivery", name="VERIFY_DELIVERY", opcode="RECONCILE", node_class=NodeClass.COMPUTE,
         inp=("case", "Case"), outp=("delivery", "DeliveryVerified"), risk=RiskClass.R2_OPERATIONAL, autonomy=_STEP_UP),
]

_WRITE = [
    dict(fid="valo.public.register_case", name="REGISTER_CASE", inp=("application", "Application"), outp=("registered", "Registered<Case>"),
         capability="ADMIN", actor="system-1", identity_id="id-system-1", target="case-1",
         action_type="REGISTER", kernel_event_type="CASE_TRANSITION", state="REGISTERED",
         postconditions={"executed": True}, risk=RiskClass.R1_REVERSIBLE_ADMINISTRATIVE, autonomy=_AUTO),
    dict(fid="valo.public.mark_ready_for_review", name="MARK_READY_FOR_REVIEW", inp=("case", "Case"), outp=("ready", "ReadyForReview"),
         capability="ADMIN", actor="system-1", identity_id="id-system-1", target="case-1",
         action_type="READY_FOR_REVIEW", kernel_event_type="CASE_TRANSITION", state="READY_FOR_REVIEW",
         postconditions={"executed": True}, risk=RiskClass.R1_REVERSIBLE_ADMINISTRATIVE, autonomy=_AUTO),
    dict(fid="valo.public.mark_under_review", name="MARK_UNDER_REVIEW", inp=("case", "Case"), outp=("reviewing", "UnderReview"),
         capability="ADMIN", actor="system-1", identity_id="id-system-1", target="case-1",
         action_type="UNDER_REVIEW", kernel_event_type="CASE_TRANSITION", state="UNDER_REVIEW",
         postconditions={"executed": True}, risk=RiskClass.R1_REVERSIBLE_ADMINISTRATIVE, autonomy=_AUTO),
    dict(fid="valo.public.mark_ready_for_decision", name="MARK_READY_FOR_DECISION", inp=("case", "Case"), outp=("ready", "ReadyForDecision"),
         capability="ADMIN", actor="system-1", identity_id="id-system-1", target="case-1",
         action_type="READY_FOR_DECISION", kernel_event_type="CASE_TRANSITION", state="READY_FOR_DECISION",
         postconditions={"executed": True}, risk=RiskClass.R2_OPERATIONAL, autonomy=_STEP_UP),
    dict(fid="valo.public.issue_public_decision", name="ISSUE_PUBLIC_DECISION", inp=("context", "DecisionContext"), outp=("decision", "VerifiedEffect<PublicDecision>"),
         capability="ISSUE_DECISION", actor="system-1", identity_id="id-system-1", target="case-1",
         action_type="ISSUE_DECISION", kernel_event_type="CASE_TRANSITION", state="DECIDED",
         postconditions={"decision_issued": True}, risk=RiskClass.R4_RIGHTS_IMPACTING, autonomy=_STEP_UP,
         idempotency=IdempotencyRequirement.REQUIRED),
    dict(fid="valo.public.notify", name="NOTIFY", inp=("notification", "Notification"), outp=("ack", "Acknowledged<Message>"),
         capability="ADMIN", actor="system-1", identity_id="id-system-1", target="case-1",
         action_type="NOTIFY", kernel_event_type="CASE_TRANSITION", state="NOTIFIED",
         postconditions={"delivered": True}, risk=RiskClass.R1_REVERSIBLE_ADMINISTRATIVE, autonomy=_AUTO,
         idempotency=IdempotencyRequirement.VERIFY_BEFORE_REPLAY),
    dict(fid="valo.public.create_appeal_right", name="CREATE_APPEAL_RIGHT", inp=("decision", "PublicDecision"), outp=("appeal", "AppealRight"),
         capability="ADMIN", actor="system-1", identity_id="id-system-1", target="case-1",
         action_type="CREATE_APPEAL_DEADLINE", kernel_event_type="CASE_TRANSITION", state="APPEAL_PERIOD",
         postconditions={"deadline_set": True}, risk=RiskClass.R2_OPERATIONAL, autonomy=_STEP_UP),
    dict(fid="valo.public.finalize_case", name="FINALIZE_CASE", inp=("case", "Case"), outp=("finalized", "FinalizedCase"),
         capability="ADMIN", actor="system-1", identity_id="id-system-1", target="case-1",
         action_type="FINALIZE", kernel_event_type="CASE_TRANSITION", state="FINAL",
         postconditions={"executed": True}, risk=RiskClass.R1_REVERSIBLE_ADMINISTRATIVE, autonomy=_AUTO),
    dict(fid="valo.public.close_case", name="CLOSE_CASE", inp=("case", "Case"), outp=("closed", "ClosedCase"),
         capability="ADMIN", actor="system-1", identity_id="id-system-1", target="case-1",
         action_type="CLOSE", kernel_event_type="CASE_TRANSITION", state="CLOSED",
         postconditions={"executed": True}, risk=RiskClass.R1_REVERSIBLE_ADMINISTRATIVE, autonomy=_AUTO),
]

CORE_REUSE_CHECK = [
    "valo.identity.verify_identity",
    "valo.evidence.verify",
    "valo.evidence.request",
    "valo.decision.approve",
]


def _register_pure(registry: FunctionRegistry, spec: dict) -> None:
    fid = spec["fid"]
    graph_id = f"wf.{fid}"
    definition = leaf_definition(
        fid, spec["name"], "1.0.0",
        input_type=_t(spec["inp"][0], spec["inp"][1]),
        output_type=_t(spec["outp"][0], spec["outp"][1]),
        workflow_graph=leaf_workflow(
            graph_id, node_id="run", opcode=spec["opcode"], node_class=spec["node_class"],
            input_refs=[_t(spec["inp"][0], spec["inp"][1])],
            output_refs=[_t(spec["outp"][0], spec["outp"][1])],
            effect=EffectType.PURE, capability=None, config=spec.get("config", {}),
        ),
        effects=["PURE"],
        risk=spec["risk"],
        autonomy=spec["autonomy"],
    )
    register_leaf(registry, definition, leaf_workflow(
        graph_id, node_id="run", opcode=spec["opcode"], node_class=spec["node_class"],
        input_refs=[_t(spec["inp"][0], spec["inp"][1])],
        output_refs=[_t(spec["outp"][0], spec["outp"][1])],
        effect=EffectType.PURE, capability=None, config=spec.get("config", {}),
    ))


def _register_write(registry: FunctionRegistry, spec: dict) -> None:
    fid = spec["fid"]
    graph_id = f"wf.{fid}"
    config = {
        "target": spec["target"],
        "actor": spec["actor"],
        "identity_id": spec["identity_id"],
        "action_type": spec["action_type"],
        "capability": spec["capability"],
        "kernel_event_type": spec["kernel_event_type"],
        "postconditions": spec["postconditions"],
        "requested_transition": {"state": spec["state"]} if spec.get("state") else {},
    }
    input_ref = _t(spec["inp"][0], spec["inp"][1])
    output_ref = _t(spec["outp"][0], spec["outp"][1])
    input_node_ref = TypedRef(name=input_ref.name, type=workflow_type(input_ref.type))
    output_node_ref = TypedRef(name=output_ref.name, type=workflow_type(output_ref.type))
    prepare = WorkflowNode(
        id="prepare", opcode="PREPARE_ACTION", node_class=NodeClass.COMPUTE,
        inputs=[input_node_ref],
        outputs=[TypedRef(name="action", type="any")],
        effect_type=EffectType.PURE,
        policies=NodePolicies(authority=IsaAuthority(capability=spec["capability"], scope=[])),
        config=config,
    )
    execute = WorkflowNode(
        id="execute", opcode="EXECUTE_ACTION", node_class=NodeClass.WRITE,
        inputs=[TypedRef(name="action", type="any")],
        outputs=[output_node_ref],
        effect_type=EffectType.WRITE_INTERNAL,
        policies=NodePolicies(
            authority=IsaAuthority(capability=spec["capability"], scope=[]),
            idempotency=IsaIdempotency(require_key=True) if spec.get("idempotency", IdempotencyRequirement.NONE) != IdempotencyRequirement.NONE else IsaIdempotency(),
        ),
        config=config,
    )
    workflow = WorkflowGraph(
        id=graph_id, version="1",
        input_schema={input_node_ref.name: input_node_ref.type},
        output_schema={output_node_ref.name: output_node_ref.type},
        nodes=[prepare, execute],
        edges=[WorkflowEdge(source="prepare", target="execute")],
        entry="prepare", terminal_states=["execute"],
    )
    definition = leaf_definition(
        fid, spec["name"], "1.0.0",
        input_type=_t(spec["inp"][0], spec["inp"][1]),
        output_type=_t(spec["outp"][0], spec["outp"][1]),
        workflow_graph=workflow,
        effects=["WRITE_INTERNAL"],
        risk=spec["risk"],
        autonomy=spec["autonomy"],
        authority=[AuthorityRequirement(capability=spec["capability"], scope=["*"])],
        idempotency=spec.get("idempotency", IdempotencyRequirement.NONE),
    )
    validate_function_definition(definition, workflow)
    registry.register(definition, workflow)
