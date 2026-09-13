"""P0 proof: the deterministic Public admissibility check runs at the
PRE-EXECUTION boundary (fresh execution context), BEFORE REHT/Gateway. A
rights-impacting decision that the invariant rejects can NEVER reach the
Gateway — zero ISSUE_DECISION executions, no EFFECT_VERIFIED, no DECIDED event.
"""

from __future__ import annotations

from valo_reht import RealReht

from valo_public_pack import run_golden, seed_world


def _assert_decision_never_executed(result, kernel) -> None:
    assert result.case_state == "READY_FOR_DECISION"
    by_type = result.economics["executions_by_type"]
    assert by_type.get("ISSUE_DECISION", 0) == 0, f"ISSUE_DECISION must never reach the Gateway: {by_type}"
    # EFFECT_VERIFIED is a Workflow ISA event (Kernel has no such EventType):
    # read the workflow event stream and assert the ISSUE node (s15) never
    # verified an effect. Earlier administrative writes may verify.
    events = result.backend.events_for(result.instance.instance_id)
    issue_effect = [e for e in events if e.get("event_type") == "EffectVerified" and "s15" in (e.get("node_id") or "")]
    assert not issue_effect, "no EFFECT_VERIFIED may be emitted for a decision rejected pre-execution"
    decided = [e for e in kernel.events() if e.subject == "case-1" and e.payload.get("state") == "DECIDED"]
    assert not decided, "no DECIDED Kernel event may be emitted"


def test_pre_execution_inactive_legal_basis() -> None:
    kernel = seed_world(legal_basis_active=False)
    result = run_golden(reht=RealReht(), kernel=kernel)
    _assert_decision_never_executed(result, kernel)


def test_pre_execution_revoked_competence() -> None:
    kernel = seed_world(revoke_competence=True)
    result = run_golden(reht=RealReht(), kernel=kernel)
    _assert_decision_never_executed(result, kernel)


def test_pre_execution_conflicted_critical_evidence() -> None:
    kernel = seed_world(residency_conflicted=True)
    result = run_golden(reht=RealReht(), kernel=kernel)
    _assert_decision_never_executed(result, kernel)


def test_pre_execution_disqualified_decision_maker() -> None:
    kernel = seed_world(decision_maker_relationship="SPOUSE")
    result = run_golden(reht=RealReht(), kernel=kernel)
    _assert_decision_never_executed(result, kernel)


def test_pre_execution_stale_evidence() -> None:
    kernel = seed_world(evidence_stale=True)
    result = run_golden(reht=RealReht(), kernel=kernel)
    _assert_decision_never_executed(result, kernel)


def test_pre_execution_mis_purposed_evidence() -> None:
    kernel = seed_world(purpose_violation=True)
    result = run_golden(reht=RealReht(), kernel=kernel)
    _assert_decision_never_executed(result, kernel)


def test_pre_execution_out_of_scope_representation() -> None:
    kernel = seed_world(has_representation=True, representation_scope_ok=False)
    result = run_golden(reht=RealReht(), kernel=kernel)
    _assert_decision_never_executed(result, kernel)


def test_pre_execution_underage_applicant() -> None:
    kernel = seed_world(applicant_age=16)
    result = run_golden(reht=RealReht(), kernel=kernel)
    _assert_decision_never_executed(result, kernel)


def test_golden_path_decision_executes_exactly_once() -> None:
    kernel = seed_world()
    result = run_golden(reht=RealReht(), kernel=kernel)
    assert result.case_state == "CLOSED"
    by_type = result.economics["executions_by_type"]
    assert by_type.get("ISSUE_DECISION", 0) == 1, "the happy path issues exactly one decision"


def _run_single_write(kernel, requested_state, action_type, postconditions, capability="ADMIN"):
    """Run a minimal single-WRITE workflow requesting a Case transition. The
    pre-execution boundary must reject an illegal transition BEFORE the
    Gateway."""
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
    )

    from valo_public_pack.ports import (
        PublicBaro,
        PublicGateway,
        PublicKernel,
        PublicVeritas,
    )

    config = {
        "target": "case-1", "actor": "system-1", "identity_id": "id-system-1",
        "action_type": action_type, "capability": capability,
        "kernel_event_type": "CASE_TRANSITION", "postconditions": postconditions,
        "requested_transition": {"state": requested_state},
    }
    prepare = WorkflowNode(
        id="prep", opcode="PREPARE_ACTION", node_class=NodeClass.COMPUTE,
        outputs=[TypedRef(name="action", type="any")],
        effect_type=EffectType.PURE,
        policies=NodePolicies(authority=AuthorityRequirements(capability=capability, scope=[])),
        config=config,
    )
    execute = WorkflowNode(
        id="exec", opcode="EXECUTE_ACTION", node_class=NodeClass.WRITE,
        inputs=[TypedRef(name="action", type="any")],
        outputs=[TypedRef(name="out", type="Executed<Action>")],
        effect_type=EffectType.WRITE_INTERNAL,
        policies=NodePolicies(authority=AuthorityRequirements(capability=capability, scope=[]), idempotency=IdempotencyPolicy(require_key=False)),
        config=config,
    )
    graph = WorkflowGraph(
        id="wf.single-write", version="1",
        input_schema={}, output_schema={"out": "Executed<Action>"},
        nodes=[prepare, execute], edges=[WorkflowEdge(source="prep", target="exec")],
        entry="prep", terminal_states=["exec"],
    )
    gateway = PublicGateway()
    engine = RuntimeEngine(
        PublicKernel(kernel), RealReht(), gateway, PublicVeritas(), PublicBaro(),
        backend=ReferenceBackend(), tenant_id="public",
    )
    instance = engine.start(graph, {})
    return instance, gateway, kernel


def _set_case_state(kernel, state: str) -> None:
    from valo_kernel.contracts import CanonicalEvent, EventType, utcnow

    kernel.append(CanonicalEvent(
        event_id=f"set-{state}", event_type=EventType.ENTITY_UPDATED,
        tenant_id="public", subject="case-1", actor="system-1", source="public-pack",
        effective_at=utcnow(),
        payload={"entity_id": "case-1", "state": state},
    ))


def test_pre_execution_notify_from_registered_never_reaches_gateway() -> None:
    """current=REGISTERED, request NOTIFIED: the pre-execution boundary rejects
    BEFORE the Gateway sends anything."""
    from valo_workflow_isa import WorkflowStatus

    kernel = seed_world()
    _set_case_state(kernel, "REGISTERED")
    instance, gateway, kernel = _run_single_write(
        kernel, "NOTIFIED", "NOTIFY", {"delivered": True}
    )
    assert instance.status == WorkflowStatus.FAILED
    assert len(gateway.executions) == 0, "NOTIFY must never reach the Gateway from REGISTERED"
    notified = [e for e in kernel.events() if e.subject == "case-1" and e.payload.get("state") == "NOTIFIED"]
    assert not notified


def test_pre_execution_appeal_deadline_from_decided_never_reaches_gateway() -> None:
    """current=DECIDED, request APPEAL_PERIOD directly (skipping NOTIFIED):
    illegal, rejected before the appeal deadline is created."""
    from valo_workflow_isa import WorkflowStatus

    kernel = seed_world()
    _set_case_state(kernel, "DECIDED")
    instance, gateway, kernel = _run_single_write(
        kernel, "APPEAL_PERIOD", "CREATE_APPEAL_DEADLINE", {"deadline_set": True}
    )
    assert instance.status == WorkflowStatus.FAILED
    assert len(gateway.executions) == 0, "CREATE_APPEAL_DEADLINE must never reach the Gateway from DECIDED"
    appeal = [e for e in kernel.events() if e.subject == "case-1" and e.payload.get("state") == "APPEAL_PERIOD"]
    assert not appeal


def test_pre_execution_legal_basis_must_cover_this_case() -> None:
    """An active LEGAL_BASIS scoped to case-2 must NOT make case-1 decidable."""
    from datetime import timedelta

    from valo_kernel.contracts import (
        Authority,
        CanonicalEvent,
        EventType,
        TimeWindow,
        utcnow,
    )

    from valo_public_pack.ports import _assert_decidable_from_raw_facts

    kernel = seed_world()
    now = utcnow()
    # revoke the case-1 legal basis
    kernel.append(CanonicalEvent(
        event_id="revoke-lb", event_type=EventType.AUTHORITY_REVOKED,
        tenant_id="public", subject="system-1", source="kernel", effective_at=now,
        payload={"authority_id": "auth-system-LEGAL_BASIS", "revocation_ref": "rev-lb"},
    ))
    # grant a legal basis scoped ONLY to case-2
    kernel.append(CanonicalEvent(
        event_id="grant-lb-case2", event_type=EventType.AUTHORITY_GRANTED,
        tenant_id="public", subject="system-1", source="kernel", effective_at=now,
        payload={"authority": Authority(
            authority_id="auth-lb-case2", principal="system-1", capability="LEGAL_BASIS",
            scope=["case-2"], constraints={"service": "PUBLIC_SERVICE_A"},
            basis="basis.public_service_b.v1",
            validity=TimeWindow(valid_from=now - timedelta(days=1), valid_until=now + timedelta(days=365)),
        )},
    ))
    try:
        _assert_decidable_from_raw_facts(kernel, "case-1", "system-1")
        raise AssertionError("case-1 must not be decidable with a legal basis scoped to case-2")
    except RuntimeError as exc:
        assert "cannot decide" in str(exc)

    result = run_golden(reht=RealReht(), kernel=kernel)
    assert result.case_state == "READY_FOR_DECISION"
    assert result.economics["executions_by_type"].get("ISSUE_DECISION", 0) == 0


def test_pre_execution_legal_basis_must_cover_this_service() -> None:
    """An active LEGAL_BASIS for a DIFFERENT service must not make this case
    decidable (the exact action must have a relevant legal basis)."""
    from datetime import timedelta

    from valo_kernel.contracts import (
        Authority,
        CanonicalEvent,
        EventType,
        TimeWindow,
        utcnow,
    )

    from valo_public_pack.ports import _assert_decidable_from_raw_facts

    kernel = seed_world()
    now = utcnow()
    kernel.append(CanonicalEvent(
        event_id="revoke-lb", event_type=EventType.AUTHORITY_REVOKED,
        tenant_id="public", subject="system-1", source="kernel", effective_at=now,
        payload={"authority_id": "auth-system-LEGAL_BASIS", "revocation_ref": "rev-lb"},
    ))
    kernel.append(CanonicalEvent(
        event_id="grant-lb-other-service", event_type=EventType.AUTHORITY_GRANTED,
        tenant_id="public", subject="system-1", source="kernel", effective_at=now,
        payload={"authority": Authority(
            authority_id="auth-lb-other", principal="system-1", capability="LEGAL_BASIS",
            scope=["case-1"], constraints={"service": "SERVICE_X"},
            basis="basis.service_x.v1",
            validity=TimeWindow(valid_from=now - timedelta(days=1), valid_until=now + timedelta(days=365)),
        )},
    ))
    try:
        _assert_decidable_from_raw_facts(kernel, "case-1", "system-1")
        raise AssertionError("case-1 (PUBLIC_SERVICE_A) must not be decidable under a SERVICE_X legal basis")
    except RuntimeError as exc:
        assert "cannot decide" in str(exc)


def test_legal_basis_without_service_constraint_is_fail_closed() -> None:
    """Adversarial: an active LEGAL_BASIS that carries NO constraints.service
    must NOT default to PUBLIC_SERVICE_A. Fail closed -> pre-execution reject,
    zero ISSUE_DECISION Gateway executions, no VerifiedEffect<PublicDecision>,
    no DECIDED."""
    from datetime import timedelta

    from valo_kernel.contracts import (
        Authority,
        CanonicalEvent,
        EventType,
        TimeWindow,
        utcnow,
    )

    from valo_public_pack.ports import _assert_decidable_from_raw_facts

    kernel = seed_world()
    now = utcnow()
    kernel.append(CanonicalEvent(
        event_id="revoke-lb", event_type=EventType.AUTHORITY_REVOKED,
        tenant_id="public", subject="system-1", source="kernel", effective_at=now,
        payload={"authority_id": "auth-system-LEGAL_BASIS", "revocation_ref": "rev-lb"},
    ))
    # LEGAL_BASIS with NO constraints at all — covers nothing (fail closed)
    kernel.append(CanonicalEvent(
        event_id="grant-lb-no-constraint", event_type=EventType.AUTHORITY_GRANTED,
        tenant_id="public", subject="system-1", source="kernel", effective_at=now,
        payload={"authority": Authority(
            authority_id="auth-lb-noconstraint", principal="system-1", capability="LEGAL_BASIS",
            scope=["case-1"], constraints={}, basis="basis.unspecified.v1",
            validity=TimeWindow(valid_from=now - timedelta(days=1), valid_until=now + timedelta(days=365)),
        )},
    ))
    # unit: the raw-facts invariant must reject
    try:
        _assert_decidable_from_raw_facts(kernel, "case-1", "system-1")
        raise AssertionError("an unconstrained legal basis must not make anything decidable")
    except RuntimeError as exc:
        assert "cannot decide" in str(exc)

    # real path: pre-execution reject -> zero ISSUE_DECISION executions, no
    # VerifiedEffect<PublicDecision>, no DECIDED event
    from valo_workflow_isa.runtime.values import RuntimeValue

    result = run_golden(reht=RealReht(), kernel=kernel)
    assert result.case_state == "READY_FOR_DECISION"
    assert result.economics["executions_by_type"].get("ISSUE_DECISION", 0) == 0
    decisions = []
    for outputs in (result.instance.outputs or {}).values():
        for value in outputs.values():
            if isinstance(value, RuntimeValue) and value.base_type == "PublicDecision":
                decisions.append(value)
    assert not decisions, "no VerifiedEffect<PublicDecision> may be produced"
    decided = [e for e in kernel.events() if e.subject == "case-1" and e.payload.get("state") == "DECIDED"]
    assert not decided, "no DECIDED Kernel event may be emitted"


def test_case_without_explicit_service_is_fail_closed() -> None:
    """Adversarial: a case with NO explicit service attribute must not default
    to PUBLIC_SERVICE_A. Even if a LEGAL_BASIS covers PUBLIC_SERVICE_A, the
    case cannot be decided: pre-execution reject, zero ISSUE_DECISION, no
    VerifiedEffect<PublicDecision>, no DECIDED."""
    from valo_kernel.contracts import CanonicalEvent, EventType, utcnow

    from valo_public_pack.ports import _assert_decidable_from_raw_facts

    kernel = seed_world()
    now = utcnow()
    # rebuild case-1 WITHOUT a service attribute (raw attributes present)
    kernel.append(CanonicalEvent(
        event_id="rebuild-case-no-service", event_type=EventType.ENTITY_UPDATED,
        tenant_id="public", subject="case-1", actor="system-1", source="public-pack", effective_at=now,
        payload={"entity_id": "case-1", "state": "READY_FOR_DECISION", "attributes": {
            "service": None,  # explicit: no service is established for this case
            "applicant_id": "applicant-1", "age": 30,
            "residency_fact": "CONFIRMED", "relations": [],
            "evidence": [{"type": "residency_document", "status": "ADMITTED", "purpose": "PUBLIC_SERVICE_A"}],
            "representation": None,
        }},
    ))
    # unit: the raw-facts invariant must reject (no explicit service)
    try:
        _assert_decidable_from_raw_facts(kernel, "case-1", "system-1")
        raise AssertionError("a case without an explicit service must not be decidable")
    except RuntimeError as exc:
        assert "no explicit service" in str(exc)

    # real path: pre-execution reject -> zero ISSUE_DECISION, no
    # VerifiedEffect<PublicDecision>, no DECIDED event
    from valo_workflow_isa.runtime.values import RuntimeValue

    result = run_golden(reht=RealReht(), kernel=kernel)
    assert result.case_state == "READY_FOR_DECISION"
    assert result.economics["executions_by_type"].get("ISSUE_DECISION", 0) == 0
    decisions = []
    for outputs in (result.instance.outputs or {}).values():
        for value in outputs.values():
            if isinstance(value, RuntimeValue) and value.base_type == "PublicDecision":
                decisions.append(value)
    assert not decisions, "no VerifiedEffect<PublicDecision> may be produced"
    decided = [e for e in kernel.events() if e.subject == "case-1" and e.payload.get("state") == "DECIDED"]
    assert not decided, "no DECIDED Kernel event may be emitted"
