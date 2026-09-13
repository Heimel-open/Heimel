from __future__ import annotations

from datetime import timedelta

import pytest
from pydantic import ValidationError

from valo_kernel import (
    CandidateKind,
    ConformanceOutcome,
    Contract,
    FailClosedError,
    ProjectionSelector,
    ProposedAction,
    Purpose,
    TimeWindow,
    WorkspaceCapabilitySpec,
    WorkspaceSpec,
    bind_workspace_execution,
    compile_governed_workspace,
    create_candidate_result,
    evaluate_candidate_conformance,
    utcnow,
)
from valo_kernel.contracts import CanonicalEvent, EntityType, EventType

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


def _sign_contract(engine, *, valid_for: timedelta = timedelta(minutes=30)) -> Contract:
    now = utcnow()
    contract = Contract(
        contract_id="contract-1",
        parties=["customer", "supplier"],
        tenant_id="tenant-a",
        effective_period=TimeWindow(
            valid_from=now - timedelta(minutes=1),
            valid_until=now + valid_for,
        ),
    )
    engine.append(
        CanonicalEvent(
            event_id="sign-contract-1",
            event_type=EventType.CONTRACT_SIGNED,
            tenant_id="tenant-a",
            subject="contract-1",
            source="kernel",
            effective_at=now,
            payload={"contract": contract},
        )
    )
    return contract


def _spec(*, expires_at, governing_contract_ids=("contract-1",)) -> WorkspaceSpec:
    return WorkspaceSpec(
        workspace_id="workspace-1",
        work_unit_id="work-unit-1",
        tenant_id="tenant-a",
        purpose_id="purpose-1",
        program_ref="valo.jobs.reserve@1.0.0",
        program_digest="a" * 64,
        governing_contract_ids=governing_contract_ids,
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


def _candidate(workspace):
    return create_candidate_result(
        candidate_id="candidate-1",
        invocation_id="invocation-1",
        worker_id="worker-1",
        workspace_id=workspace.spec.workspace_id,
        workspace_digest=workspace.workspace_digest,
        output_kind=CandidateKind.EXTERNAL_ACTION,
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


@pytest.fixture
def contract_engine(engine):
    engine.append(
        entity_event(
            "tenant-a",
            "job-1",
            entity_type=EntityType.JOB,
            state="READY",
        )
    )
    _register_purpose(engine)
    _sign_contract(engine)
    return engine


def test_governing_contract_is_hidden_freshness_dependency(contract_engine) -> None:
    moment = utcnow()
    workspace = compile_governed_workspace(
        contract_engine.state(),
        _spec(expires_at=moment + timedelta(minutes=10)),
        source_event_position=contract_engine.sequence(),
        moment=moment,
    )

    assert "contracts:contract-1" not in {
        item.ref for item in workspace.projection.objects
    }
    assert "contracts:contract-1" in {
        item.ref for item in workspace.projection.dependencies
    }

    candidate = _candidate(workspace)
    report = evaluate_candidate_conformance(
        workspace,
        candidate,
        contract_engine.state(),
        moment=moment + timedelta(seconds=1),
    )
    assert report.outcome == ConformanceOutcome.PASS

    binding = bind_workspace_execution(
        workspace,
        candidate,
        report,
        action_id="action-1",
    )
    assert binding.governing_contract_ids == ("contract-1",)
    assert "contracts:contract-1" in {item.ref for item in binding.dependencies}


def test_contract_amendment_invalidates_continuation(contract_engine) -> None:
    moment = utcnow()
    workspace = compile_governed_workspace(
        contract_engine.state(),
        _spec(expires_at=moment + timedelta(minutes=10)),
        source_event_position=contract_engine.sequence(),
        moment=moment,
    )
    candidate = _candidate(workspace)

    contract_engine.append(
        CanonicalEvent(
            event_id="amend-contract-1",
            event_type=EventType.CONTRACT_AMENDED,
            tenant_id="tenant-a",
            subject="contract-1",
            source="kernel",
            payload={"contract_id": "contract-1"},
        )
    )

    report = evaluate_candidate_conformance(
        workspace,
        candidate,
        contract_engine.state(),
        moment=moment + timedelta(seconds=2),
    )
    assert report.outcome == ConformanceOutcome.DEFER
    assert {item.code for item in report.mismatches} == {
        "GOVERNING_CONTRACT_DRIFT"
    }
    assert report.mismatches[0].pointer == "contracts:contract-1"


def test_terminated_or_unknown_governing_contract_fails_closed(contract_engine) -> None:
    moment = utcnow()
    contract_engine.append(
        CanonicalEvent(
            event_id="terminate-contract-1",
            event_type=EventType.CONTRACT_TERMINATED,
            tenant_id="tenant-a",
            subject="contract-1",
            source="kernel",
            payload={"contract_id": "contract-1"},
        )
    )
    with pytest.raises(FailClosedError, match="not operative"):
        compile_governed_workspace(
            contract_engine.state(),
            _spec(expires_at=moment + timedelta(minutes=10)),
            source_event_position=contract_engine.sequence(),
            moment=moment,
        )

    with pytest.raises(FailClosedError, match="unknown governing contract"):
        compile_governed_workspace(
            contract_engine.state(),
            _spec(
                expires_at=moment + timedelta(minutes=10),
                governing_contract_ids=("missing-contract",),
            ),
            source_event_position=contract_engine.sequence(),
            moment=moment,
        )


def test_workspace_cannot_outlive_governing_contract(engine) -> None:
    engine.append(
        entity_event(
            "tenant-a",
            "job-1",
            entity_type=EntityType.JOB,
            state="READY",
        )
    )
    _register_purpose(engine)
    contract = _sign_contract(engine, valid_for=timedelta(minutes=5))
    moment = utcnow()

    with pytest.raises(FailClosedError, match="cannot outlive governing contract"):
        compile_governed_workspace(
            engine.state(),
            _spec(expires_at=contract.effective_period.valid_until + timedelta(seconds=1)),
            source_event_position=engine.sequence(),
            moment=moment,
        )


def test_governing_contract_ids_are_unique() -> None:
    with pytest.raises(ValidationError, match="governing contract ids must be unique"):
        _spec(
            expires_at=utcnow() + timedelta(minutes=5),
            governing_contract_ids=("contract-1", "contract-1"),
        )
