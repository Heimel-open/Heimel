from __future__ import annotations

import pytest

from valo_edge.contracts import (
    ConsequenceDecision,
    EdgeActionCommitmentV1,
    EdgeClearanceV1,
)
from valo_edge.gateway import (
    DeviceCommandV1,
    DeviceEnforcementGatewayV1,
    DriverExecutionStatus,
    DriverOutcomeV1,
)
from valo_edge.runtime import HmacAuthorityVerifier, MicroRehtV1
from valo_edge.runtime.contracts_v1 import MicroRehtStateV1, PermitStateV1


NOW = "2026-08-08T16:00:02Z"


def _proposal() -> EdgeActionCommitmentV1:
    return EdgeActionCommitmentV1(
        proposal_id="proposal-001",
        device_id="pump-7",
        action_type="SET_FLOW",
        parameters={"litres_per_minute": 2.5, "enabled": True},
        model_hash="sha256:model",
        firmware_hash="sha256:firmware",
        runtime_hash="sha256:runtime",
        sensor_evidence_digest="sha256:sensors",
        physical_state_digest="sha256:state",
        authority_envelope_digest="sha256:authority",
        boot_epoch="boot-44",
        sequence=17,
        nonce="nonce-001",
        issued_at_iso="2026-08-08T16:00:00Z",
        valid_until_iso="2026-08-08T16:00:10Z",
        signer_key_id="device-key-7",
    )


def _clearance(
    proposal: EdgeActionCommitmentV1,
    *,
    decision: ConsequenceDecision = ConsequenceDecision.ALLOW,
    permit_uses: int = 2,
) -> EdgeClearanceV1:
    return EdgeClearanceV1(
        clearance_id="clearance-001",
        proposal_digest=proposal.compute_digest(),
        evidence_digest="sha256:evidence",
        authority_envelope_digest=proposal.authority_envelope_digest,
        decision=decision,
        reason_codes=["TEST"],
        issued_at_iso="2026-08-08T16:00:01Z",
        valid_until_iso="2026-08-08T16:00:05Z",
        boot_epoch=proposal.boot_epoch,
        sequence=proposal.sequence,
        permit_id="permit-001" if decision is ConsequenceDecision.ALLOW else None,
        permit_uses=permit_uses if decision is ConsequenceDecision.ALLOW else 0,
        signer_key_id="micro-reht-key-1",
    )


def _command(
    proposal: EdgeActionCommitmentV1,
    *,
    command_id: str = "command-001",
    permit_use_index: int = 0,
) -> DeviceCommandV1:
    return DeviceCommandV1(
        command_id=command_id,
        proposal_digest=proposal.compute_digest(),
        device_id=proposal.device_id,
        action_type=proposal.action_type,
        parameters=proposal.parameters,
        permit_id="permit-001",
        permit_use_index=permit_use_index,
        issued_at_iso=NOW,
    )


class PermitStore:
    def __init__(self, remaining: int = 2) -> None:
        self.remaining = remaining
        self.calls = 0

    def consume(self, permit_id: str, proposal_digest: str) -> bool:
        self.calls += 1
        if permit_id != "permit-001" or proposal_digest != _proposal().compute_digest():
            return False
        if self.remaining <= 0:
            return False
        self.remaining -= 1
        return True


class RecordingDriver:
    def __init__(self, outcome: DriverOutcomeV1 | None = None) -> None:
        self.calls: list[DeviceCommandV1] = []
        self.outcome = outcome or DriverOutcomeV1(
            status=DriverExecutionStatus.EXECUTED,
            observed_output={"actual_flow": 2.48},
        )

    def execute(self, command: DeviceCommandV1) -> DriverOutcomeV1:
        self.calls.append(command)
        return self.outcome


def _gateway(
    store: PermitStore,
    driver: RecordingDriver,
    *,
    verifier=lambda clearance: clearance.signer_key_id == "micro-reht-key-1",
) -> DeviceEnforcementGatewayV1:
    return DeviceEnforcementGatewayV1(
        gateway_id="gateway-1",
        clearance_verifier=verifier,
        permit_consumer=store.consume,
        driver=driver,
    )


def test_exact_bound_allow_consumes_permit_and_calls_driver():
    proposal = _proposal()
    clearance = _clearance(proposal)
    command = _command(proposal)
    store = PermitStore()
    driver = RecordingDriver()

    result = _gateway(store, driver).enforce(proposal, clearance, command, now_iso=NOW)

    assert result.enforcement.accepted is True
    assert result.enforcement.proposal_digest == proposal.compute_digest()
    assert result.enforcement.clearance_digest == clearance.compute_digest()
    assert result.enforcement.device_command_digest == command.compute_digest()
    assert result.driver_outcome.status is DriverExecutionStatus.EXECUTED
    assert store.remaining == 1
    assert len(driver.calls) == 1


def test_changed_parameters_are_rejected_before_permit_consumption():
    proposal = _proposal()
    clearance = _clearance(proposal)
    command = _command(proposal).model_copy(update={"parameters": {"litres_per_minute": 9.0}})
    store = PermitStore()
    driver = RecordingDriver()

    result = _gateway(store, driver).enforce(proposal, clearance, command, now_iso=NOW)

    assert result.enforcement.accepted is False
    assert result.driver_outcome.error_code == "COMMAND_PARAMETERS_MISMATCH"
    assert store.calls == 0
    assert driver.calls == []


@pytest.mark.parametrize(
    "decision",
    [
        ConsequenceDecision.DENY,
        ConsequenceDecision.DEFER,
        ConsequenceDecision.STEP_UP,
        ConsequenceDecision.HALT,
    ],
)
def test_non_allow_never_reaches_driver(decision: ConsequenceDecision):
    proposal = _proposal()
    clearance = _clearance(proposal, decision=decision)
    command = _command(proposal)
    store = PermitStore()
    driver = RecordingDriver()

    result = _gateway(store, driver).enforce(proposal, clearance, command, now_iso=NOW)

    assert result.enforcement.accepted is False
    assert result.driver_outcome.error_code == f"CLEARANCE_{decision.value}"
    assert store.calls == 0
    assert driver.calls == []


def test_unverified_clearance_is_rejected():
    proposal = _proposal()
    store = PermitStore()
    driver = RecordingDriver()
    gateway = _gateway(store, driver, verifier=lambda _: False)

    result = gateway.enforce(proposal, _clearance(proposal), _command(proposal), now_iso=NOW)

    assert result.driver_outcome.error_code == "CLEARANCE_VERIFICATION_FAILED"
    assert store.calls == 0


def test_expired_clearance_is_rejected():
    proposal = _proposal()
    clearance = _clearance(proposal).model_copy(update={"valid_until_iso": "2026-08-08T15:59:59Z"})
    store = PermitStore()
    driver = RecordingDriver()

    result = _gateway(store, driver).enforce(proposal, clearance, _command(proposal), now_iso=NOW)

    assert result.driver_outcome.error_code == "CLEARANCE_EXPIRED_OR_NOT_YET_VALID"
    assert store.calls == 0


def test_device_and_action_binding_are_exact():
    proposal = _proposal()
    clearance = _clearance(proposal)
    store = PermitStore()
    driver = RecordingDriver()
    gateway = _gateway(store, driver)

    wrong_device = _command(proposal).model_copy(update={"device_id": "pump-8"})
    assert gateway.enforce(proposal, clearance, wrong_device, now_iso=NOW).driver_outcome.error_code == "COMMAND_DEVICE_MISMATCH"

    wrong_action = _command(proposal, command_id="command-002").model_copy(update={"action_type": "STOP"})
    assert gateway.enforce(proposal, clearance, wrong_action, now_iso=NOW).driver_outcome.error_code == "COMMAND_ACTION_MISMATCH"
    assert store.calls == 0


def test_permit_id_and_use_index_must_match_clearance():
    proposal = _proposal()
    clearance = _clearance(proposal, permit_uses=1)
    store = PermitStore()
    driver = RecordingDriver()
    gateway = _gateway(store, driver)

    wrong_id = _command(proposal).model_copy(update={"permit_id": "permit-other"})
    assert gateway.enforce(proposal, clearance, wrong_id, now_iso=NOW).driver_outcome.error_code == "COMMAND_PERMIT_MISMATCH"

    out_of_range = _command(proposal, command_id="command-002", permit_use_index=1)
    assert gateway.enforce(proposal, clearance, out_of_range, now_iso=NOW).driver_outcome.error_code == "PERMIT_USE_OUT_OF_RANGE"
    assert store.calls == 0


def test_same_command_cannot_be_replayed_even_when_permit_has_more_uses():
    proposal = _proposal()
    clearance = _clearance(proposal, permit_uses=2)
    command = _command(proposal)
    store = PermitStore(remaining=2)
    driver = RecordingDriver()
    gateway = _gateway(store, driver)

    first = gateway.enforce(proposal, clearance, command, now_iso=NOW)
    second = gateway.enforce(proposal, clearance, command, now_iso="2026-08-08T16:00:03Z")

    assert first.enforcement.accepted is True
    assert second.enforcement.accepted is False
    assert second.driver_outcome.error_code == "COMMAND_REPLAY"
    assert store.remaining == 1
    assert len(driver.calls) == 1


def test_same_permit_use_index_cannot_be_reused_with_new_command_id():
    proposal = _proposal()
    clearance = _clearance(proposal, permit_uses=2)
    store = PermitStore(remaining=2)
    driver = RecordingDriver()
    gateway = _gateway(store, driver)

    gateway.enforce(proposal, clearance, _command(proposal), now_iso=NOW)
    second = gateway.enforce(
        proposal,
        clearance,
        _command(proposal, command_id="command-002"),
        now_iso="2026-08-08T16:00:03Z",
    )

    assert second.enforcement.accepted is False
    assert second.driver_outcome.error_code == "PERMIT_USE_REPLAY"
    assert store.remaining == 1


def test_distinct_permit_use_indices_can_execute_within_clearance_limit():
    proposal = _proposal()
    clearance = _clearance(proposal, permit_uses=2)
    store = PermitStore(remaining=2)
    driver = RecordingDriver()
    gateway = _gateway(store, driver)

    first = gateway.enforce(proposal, clearance, _command(proposal), now_iso=NOW)
    second = gateway.enforce(
        proposal,
        clearance,
        _command(proposal, command_id="command-002", permit_use_index=1),
        now_iso="2026-08-08T16:00:03Z",
    )

    assert first.enforcement.accepted is True
    assert second.enforcement.accepted is True
    assert store.remaining == 0
    assert len(driver.calls) == 2


class TimeoutDriver:
    def execute(self, command: DeviceCommandV1) -> DriverOutcomeV1:
        raise TimeoutError("device did not respond")


class FailingDriver:
    def execute(self, command: DeviceCommandV1) -> DriverOutcomeV1:
        raise RuntimeError("motor fault")


class InvalidDriver:
    def execute(self, command: DeviceCommandV1):
        return {"status": "EXECUTED"}


def test_timeout_is_recorded_not_upgraded_and_permit_stays_consumed():
    proposal = _proposal()
    clearance = _clearance(proposal)
    store = PermitStore(remaining=1)
    gateway = DeviceEnforcementGatewayV1(
        gateway_id="gateway-1",
        clearance_verifier=lambda _: True,
        permit_consumer=store.consume,
        driver=TimeoutDriver(),
    )

    result = gateway.enforce(proposal, clearance, _command(proposal), now_iso=NOW)

    assert result.enforcement.accepted is True
    assert result.driver_outcome.status is DriverExecutionStatus.TIMEOUT
    assert result.driver_outcome.error_code == "DRIVER_TIMEOUT"
    assert store.remaining == 0


def test_driver_exception_is_failure_not_success():
    proposal = _proposal()
    store = PermitStore(remaining=1)
    gateway = DeviceEnforcementGatewayV1(
        gateway_id="gateway-1",
        clearance_verifier=lambda _: True,
        permit_consumer=store.consume,
        driver=FailingDriver(),
    )

    result = gateway.enforce(proposal, _clearance(proposal), _command(proposal), now_iso=NOW)

    assert result.enforcement.accepted is True
    assert result.driver_outcome.status is DriverExecutionStatus.FAILED
    assert result.driver_outcome.error_code == "DRIVER_EXCEPTION"


def test_partial_driver_outcome_is_preserved_exactly():
    proposal = _proposal()
    partial = DriverOutcomeV1(
        status=DriverExecutionStatus.PARTIAL,
        observed_output={"valve_open_percent": 40},
        error_code="LIMIT_SWITCH_FAULT",
    )
    store = PermitStore(remaining=1)
    driver = RecordingDriver(partial)

    result = _gateway(store, driver).enforce(proposal, _clearance(proposal), _command(proposal), now_iso=NOW)

    assert result.driver_outcome == partial
    assert result.driver_outcome.status is DriverExecutionStatus.PARTIAL


def test_invalid_driver_return_is_fail_closed():
    proposal = _proposal()
    store = PermitStore(remaining=1)
    gateway = DeviceEnforcementGatewayV1(
        gateway_id="gateway-1",
        clearance_verifier=lambda _: True,
        permit_consumer=store.consume,
        driver=InvalidDriver(),
    )

    result = gateway.enforce(proposal, _clearance(proposal), _command(proposal), now_iso=NOW)

    assert result.driver_outcome.status is DriverExecutionStatus.FAILED
    assert result.driver_outcome.error_code == "INVALID_DRIVER_OUTCOME"


def test_gateway_consumes_real_micro_reht_permit_state():
    proposal = _proposal()
    state = MicroRehtStateV1(
        issued_permits={
            "permit-001": PermitStateV1(
                permit_id="permit-001",
                envelope_id="envelope-1",
                proposal_digest=proposal.compute_digest(),
                remaining_uses=1,
            )
        }
    )
    micro_reht = MicroRehtV1(
        authority_verifier=HmacAuthorityVerifier({}),
        state=state,
    )
    driver = RecordingDriver()
    gateway = DeviceEnforcementGatewayV1(
        gateway_id="gateway-1",
        clearance_verifier=lambda _: True,
        permit_consumer=micro_reht.consume_permit,
        driver=driver,
    )

    result = gateway.enforce(proposal, _clearance(proposal, permit_uses=1), _command(proposal), now_iso=NOW)

    assert result.enforcement.accepted is True
    assert micro_reht.state.issued_permits["permit-001"].remaining_uses == 0
