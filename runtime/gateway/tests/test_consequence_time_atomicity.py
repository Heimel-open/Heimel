from __future__ import annotations

from datetime import datetime
from threading import Event, Thread

import pytest

from tests.conftest import make_chain
from valo_gateway import ValoGateway
from valo_gateway.gateway import ControlEvent, ControlEventType, RuntimeControlPlane
from valo_gateway.gateway.permit_consumption import SQLitePermitConsumptionStore
from valo_gateway.tool_adapters import FunctionTool


class PausingPermitConsumptionStore:
    def __init__(self, delegate: SQLitePermitConsumptionStore) -> None:
        self._delegate = delegate
        self.consume_reached = Event()
        self.release_consume = Event()

    def consume_once(self, permit_id: str, consumed_at: datetime) -> bool:
        self.consume_reached.set()
        if not self.release_consume.wait(timeout=5):
            raise AssertionError("timed out waiting to release permit consumption")
        return self._delegate.consume_once(permit_id, consumed_at)


def _revocation(authority_envelope_id: str) -> ControlEvent:
    return ControlEvent(
        event_type=ControlEventType.REVOKE_AUTHORITY,
        issuer_id="consequence-time-atomicity-test",
        reason="deterministic consequence-time race",
        authority_envelope_id=authority_envelope_id,
    )


def test_revocation_before_consequence_blocks_effect(tmp_path):
    now, authority, action, clearance, permit = make_chain()
    control = RuntimeControlPlane()
    gateway = ValoGateway(
        control_plane=control,
        permit_store=SQLitePermitConsumptionStore(tmp_path / "permits.sqlite3"),
    )
    effects: list[str] = []

    control.apply(_revocation(authority.envelope_id))

    with pytest.raises(ValueError, match="revocation or HALT"):
        gateway.execute(
            authority=authority,
            clearance=clearance,
            permit=permit,
            action=action,
            executor_id="revocation-wins",
            tool=FunctionTool("effect", lambda: effects.append("EFFECT_OCCURRED")),
            now=now,
        )

    assert effects == []


def test_revocation_cannot_apply_inside_consequence_commit(tmp_path):
    now, authority, action, clearance, permit = make_chain()
    control = RuntimeControlPlane()
    pausing_store = PausingPermitConsumptionStore(
        SQLitePermitConsumptionStore(tmp_path / "permits.sqlite3")
    )
    gateway = ValoGateway(control_plane=control, permit_store=pausing_store)

    effects: list[str] = []
    worker_errors: list[BaseException] = []
    revocation_errors: list[BaseException] = []
    revocation_started = Event()
    revocation_applied = Event()

    def execute() -> None:
        try:
            gateway.execute(
                authority=authority,
                clearance=clearance,
                permit=permit,
                action=action,
                executor_id="consequence-wins",
                tool=FunctionTool("effect", lambda: effects.append("EFFECT_OCCURRED")),
                now=now,
            )
        except BaseException as exc:
            worker_errors.append(exc)

    def revoke() -> None:
        revocation_started.set()
        try:
            control.apply(_revocation(authority.envelope_id))
            revocation_applied.set()
        except BaseException as exc:
            revocation_errors.append(exc)

    worker = Thread(target=execute)
    worker.start()
    assert pausing_store.consume_reached.wait(timeout=5)

    revoker = Thread(target=revoke)
    revoker.start()
    assert revocation_started.wait(timeout=5)

    assert not revocation_applied.wait(timeout=0.1)

    pausing_store.release_consume.set()
    worker.join(timeout=5)
    revoker.join(timeout=5)

    assert not worker.is_alive()
    assert not revoker.is_alive()
    assert worker_errors == []
    assert revocation_errors == []
    assert effects == ["EFFECT_OCCURRED"]
    assert revocation_applied.is_set()
