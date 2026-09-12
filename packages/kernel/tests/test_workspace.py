from __future__ import annotations

from datetime import timedelta

import pytest
from pydantic import ValidationError

from valo_kernel import (
    CandidateClaim,
    CandidateKind,
    ConformanceOutcome,
    ExecutionContextError,
    FailClosedError,
    IdentityClaim,
    ProjectionSelector,
    ProposedAction,
    Purpose,
    TimeWindow,
    TruthStatus,
    VerificationStatus,
    WorkspaceCapabilitySpec,
    WorkspaceSpec,
    bind_workspace_execution,
    build_execution_context,
    compile_governed_workspace,
    create_candidate_result,
    evaluate_candidate_conformance,
    utcnow,
)
from valo_kernel.contracts import CanonicalEvent, EntityType, EventType

from .conftest import entity_event


def _register_purpose(engine, *, purpose_id: str = "purpose-1") -> Purpose:
    now = utcnow()
    purpose = Purpose(
        purpose_id=purpose_id,
        purpose_type="reservation",
        scope=["job-1"],
        basis="customer-request",
        permitted_data=["entities:job-1"],
        permitted_actions=["BOOK"],
        validity=TimeWindow(
            valid_from=now - timedelta(minutes=1),
            valid_until=now + timedelta(hours=1),
        ),
    )
    engine.append(
        CanonicalEvent(
            event_id=f"register-{purpose_id}",
            event_type=EventType.PURPOSE_REGISTERED,
            tenant_id="tenant-a",
            subject=purpose_id,
            source="kernel",
            effective_at=now,
            payload={"purpose": purpose},
        )
    )
    return purpose


def _spec(*, expires_at, step_up_required: bool = False) -> WorkspaceSpec:
    return WorkspaceSpec(
        workspace_id="workspace-1",
        work_unit_id="work-unit-1",
        tenant_id="tenant-a",
        purpose_id="purpose-1",
        program_ref="valo.jobs.reserve@1.0.0",
        program_digest="a" * 64,
        selectors=(ProjectionSelector(collection="entities", object_ids=("job-1",)),),
        capabilities=(
            WorkspaceCapabilitySpec(
                capability="BOOK",
                target_refs=("job-1",),
                allowed_effects=("reserve",),
                parameter_constraints={
                    "quantity": {"required": True, "min": 1, "max": 2}
                },
            ),
        ),
        allowed_output_kinds=(CandidateKind.EXTERNAL_ACTION,),
        expires_at=expires_at,
        max_actions=1,
        step_up_required=step_up_required,
    )


def _workspace(engine, *, moment=None, step_up_required: bool = False):
    moment = moment or utcnow()
    return compile_governed_workspace(
        engine.state(),
        _spec(
            expires_at=moment + timedelta(minutes=30),
            step_up_required=step_up_required,
        ),
        source_event_position=engine.sequence(),
        moment=moment,
    )


def _candidate(workspace, *, worker_id: str = "worker-a", **updates):
    values = {
        "candidate_id": f"candidate-{worker_id}",
        "invocation_id": f"invocation-{worker_id}",
        "worker_id": worker_id,
        "workspace_id": workspace.spec.workspace_id,
        "workspace_digest": workspace.workspace_digest,
        "output_kind": CandidateKind.EXTERNAL_ACTION,
        "claims": (
            CandidateClaim(
                claim_id="claim-1",
                subject="job-1",
                predicate="is_reservable",
                object="true",
                truth_status=TruthStatus.INFERRED,
                source_refs=("entities:job-1",),
            ),
        ),
        "proposed_actions": (
            ProposedAction(
                action_id="action-1",
                capability="BOOK",
                target="job-1",
                purpose_id="purpose-1",
                parameters={"quantity": 1},
                declared_effects=("reserve",),
            ),
        ),
    }
    values.update(updates)
    return create_candidate_result(**values)


@pytest.fixture
def governed_engine(engine):
    engine.append(
        entity_event(
            "tenant-a",
            "job-1",
            entity_type=EntityType.JOB,
            state="READY",
        )
    )
    engine.append(
        entity_event(
            "tenant-a",
            "job-unrelated",
            entity_type=EntityType.JOB,
            state="READY",
        )
    )
    _register_purpose(engine)
    return engine


def test_purpose_is_canonical_event_state_and_can_be_revoked(governed_engine) -> None:
    assert "purpose-1" in governed_engine.state().purposes
    now = utcnow()
    governed_engine.append(
        CanonicalEvent(
            event_id="revoke-purpose-1",
            event_type=EventType.PURPOSE_REVOKED,
            tenant_id="tenant-a",
            subject="purpose-1",
            source="kernel",
            effective_at=now,
            payload={"purpose_id": "purpose-1"},
        )
    )
    assert not governed_engine.state().purposes["purpose-1"].validity.is_active_at(now)


def test_workspace_is_minimal_sealed_and_non_authoritative(governed_engine) -> None:
    moment = utcnow()
    first = _workspace(governed_engine, moment=moment)
    second = _workspace(governed_engine, moment=moment)

    assert first == second
    assert first.workspace_digest == first.computed_digest
    assert {item.ref for item in first.projection.objects} == {
        "entities:job-1",
        "purposes:purpose-1",
    }
    assert "job-unrelated" not in first.model_dump_json()
    assert first.authority_effect == "NO_AUTHORITY_CREATION"
    assert first.can_issue_clearance is False
    assert first.spec.program_ref == "valo.jobs.reserve@1.0.0"
    assert first.spec.program_digest == "a" * 64
    assert all(not lease.can_issue_clearance for lease in first.capability_leases)


def test_workspace_expiry_is_bounded_by_registered_purpose(governed_engine) -> None:
    moment = utcnow()
    purpose = governed_engine.state().purposes["purpose-1"]
    at_boundary = compile_governed_workspace(
        governed_engine.state(),
        _spec(expires_at=purpose.validity.valid_until),
        source_event_position=governed_engine.sequence(),
        moment=moment,
    )

    assert at_boundary.spec.expires_at == purpose.validity.valid_until
    assert at_boundary.projection.expires_at == purpose.validity.valid_until
    assert all(
        lease.valid_until == purpose.validity.valid_until
        for lease in at_boundary.capability_leases
    )

    with pytest.raises(FailClosedError, match="cannot outlive"):
        compile_governed_workspace(
            governed_engine.state(),
            _spec(expires_at=purpose.validity.valid_until + timedelta(microseconds=1)),
            source_event_position=governed_engine.sequence(),
            moment=moment,
        )


def test_workspace_program_lineage_is_atomic() -> None:
    with pytest.raises(ValidationError, match="bound together"):
        WorkspaceSpec(
            workspace_id="workspace-1",
            work_unit_id="work-unit-1",
            tenant_id="tenant-a",
            purpose_id="purpose-1",
            program_ref="valo.jobs.reserve@1.0.0",
            selectors=(
                ProjectionSelector(collection="entities", object_ids=("job-1",)),
            ),
            capabilities=(),
            allowed_output_kinds=(CandidateKind.ARTIFACT,),
            expires_at=utcnow() + timedelta(minutes=5),
        )


def test_workspace_fails_closed_outside_purpose(governed_engine) -> None:
    moment = utcnow()
    spec = _spec(expires_at=moment + timedelta(minutes=30)).model_copy(
        update={
            "selectors": (
                ProjectionSelector(
                    collection="entities",
                    object_ids=("job-unrelated",),
                ),
            )
        }
    )
    with pytest.raises(FailClosedError, match="outside purpose"):
        compile_governed_workspace(
            governed_engine.state(),
            spec,
            source_event_position=governed_engine.sequence(),
            moment=moment,
        )


@pytest.mark.parametrize(
    ("spec_update", "message"),
    [
        ({"tenant_id": "tenant-b"}, "tenant"),
        ({"purpose_id": "missing-purpose"}, "active registered purpose"),
    ],
)
def test_workspace_fails_closed_on_invalid_root_binding(
    governed_engine,
    spec_update,
    message,
) -> None:
    moment = utcnow()
    spec = _spec(expires_at=moment + timedelta(minutes=30)).model_copy(
        update=spec_update
    )
    with pytest.raises(FailClosedError, match=message):
        compile_governed_workspace(
            governed_engine.state(),
            spec,
            source_event_position=governed_engine.sequence(),
            moment=moment,
        )


def test_workspace_fails_closed_when_expired(governed_engine) -> None:
    moment = utcnow()
    spec = _spec(expires_at=moment + timedelta(minutes=30)).model_copy(
        update={"expires_at": moment}
    )
    with pytest.raises(FailClosedError, match="already expired"):
        compile_governed_workspace(
            governed_engine.state(),
            spec,
            source_event_position=governed_engine.sequence(),
            moment=moment,
        )


@pytest.mark.parametrize(
    ("capability", "target", "message"),
    [
        ("DELETE", "job-1", "capability is outside purpose"),
        ("BOOK", "job-unrelated", "target is outside purpose scope"),
    ],
)
def test_workspace_fails_closed_on_capability_scope_escape(
    governed_engine,
    capability,
    target,
    message,
) -> None:
    moment = utcnow()
    spec = _spec(expires_at=moment + timedelta(minutes=30)).model_copy(
        update={
            "capabilities": (
                WorkspaceCapabilitySpec(
                    capability=capability,
                    target_refs=(target,),
                ),
            )
        }
    )
    with pytest.raises(FailClosedError, match=message):
        compile_governed_workspace(
            governed_engine.state(),
            spec,
            source_event_position=governed_engine.sequence(),
            moment=moment,
        )


def test_worker_candidate_cannot_create_confirmed_truth() -> None:
    with pytest.raises(ValidationError, match="cannot create CONFIRMED truth"):
        CandidateClaim(
            claim_id="claim-1",
            subject="job-1",
            predicate="state",
            object="READY",
            truth_status=TruthStatus.CONFIRMED,
        )


def test_replaceable_workers_conform_against_same_space(governed_engine) -> None:
    workspace = _workspace(governed_engine)
    first = evaluate_candidate_conformance(
        workspace,
        _candidate(workspace, worker_id="worker-a"),
        governed_engine.state(),
    )
    second = evaluate_candidate_conformance(
        workspace,
        _candidate(workspace, worker_id="worker-b"),
        governed_engine.state(),
    )

    assert first.outcome == ConformanceOutcome.PASS
    assert second.outcome == ConformanceOutcome.PASS


def test_claim_without_workspace_provenance_requires_redo(governed_engine) -> None:
    workspace = _workspace(governed_engine)
    unsupported = CandidateClaim(
        claim_id="claim-outside",
        subject="job-1",
        predicate="customer_tier",
        object="gold",
        truth_status=TruthStatus.INFERRED,
        source_refs=("entities:customer-secret",),
    )
    report = evaluate_candidate_conformance(
        workspace,
        _candidate(workspace, claims=(unsupported,)),
        governed_engine.state(),
    )

    assert report.outcome == ConformanceOutcome.REDO
    assert {item.code for item in report.mismatches} == {"UNSUPPORTED_CLAIM"}


def test_capability_or_parameter_escape_is_not_executable(governed_engine) -> None:
    workspace = _workspace(governed_engine)
    escaped_action = ProposedAction(
        action_id="action-1",
        capability="DELETE",
        target="job-unrelated",
        purpose_id="purpose-1",
        parameters={"quantity": 100},
        declared_effects=("destroy",),
    )
    candidate = _candidate(workspace, proposed_actions=(escaped_action,))
    report = evaluate_candidate_conformance(
        workspace,
        candidate,
        governed_engine.state(),
    )

    assert report.outcome == ConformanceOutcome.DENY
    assert "CAPABILITY_ESCAPE" in {item.code for item in report.mismatches}
    with pytest.raises(FailClosedError, match="only PASS"):
        bind_workspace_execution(
            workspace,
            candidate,
            report,
            action_id="action-1",
        )


def test_action_target_purpose_effect_and_parameters_are_conformed(
    governed_engine,
) -> None:
    workspace = _workspace(governed_engine)
    escaped_action = ProposedAction(
        action_id="action-1",
        capability="BOOK",
        target="job-unrelated",
        purpose_id="another-purpose",
        parameters={"quantity": 100},
        declared_effects=("destroy",),
    )
    report = evaluate_candidate_conformance(
        workspace,
        _candidate(workspace, proposed_actions=(escaped_action,)),
        governed_engine.state(),
    )

    assert report.outcome == ConformanceOutcome.DENY
    assert {item.code for item in report.mismatches} == {
        "EFFECT_ESCAPE",
        "PARAMETER_CONSTRAINT",
        "PURPOSE_DRIFT",
        "TARGET_ESCAPE",
    }


@pytest.mark.parametrize(
    ("candidate_update", "outcome", "code"),
    [
        ({"proposed_actions": ()}, ConformanceOutcome.REDO, "MISSING_ACTION"),
        (
            {"unknowns": ("customer intent",)},
            ConformanceOutcome.DEFER,
            "UNRESOLVED_UNKNOWN",
        ),
        (
            {"output_kind": CandidateKind.DEFER, "proposed_actions": ()},
            ConformanceOutcome.DEFER,
            "WORKER_DEFER",
        ),
        (
            {"output_kind": CandidateKind.ARTIFACT},
            ConformanceOutcome.DENY,
            "ACTION_KIND_ESCAPE",
        ),
    ],
)
def test_candidate_shape_routes_deterministically(
    governed_engine,
    candidate_update,
    outcome,
    code,
) -> None:
    workspace = _workspace(governed_engine)
    report = evaluate_candidate_conformance(
        workspace,
        _candidate(workspace, **candidate_update),
        governed_engine.state(),
    )
    assert report.outcome == outcome
    assert code in {item.code for item in report.mismatches}


def test_duplicate_or_excess_actions_are_denied(governed_engine) -> None:
    workspace = _workspace(governed_engine)
    action = _candidate(workspace).proposed_actions[0]
    report = evaluate_candidate_conformance(
        workspace,
        _candidate(workspace, proposed_actions=(action, action)),
        governed_engine.state(),
    )
    assert report.outcome == ConformanceOutcome.DENY
    assert {item.code for item in report.mismatches} == {
        "ACTION_COUNT",
        "DUPLICATE_ACTION_ID",
    }


def test_relevant_state_drift_defers_but_unrelated_drift_does_not(
    governed_engine,
) -> None:
    workspace = _workspace(governed_engine)
    candidate = _candidate(workspace)

    governed_engine.append(
        CanonicalEvent(
            event_id="update-unrelated",
            event_type=EventType.ENTITY_UPDATED,
            tenant_id="tenant-a",
            subject="job-unrelated",
            source="kernel",
            payload={"entity_id": "job-unrelated", "state": "BUSY"},
        )
    )
    unaffected = evaluate_candidate_conformance(
        workspace,
        candidate,
        governed_engine.state(),
    )
    assert unaffected.outcome == ConformanceOutcome.PASS

    governed_engine.append(
        CanonicalEvent(
            event_id="update-relevant",
            event_type=EventType.ENTITY_UPDATED,
            tenant_id="tenant-a",
            subject="job-1",
            source="kernel",
            payload={"entity_id": "job-1", "state": "BUSY"},
        )
    )
    changed = evaluate_candidate_conformance(
        workspace,
        candidate,
        governed_engine.state(),
    )
    assert changed.outcome == ConformanceOutcome.DEFER
    assert {item.code for item in changed.mismatches} == {"RELEVANT_STATE_DRIFT"}


def test_tamper_halts_even_when_workspace_is_also_expired(governed_engine) -> None:
    moment = utcnow()
    workspace = _workspace(governed_engine, moment=moment)
    candidate = _candidate(workspace).model_copy(update={"worker_id": "intruder"})
    report = evaluate_candidate_conformance(
        workspace,
        candidate,
        governed_engine.state(),
        moment=workspace.spec.expires_at + timedelta(seconds=1),
    )

    assert report.outcome == ConformanceOutcome.HALT
    assert {item.code for item in report.mismatches} == {
        "CANDIDATE_TAMPER",
        "WORKSPACE_EXPIRED",
    }


def test_step_up_is_explicit_and_cannot_create_execution_binding(
    governed_engine,
) -> None:
    workspace = _workspace(governed_engine, step_up_required=True)
    candidate = _candidate(workspace)
    report = evaluate_candidate_conformance(
        workspace,
        candidate,
        governed_engine.state(),
    )

    assert report.outcome == ConformanceOutcome.STEP_UP
    with pytest.raises(FailClosedError, match="only PASS"):
        bind_workspace_execution(
            workspace,
            candidate,
            report,
            action_id="action-1",
        )


def test_pass_binds_exact_action_and_fresh_execution_state(governed_engine) -> None:
    now = utcnow()
    governed_engine.append(
        entity_event("tenant-a", "worker-a", entity_type=EntityType.AGENT)
    )
    governed_engine.append(
        CanonicalEvent(
            event_id="identity-worker-a",
            event_type=EventType.IDENTITY_CLAIMED,
            tenant_id="tenant-a",
            subject="worker-a",
            source="kernel",
            effective_at=now,
            payload={
                "identity": IdentityClaim(
                    identity_id="identity-worker-a",
                    entity_id="worker-a",
                    tenant_id="tenant-a",
                    claim_type="service_identity",
                    value="worker-a",
                    verification_status=VerificationStatus.VERIFIED,
                )
            },
        )
    )
    workspace = _workspace(governed_engine, moment=now)
    candidate = _candidate(workspace)
    report = evaluate_candidate_conformance(
        workspace,
        candidate,
        governed_engine.state(),
        moment=now,
    )
    binding = bind_workspace_execution(
        workspace,
        candidate,
        report,
        action_id="action-1",
    )
    request = CanonicalEvent(
        event_id="request-1",
        event_type=EventType.RESOURCE_RESERVED,
        tenant_id="tenant-a",
        subject="job-1",
        actor="worker-a",
        source="reht",
        effective_at=now,
        idempotency_key="nonce-1",
        payload={"capability": "BOOK"},
    )
    context = build_execution_context(
        governed_engine.state(),
        actor="worker-a",
        capability="BOOK",
        target="job-1",
        purpose_id="purpose-1",
        requested_transition=request,
        event_position=governed_engine.sequence(),
        workspace_binding=binding,
    )

    assert context["workspace_binding"]["proposed_action_digest"]
    assert context["workspace_binding"]["program_ref"] == ("valo.jobs.reserve@1.0.0")
    assert context["workspace_binding"]["program_digest"] == "a" * 64
    assert context["workspace_binding"]["tenant_id"] == "tenant-a"
    assert (
        context["workspace_binding"]["workspace_expires_at"]
        == (binding.model_dump(mode="json")["workspace_expires_at"])
    )
    assert context["workspace_binding"]["source_event_position"] == (
        workspace.projection.source_event_position
    )
    assert context["state_ref"] == workspace.projection.dependency_digest
    assert context["state_root"] == governed_engine.state().root_hash()
    assert context["execution_nonce"] == "nonce-1"

    with pytest.raises(ExecutionContextError, match="differs from conformed"):
        build_execution_context(
            governed_engine.state(),
            actor="worker-a",
            capability="DELETE",
            target="job-1",
            purpose_id="purpose-1",
            requested_transition=request,
            event_position=governed_engine.sequence(),
            workspace_binding=binding,
        )

    with pytest.raises(ExecutionContextError, match="expired after conformance"):
        build_execution_context(
            governed_engine.state(),
            actor="worker-a",
            capability="BOOK",
            target="job-1",
            purpose_id="purpose-1",
            requested_transition=request,
            moment=workspace.spec.expires_at,
            event_position=governed_engine.sequence(),
            workspace_binding=binding,
        )

    with pytest.raises(ExecutionContextError, match="tenant differs"):
        build_execution_context(
            governed_engine.state(),
            actor="worker-a",
            capability="BOOK",
            target="job-1",
            purpose_id="purpose-1",
            requested_transition=request,
            event_position=governed_engine.sequence(),
            workspace_binding=binding.model_copy(update={"tenant_id": "tenant-b"}),
        )

    with pytest.raises(ExecutionContextError, match="predates"):
        build_execution_context(
            governed_engine.state(),
            actor="worker-a",
            capability="BOOK",
            target="job-1",
            purpose_id="purpose-1",
            requested_transition=request,
            event_position=workspace.projection.source_event_position - 1,
            workspace_binding=binding,
        )

    governed_engine.append(
        CanonicalEvent(
            event_id="job-changed-after-binding",
            event_type=EventType.ENTITY_UPDATED,
            tenant_id="tenant-a",
            subject="job-1",
            source="kernel",
            payload={"entity_id": "job-1", "state": "BUSY"},
        )
    )
    with pytest.raises(ExecutionContextError, match="changed after conformance"):
        build_execution_context(
            governed_engine.state(),
            actor="worker-a",
            capability="BOOK",
            target="job-1",
            purpose_id="purpose-1",
            requested_transition=request,
            event_position=governed_engine.sequence(),
            workspace_binding=binding,
        )


def test_binding_rejects_tampered_or_ambiguous_lineage(governed_engine) -> None:
    workspace = _workspace(governed_engine)
    candidate = _candidate(workspace)
    report = evaluate_candidate_conformance(
        workspace,
        candidate,
        governed_engine.state(),
    )

    with pytest.raises(FailClosedError, match="candidate is unsealed"):
        bind_workspace_execution(
            workspace,
            candidate.model_copy(update={"worker_id": "tampered"}),
            report,
            action_id="action-1",
        )
    with pytest.raises(FailClosedError, match="conformance candidate binding"):
        bind_workspace_execution(
            workspace,
            candidate,
            report.model_copy(update={"candidate_id": "another-candidate"}),
            action_id="action-1",
        )
    with pytest.raises(FailClosedError, match="one conformed proposed action"):
        bind_workspace_execution(
            workspace,
            candidate,
            report,
            action_id="missing-action",
        )

