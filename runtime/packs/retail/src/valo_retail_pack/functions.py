from __future__ import annotations

from valo_function_fabric.compiler import validate_function_definition
from valo_function_fabric.contracts import (
    AutonomyLevel,
    AutonomyProfile,
    AuthorityRequirement,
    IdempotencyRequirement,
    RiskClass,
    TypeRef,
)
from valo_function_fabric.registry import FunctionRegistry
from valo_function_fabric.stdlib import build_stdlib
from valo_function_fabric.stdlib.helpers import leaf_definition
from valo_function_fabric.types import workflow_type
from valo_workflow_isa.contracts import (
    AuthorityRequirements as IsaAuthority,
    EffectType,
    IdempotencyPolicy,
    NodeClass,
    NodePolicies,
    TypedRef,
    WorkflowEdge,
    WorkflowGraph,
    WorkflowNode,
)

PORTFOLIO_TARGET = "vehicle-export-portfolio"
AGENT_ACTOR = "vehicle-export-agent"
AGENT_IDENTITY = "id-vehicle-export-agent"
CAPABILITY = "VEHICLE_TRADE"

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


def build_retail_registry() -> FunctionRegistry:
    """Core stdlib plus six vehicle-trade effects.

    Candidate selection and economics remain pack admissibility. Once admitted,
    every real-world effect is a registered Function that enters the unchanged
    Workflow ISA -> fresh REHT -> Gateway -> Veritas/BARO -> Kernel path.
    """
    registry = build_stdlib()
    specs = (
        (
            "valo.retail.vehicle_purchase",
            "VEHICLE_PURCHASE",
            "RETAIL_VEHICLE_PURCHASE",
            EffectType.MOVE_MONEY,
            RiskClass.R3_FINANCIAL_LEGAL,
            "vehicle_purchase_verified",
        ),
        (
            "valo.retail.vehicle_book_transport",
            "VEHICLE_BOOK_TRANSPORT",
            "RETAIL_VEHICLE_BOOK_TRANSPORT",
            EffectType.CREATE_OBLIGATION,
            RiskClass.R2_OPERATIONAL,
            "vehicle_transport_verified",
        ),
        (
            "valo.retail.vehicle_export",
            "VEHICLE_EXPORT",
            "RETAIL_VEHICLE_EXPORT",
            EffectType.COMMUNICATE,
            RiskClass.R3_FINANCIAL_LEGAL,
            "vehicle_export_verified",
        ),
        (
            "valo.retail.vehicle_list_sale",
            "VEHICLE_LIST_SALE",
            "RETAIL_VEHICLE_LIST_SALE",
            EffectType.COMMUNICATE,
            RiskClass.R2_OPERATIONAL,
            "vehicle_sale_verified",
        ),
        (
            "valo.retail.vehicle_accept_sale",
            "VEHICLE_ACCEPT_SALE",
            "RETAIL_VEHICLE_ACCEPT_SALE",
            EffectType.CREATE_OBLIGATION,
            RiskClass.R3_FINANCIAL_LEGAL,
            "vehicle_sale_verified",
        ),
        (
            "valo.retail.vehicle_settle_sale",
            "VEHICLE_SETTLE_SALE",
            "RETAIL_VEHICLE_SETTLE_SALE",
            EffectType.CHANGE_RIGHT,
            RiskClass.R3_FINANCIAL_LEGAL,
            "vehicle_sale_verified",
        ),
    )
    for fid, name, action_type, effect, risk, effect_key in specs:
        _register_vehicle_write(
            registry,
            fid=fid,
            name=name,
            action_type=action_type,
            effect=effect,
            risk=risk,
            effect_key=effect_key,
        )
    return registry


def _register_vehicle_write(
    registry: FunctionRegistry,
    *,
    fid: str,
    name: str,
    action_type: str,
    effect: EffectType,
    risk: RiskClass,
    effect_key: str,
) -> None:
    graph_id = f"wf.{fid}"
    input_ref = _t("vehicle_trade", "VehicleTradeRequest")
    output_ref = _t("effect", "VerifiedEffect<VehicleTradeEffect>")
    input_node_ref = TypedRef(name=input_ref.name, type=workflow_type(input_ref.type))
    output_node_ref = TypedRef(name=output_ref.name, type=workflow_type(output_ref.type))
    common = {
        "target": PORTFOLIO_TARGET,
        "actor": AGENT_ACTOR,
        "identity_id": AGENT_IDENTITY,
        "action_type": action_type,
        "capability": CAPABILITY,
        "kernel_event_type": "EXTERNAL_EFFECT_OBSERVED",
        "postconditions": {effect_key: True},
        "requested_transition": {},
    }
    prepare = WorkflowNode(
        id="prepare",
        opcode="PREPARE_ACTION",
        node_class=NodeClass.COMPUTE,
        inputs=[input_node_ref],
        outputs=[TypedRef(name="action", type="any")],
        effect_type=EffectType.PURE,
        policies=NodePolicies(
            authority=IsaAuthority(capability=CAPABILITY, scope=[]),
        ),
        config=common,
    )
    execute = WorkflowNode(
        id="execute",
        opcode="EXECUTE_ACTION",
        node_class=NodeClass.WRITE,
        inputs=[TypedRef(name="action", type="any")],
        outputs=[output_node_ref],
        effect_type=effect,
        policies=NodePolicies(
            authority=IsaAuthority(capability=CAPABILITY, scope=[]),
            idempotency=IdempotencyPolicy(
                require_key=True,
                verify_before_replay=True,
            ),
        ),
        config=common,
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
        fid,
        name,
        "1.0.0",
        input_type=input_ref,
        output_type=output_ref,
        workflow_graph=workflow,
        effects=[effect.value],
        risk=risk,
        autonomy=_AUTO,
        authority=[AuthorityRequirement(capability=CAPABILITY, scope=[PORTFOLIO_TARGET])],
        idempotency=IdempotencyRequirement.VERIFY_BEFORE_REPLAY,
    )
    validate_function_definition(definition, workflow)
    registry.register(definition, workflow)


VEHICLE_FUNCTION_IDS = (
    "valo.retail.vehicle_purchase",
    "valo.retail.vehicle_book_transport",
    "valo.retail.vehicle_export",
    "valo.retail.vehicle_list_sale",
    "valo.retail.vehicle_accept_sale",
    "valo.retail.vehicle_settle_sale",
)
