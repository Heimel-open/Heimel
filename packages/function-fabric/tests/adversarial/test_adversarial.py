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
    CompileError,
    FunctionDefinition,
    RiskClass,
    TypeRef,
    can_consume,
    compile_function_graph,
)
from valo_function_fabric.compiler import validate_function_definition
from valo_function_fabric.packs import PackError, apply_pack, country_pack


def _profile() -> AutonomyProfile:
    return AutonomyProfile(allowed_autonomy_levels=[AutonomyLevel.HUMAN, AutonomyLevel.STEP_UP], default_autonomy_level=AutonomyLevel.STEP_UP)


def _make_definition(function_id="valo.pack.tightened", workflow_ref="wf.valo.finance.price", effects=("PURE",), autonomy=None) -> FunctionDefinition:
    return FunctionDefinition(
        function_id=function_id, name="X", version="1.0.0",
        input_type=TypeRef(name="scope", type="PriceScope"),
        output_type=TypeRef(name="price", type="Calculated<Price>"),
        workflow_ref=workflow_ref,
        effects=list(effects),
        risk_class=RiskClass.R1_REVERSIBLE_ADMINISTRATIVE,
        autonomy_profile=autonomy or _profile(),
        authority_requirements=[],
        status="ACTIVE",
    )


def test_function_refers_to_nonexistent_workflow(stdlib_registry) -> None:
    """A Function whose workflow_ref has no graph must fail at compile time."""
    stdlib_registry._graphs.pop("wf.valo.finance.price")  # white-box: dangle the ref
    snapshot = stdlib_registry.snapshot()
    g = graph(
        "adv.ghost",
        [call("a", "valo.finance.price", input_bindings={"scope": "scope"})],
        inputs={"scope": "PriceScope"}, outputs={"price": "Calculated<Price>"},
    )
    with pytest.raises(Exception, match="no registered workflow"):
        compile_function_graph(g, snapshot)


def test_function_declares_pure_compiles_write() -> None:
    node = WorkflowNode(
        id="w", opcode="EXECUTE_ACTION", node_class=NodeClass.WRITE,
        inputs=[TypedRef(name="x", type="x")], outputs=[TypedRef(name="y", type="any")],
        effect_type=EffectType.MOVE_MONEY,
        policies=IsaNodePolicies(authority=IsaAuthority(capability="PAY", scope=[]), idempotency=IsaIdempotency(require_key=True)),
        config={"target": "t", "actor": "a"},
    )
    wf = WorkflowGraph(id="wf.hidden", version="1", input_schema={"x": "x"}, output_schema={"y": "any"}, nodes=[node], edges=[], entry="w", terminal_states=["w"])
    definition = _make_definition(function_id="valo.pack.hidden", workflow_ref="wf.hidden", effects=["PURE"])
    from valo_function_fabric import EffectsError

    with pytest.raises(EffectsError, match="undeclared"):
        validate_function_definition(definition, wf)


def test_pack_weakens_evidence_rejected(stdlib_registry) -> None:
    from valo_function_fabric.contracts import Pack, PackRule

    pack = Pack(
        pack="weaken", version="1.0.0",
        rules=[PackRule(constraint_type="WEAKEN", subject="pay", predicate="weaken evidence", severity="REQUIRED")],
    )
    with pytest.raises(PackError, match="tighten"):
        apply_pack(stdlib_registry, pack)


def test_pack_expands_autonomy_rejected(stdlib_registry) -> None:
    from valo_function_fabric.contracts import Pack

    # APPROVE (valo.decision.approve) allows only HUMAN/RECOMMEND/STEP_UP;
    # a pack that expands it to AUTO_EXECUTE must be rejected.
    expanded = _make_definition(
        function_id="valo.decision.approve",
        workflow_ref="wf.valo.decision.approve",
        autonomy=AutonomyProfile(
            allowed_autonomy_levels=[AutonomyLevel.HUMAN, AutonomyLevel.RECOMMEND, AutonomyLevel.STEP_UP, AutonomyLevel.AUTO_EXECUTE],
            default_autonomy_level=AutonomyLevel.AUTO_EXECUTE,
        ),
    )
    pack = Pack(pack="expands", version="1.0.0", functions=[expanded])
    with pytest.raises(PackError, match="weakens governance"):
        apply_pack(stdlib_registry, pack)


def test_pack_can_tighten(stdlib_registry) -> None:
    from valo_function_fabric.contracts import Pack

    tightened = _make_definition(
        function_id="valo.finance.price",
        autonomy=AutonomyProfile(allowed_autonomy_levels=[AutonomyLevel.HUMAN], default_autonomy_level=AutonomyLevel.HUMAN),
    ).model_copy(update={"version": "1.0.1"})
    pack = Pack(pack="tightens", version="1.0.0", functions=[tightened])
    assert apply_pack(stdlib_registry, pack) == 1
    assert stdlib_registry.resolve("valo.finance.price").version == "1.0.1"


def test_pack_cannot_bypass_reht() -> None:
    node = WorkflowNode(
        id="w", opcode="EXECUTE_ACTION", node_class=NodeClass.WRITE,
        inputs=[TypedRef(name="x", type="x")], outputs=[TypedRef(name="y", type="any")],
        effect_type=EffectType.MOVE_MONEY,  # WRITE WITHOUT authority -> ISA rejects
        config={"target": "t", "actor": "a"},
    )
    wf = WorkflowGraph(id="wf.bypass", version="1", input_schema={"x": "x"}, output_schema={"y": "any"}, nodes=[node], edges=[], entry="w", terminal_states=["w"])
    definition = _make_definition(function_id="valo.pack.bypass", workflow_ref="wf.bypass", effects=["MOVE_MONEY"])
    from valo_function_fabric import CompileError

    with pytest.raises(CompileError):
        validate_function_definition(definition, wf)


def test_country_pack_extension_point() -> None:
    no_pack = country_pack("no")
    assert no_pack.mappings["jurisdiction"] == "NO"
    se_pack = country_pack("se")
    assert se_pack.mappings["jurisdiction"] == "SE"


def test_deprecated_function_pinning(stdlib_registry) -> None:
    stdlib_registry.deprecate("valo.finance.price", "1.0.0")
    snapshot = stdlib_registry.snapshot()
    assert snapshot.current_version("valo.finance.price") is None
    # explicit pin still resolves the deprecated version (explicit opt-in)
    assert snapshot.resolve("valo.finance.price", "1.0.0") is not None


def test_raw_supplied_as_verified_rejected() -> None:
    assert not can_consume("BankAccount", "Verified<Account>")


def test_inferred_supplied_as_confirmed_rejected() -> None:
    assert not can_consume("Inferred<Payment>", "Confirmed<Payment>")


def test_gateway_success_not_verified_effect() -> None:
    assert not can_consume("GatewaySuccess<Payment>", "VerifiedEffect<Payment>")


def test_unknown_jurisdiction_rejected() -> None:
    definition = _make_definition(function_id="valo.finance.price")
    bad = definition.model_copy(update={"jurisdiction_constraints": [__import__("valo_function_fabric").contracts.JurisdictionRef(country="XX")]})
    with pytest.raises(CompileError, match="jurisdiction"):
        validate_function_definition(bad, __import__("valo_function_fabric").stdlib.helpers.leaf_workflow(
            "wf.valo.finance.price", node_id="calc", opcode="CALCULATE", node_class=NodeClass.COMPUTE,
            input_refs=[TypeRef(name="scope", type="PriceScope")],
            output_refs=[TypeRef(name="price", type="Calculated<Price>")],
            effect=EffectType.PURE, capability=None,
        ))


def test_recursive_function_loop_rejected(snapshot, stdlib_registry) -> None:
    g = graph(
        "adv.recursive",
        [call("a", "valo.finance.price", input_bindings={"scope": "scope"})],
        inputs={"scope": "PriceScope"}, outputs={"price": "Calculated<Price>"},
    )
    # add a self-loop edge -> recursive composition without bound
    from valo_function_fabric.contracts import FunctionEdge

    g = g.model_copy(update={"edges": g.edges + [FunctionEdge(source="a", target="a")]})
    with pytest.raises(CompileError, match="recursive"):
        compile_function_graph(g, snapshot)


def test_unknown_input_binding_rejected(snapshot, stdlib_registry) -> None:
    from valo_function_fabric.compiler.errors import TypecheckError

    g = graph(
        "adv.unknown_input_binding",
        [call("a", "valo.finance.price", input_bindings={"scope": "scope", "extraneous_param": "root"})],
        inputs={"scope": "PriceScope", "root": "any"}, outputs={"price": "Calculated<Price>"},
    )
    with pytest.raises(TypecheckError, match="unknown input binding"):
        compile_function_graph(g, snapshot)


def test_unknown_output_binding_rejected(snapshot, stdlib_registry) -> None:
    from valo_function_fabric.compiler.errors import TypecheckError

    g = graph(
        "adv.unknown_output_binding",
        [call("a", "valo.finance.price", input_bindings={"scope": "scope"}, output_bindings={"bogus_out": "price"})],
        inputs={"scope": "PriceScope"}, outputs={"price": "Calculated<Price>"},
    )
    with pytest.raises(TypecheckError, match="unknown output binding"):
        compile_function_graph(g, snapshot)


def test_unreachable_node_rejected(snapshot, stdlib_registry) -> None:
    g = graph(
        "adv.unreachable_node",
        [
            call("a", "valo.finance.price", input_bindings={"scope": "scope"}),
            call("b", "valo.finance.price", input_bindings={"scope": "scope"}),
        ],
        inputs={"scope": "PriceScope"}, outputs={"price": "Calculated<Price>"},
        entry_nodes=["a"], terminal_nodes=["a"],
    )
    # Node 'b' is not reachable from 'a'
    with pytest.raises(CompileError, match="unreachable"):
        compile_function_graph(g, snapshot)


def test_node_cannot_reach_terminal_rejected(snapshot, stdlib_registry) -> None:
    from valo_function_fabric.contracts import FunctionEdge

    g = graph(
        "adv.dead_end_node",
        [
            call("a", "valo.finance.price", input_bindings={"scope": "scope"}),
            call("b", "valo.finance.price", input_bindings={"scope": "scope"}),
        ],
        inputs={"scope": "PriceScope"}, outputs={"price": "Calculated<Price>"},
        entry_nodes=["a"], terminal_nodes=["a"],
    )
    # a -> b, but b is not in terminal_nodes and has no path to a terminal node
    g = g.model_copy(update={"edges": [FunctionEdge(source="a", target="b")]})
    with pytest.raises(CompileError, match="cannot reach any terminal node"):
        compile_function_graph(g, snapshot)


def test_empty_terminal_nodes_rejected() -> None:
    from valo_function_fabric.contracts import FunctionGraph

    with pytest.raises(ValueError, match="terminal_nodes is required"):
        FunctionGraph(
            graph_id="adv.no_terminals", version="1",
            inputs={"scope": "PriceScope"}, outputs={"price": "Calculated<Price>"},
            nodes=[call("a", "valo.finance.price", input_bindings={"scope": "scope"})],
            edges=[], entry_nodes=["a"], terminal_nodes=[],
        )


def test_compiled_function_provenance_verification(snapshot, stdlib_registry) -> None:
    g = graph(
        "adv.provenance",
        [call("a", "valo.finance.price", input_bindings={"scope": "scope"})],
        inputs={"scope": "PriceScope"}, outputs={"price": "Calculated<Price>"},
    )
    compiled = compile_function_graph(g, snapshot)
    assert compiled.verify_provenance(snapshot) is True

    # Tampered workflow graph
    from valo_workflow_isa.contracts import WorkflowGraph as IsaWorkflowGraph

    tampered_wf = IsaWorkflowGraph.model_validate(compiled.workflow_graph.model_dump())
    tampered_wf = tampered_wf.model_copy(update={"version": "999"})
    tampered_compiled = __import__("dataclasses").replace(compiled, workflow_graph=tampered_wf)
    assert tampered_compiled.verify_provenance(snapshot) is False

    # Tampered snapshot
    assert compiled.verify_provenance(snapshot.model_copy(update={"hash": "tampered_hash"})) is False


def test_multi_node_intermediate_state_isolation(stdlib_registry) -> None:
    from valo_workflow_isa.contracts import WorkflowEdge, WorkflowNode

    from valo_function_fabric.contracts import FunctionGraph
    from valo_function_fabric.contracts.graph import FunctionEdge
    from valo_function_fabric.stdlib import AUTO_AUTONOMY
    from valo_function_fabric.stdlib.helpers import leaf_definition

    # Register a 2-node leaf function: step1 (entry) -> step2 (terminal)
    node1 = WorkflowNode(
        id="step1", opcode="CALCULATE", node_class=NodeClass.COMPUTE,
        inputs=[TypedRef(name="scope", type="PriceScope")],
        outputs=[TypedRef(name="interm", type="any")],
        effect_type=EffectType.PURE, policies=IsaNodePolicies(),
        config={"expression": "scope"},
    )
    node2 = WorkflowNode(
        id="step2", opcode="CALCULATE", node_class=NodeClass.COMPUTE,
        inputs=[TypedRef(name="interm", type="any")],
        outputs=[TypedRef(name="price", type="PriceScope")],
        effect_type=EffectType.PURE, policies=IsaNodePolicies(),
        config={"expression": "interm"},
    )
    wf_multi = WorkflowGraph(
        id="wf.demo.multi_step", version="1",
        input_schema={"scope": "PriceScope"}, output_schema={"price": "PriceScope"},
        nodes=[node1, node2],
        edges=[WorkflowEdge(source="step1", target="step2", edge_type="NEXT")],
        entry="step1", terminal_states=["step2"],
    )
    def_multi = leaf_definition(
        "valo.test.multi_step", "MULTI_STEP", "1.0.0",
        input_type=TypeRef(name="scope", type="PriceScope"),
        output_type=TypeRef(name="price", type="PriceScope"),
        workflow_graph=wf_multi,
        effects=["PURE"], risk=RiskClass.R1_REVERSIBLE_ADMINISTRATIVE,
        autonomy=AUTO_AUTONOMY,
    )
    stdlib_registry.register(def_multi, wf_multi)
    snapshot = stdlib_registry.snapshot()

    # Compose two sequential calls to valo.test.multi_step: call1 -> call2
    comp_graph = FunctionGraph(
        graph_id="graph.demo.two_multis", version="1",
        inputs={"in1": "PriceScope"},
        outputs={"res2": "PriceScope"},
        nodes=[
            call("c1", "valo.test.multi_step", input_bindings={"scope": "in1"}, output_bindings={"price": "c1_out"}),
            call("c2", "valo.test.multi_step", input_bindings={"scope": "c1"}, output_bindings={"price": "res2"}),
        ],
        edges=[FunctionEdge(source="c1", target="c2")],
        entry_nodes=["c1"], terminal_nodes=["c2"],
    )
    compiled = compile_function_graph(comp_graph, snapshot)
    nodes_by_id = {n.id: n for n in compiled.workflow_graph.nodes}

    # Verify that intermediate variables are strictly call-prefixed
    assert nodes_by_id["c1.step1"].outputs[0].name == "c1.interm"
    assert nodes_by_id["c1.step2"].inputs[0].name == "c1.interm"
    assert nodes_by_id["c2.step1"].outputs[0].name == "c2.interm"
    assert nodes_by_id["c2.step2"].inputs[0].name == "c2.interm"

    # External wiring between calls and terminal output
    assert nodes_by_id["c1.step1"].inputs[0].name == "in1"
    assert nodes_by_id["c1.step2"].outputs[0].name == "c1_out"
    assert nodes_by_id["c2.step1"].inputs[0].name == "c1_out"
    assert nodes_by_id["c2.step2"].outputs[0].name == "res2"


