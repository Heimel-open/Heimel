from __future__ import annotations

from datetime import timedelta

import pytest

from valo_kernel import (
    AdmissionCandidate,
    AdmissionOutcome,
    AdmissionPolicy,
    ArtifactContextBinding,
    CandidateKind,
    ConformanceOutcome,
    FailClosedError,
    KernelInvariantViolation,
    ProjectionSelector,
    ProviderAdmissionAssessment,
    ProviderAdmissionDisposition,
    Purpose,
    TimeWindow,
    WorkspaceSpec,
    compile_governed_workspace,
    create_admission_event,
    create_candidate_result,
    evaluate_candidate_conformance,
    evaluate_state_admission,
    replay,
    utcnow,
)
from valo_kernel.contracts import CanonicalEvent, EventType, Fact, TruthStatus

from .conftest import entity_event, evidence_event, make_provenance


def _candidate(engine, evidence_id: str, *, candidate_id: str = "candidate-1", **kw):
    evidence = engine.state().evidence[evidence_id]
    values = {
        "candidate_id": candidate_id,
        "tenant_id": engine.tenant_id,
        "evidence_id": evidence_id,
        "material_type": evidence.type,
        "source_fingerprint": evidence.integrity_hash,
        "subject_refs": (evidence.subject,),
        "entity_refs": (evidence.subject,),
        "provenance_refs": (f"source:{evidence.source}",),
        "captured_at": evidence.captured_at,
    }
    values.update(kw)
    return AdmissionCandidate(**values)


def _policy(*, trusted=(), required=()) -> AdmissionPolicy:
    return AdmissionPolicy(
        policy_id="native-policy",
        tenant_id="tenant-a",
        trusted_provider_ids=trusted,
        required_provider_ids=required,
    )


def _assessment(candidate, disposition) -> ProviderAdmissionAssessment:
    now = utcnow()
    sealed = candidate.model_copy(
        update={"candidate_digest": candidate.computed_digest}
    )
    return ProviderAdmissionAssessment(
        assessment_id=f"assessment-{disposition.value.lower()}",
        provider_id="external-lens",
        tenant_id="tenant-a",
        candidate_id=sealed.candidate_id,
        candidate_digest=sealed.candidate_digest,
        disposition=disposition,
        validity=TimeWindow(
            valid_from=now - timedelta(minutes=1),
            valid_until=now + timedelta(minutes=5),
        ),
        source_fingerprint="b" * 64,
    )


def _receive(engine, evidence_id: str = "ev-1", subject: str = "subject-1"):
    engine.append(entity_event("tenant-a", subject))
    engine.append(evidence_event("tenant-a", evidence_id, subject))


def test_native_admission_has_no_external_dependency(engine) -> None:
    _receive(engine)
    candidate = _candidate(engine, "ev-1")
    decision = evaluate_state_admission(engine.state(), candidate, _policy())

    assert decision.outcome == AdmissionOutcome.ADMIT
    assert decision.assessed_provider_ids == ()
    assert decision.decision_owner == "VALO_KERNEL"
    assert decision.can_enter_operational_state is True
    assert decision.can_create_authority is False

    event = create_admission_event(
        engine.state(),
        candidate,
        _policy(),
        event_id="admission-1",
    )
    engine.append(event)
    state = engine.state()
    assert state.evidence["ev-1"].status.value == "ADMITTED"
    assert len(state.admissions) == 1
    assert state.facts == {}
    assert state.authorities == {}
    assert state.delegations == {}


def test_provider_is_required_only_when_tenant_policy_says_so(engine) -> None:
    _receive(engine)
    decision = evaluate_state_admission(
        engine.state(),
        _candidate(engine, "ev-1"),
        _policy(trusted=("external-lens",), required=("external-lens",)),
    )

    assert decision.outcome == AdmissionOutcome.HOLD
    assert "REQUIRED_PROVIDER_MISSING:external-lens" in decision.reason_codes
    assert decision.can_enter_operational_state is False


def test_trusted_external_provider_may_preclude_but_not_admit_by_itself(engine) -> None:
    _receive(engine)
    candidate = _candidate(engine, "ev-1")
    assessment = _assessment(
        candidate,
        ProviderAdmissionDisposition.PRECLUDE,
    )
    decision = evaluate_state_admission(
        engine.state(),
        candidate,
        _policy(trusted=("external-lens",)),
        (assessment,),
    )

    assert decision.outcome == AdmissionOutcome.REJECT
    assert decision.assessed_provider_ids == ("external-lens",)
    assert decision.can_create_authority is False
    assert decision.can_issue_clearance is False


def test_untrusted_provider_input_fails_closed(engine) -> None:
    _receive(engine)
    candidate = _candidate(engine, "ev-1")
    assessment = _assessment(candidate, ProviderAdmissionDisposition.SUPPORT)

    with pytest.raises(FailClosedError, match="untrusted provider"):
        evaluate_state_admission(
            engine.state(),
            candidate,
            _policy(),
            (assessment,),
        )


def test_unresolved_and_contradicted_material_cannot_be_admitted(engine) -> None:
    _receive(engine)
    unresolved = _candidate(
        engine,
        "ev-1",
        unresolved_refs=("identity:unknown",),
    )
    decision = evaluate_state_admission(engine.state(), unresolved, _policy())
    assert decision.outcome == AdmissionOutcome.HOLD
    assert decision.unresolved_refs == ("identity:unknown",)

    event = create_admission_event(
        engine.state(),
        unresolved,
        _policy(),
        event_id="hold-unresolved",
    )
    engine.append(event)
    assert engine.state().evidence["ev-1"].status.value == "UNVERIFIED"


def test_unknown_entity_binding_is_retained_as_unresolved(engine) -> None:
    _receive(engine)
    candidate = _candidate(
        engine,
        "ev-1",
        entity_refs=("subject-1", "entity-missing"),
    )

    decision = evaluate_state_admission(engine.state(), candidate, _policy())

    assert decision.outcome == AdmissionOutcome.HOLD
    assert "entity:entity-missing" in decision.unresolved_refs


def test_direct_evidence_admission_bypass_is_rejected(engine) -> None:
    _receive(engine)
    with pytest.raises(KernelInvariantViolation, match="VALO admission decision"):
        engine.append(
            CanonicalEvent(
                event_id="direct-admit",
                event_type=EventType.EVIDENCE_ADMITTED,
                tenant_id="tenant-a",
                subject="ev-1",
                source="external-lens",
                payload={"evidence_id": "ev-1"},
            )
        )


def test_direct_evidence_rejection_bypass_is_rejected(engine) -> None:
    _receive(engine)
    with pytest.raises(KernelInvariantViolation, match="VALO admission decision"):
        engine.append(
            CanonicalEvent(
                event_id="direct-reject",
                event_type=EventType.EVIDENCE_REJECTED,
                tenant_id="tenant-a",
                subject="ev-1",
                source="external-lens",
                payload={"evidence_id": "ev-1"},
            )
        )


def test_tampered_admission_event_is_not_replayable(engine) -> None:
    _receive(engine)
    event = create_admission_event(
        engine.state(),
        _candidate(engine, "ev-1"),
        _policy(),
        event_id="admission-1",
    )
    payload = dict(event.payload)
    decision = dict(payload["decision"])
    decision["reason_codes"] = ["FABRICATED"]
    payload["decision"] = decision

    with pytest.raises(KernelInvariantViolation, match="invalid state admission"):
        engine.append(event.model_copy(update={"payload": payload}))


def test_admission_replay_is_deterministic(engine) -> None:
    _receive(engine)
    engine.append(
        create_admission_event(
            engine.state(),
            _candidate(engine, "ev-1"),
            _policy(),
            event_id="admission-1",
        )
    )
    assert replay(engine.events()).root_hash() == engine.state().root_hash()


def test_workspace_binds_hidden_admission_dependencies_and_detects_reversal(
    engine,
) -> None:
    _receive(engine)
    first_candidate = _candidate(engine, "ev-1")
    engine.append(
        create_admission_event(
            engine.state(),
            first_candidate,
            _policy(),
            event_id="admission-1",
            decision_id="decision-1",
        )
    )
    engine.append(
        CanonicalEvent(
            event_id="fact-1",
            event_type=EventType.FACT_ASSERTED,
            tenant_id="tenant-a",
            subject="subject-1",
            source="kernel",
            payload={
                "fact": Fact(
                    fact_id="fact-1",
                    subject="subject-1",
                    predicate="eligible",
                    object="true",
                    tenant_id="tenant-a",
                    provenance=make_provenance("fact-1"),
                )
            },
        )
    )
    engine.append(
        CanonicalEvent(
            event_id="confirm-fact-1",
            event_type=EventType.FACT_CONFIRMED,
            tenant_id="tenant-a",
            subject="subject-1",
            source="kernel",
            payload={"fact_id": "fact-1"},
            evidence_refs=["ev-1"],
        )
    )
    now = utcnow()
    purpose = Purpose(
        purpose_id="purpose-1",
        purpose_type="review",
        scope=[],
        basis="test",
        permitted_data=["facts:fact-1"],
        permitted_actions=[],
        validity=TimeWindow(
            valid_from=now - timedelta(minutes=1),
            valid_until=now + timedelta(hours=1),
        ),
    )
    engine.append(
        CanonicalEvent(
            event_id="purpose-1",
            event_type=EventType.PURPOSE_REGISTERED,
            tenant_id="tenant-a",
            subject="purpose-1",
            source="kernel",
            payload={"purpose": purpose},
        )
    )
    spec = WorkspaceSpec(
        workspace_id="workspace-1",
        work_unit_id="work-1",
        tenant_id="tenant-a",
        purpose_id="purpose-1",
        selectors=(ProjectionSelector(collection="facts", object_ids=("fact-1",)),),
        capabilities=(),
        allowed_output_kinds=(CandidateKind.ARTIFACT,),
        expires_at=now + timedelta(minutes=30),
        max_actions=0,
    )
    workspace = compile_governed_workspace(
        engine.state(),
        spec,
        source_event_position=engine.sequence(),
        moment=now,
    )
    dependency_refs = {item.ref for item in workspace.projection.dependencies}
    assert "evidence:ev-1" in dependency_refs
    assert "admissions:decision-1" in dependency_refs

    artifact_binding = ArtifactContextBinding(
        artifact_ref="artifact:1",
        artifact_digest="a" * 64,
        workspace_id="workspace-1",
        workspace_digest=workspace.workspace_digest,
        invocation_id="invocation-1",
        candidate_id="worker-result",
        worker_id="worker-1",
        session_id="session-1",
        continuation_nonce="nonce-1",
    )
    artifact_binding = artifact_binding.model_copy(
        update={"binding_digest": artifact_binding.computed_digest}
    )
    worker_candidate = create_candidate_result(
        candidate_id="worker-result",
        invocation_id="invocation-1",
        worker_id="worker-1",
        workspace_id="workspace-1",
        workspace_digest=workspace.workspace_digest,
        output_kind=CandidateKind.ARTIFACT,
        artifact_refs=("artifact:1",),
        artifact_bindings=(artifact_binding,),
    )
    assert (
        evaluate_candidate_conformance(
            workspace,
            worker_candidate,
            engine.state(),
            moment=now,
        ).outcome
        == ConformanceOutcome.PASS
    )

    second_candidate = _candidate(
        engine,
        "ev-1",
        candidate_id="candidate-2",
    )
    preclude = _assessment(
        second_candidate,
        ProviderAdmissionDisposition.PRECLUDE,
    )
    engine.append(
        create_admission_event(
            engine.state(),
            second_candidate,
            _policy(trusted=("external-lens",)),
            (preclude,),
            event_id="admission-2",
            decision_id="decision-2",
        )
    )
    report = evaluate_candidate_conformance(
        workspace,
        worker_candidate,
        engine.state(),
        moment=now,
    )
    assert report.outcome == ConformanceOutcome.DEFER
    assert engine.state().facts["fact-1"].truth_status == TruthStatus.STALE

