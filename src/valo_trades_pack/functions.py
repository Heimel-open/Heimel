from __future__ import annotations

from valo_function_fabric.compiler import validate_function_definition
from valo_function_fabric.contracts import (
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
from valo_workflow_isa.contracts import EffectType, NodeClass

from .domain import verified

_AUTO = AutonomyProfile(
    allowed_autonomy_levels=[AutonomyLevel.HUMAN, AutonomyLevel.RECOMMEND, AutonomyLevel.STEP_UP, AutonomyLevel.AUTO_EXECUTE],
    default_autonomy_level=AutonomyLevel.AUTO_EXECUTE,
)
_STEP_UP = AutonomyProfile(
    allowed_autonomy_levels=[AutonomyLevel.HUMAN, AutonomyLevel.RECOMMEND, AutonomyLevel.STEP_UP],
    default_autonomy_level=AutonomyLevel.STEP_UP,
)


def _t(name: str, type_expr: str) -> TypeRef:
    return TypeRef(name=name, type=type_expr)


def build_trades_registry() -> FunctionRegistry:
    """FF registry = exact core stdlib + effectful trades Functions. Every
    world-changing Function is a WRITE that flows Workflow ISA -> REHT."""
    registry = build_stdlib()

    # --- pure / read functions ------------------------------------------------
    _register(registry, dict(
        fid="valo.trades.classify_service", name="CLASSIFY_SERVICE", node_class=NodeClass.DECIDE, opcode="EVALUATE_RULE",
        inp=("request", "Request"), outp=("classification", "Classification"), effect=EffectType.PURE, capability=None, config={"rule": "true"},
        risk=RiskClass.R1_REVERSIBLE_ADMINISTRATIVE, autonomy=_AUTO,
    ))
    _register(registry, dict(
        fid="valo.trades.check_site_requirements", name="CHECK_SITE_REQUIREMENTS", node_class=NodeClass.DECIDE, opcode="EVALUATE_RULE",
        inp=("site", "Site"), outp=("assessment", "SiteAssessment"), effect=EffectType.PURE, capability=None, config={"rule": "true"},
        risk=RiskClass.R1_REVERSIBLE_ADMINISTRATIVE, autonomy=_AUTO,
    ))
    _register(registry, dict(
        fid="valo.trades.select_worker", name="SELECT_WORKER", node_class=NodeClass.DECIDE, opcode="EVALUATE_RULE",
        inp=("candidates", "CandidateSet<Resource>"), outp=("selected", "Candidate<Resource>"), effect=EffectType.PURE, capability=None, config={"rule": "true"},
        risk=RiskClass.R2_OPERATIONAL, autonomy=_AUTO,
    ))
    _register(registry, dict(
        fid="valo.trades.verify_credential", name="VERIFY_TRADE_CREDENTIAL", node_class=NodeClass.COMPUTE, opcode="RECONCILE",
        inp=("worker", "Candidate<Resource>"), outp=("credential", verified("Credential")), effect=EffectType.PURE, capability=None,
        risk=RiskClass.R2_OPERATIONAL, autonomy=_AUTO,
    ))
    _register(registry, dict(
        fid="valo.trades.generate_quote", name="GENERATE_QUOTE", node_class=NodeClass.COMPUTE, opcode="CALCULATE",
        inp=("request", "Request"), outp=("quote", "Quote"), effect=EffectType.PURE, capability=None, config={"expression": "request"},
        risk=RiskClass.R1_REVERSIBLE_ADMINISTRATIVE, autonomy=_AUTO,
    ))
    _register(registry, dict(
        fid="valo.trades.receive_acceptance", name="RECEIVE_ACCEPTANCE", node_class=NodeClass.DECIDE, opcode="REQUEST_INPUT",
        inp=("quote", "Quote"), outp=("accepted", "AcceptedQuote"), effect=EffectType.PURE, capability=None,
        risk=RiskClass.R1_REVERSIBLE_ADMINISTRATIVE, autonomy=_STEP_UP,
    ))
    _register(registry, dict(
        fid="valo.trades.verify_job_completion", name="VERIFY_JOB_COMPLETION", node_class=NodeClass.COMPUTE, opcode="RECONCILE",
        inp=("evidence", "Admitted<Evidence>"), outp=("completion", verified("CompletionEvidence")), effect=EffectType.PURE, capability=None,
        risk=RiskClass.R2_OPERATIONAL, autonomy=_STEP_UP,
    ))

    # --- world-changing WRITE functions (go through REHT) ---------------------
    _register_write(registry, dict(
        fid="valo.trades.dispatch", name="DISPATCH",
        inp=("reservation", "Reserved<Resource>"), outp=("decision", "DispatchDecision"),
        capability="DISPATCH", actor="worker-a", identity_id="id-worker-a", target="workorder-1",
        action_type="DISPATCH", kernel_event_type="WORK_ORDER_TRANSITION", state="DISPATCHED",
        postconditions={"dispatch_confirmed": True}, risk=RiskClass.R2_OPERATIONAL, autonomy=_STEP_UP,
    ))
    _register_write(registry, dict(
        fid="valo.trades.execute_work", name="EXECUTE_WORK",
        inp=("decision", "DispatchDecision"), outp=("record", "WorkRecord"),
        capability="ADMIN", actor="system-1", identity_id="id-system-1", target="workorder-1",
        action_type="EXECUTE_WORK", kernel_event_type="WORK_ORDER_TRANSITION", state="IN_PROGRESS",
        postconditions={"executed": True}, risk=RiskClass.R2_OPERATIONAL, autonomy=_AUTO,
    ))
    _register_write(registry, dict(
        fid="valo.trades.issue_invoice", name="ISSUE_INVOICE",
        inp=("completion", verified("CompletionEvidence")), outp=("invoice", "Issued<Invoice>"),
        capability="ADMIN", actor="system-1", identity_id="id-system-1", target="workorder-1",
        action_type="INVOICE", kernel_event_type="WORK_ORDER_TRANSITION", state="INVOICED",
        postconditions={"invoice_issued": True}, risk=RiskClass.R3_FINANCIAL_LEGAL, autonomy=_STEP_UP,
    ))
    _register_write(registry, dict(
        fid="valo.trades.receive_payment", name="RECEIVE_PAYMENT",
        inp=("obligation", "PaymentObligation"), outp=("payment", "Payment"),
        capability="ADMIN", actor="system-1", identity_id="id-system-1", target="workorder-1",
        action_type="PAY", kernel_event_type="EXTERNAL_EFFECT_OBSERVED", state=None,
        postconditions={"payment_observed": True}, risk=RiskClass.R3_FINANCIAL_LEGAL, autonomy=_STEP_UP,
        idempotency=IdempotencyRequirement.VERIFY_BEFORE_REPLAY,
    ))
    _register_write(registry, dict(
        fid="valo.trades.reconcile_payment", name="RECONCILE_PAYMENT",
        inp=("payment", "Payment"), outp=("reconciled", "VerifiedEffect<Payment>"),
        capability="ADMIN", actor="system-1", identity_id="id-system-1", target="workorder-1",
        action_type="RECONCILE_PAYMENT", kernel_event_type="WORK_ORDER_TRANSITION", state="PAID",
        postconditions={"executed": True}, risk=RiskClass.R3_FINANCIAL_LEGAL, autonomy=_AUTO,
    ))
    _register(registry, dict(
        fid="valo.trades.verify_postconditions", name="VERIFY_POSTCONDITIONS", node_class=NodeClass.COMPUTE, opcode="RECONCILE",
        inp=("work_order", "WorkOrder"), outp=("verified", "CompletionVerified"), effect=EffectType.PURE, capability=None,
        risk=RiskClass.R2_OPERATIONAL, autonomy=_STEP_UP,
    ))
    _register_write(registry, dict(
        fid="valo.trades.close_work_order", name="CLOSE_WORK_ORDER",
        inp=("verified", "CompletionVerified"), outp=("closed", "Registered<Entity>"),
        capability="ADMIN", actor="system-1", identity_id="id-system-1", target="workorder-1",
        action_type="CLOSE", kernel_event_type="WORK_ORDER_TRANSITION", state="CLOSED",
        postconditions={"executed": True}, risk=RiskClass.R2_OPERATIONAL, autonomy=_AUTO,
    ))
    _register_write(registry, dict(
        fid="valo.trades.register_workorder", name="REGISTER_WORKORDER",
        inp=("registration", "Registration"), outp=("registered", "Registered<Entity>"),
        capability="ADMIN", actor="system-1", identity_id="id-system-1", target="workorder-1",
        action_type="REGISTER", kernel_event_type="WORK_ORDER_TRANSITION", state="READY_TO_QUOTE",
        postconditions={"executed": True}, risk=RiskClass.R1_REVERSIBLE_ADMINISTRATIVE, autonomy=_AUTO,
    ))
    _register_write(registry, dict(
        fid="valo.trades.reserve", name="RESERVE",
        inp=("resource", "Candidate<Resource>"), outp=("reservation", "Reserved<Resource>"),
        capability="ALLOCATE", actor="worker-a", identity_id="id-worker-a", target="workorder-1",
        action_type="RESERVE_RESOURCE", kernel_event_type="RESOURCE_RESERVED", state=None,
        requested_transition={"reservation": {"reservation_id": "res-wf-1", "resource_id": "worker-a", "holder": "worker-a", "tenant_id": "trades", "quantity": 1}},
        postconditions={"executed": True}, risk=RiskClass.R3_FINANCIAL_LEGAL, autonomy=_STEP_UP,
    ))
    _register_write(registry, dict(
        fid="valo.trades.schedule", name="SCHEDULE",
        inp=("requirement", "ScheduleRequirement"), outp=("booking", "Confirmed<Booking>"),
        capability="ADMIN", actor="system-1", identity_id="id-system-1", target="workorder-1",
        action_type="SCHEDULE", kernel_event_type="WORK_ORDER_TRANSITION", state="SCHEDULED",
        postconditions={"executed": True}, risk=RiskClass.R2_OPERATIONAL, autonomy=_STEP_UP,
    ))
    _register_write(registry, dict(
        fid="valo.trades.notify", name="NOTIFY",
        inp=("notification", "Notification"), outp=("ack", "Acknowledged<Message>"),
        capability="ADMIN", actor="system-1", identity_id="id-system-1", target="workorder-1",
        action_type="NOTIFY", kernel_event_type="EXTERNAL_EFFECT_OBSERVED", state=None,
        postconditions={"executed": True}, risk=RiskClass.R1_REVERSIBLE_ADMINISTRATIVE, autonomy=_AUTO,
    ))
    return registry


def _register(registry: FunctionRegistry, spec: dict) -> None:
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
            effect=spec["effect"], capability=None, config=spec.get("config", {}),
        ),
        effects=["PURE"],
        risk=spec["risk"],
        autonomy=spec["autonomy"],
    )
    register_leaf(registry, definition, leaf_workflow(
        graph_id, node_id="run", opcode=spec["opcode"], node_class=spec["node_class"],
        input_refs=[_t(spec["inp"][0], spec["inp"][1])],
        output_refs=[_t(spec["outp"][0], spec["outp"][1])],
        effect=spec["effect"], capability=None, config=spec.get("config", {}),
    ))


def _register_write(registry: FunctionRegistry, spec: dict) -> None:
    from valo_workflow_isa.contracts import AuthorityRequirements as IsaAuthority
    from valo_workflow_isa.contracts import (
        NodePolicies,
        TypedRef,
        WorkflowEdge,
        WorkflowGraph,
        WorkflowNode,
    )

    fid = spec["fid"]
    graph_id = f"wf.{fid}"
    requested_transition = dict(spec.get("requested_transition") or {})
    if spec.get("state"):
        requested_transition["state"] = spec["state"]
    config = {
        "target": spec["target"],
        "actor": spec["actor"],
        "identity_id": spec["identity_id"],
        "action_type": spec["action_type"],
        "capability": spec["capability"],
        "kernel_event_type": spec["kernel_event_type"],
        "postconditions": spec["postconditions"],
        "requested_transition": requested_transition,
    }
    input_ref = _t(spec["inp"][0], spec["inp"][1])
    output_ref = _t(spec["outp"][0], spec["outp"][1])
    input_node_ref = TypedRef(name=input_ref.name, type=workflow_type(input_ref.type))
    output_node_ref = TypedRef(name=output_ref.name, type=workflow_type(output_ref.type))
    # A WRITE Function's workflow is: PREPARE_ACTION (build the Action Contract
    # from domain config) -> EXECUTE_ACTION (full REHT/RACS/Gateway/Veritas/
    # BARO/Kernel boundary). Domain values never enter EXECUTE_ACTION raw.
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
        effect_type=EffectType.MOVE_MONEY if spec["action_type"] == "PAY" else EffectType.WRITE_INTERNAL,
        policies=NodePolicies(
            authority=IsaAuthority(capability=spec["capability"], scope=[]),
            idempotency=__import__("valo_workflow_isa").contracts.IdempotencyPolicy(require_key=True) if spec.get("idempotency", IdempotencyRequirement.NONE) != IdempotencyRequirement.NONE else __import__("valo_workflow_isa").contracts.IdempotencyPolicy(),
        ),
        config={**config, "action_type": spec["action_type"]},
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
        effects=["MOVE_MONEY"] if spec["action_type"] == "PAY" else ["WRITE_INTERNAL"],
        risk=spec["risk"],
        autonomy=spec["autonomy"],
        authority=[__import__("valo_function_fabric").contracts.AuthorityRequirement(capability=spec["capability"], scope=["*"])],
        idempotency=spec.get("idempotency", IdempotencyRequirement.NONE),
    )
    validate_function_definition(definition, workflow)
    registry.register(definition, workflow)


CORE_REUSE_CHECK = [
    "valo.identity.verify_identity",
    "valo.evidence.verify",
    "valo.evidence.request",
    "valo.resource.match",
    "valo.resource.reserve",
    "valo.coordination.schedule",
    "valo.finance.price",
    "valo.decision.approve",
    "valo.communication.notify",
    "valo.finance.invoice",
]
