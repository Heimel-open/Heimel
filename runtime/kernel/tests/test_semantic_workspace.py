from __future__ import annotations

from datetime import timedelta

import pytest

from valo_kernel import (
    CandidateClaim,
    CandidateKind,
    CanonicalEvent,
    ConformanceOutcome,
    EntityType,
    EventType,
    FailClosedError,
    ProjectionSelector,
    ProposedAction,
    Purpose,
    SemanticTerm,
    SemanticTermKind,
    TimeWindow,
    TruthStatus,
    WorkspaceCapabilitySpec,
    WorkspaceSpec,
    bind_semantic_workspace_execution,
    compile_semantic_governed_workspace,
    create_candidate_result,
    create_semantic_contract,
    evaluate_semantic_candidate_conformance,
    utcnow,
)

from .conftest import entity_event


def _register_purpose(engine) -> None:
    now = utcnow()
    purpose = Purpose(
        purpose_id="purpose-1",
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
            event_id="register-purpose-1",
            event_type=EventType.PURPOSE_REGISTERED,
            tenant_id="tenant-a",
            subject="purpose-1",
            source="kernel",
            effective_at=now,
            payload={"purpose": purpose},
        )
    )


def _spec(*, expires_at) -> WorkspaceSpec:
    return WorkspaceSpec(
        workspace_id="workspace-1",
        work_unit_id="work-unit-1",
        tenant_id="tenant-a",
        purpose_id="purpose-1",
        selectors=(
            ProjectionSelector(collection="entities", object_ids=("job-1",)),
        ),
        capabilities=(
            WorkspaceCapabilitySpec(
                capability="BOOK",
                target_refs=("job-1",),
                allowed_effects=("reserve",),
            ),
        ),
        allowed_output_kinds=(CandidateKind.EXTERNAL_ACTION,),
        expires_at=expires_at,
    )


def _semantic_contract(*, include_entity: bool = True):
    terms = [
        SemanticTerm(
            term_id="valo:predicate:is_reservable",
            kind=SemanticTermKind.PREDICATE,
            kernel_value="is_reservable",
            definition="The referenced job can be proposed for reservation.",
            aliases=("can_book",),
        )
    ]
    if include_entity:
        terms.append(
            SemanticTerm(
                term_id="valo:entity-type:job",
                kind=SemanticTermKind.ENTITY_TYPE,
                kernel_value=EntityType.JOB.value,
                definition="A canonical Kernel job entity.",
                aliases=("work_order",),
            )
        )
    return create_semantic_contract(
        ontology_id="valo.operations",
        ontology_version="1.0.0",
        terms=tuple(terms),
    )


@pytest.fixture
def semantic_engine(engine):
    engine.append(
        entity_event(
            "tenant-a",
            "job-1",
            entity_type=EntityType.JOB,
            state="READY",
        )
    )
    _register_purpose(engine)
    return engine


def _workspace(semantic_engine):
    moment = utcnow()
    return compile_semantic_governed_workspace(
        semantic_engine.state(),
        _spec(expires_at=moment + timedelta(minutes=30)),
        _semantic_contract(),
        source_event_position=semantic_engine.sequence(),
        moment=moment,
    )


def _candidate(workspace, *, predicate="is_reservable", subject="job-1"):
    return create_candidate_result(
        candidate_id="candidate-1",
        invocation_id="invocation-1",
        worker_id="worker-a",
        workspace_id=workspace.base_workspace.spec.workspace_id,
        workspace_digest=workspace.workspace_digest,
        output_kind=CandidateKind.EXTERNAL_ACTION,
        claims=(
            CandidateClaim(
                claim_id="claim-1",
                subject=subject,
                predicate=predicate,
                object="true",
                truth_status=TruthStatus.INFERRED,
                source_refs=("entities:job-1",),
            ),
        ),
        proposed_actions=(
            ProposedAction(
                action_id="action-1",
                capability="BOOK",
                target="job-1",
                purpose_id="purpose-1",
                declared_effects=("reserve",),
            ),
        ),
    )


def test_semantic_workspace_digest_binds_ontology_and_base_state(
    semantic_engine,
) -> None:
    workspace = _workspace(semantic_engine)

    assert workspace.workspace_digest == workspace.computed_digest
    assert workspace.semantic_contract.contract_digest == (
        workspace.semantic_contract.computed_digest
    )
    assert workspace.workspace_digest != workspace.base_workspace.workspace_digest
    assert workspace.authority_effect == "NO_AUTHORITY_CREATION"
    assert workspace.can_issue_clearance is False


def test_compile_fails_closed_when_ontology_does_not_cover_projected_type(
    semantic_engine,
) -> None:
    moment = utcnow()
    with pytest.raises(FailClosedError, match="does not cover projected Kernel meaning"):
        compile_semantic_governed_workspace(
            semantic_engine.state(),
            _spec(expires_at=moment + timedelta(minutes=30)),
            _semantic_contract(include_entity=False),
            source_event_position=semantic_engine.sequence(),
            moment=moment,
        )


def test_semantic_alias_resolves_to_one_canonical_predicate(semantic_engine) -> None:
    workspace = _workspace(semantic_engine)
    candidate = _candidate(workspace, predicate="can_book")

    report = evaluate_semantic_candidate_conformance(
        workspace,
        candidate,
        semantic_engine.state(),
    )

    assert report.outcome == ConformanceOutcome.PASS
    assert report.resolutions[0].predicate_term_id == "valo:predicate:is_reservable"
    assert report.resolutions[0].subject_ref == "entities:job-1"
    assert report.semantic_contract_digest == workspace.semantic_contract.contract_digest


def test_unknown_predicate_requires_redo_even_with_valid_source_ref(
    semantic_engine,
) -> None:
    workspace = _workspace(semantic_engine)
    candidate = _candidate(workspace, predicate="looks_bookable")

    report = evaluate_semantic_candidate_conformance(
        workspace,
        candidate,
        semantic_engine.state(),
    )

    assert report.outcome == ConformanceOutcome.REDO
    assert {item.code for item in report.mismatches} == {
        "SEMANTIC_PREDICATE_ESCAPE"
    }


def test_wrong_subject_is_denied_even_when_provenance_is_inside_workspace(
    semantic_engine,
) -> None:
    workspace = _workspace(semantic_engine)
    candidate = _candidate(workspace, subject="job-other")

    report = evaluate_semantic_candidate_conformance(
        workspace,
        candidate,
        semantic_engine.state(),
    )

    assert report.outcome == ConformanceOutcome.DENY
    assert "SEMANTIC_SUBJECT_ESCAPE" in {item.code for item in report.mismatches}


def test_execution_binding_carries_semantic_lineage(semantic_engine) -> None:
    workspace = _workspace(semantic_engine)
    candidate = _candidate(workspace, predicate="can_book")
    report = evaluate_semantic_candidate_conformance(
        workspace,
        candidate,
        semantic_engine.state(),
    )

    binding = bind_semantic_workspace_execution(
        workspace,
        candidate,
        report,
        action_id="action-1",
    )

    assert binding.workspace_digest == workspace.workspace_digest
    assert binding.semantic_contract_digest == workspace.semantic_contract.contract_digest
    assert binding.ontology_id == "valo.operations"
    assert binding.ontology_version == "1.0.0"
