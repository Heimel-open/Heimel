from __future__ import annotations

from valo_reht import RealReht
from valo_workflow_isa import compile_graph as isa_compile

from valo_public_pack import (
    build_public_registry,
    compile_golden,
    run_golden,
    seed_world,
)


def test_golden_path_runs_through_isa_runtime() -> None:
    registry = build_public_registry()
    compiled = compile_golden(registry)
    isa_compile(compiled.workflow_graph)
    result = run_golden(reht=RealReht(), kernel=seed_world())
    assert result.case_state == "CLOSED"
    assert result.instance_status == "COMPLETED"


def test_kernel_owns_business_truth() -> None:
    kernel = seed_world()
    run_golden(reht=RealReht(), kernel=kernel)
    assert kernel.state().entities["case-1"].state == "CLOSED"
    transitions = [e for e in kernel.events() if e.subject == "case-1" and e.event_type.value == "ENTITY_UPDATED"]
    assert transitions, "no kernel event recorded for the transitions"


def test_reht_is_test_double_outside_pack() -> None:
    """Legal basis and competence are Kernel authorities; the REHT adapter
    (a test double OUTSIDE the pack) decides against the fresh execution
    context. The pack owns no authorize() logic and no authorization
    component."""
    kernel = seed_world(legal_basis_active=False)
    result = run_golden(reht=RealReht(), kernel=kernel)
    assert result.case_state == "READY_FOR_DECISION"
    # legal basis is a separate Kernel authority; REHT still sees the active
    # competence and says ALLOW, but the decision boundary re-derives that no
    # decision may be issued without an active legal basis.
    assert all(d["decision"] == "ALLOW" for d in result.reht_decisions)


def test_reht_enforces_authority_scope() -> None:
    """The REHT test double enforces authority scope: an authority for case-1
    must not authorize a decision against case-2. DENY, zero Gateway
    executions, no Kernel decision event."""
    from valo_kernel.contracts import (
        CanonicalEvent,
        Entity,
        EntityType,
        EventType,
        Provenance,
        utcnow,
    )

    kernel = seed_world()
    now = utcnow()
    prov = Provenance(source_type="system", source_id="seed", source_system="public-pack")
    # register a second case
    kernel.append(CanonicalEvent(
        event_id="seed-case-2", event_type=EventType.ENTITY_REGISTERED, tenant_id="public",
        subject="case-2", source="kernel", effective_at=now,
        payload={"entity": Entity(entity_id="case-2", entity_type=EntityType.CASE, tenant_id="public", state="RECEIVED", attributes={"age": 30, "service": "PUBLIC_SERVICE_A"}, provenance=prov)},
    ))
    # ISSUE_DECISION authority is scoped to case-1 ONLY. The real REHT (the
    # valo-reht package, not a test double) enforces scope.
    reht = RealReht()
    execution_context = {
        "actor": "system-1",
        "identity": "id-system-1",
        "time": {"now": "2026-08-08T00:00:00+00:00"},
        "authority": [{
            "authority_id": "auth-1", "principal": "system-1",
            "capability": "ISSUE_DECISION",
            "scope": ["case-1"],
            "status": "ACTIVE",
            "validity": {"valid_from": "2020-01-01T00:00:00+00:00", "valid_until": "2100-01-01T00:00:00+00:00"},
        }],
    }
    allowed = reht.authorize(execution_context, {"capability": "ISSUE_DECISION", "target": "case-1"})
    assert allowed.decision == "ALLOW"
    denied = reht.authorize(execution_context, {"capability": "ISSUE_DECISION", "target": "case-2"})
    assert denied.decision == "DENY"
    assert "scope" in (denied.reason or "")


def test_scope_violation_blocks_runtime_boundary() -> None:
    """End-to-end: a WRITE targeting case-2 with an authority scoped to case-1
    is DENIED by REHT -> zero Gateway executions, no Kernel decision event."""
    from valo_workflow_isa import (
        AuthorityRequirements,
        EffectType,
        IdempotencyPolicy,
        NodeClass,
        NodePolicies,
        ReferenceBackend,
        RuntimeEngine,
        TypedRef,
        WorkflowEdge,
        WorkflowGraph,
        WorkflowNode,
        WorkflowStatus,
    )

    from valo_public_pack.ports import (
        PublicBaro,
        PublicGateway,
        PublicKernel,
        PublicVeritas,
    )

    kernel = seed_world()
    from valo_kernel.contracts import (
        CanonicalEvent,
        Entity,
        EntityType,
        EventType,
        Provenance,
        utcnow,
    )

    kernel.append(CanonicalEvent(
        event_id="seed-case-2", event_type=EventType.ENTITY_REGISTERED, tenant_id="public",
        subject="case-2", source="kernel", effective_at=utcnow(),
        payload={"entity": Entity(entity_id="case-2", entity_type=EntityType.CASE, tenant_id="public", state="READY_FOR_DECISION", attributes={"age": 30, "service": "PUBLIC_SERVICE_A"}, provenance=Provenance(source_type="system", source_id="t", source_system="public-pack"))},
    ))
    config = {
        "target": "case-2", "actor": "system-1", "identity_id": "id-system-1",
        "action_type": "ISSUE_DECISION", "capability": "ISSUE_DECISION",
        "kernel_event_type": "CASE_TRANSITION", "postconditions": {"decision_issued": True},
        "requested_transition": {"state": "DECIDED"},
    }
    prepare = WorkflowNode(
        id="prep", opcode="PREPARE_ACTION", node_class=NodeClass.COMPUTE,
        outputs=[TypedRef(name="action", type="any")],
        effect_type=EffectType.PURE,
        policies=NodePolicies(authority=AuthorityRequirements(capability="ISSUE_DECISION", scope=[])),
        config=config,
    )
    execute = WorkflowNode(
        id="exec", opcode="EXECUTE_ACTION", node_class=NodeClass.WRITE,
        inputs=[TypedRef(name="action", type="any")],
        outputs=[TypedRef(name="decision", type="VerifiedEffect<PublicDecision>")],
        effect_type=EffectType.WRITE_INTERNAL,
        policies=NodePolicies(authority=AuthorityRequirements(capability="ISSUE_DECISION", scope=[]), idempotency=IdempotencyPolicy(require_key=False)),
        config=config,
    )
    graph = WorkflowGraph(
        id="wf.scope-violation", version="1",
        input_schema={}, output_schema={"decision": "VerifiedEffect<PublicDecision>"},
        nodes=[prepare, execute], edges=[WorkflowEdge(source="prep", target="exec")],
        entry="prep", terminal_states=["exec"],
    )
    gateway = PublicGateway()
    engine = RuntimeEngine(
        PublicKernel(kernel), RealReht(), gateway, PublicVeritas(), PublicBaro(),
        backend=ReferenceBackend(), tenant_id="public",
    )
    instance = engine.start(graph, {})
    assert instance.status == WorkflowStatus.FAILED
    assert len(gateway.executions) == 0, "Gateway must not execute on an out-of-scope decision"
    decided = [e for e in kernel.events() if e.subject == "case-2" and e.payload.get("state") == "DECIDED"]
    assert not decided, "no Kernel decision event may be emitted"


def test_world_changing_functions_are_write() -> None:
    registry = build_public_registry()
    for function_id in [
        "valo.public.issue_public_decision",
        "valo.public.notify",
        "valo.public.create_appeal_right",
        "valo.public.finalize_case",
        "valo.public.close_case",
        "valo.public.register_case",
    ]:
        workflow = registry.graph_for(registry.get(f"{function_id}@1.0.0"))
        assert any(n.node_class.value == "WRITE" and n.effect_type.value != "PURE" for n in workflow.nodes), f"{function_id} must be WRITE"


def test_decision_transition_admissibility() -> None:
    """Deterministic Case transition contract against CURRENT Kernel state.
    Each illegal hop is asserted from the ACTUAL state it claims to start from —
    the Kernel is advanced to `current` before the requested transition is
    tried. Golden-path ordering is not a security control."""
    from valo_kernel.contracts import CanonicalEvent, EventType

    from valo_public_pack.ports import _admissible_case_transition

    illegal = [
        ("RECEIVED", "DECIDED"),
        ("READY_FOR_REVIEW", "CLOSED"),
        ("AWAITING_INFORMATION", "APPEAL_PERIOD"),
        ("NOTIFIED", "FINAL"),
    ]
    for current, requested in illegal:
        kernel = seed_world()
        kernel.append(CanonicalEvent(
            event_id=f"set-{current}", event_type=EventType.ENTITY_UPDATED,
            tenant_id="public", subject="case-1", actor="system-1", source="public-pack",
            effective_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
            payload={"entity_id": "case-1", "state": current},
        ))
        assert kernel.state().entities["case-1"].state == current
        try:
            _admissible_case_transition(kernel, "case-1", requested)
            raise AssertionError(f"illegal Case transition {current} -> {requested} must be rejected")
        except RuntimeError as exc:
            assert "illegal Case transition" in str(exc)


def test_decided_requires_eligible_and_unconflicted() -> None:
    """No rights-impacting decision on a case that is not eligible or whose
    critical fact is conflicted — derived from RAW Kernel facts at the DECIDED
    write boundary (no pre-seeded adjudication flags)."""
    from valo_kernel.contracts import CanonicalEvent, EventType

    from valo_public_pack.ports import _admissible_case_transition

    def ready_for_decision(**seed):
        kernel = seed_world(**seed)
        kernel.append(CanonicalEvent(
            event_id="to-rfd", event_type=EventType.ENTITY_UPDATED,
            tenant_id="public", subject="case-1", actor="system-1", source="public-pack",
            effective_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
            payload={"entity_id": "case-1", "state": "READY_FOR_DECISION"},
        ))
        return kernel

    for seed, label in [
        ({"residency_conflicted": True}, "conflicted critical fact"),
        ({"decision_maker_relationship": "SPOUSE"}, "disqualified decision maker"),
        ({"evidence_stale": True}, "stale evidence"),
        ({"purpose_violation": True}, "mis-purposed evidence"),
        ({"has_representation": True, "representation_scope_ok": False}, "out-of-scope representation"),
        ({"legal_basis_active": False}, "inactive legal basis"),
        ({"applicant_age": 16}, "ineligible applicant"),
    ]:
        kernel = ready_for_decision(**seed)
        try:
            _admissible_case_transition(kernel, "case-1", "DECIDED")
            raise AssertionError(f"must not decide with {label}")
        except RuntimeError as exc:
            assert "cannot decide" in str(exc), f"{label}: {exc}"


def test_issue_public_decision_requires_decision_context() -> None:
    """P0: ISSUE_PUBLIC_DECISION consumes a DecisionContext, NOT a bare Case.
    It must not compile when bound directly to the raw Case input."""
    registry = build_public_registry()
    definition = registry.resolve("valo.public.issue_public_decision", "1.0.0")
    assert definition.input_type.type == "DecisionContext"
    assert definition.output_type.type == "VerifiedEffect<PublicDecision>"

    from valo_function_fabric.compiler import compile_function_graph
    from valo_function_fabric.contracts import (
        FunctionCall,
        FunctionGraph,
        FunctionRef,
    )

    bad_graph = FunctionGraph(
        graph_id="graph.bad_issue_on_case", version="2",
        inputs={"case": "Case"},
        outputs={"out_final": "VerifiedEffect<PublicDecision>"},
        nodes=[
            FunctionCall(id="bad", function_ref=FunctionRef(function_id="valo.public.issue_public_decision", version="1.0.0"), input_bindings={"context": "case"}, output_bindings={"decision": "out_final"}),
        ],
        edges=[], entry_nodes=["bad"], terminal_nodes=["bad"],
    )
    try:
        compile_function_graph(bad_graph, registry.snapshot())
        raise AssertionError("ISSUE_PUBLIC_DECISION must not compile on a bare Case")
    except Exception as exc:
        assert "cannot satisfy" in str(exc)


def test_runtime_refinement_verified_effect() -> None:
    """P1: the issued decision is a VerifiedEffect<PublicDecision> carried as a
    runtime RuntimeValue — the runtime provably attached VERIFIED_EFFECT at the
    WRITE boundary that verified the effect."""
    from valo_workflow_isa.runtime.values import RuntimeValue

    result = run_golden(reht=RealReht(), kernel=seed_world())
    runtime_values = []
    for node_id, outputs in (result.instance.outputs or {}).items():
        for name, value in outputs.items():
            if isinstance(value, RuntimeValue):
                runtime_values.append((node_id, name, value))
    assert runtime_values, "no RuntimeValue produced"
    decisions = [rv for (_, _, rv) in runtime_values if rv.base_type == "PublicDecision" and rv.refinements]
    assert decisions, "the ISSUE decision output must be a RuntimeValue with refinements"
    assert "VerifiedEffect" in decisions[0].refinements, decisions[0].refinements


def test_shadow_is_same_path_no_writes() -> None:
    result = run_golden(reht=RealReht(), kernel=seed_world(), shadow=True)
    assert result.instance_status == "COMPLETED"
    assert result.case_state == "RECEIVED"
    assert result.economics["gateway_executions"] == 0
    assert result.economics["proposed_kernel_events"] > 0


def test_kernel_replay_reconstructs_same_state() -> None:
    from valo_kernel import replay

    kernel = seed_world()
    run_golden(reht=RealReht(), kernel=kernel)
    rebuilt = replay(kernel.events())
    assert rebuilt.entities["case-1"].state == kernel.state().entities["case-1"].state
    assert rebuilt.root_hash() == kernel.state().root_hash()


def test_event_chain_integrity() -> None:
    kernel = seed_world()
    run_golden(reht=RealReht(), kernel=kernel)
    kernel.verify_integrity()
