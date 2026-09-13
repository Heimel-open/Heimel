from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

import pytest

from valo_reht.active_session import (
    ActiveExecutionSession,
    ObservationSource,
    SessionDisposition,
    SessionObservation,
    SessionState,
)
from valo_reht.contracts import DecisionResult
from valo_reht.runtime_interlocks import RuntimeControlPlane


def _digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _action() -> dict[str, Any]:
    return {
        "action_id": "action:session",
        "capability": "OPERATE_MACHINE",
        "action_type": "OPERATE_MACHINE",
        "target": "machine:1",
        "actor_id": "actor:1",
        "principal_id": "principal:1",
    }


def _context(version: int = 1) -> dict[str, Any]:
    return {
        "state_version": version,
        "actor_id": "actor:1",
        "principal_id": "principal:1",
        "authority_state_id": "authority:1",
    }


def _allow(context: dict[str, Any], *, suffix: str = "1") -> DecisionResult:
    return DecisionResult(
        decision="ALLOW",
        clearance_ref=f"clearance:{suffix}",
        permit_ref=f"permit:{suffix}",
        execution_context_hash=_digest(context),
    )


class StaticReht:
    def __init__(self, decision: str = "ALLOW") -> None:
        self.decision = decision
        self.seen: list[tuple[dict[str, Any], dict[str, Any]]] = []

    def authorize(
        self,
        execution_context: dict[str, Any],
        action_contract: dict[str, Any],
    ) -> DecisionResult:
        self.seen.append((deepcopy(execution_context), deepcopy(action_contract)))
        if self.decision != "ALLOW":
            return DecisionResult(decision=self.decision, reason="reauthorization denied")
        return DecisionResult(
            decision="ALLOW",
            clearance_ref="clearance:fresh",
            permit_ref="permit:fresh",
            execution_context_hash=_digest(execution_context),
        )


def _session(*, control: RuntimeControlPlane | None = None) -> ActiveExecutionSession:
    context = _context()
    return ActiveExecutionSession(
        action_contract=_action(),
        execution_context=context,
        decision=_allow(context),
        runtime_control=control,
        dynamic_bounds={
            "max_usd": 100.0,
            "targets": ("a", "b"),
            "may_retry": True,
            "mode": "bounded",
        },
    )


def test_session_requires_real_reht_allow_and_binding() -> None:
    with pytest.raises(ValueError, match="requires REHT ALLOW"):
        ActiveExecutionSession(
            action_contract=_action(),
            execution_context=_context(),
            decision=DecisionResult(decision="DENY"),
        )
    with pytest.raises(ValueError, match="does not match REHT binding"):
        ActiveExecutionSession(
            action_contract=_action(),
            execution_context=_context(),
            decision=DecisionResult(
                decision="ALLOW",
                clearance_ref="c",
                permit_ref="p",
                execution_context_hash="wrong",
            ),
        )


def test_sensor_continue_on_same_context_keeps_session_current() -> None:
    session = _session()
    checkpoint = session.observe(
        execution_context=_context(),
        observation=SessionObservation(
            ObservationSource.SENSOR,
            SessionDisposition.CONTINUE,
            evidence_refs=("sensor:1",),
        ),
    )
    assert checkpoint.valid_for_continuation is True
    assert checkpoint.requires_reauthorization is False
    assert session.state is SessionState.RUNNING


def test_context_change_forces_reauthorization_even_if_watcher_says_continue() -> None:
    session = _session()
    checkpoint = session.observe(
        execution_context=_context(version=2),
        observation=SessionObservation(
            ObservationSource.WATCHER,
            SessionDisposition.CONTINUE,
        ),
    )
    assert checkpoint.disposition is SessionDisposition.REAUTHORIZE
    assert checkpoint.reason == "EXECUTION_CONTEXT_CHANGED"
    assert checkpoint.valid_for_continuation is False
    assert session.state is SessionState.PAUSED
    assert session.requires_reauthorization is True


def test_fresh_reht_allow_is_required_to_resume_changed_context() -> None:
    session = _session()
    changed = _context(version=2)
    session.observe(
        execution_context=changed,
        observation=SessionObservation(
            ObservationSource.SYSTEM,
            SessionDisposition.CONTINUE,
        ),
    )
    reht = StaticReht("ALLOW")
    checkpoint = session.reauthorize(reht=reht, execution_context=changed)
    assert checkpoint.reason == "REAUTHORIZED_BY_REHT"
    assert checkpoint.valid_for_continuation is True
    assert session.state is SessionState.RUNNING
    assert session.requires_reauthorization is False
    assert reht.seen


def test_failed_reauthorization_remains_halted() -> None:
    session = _session()
    changed = _context(version=2)
    session.observe(
        execution_context=changed,
        observation=SessionObservation(
            ObservationSource.WATCHER,
            SessionDisposition.REAUTHORIZE,
        ),
    )
    denied = session.reauthorize(reht=StaticReht("DENY"), execution_context=changed)
    assert denied.disposition is SessionDisposition.HALT
    assert session.state is SessionState.HALTED

    later = session.observe(
        execution_context=changed,
        observation=SessionObservation(
            ObservationSource.HUMAN,
            SessionDisposition.CONTINUE,
        ),
    )
    assert later.disposition is SessionDisposition.HALT
    assert session.state is SessionState.HALTED


def test_runtime_global_halt_stops_active_session_without_creating_decision() -> None:
    control = RuntimeControlPlane()
    session = _session(control=control)
    control.halt_global()
    checkpoint = session.observe(
        execution_context=_context(),
        observation=SessionObservation(
            ObservationSource.WATCHER,
            SessionDisposition.CONTINUE,
        ),
    )
    assert checkpoint.disposition is SessionDisposition.HALT
    assert checkpoint.reason == "HALT_GLOBAL"
    assert checkpoint.authority_granted is False
    assert session.state is SessionState.HALTED


@pytest.mark.parametrize(
    "disposition,expected_state",
    [
        (SessionDisposition.PAUSE, SessionState.PAUSED),
        (SessionDisposition.STOP, SessionState.HALTED),
        (SessionDisposition.HALT, SessionState.HALTED),
        (SessionDisposition.ROLLBACK, SessionState.PAUSED),
        (SessionDisposition.HANDOVER, SessionState.PAUSED),
    ],
)
def test_runtime_observation_dispositions_are_mechanical_only(
    disposition: SessionDisposition,
    expected_state: SessionState,
) -> None:
    session = _session()
    checkpoint = session.observe(
        execution_context=_context(),
        observation=SessionObservation(
            ObservationSource.WATCHER,
            disposition,
            reason="watcher signal",
        ),
    )
    assert session.state is expected_state
    assert checkpoint.authority_granted is False
    if disposition in {SessionDisposition.ROLLBACK, SessionDisposition.HANDOVER}:
        assert session.requires_reauthorization is True


def test_runtime_observation_cannot_grant_authority() -> None:
    with pytest.raises(ValueError, match="cannot grant execution authority"):
        SessionObservation(
            ObservationSource.SENSOR,
            SessionDisposition.CONTINUE,
            authority_granted=True,
        )


def test_numeric_bounds_can_only_narrow() -> None:
    session = _session()
    session.observe(
        execution_context=_context(),
        observation=SessionObservation(
            ObservationSource.SYSTEM,
            SessionDisposition.CONTINUE,
            bound_updates={"max_usd": 50.0},
        ),
    )
    assert session.dynamic_bounds["max_usd"] == 50.0
    with pytest.raises(ValueError, match="cannot widen"):
        session.observe(
            execution_context=_context(),
            observation=SessionObservation(
                ObservationSource.SYSTEM,
                SessionDisposition.CONTINUE,
                bound_updates={"max_usd": 60.0},
            ),
        )


def test_set_and_boolean_bounds_can_only_narrow() -> None:
    session = _session()
    session.observe(
        execution_context=_context(),
        observation=SessionObservation(
            ObservationSource.SYSTEM,
            SessionDisposition.CONTINUE,
            bound_updates={"targets": ("a",), "may_retry": False},
        ),
    )
    assert session.dynamic_bounds["targets"] == ("a",)
    assert session.dynamic_bounds["may_retry"] is False

    with pytest.raises(ValueError, match="cannot widen"):
        session.observe(
            execution_context=_context(),
            observation=SessionObservation(
                ObservationSource.SYSTEM,
                SessionDisposition.CONTINUE,
                bound_updates={"targets": ("a", "b")},
            ),
        )
    with pytest.raises(ValueError, match="cannot widen"):
        session.observe(
            execution_context=_context(),
            observation=SessionObservation(
                ObservationSource.SYSTEM,
                SessionDisposition.CONTINUE,
                bound_updates={"may_retry": True},
            ),
        )


def test_new_runtime_bound_cannot_be_injected_mid_session() -> None:
    session = _session()
    with pytest.raises(ValueError, match="cannot be introduced"):
        session.observe(
            execution_context=_context(),
            observation=SessionObservation(
                ObservationSource.EXECUTOR,
                SessionDisposition.CONTINUE,
                bound_updates={"new_capability": 1},
            ),
        )


def test_completion_requires_current_context() -> None:
    session = _session()
    checkpoint = session.complete(execution_context=_context(version=2))
    assert checkpoint.disposition is SessionDisposition.REAUTHORIZE
    assert session.state is SessionState.PAUSED


def test_current_session_can_complete_but_cannot_continue_after_completion() -> None:
    session = _session()
    completed = session.complete(execution_context=_context())
    assert completed.reason == "SESSION_COMPLETED"
    assert session.state is SessionState.COMPLETED
    later = session.observe(
        execution_context=_context(),
        observation=SessionObservation(
            ObservationSource.SENSOR,
            SessionDisposition.CONTINUE,
        ),
    )
    assert later.disposition is SessionDisposition.HALT
    assert session.state is SessionState.COMPLETED
