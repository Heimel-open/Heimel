"""Mechanical Device Enforcement Gateway V1.

The gateway has no authority. It verifies an already-issued clearance through an
injected verifier, binds it to one exact device command, consumes one permit use,
and invokes a hardware-neutral driver.
"""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Callable, Protocol

from valo_edge.contracts import (
    ConsequenceDecision,
    EdgeActionCommitmentV1,
    EdgeClearanceV1,
    EdgeEnforcementV1,
    sha256_digest,
)
from valo_edge.gateway.contracts_v1 import (
    DeviceCommandV1,
    DriverExecutionStatus,
    DriverOutcomeV1,
    GatewayExecutionResultV1,
)


ClearanceVerifier = Callable[[EdgeClearanceV1], bool]
PermitConsumer = Callable[[str, str], bool]


class DeviceDriverV1(Protocol):
    def execute(self, command: DeviceCommandV1) -> DriverOutcomeV1:
        """Execute exactly the supplied command and report the actual outcome."""
        ...


def _parse_iso(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamps must include a timezone")
    return parsed.astimezone(timezone.utc)


class DeviceEnforcementGatewayV1:
    """Fail-closed mechanical enforcement after micro-REHT authorization."""

    def __init__(
        self,
        *,
        gateway_id: str,
        clearance_verifier: ClearanceVerifier,
        permit_consumer: PermitConsumer,
        driver: DeviceDriverV1,
    ) -> None:
        self.gateway_id = gateway_id
        self._clearance_verifier = clearance_verifier
        self._permit_consumer = permit_consumer
        self._driver = driver
        self._lock = Lock()
        self._spent_command_ids: set[str] = set()
        self._spent_permit_uses: set[tuple[str, int]] = set()

    def enforce(
        self,
        proposal: EdgeActionCommitmentV1,
        clearance: EdgeClearanceV1,
        command: DeviceCommandV1,
        *,
        now_iso: str,
    ) -> GatewayExecutionResultV1:
        proposal_digest = proposal.compute_digest()
        clearance_digest = clearance.compute_digest()
        command_digest = command.compute_digest()

        rejection = self._validate_binding(
            proposal=proposal,
            clearance=clearance,
            command=command,
            proposal_digest=proposal_digest,
            now_iso=now_iso,
        )
        if rejection is not None:
            return self._result(
                proposal_digest=proposal_digest,
                clearance_digest=clearance_digest,
                command=command,
                command_digest=command_digest,
                accepted=False,
                now_iso=now_iso,
                outcome=DriverOutcomeV1(
                    status=DriverExecutionStatus.REJECTED,
                    error_code=rejection,
                ),
            )

        permit_use = (command.permit_id, command.permit_use_index)
        with self._lock:
            if command.command_id in self._spent_command_ids:
                return self._result(
                    proposal_digest=proposal_digest,
                    clearance_digest=clearance_digest,
                    command=command,
                    command_digest=command_digest,
                    accepted=False,
                    now_iso=now_iso,
                    outcome=DriverOutcomeV1(
                        status=DriverExecutionStatus.REJECTED,
                        error_code="COMMAND_REPLAY",
                    ),
                )
            if permit_use in self._spent_permit_uses:
                return self._result(
                    proposal_digest=proposal_digest,
                    clearance_digest=clearance_digest,
                    command=command,
                    command_digest=command_digest,
                    accepted=False,
                    now_iso=now_iso,
                    outcome=DriverOutcomeV1(
                        status=DriverExecutionStatus.REJECTED,
                        error_code="PERMIT_USE_REPLAY",
                    ),
                )

            # The permit consumer belongs to micro-REHT/runtime state. The gateway
            # cannot mint, replenish or reinterpret a permit.
            if not self._permit_consumer(command.permit_id, proposal_digest):
                return self._result(
                    proposal_digest=proposal_digest,
                    clearance_digest=clearance_digest,
                    command=command,
                    command_digest=command_digest,
                    accepted=False,
                    now_iso=now_iso,
                    outcome=DriverOutcomeV1(
                        status=DriverExecutionStatus.REJECTED,
                        error_code="PERMIT_CONSUMPTION_REJECTED",
                    ),
                )

            # Consumption is final even if the driver later fails or times out.
            self._spent_command_ids.add(command.command_id)
            self._spent_permit_uses.add(permit_use)

        try:
            outcome = self._driver.execute(command)
            if not isinstance(outcome, DriverOutcomeV1):
                outcome = DriverOutcomeV1(
                    status=DriverExecutionStatus.FAILED,
                    error_code="INVALID_DRIVER_OUTCOME",
                )
        except TimeoutError as exc:
            outcome = DriverOutcomeV1(
                status=DriverExecutionStatus.TIMEOUT,
                error_code="DRIVER_TIMEOUT",
                error_detail=str(exc) or None,
            )
        except Exception as exc:  # mechanical failure is recorded, never upgraded
            outcome = DriverOutcomeV1(
                status=DriverExecutionStatus.FAILED,
                error_code="DRIVER_EXCEPTION",
                error_detail=f"{type(exc).__name__}: {exc}",
            )

        return self._result(
            proposal_digest=proposal_digest,
            clearance_digest=clearance_digest,
            command=command,
            command_digest=command_digest,
            accepted=True,
            now_iso=now_iso,
            outcome=outcome,
        )

    def _validate_binding(
        self,
        *,
        proposal: EdgeActionCommitmentV1,
        clearance: EdgeClearanceV1,
        command: DeviceCommandV1,
        proposal_digest: str,
        now_iso: str,
    ) -> str | None:
        try:
            now = _parse_iso(now_iso)
            issued = _parse_iso(clearance.issued_at_iso)
            valid_until = _parse_iso(clearance.valid_until_iso)
        except ValueError:
            return "CLEARANCE_TIME_INVALID"

        if not self._clearance_verifier(clearance):
            return "CLEARANCE_VERIFICATION_FAILED"
        if clearance.decision is not ConsequenceDecision.ALLOW:
            return f"CLEARANCE_{clearance.decision.value}"
        if now < issued or now > valid_until:
            return "CLEARANCE_EXPIRED_OR_NOT_YET_VALID"
        if clearance.proposal_digest != proposal_digest:
            return "CLEARANCE_PROPOSAL_MISMATCH"
        if clearance.boot_epoch != proposal.boot_epoch:
            return "CLEARANCE_BOOT_EPOCH_MISMATCH"
        if clearance.sequence != proposal.sequence:
            return "CLEARANCE_SEQUENCE_MISMATCH"
        if clearance.permit_id is None or clearance.permit_uses <= 0:
            return "CLEARANCE_PERMIT_MISSING"
        if command.permit_id != clearance.permit_id:
            return "COMMAND_PERMIT_MISMATCH"
        if command.permit_use_index >= clearance.permit_uses:
            return "PERMIT_USE_OUT_OF_RANGE"
        if command.proposal_digest != proposal_digest:
            return "COMMAND_PROPOSAL_MISMATCH"
        if command.device_id != proposal.device_id:
            return "COMMAND_DEVICE_MISMATCH"
        if command.action_type != proposal.action_type:
            return "COMMAND_ACTION_MISMATCH"
        if command.parameters != proposal.parameters:
            return "COMMAND_PARAMETERS_MISMATCH"
        return None

    def _result(
        self,
        *,
        proposal_digest: str,
        clearance_digest: str,
        command: DeviceCommandV1,
        command_digest: str,
        accepted: bool,
        now_iso: str,
        outcome: DriverOutcomeV1,
    ) -> GatewayExecutionResultV1:
        enforcement_id = "enforcement-" + sha256_digest(
            {
                "gateway_id": self.gateway_id,
                "proposal_digest": proposal_digest,
                "clearance_digest": clearance_digest,
                "command_digest": command_digest,
                "permit_id": command.permit_id,
                "permit_use_index": command.permit_use_index,
                "accepted": accepted,
                "enforced_at_iso": now_iso,
            }
        ).split(":", 1)[1][:16]
        enforcement = EdgeEnforcementV1(
            enforcement_id=enforcement_id,
            proposal_digest=proposal_digest,
            clearance_digest=clearance_digest,
            device_command_digest=command_digest,
            permit_id=command.permit_id,
            permit_use_index=command.permit_use_index,
            accepted=accepted,
            gateway_id=self.gateway_id,
            enforced_at_iso=now_iso,
        )
        return GatewayExecutionResultV1(
            enforcement=enforcement,
            driver_outcome=outcome,
        )


__all__ = [
    "ClearanceVerifier",
    "DeviceDriverV1",
    "DeviceEnforcementGatewayV1",
    "PermitConsumer",
]
