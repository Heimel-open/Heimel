from __future__ import annotations

import pytest
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

from tests.helpers import call, graph
from valo_function_fabric import (
    AutonomyLevel,
    AutonomyProfile,
    EffectsError,
    FunctionDefinition,
    GovernanceError,
    RiskClass,
    TypeRef,
    compile_function_graph,
)
from valo_function_fabric.compiler import validate_function_definition


def _profile() -> AutonomyProfile:
    return AutonomyProfile(
        allowed_autonomy_levels=[AutonomyLevel.HUMAN, AutonomyLevel.STEP_UP],
        default_autonomy_level=AutonomyLevel.STEP_UP,
    )


def _write_graph() -> WorkflowGraph:
    node = WorkflowNode(
        id="w", opcode="EXECUTE_ACTION", node_class=NodeClass.WRITE,
        inputs=[TypedRef(name="payment", type="PaymentRequest")],
        outputs=[TypedRef(name="payment_result", type="any")],
        effect_type=EffectType.MOVE_MONEY,
        policies=IsaNodePolicies(
            authority=IsaAuthority(capability="PAY", scope=[]),
            idempotency=IsaIdempotency(require_key=True, verify_before_replay=True),
        ),
        config={"target": "x", "actor": "a", "action_type": "PAY"},
    )
    return WorkflowGraph(id="wf.bad", version="1", input_schema={"payment": "PaymentRequest"}, output_schema={"payment_result": "any"}, nodes=[node], edges=[], entry="w", terminal_states=["w"])


def test_function_declares_pure_but_compiles_write() -> None:
    """Golden invariant: a Function declaring only PURE must never compile a
    MOVE_MONEY WRITE."""
    definition = FunctionDefinition(
        function_id="valo.test.hidden_write", name="HIDDEN_WRITE", version="1.0.0",
        input_type=TypeRef(name="payment", type="PaymentRequest"),
        output_type=TypeRef(name="payment_result", type="VerifiedEffect<Payment>"),
        workflow_ref="wf.bad",
        effects=["PURE"],
        risk_class=RiskClass.R1_REVERSIBLE_ADMINISTRATIVE,
        autonomy_profile=_profile(),
        status="ACTIVE",
    )
    with pytest.raises(EffectsError, match="undeclared"):
        validate_function_definition(definition, _write_graph())


def test_parent_must_cover_child_effects(snapshot, stdlib_registry) -> None:
    """Golden invariant (composition): parent effects must cover children. The
    parent here hides MOVE_MONEY that PAY produces."""
    g = graph(
        "governance.hidden_effect",
        [
            call("pay", "valo.finance.pay", input_bindings={"payment": "payment"}),
        ],
        inputs={"payment": "PaymentRequest"},
        outputs={"payment_result": "VerifiedEffect<Payment>"},
    )
    parent = FunctionDefinition(
        function_id="valo.test.parent", name="PARENT", version="1.0.0",
        input_type=TypeRef(name="payment", type="PaymentRequest"),
        output_type=TypeRef(name="payment_result", type="VerifiedEffect<Payment>"),
        workflow_ref="graph",
        effects=["PURE"],  # hides MOVE_MONEY
        risk_class=RiskClass.R3_FINANCIAL_LEGAL,
        autonomy_profile=_profile(),
        authority_requirements=[],
        status="ACTIVE",
    )
    with pytest.raises(EffectsError, match="not declared"):
        compile_function_graph(g, snapshot, parent_definition=parent)


def test_risk_cannot_decrease_through_composition(snapshot, stdlib_registry) -> None:
    """Governance monotonicity: parent risk must be >= max(risk(children))."""
    g = graph(
        "governance.risk_downgrade",
        [
            call("pay", "valo.finance.pay", input_bindings={"payment": "payment"}),
        ],
        inputs={"payment": "PaymentRequest"},
        outputs={"payment_result": "VerifiedEffect<Payment>"},
    )
    parent = FunctionDefinition(
        function_id="valo.test.parent", name="PARENT", version="1.0.0",
        input_type=TypeRef(name="payment", type="PaymentRequest"),
        output_type=TypeRef(name="payment_result", type="VerifiedEffect<Payment>"),
        workflow_ref="graph",
        effects=["MOVE_MONEY"],
        risk_class=RiskClass.R0_INFORMATIONAL,  # hides PAY's R3
        autonomy_profile=_profile(),
        authority_requirements=[],
        status="ACTIVE",
    )
    with pytest.raises(GovernanceError, match="risk"):
        compile_function_graph(g, snapshot, parent_definition=parent)


def test_autonomy_cannot_expand_through_composition(snapshot, stdlib_registry) -> None:
    g = graph(
        "governance.autonomy_expansion",
        [
            call("approve", "valo.decision.approve", input_bindings={"approval": "approval"}),
        ],
        inputs={"approval": "ApprovalRequest"},
        outputs={"attestation": "ApprovalAttestation"},
    )
    parent = FunctionDefinition(
        function_id="valo.test.parent", name="PARENT", version="1.0.0",
        input_type=TypeRef(name="approval", type="ApprovalRequest"),
        output_type=TypeRef(name="attestation", type="ApprovalAttestation"),
        workflow_ref="graph",
        effects=["PURE"],
        risk_class=RiskClass.R2_OPERATIONAL,
        autonomy_profile=AutonomyProfile(
            allowed_autonomy_levels=[AutonomyLevel.HUMAN, AutonomyLevel.RECOMMEND, AutonomyLevel.STEP_UP, AutonomyLevel.AUTO_EXECUTE],
            default_autonomy_level=AutonomyLevel.AUTO_EXECUTE,
        ),
        authority_requirements=[],
        status="ACTIVE",
    )
    with pytest.raises(GovernanceError, match="autonomy"):
        compile_function_graph(g, snapshot, parent_definition=parent)
