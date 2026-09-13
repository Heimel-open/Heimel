from datetime import UTC, datetime

import pytest

from valo_kernel.contracts import (
    IncidentPhase,
    IncidentPostState,
    IncidentSeverity,
    IncidentState,
    transition_incident,
)

NOW = datetime(2026, 8, 16, 19, 0, tzinfo=UTC)


def _open() -> IncidentState:
    return IncidentState(
        incident_id="incident-7",
        tenant_id="tenant-a",
        subject_ref="service/payments",
        updated_at=NOW,
    )


def test_severity_is_independent_of_root_cause() -> None:
    diagnosing = transition_incident(
        _open(), IncidentPhase.DIAGNOSING, severity=IncidentSeverity.SEV1, updated_at=NOW
    )
    assert diagnosing.severity is IncidentSeverity.SEV1
    assert diagnosing.root_cause_ref is None
    assert diagnosing.phase is IncidentPhase.DIAGNOSING


def test_incident_cannot_skip_governed_lifecycle() -> None:
    with pytest.raises(ValueError, match="illegal incident transition"):
        transition_incident(_open(), IncidentPhase.EXECUTED, execution_ref="exec-1")


def test_resolved_requires_authorized_execution_and_matching_poststate() -> None:
    state = transition_incident(_open(), IncidentPhase.DIAGNOSING, updated_at=NOW)
    state = transition_incident(
        state,
        IncidentPhase.REMEDIATION_PROPOSED,
        remediation_ref="remediation-1",
        updated_at=NOW,
    )
    state = transition_incident(
        state,
        IncidentPhase.AUTHORIZED,
        authorization_ref="auth-1",
        updated_at=NOW,
    )
    state = transition_incident(
        state,
        IncidentPhase.EXECUTED,
        execution_ref="exec-1",
        updated_at=NOW,
    )
    state = transition_incident(state, IncidentPhase.VERIFYING, updated_at=NOW)

    with pytest.raises(ValueError, match="matching verified post-state"):
        transition_incident(
            state,
            IncidentPhase.RESOLVED,
            poststate_ref="post-1",
            poststate_status=IncidentPostState.DIVERGED,
            updated_at=NOW,
        )

    resolved = transition_incident(
        state,
        IncidentPhase.RESOLVED,
        poststate_ref="post-1",
        poststate_status=IncidentPostState.MATCH,
        updated_at=NOW,
    )
    assert resolved.phase is IncidentPhase.RESOLVED
    assert resolved.version == 7

    with pytest.raises(ValueError, match="illegal incident transition"):
        transition_incident(resolved, IncidentPhase.DIAGNOSING)
