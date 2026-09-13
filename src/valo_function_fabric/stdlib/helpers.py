from __future__ import annotations

from typing import Any

from valo_workflow_isa.contracts import (
    AuthorityRequirements as IsaAuthority,
)
from valo_workflow_isa.contracts import (
    EffectType,
    NodeClass,
    TypedRef,
    WorkflowGraph,
    WorkflowNode,
)
from valo_workflow_isa.contracts import (
    IdempotencyPolicy as IsaIdempotency,
)
from valo_workflow_isa.contracts import (
    NodePolicies as IsaNodePolicies,
)

from ..compiler import validate_function_definition
from ..contracts.common import IdempotencyRequirement, RiskClass
from ..contracts.function import (
    AuthorityRequirement,
    AutonomyProfile,
    EvidenceRequirement,
    FunctionDefinition,
    PurposeRequirement,
    RightsRequirement,
    TypeRef,
)
from ..registry.store import FunctionRegistry
from ..types.strength import workflow_type


def node_ref(name: str, type_expr: str) -> TypedRef:
    return TypedRef(name=name, type=workflow_type(type_expr))


def idempotency_policy(requirement: IdempotencyRequirement) -> IsaIdempotency:
    if requirement == IdempotencyRequirement.REQUIRED:
        return IsaIdempotency(require_key=True)
    if requirement == IdempotencyRequirement.VERIFY_BEFORE_REPLAY:
        return IsaIdempotency(require_key=True, verify_before_replay=True)
    return IsaIdempotency()


def leaf_workflow(
    graph_id: str,
    *,
    node_id: str,
    opcode: str,
    node_class: NodeClass,
    input_refs: list[TypeRef],
    output_refs: list[TypeRef],
    effect: EffectType,
    capability: str | None,
    idempotency: IdempotencyRequirement = IdempotencyRequirement.NONE,
    config: dict[str, Any] | None = None,
) -> WorkflowGraph:
    policies = IsaNodePolicies()
    if node_class == NodeClass.WRITE:
        assert capability is not None, "WRITE nodes require a capability"
        policies = IsaNodePolicies(
            authority=IsaAuthority(capability=capability, scope=[]),
            idempotency=idempotency_policy(idempotency),
        )
    inputs = [node_ref(r.name, r.type) for r in input_refs]
    outputs = [node_ref(r.name, r.type) for r in output_refs]
    node = WorkflowNode(
        id=node_id,
        opcode=opcode,
        node_class=node_class,
        inputs=inputs,
        outputs=outputs,
        effect_type=effect,
        policies=policies,
        config=config or {},
    )
    return WorkflowGraph(
        id=graph_id,
        version="1",
        input_schema={ref.name: ref.type for ref in inputs},
        output_schema={ref.name: ref.type for ref in outputs},
        nodes=[node],
        edges=[],
        entry=node_id,
        terminal_states=[node_id],
    )


def leaf_definition(
    function_id: str,
    name: str,
    version: str,
    *,
    input_type: TypeRef,
    output_type: TypeRef,
    workflow_graph: WorkflowGraph,
    effects: list[str],
    risk: RiskClass,
    autonomy: AutonomyProfile,
    authority: list[AuthorityRequirement] | None = None,
    evidence: list[EvidenceRequirement] | None = None,
    rights: list[RightsRequirement] | None = None,
    purpose: list[PurposeRequirement] | None = None,
    idempotency: IdempotencyRequirement = IdempotencyRequirement.NONE,
    reversible: bool = False,
    jurisdiction: list | None = None,
) -> FunctionDefinition:
    return FunctionDefinition(
        function_id=function_id,
        name=name,
        version=version,
        input_type=input_type,
        output_type=output_type,
        workflow_ref=workflow_graph.id,
        effects=effects,
        risk_class=risk,
        autonomy_profile=autonomy,
        authority_requirements=authority or [],
        evidence_requirements=evidence or [],
        rights_requirements=rights or [],
        purpose_requirements=purpose or [],
        jurisdiction_constraints=jurisdiction or [],
        reversible=reversible,
        idempotency_requirement=idempotency,
        status="ACTIVE",
    )


def register_leaf(registry: FunctionRegistry, definition: FunctionDefinition, workflow_graph: WorkflowGraph) -> None:
    validate_function_definition(definition, workflow_graph)
    registry.register(definition, workflow_graph)
