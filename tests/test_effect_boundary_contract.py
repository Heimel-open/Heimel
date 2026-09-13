from __future__ import annotations

import pytest
from pydantic import ValidationError

from valo_kernel import (
    ConformanceOutcome,
    EntityType,
    FailClosedError,
    KernelEngine,
    PersistentStateBinding,
    PersistentStateKind,
    ProposedAction,
    bind_workspace_execution,
    evaluate_candidate_conformance,
)

from .conftest import entity_event
from .test_workspace import _candidate, _register_purpose, _workspace


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
    _register_purpose(engine)
    return engine


def test_kernel_exposes_no_direct_execution_path() -> None:
    assert not hasattr(KernelEngine, "execute")


@pytest.mark.parametrize(
    "outcome",
    (
        ConformanceOutcome.DEFER,
        ConformanceOutcome.STEP_UP,
        ConformanceOutcome.DENY,
        ConformanceOutcome.HALT,
    ),
)
def test_non_pass_outcomes_produce_no_execution_binding(
    governed_engine,
    outcome: ConformanceOutcome,
) -> None:
    workspace = _workspace(
        governed_engine,
        step_up_required=outcome is ConformanceOutcome.STEP_UP,
    )
    candidate = _candidate(workspace)
    if outcome is ConformanceOutcome.DEFER:
        candidate = _candidate(workspace, unknowns=("governance basis",))
    elif outcome is ConformanceOutcome.DENY:
        action = ProposedAction(
            action_id="action-1",
            capability="DELETE",
            target="job-1",
            purpose_id="purpose-1",
            declared_effects=("destroy",),
        )
        candidate = _candidate(workspace, proposed_actions=(action,))
    elif outcome is ConformanceOutcome.HALT:
        candidate = candidate.model_copy(update={"worker_id": "tampered"})

    report = evaluate_candidate_conformance(
        workspace,
        candidate,
        governed_engine.state(),
    )

    assert report.outcome is outcome
    with pytest.raises(FailClosedError, match="only PASS"):
        bind_workspace_execution(
            workspace,
            candidate,
            report,
            action_id="action-1",
        )


def _memory_binding_values() -> dict[str, object]:
    return {
        "persistent_ref": "memory:decision-context",
        "state_kind": PersistentStateKind.MEMORY,
        "content_digest": "a" * 64,
        "workspace_id": "workspace-1",
        "workspace_digest": "b" * 64,
        "source_state_root": "c" * 64,
        "source_ref": "evidence:memory-1",
        "source_object_digest": "d" * 64,
        "purpose_id": "purpose-1",
    }


def test_decision_relevant_memory_cannot_enter_from_direct_source() -> None:
    values = _memory_binding_values()
    values["source_ref"] = "memory:agent-local"
    with pytest.raises(ValidationError, match="admitted evidence"):
        PersistentStateBinding(**values)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("read_only", False),
        ("requires_fresh_admission", False),
        ("can_self_propagate", True),
        ("can_issue_clearance", True),
    ),
)
def test_persistent_memory_cannot_widen_its_governance_contract(
    field: str,
    value: bool,
) -> None:
    values = _memory_binding_values()
    values[field] = value
    with pytest.raises(ValidationError):
        PersistentStateBinding(**values)
