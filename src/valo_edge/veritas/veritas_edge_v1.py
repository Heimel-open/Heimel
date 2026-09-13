"""Veritas Edge V1: append-only consequence evidence, never authority."""

from __future__ import annotations

import hashlib
import hmac
from typing import Callable, Mapping, Optional

from valo_edge.contracts import (
    EdgeActionCommitmentV1,
    EdgeClearanceV1,
    SignatureV1,
    sha256_digest,
)
from valo_edge.gateway.contracts_v1 import (
    DriverExecutionStatus,
    GatewayExecutionResultV1,
)
from valo_edge.veritas.archive_v1 import VeritasJsonlArchiveV1, verify_chain_entries
from valo_edge.veritas.contracts_v1 import (
    AuthorizationReceiptV1,
    BootContinuityReceiptV1,
    CompensationReceiptV1,
    CompensationStatus,
    ConsequenceEvidenceState,
    EdgeEvidencePackageV1,
    EnforcementReceiptV1,
    ExecutionObservationReceiptV1,
    ReconciliationReceiptV1,
    VERITAS_GENESIS_DIGEST,
    VeritasChainEntryV1,
    VeritasEdgeStateV1,
    VeritasRecordType,
    VeritasRecordV1,
)


AttestationVerifier = Callable[[str, SignatureV1], bool]


def _short_id(prefix: str, payload: object) -> str:
    return f"{prefix}-" + sha256_digest(payload).split(":", 1)[1][:16]


class HmacEvidenceAttesterV1:
    """Deterministic reference attester for edge evidence packages.

    Hardware-backed asymmetric attestation belongs to the OEM/provisioning layer;
    this reference profile exists to make package signing and verification testable.
    """

    def __init__(self, *, key_id: str, key: bytes) -> None:
        self.key_id = key_id
        self._key = bytes(key)

    def sign_digest(self, digest: str) -> SignatureV1:
        signature = hmac.new(self._key, digest.encode("utf-8"), hashlib.sha256).hexdigest()
        return SignatureV1(
            algorithm="HMAC-SHA256",
            key_id=self.key_id,
            signature=signature,
        )

    def verify(self, digest: str, signature: SignatureV1) -> bool:
        if signature.algorithm != "HMAC-SHA256" or signature.key_id != self.key_id:
            return False
        expected = hmac.new(
            self._key,
            digest.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(signature.signature, expected)


class HmacEvidenceVerifierV1:
    """Keyring verifier for centrally checking reference HMAC attestations."""

    def __init__(self, keyring: Mapping[str, bytes]) -> None:
        self._keyring = {key_id: bytes(key) for key_id, key in keyring.items()}

    def verify(self, digest: str, signature: SignatureV1) -> bool:
        if signature.algorithm != "HMAC-SHA256":
            return False
        key = self._keyring.get(signature.key_id)
        if key is None:
            return False
        expected = hmac.new(key, digest.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature.signature, expected)


class VeritasEdgeV1:
    """Local evidence recorder for authorization, enforcement and consequences."""

    def __init__(
        self,
        *,
        device_id: str,
        archive: Optional[VeritasJsonlArchiveV1] = None,
        state: Optional[VeritasEdgeStateV1] = None,
    ) -> None:
        self.device_id = device_id
        self._archive = archive

        if archive is not None:
            existing = archive.read_all()
            derived = self._state_from_entries(existing)
            if state is not None and state != derived:
                raise ValueError("provided Veritas state does not match archive")
            self.state = derived
            self._entries = existing
            self._segment_start_sequence = 0
            self._segment_start_previous_digest = VERITAS_GENESIS_DIGEST
        else:
            self.state = state.model_copy(deep=True) if state is not None else VeritasEdgeStateV1()
            self._entries: list[VeritasChainEntryV1] = []
            self._segment_start_sequence = self.state.next_sequence
            self._segment_start_previous_digest = self.state.tail_digest

    @staticmethod
    def _state_from_entries(entries: list[VeritasChainEntryV1]) -> VeritasEdgeStateV1:
        if not entries:
            return VeritasEdgeStateV1()
        if not verify_chain_entries(entries):
            raise ValueError("Veritas entry chain is invalid")
        last = entries[-1]
        assert last.entry_digest is not None
        return VeritasEdgeStateV1(
            next_sequence=last.sequence + 1,
            tail_digest=last.entry_digest,
            current_boot_epoch=last.record.boot_epoch,
        )

    def snapshot_state(self) -> VeritasEdgeStateV1:
        return self.state.model_copy(deep=True)

    def get_entries(self) -> list[VeritasChainEntryV1]:
        return [entry.model_copy(deep=True) for entry in self._entries]

    def verify_local_chain(self) -> bool:
        return verify_chain_entries(
            self._entries,
            starting_previous_digest=self._segment_start_previous_digest,
            starting_sequence=self._segment_start_sequence,
        )

    def start_boot(self, *, boot_epoch: str, recorded_at_iso: str) -> Optional[VeritasChainEntryV1]:
        if not boot_epoch:
            raise ValueError("boot_epoch is required")
        if self.state.current_boot_epoch == boot_epoch:
            return None

        previous_boot = self.state.current_boot_epoch
        previous_tail = self.state.tail_digest
        receipt = BootContinuityReceiptV1(
            receipt_id=_short_id(
                "boot",
                {
                    "device_id": self.device_id,
                    "boot_epoch": boot_epoch,
                    "previous_tail": previous_tail,
                    "recorded_at_iso": recorded_at_iso,
                },
            ),
            device_id=self.device_id,
            boot_epoch=boot_epoch,
            previous_boot_epoch=previous_boot,
            previous_tail_digest=previous_tail,
            recorded_at_iso=recorded_at_iso,
        )
        entry = self._append(
            VeritasRecordType.BOOT_CONTINUITY,
            receipt,
            boot_epoch=boot_epoch,
            recorded_at_iso=recorded_at_iso,
        )
        self.state.current_boot_epoch = boot_epoch
        return entry

    def record_authorization(
        self,
        proposal: EdgeActionCommitmentV1,
        clearance: EdgeClearanceV1,
        *,
        recorded_at_iso: str,
    ) -> VeritasChainEntryV1:
        self._require_boot(proposal.boot_epoch)
        proposal_digest = proposal.compute_digest()
        if clearance.proposal_digest != proposal_digest:
            raise ValueError("clearance does not bind the supplied proposal")
        if clearance.boot_epoch != proposal.boot_epoch:
            raise ValueError("clearance boot epoch mismatch")
        if clearance.sequence != proposal.sequence:
            raise ValueError("clearance sequence mismatch")

        clearance_digest = clearance.compute_digest()
        receipt = AuthorizationReceiptV1(
            receipt_id=_short_id(
                "auth",
                {
                    "proposal_digest": proposal_digest,
                    "clearance_digest": clearance_digest,
                    "recorded_at_iso": recorded_at_iso,
                },
            ),
            device_id=self.device_id,
            boot_epoch=proposal.boot_epoch,
            proposal_digest=proposal_digest,
            clearance_digest=clearance_digest,
            authority_envelope_digest=clearance.authority_envelope_digest,
            decision=clearance.decision,
            permit_id=clearance.permit_id,
            permit_uses=clearance.permit_uses,
            recorded_at_iso=recorded_at_iso,
        )
        return self._append(
            VeritasRecordType.AUTHORIZATION,
            receipt,
            boot_epoch=proposal.boot_epoch,
            recorded_at_iso=recorded_at_iso,
        )

    def record_gateway_result(
        self,
        result: GatewayExecutionResultV1,
        *,
        boot_epoch: str,
        observed_at_iso: str,
        physical_observation_digest: Optional[str] = None,
    ) -> tuple[VeritasChainEntryV1, VeritasChainEntryV1]:
        self._require_boot(boot_epoch)
        enforcement = result.enforcement
        outcome = result.driver_outcome

        if not enforcement.accepted and outcome.status is not DriverExecutionStatus.REJECTED:
            raise ValueError("rejected enforcement must have REJECTED driver status")
        if enforcement.accepted and outcome.status is DriverExecutionStatus.REJECTED:
            raise ValueError("accepted enforcement cannot have REJECTED driver status")

        enforcement_digest = enforcement.compute_digest()
        enforcement_receipt = EnforcementReceiptV1(
            receipt_id=_short_id(
                "enforce",
                {
                    "enforcement_digest": enforcement_digest,
                    "recorded_at_iso": observed_at_iso,
                },
            ),
            device_id=self.device_id,
            boot_epoch=boot_epoch,
            proposal_digest=enforcement.proposal_digest,
            clearance_digest=enforcement.clearance_digest,
            enforcement_digest=enforcement_digest,
            device_command_digest=enforcement.device_command_digest,
            permit_id=enforcement.permit_id,
            permit_use_index=enforcement.permit_use_index,
            accepted=enforcement.accepted,
            gateway_id=enforcement.gateway_id,
            recorded_at_iso=observed_at_iso,
        )

        consequence_state = self._consequence_state(result)
        outcome_digest = outcome.compute_digest()
        observation_receipt = ExecutionObservationReceiptV1(
            receipt_id=_short_id(
                "observe",
                {
                    "enforcement_digest": enforcement_digest,
                    "driver_outcome_digest": outcome_digest,
                    "observed_at_iso": observed_at_iso,
                },
            ),
            device_id=self.device_id,
            boot_epoch=boot_epoch,
            enforcement_digest=enforcement_digest,
            driver_outcome_digest=outcome_digest,
            driver_status=outcome.status,
            consequence_state=consequence_state,
            observed_output=outcome.observed_output,
            error_code=outcome.error_code,
            error_detail=outcome.error_detail,
            physical_observation_digest=physical_observation_digest,
            observed_at_iso=observed_at_iso,
        )

        enforcement_entry = self._append(
            VeritasRecordType.ENFORCEMENT,
            enforcement_receipt,
            boot_epoch=boot_epoch,
            recorded_at_iso=observed_at_iso,
        )
        observation_entry = self._append(
            VeritasRecordType.EXECUTION_OBSERVATION,
            observation_receipt,
            boot_epoch=boot_epoch,
            recorded_at_iso=observed_at_iso,
        )
        return enforcement_entry, observation_entry

    @staticmethod
    def _consequence_state(result: GatewayExecutionResultV1) -> ConsequenceEvidenceState:
        enforcement = result.enforcement
        status = result.driver_outcome.status
        if not enforcement.accepted:
            return ConsequenceEvidenceState.GATEWAY_REJECTED_NO_DRIVER_CALL
        if status is DriverExecutionStatus.EXECUTED:
            return ConsequenceEvidenceState.DRIVER_REPORTED_EXECUTED
        if status is DriverExecutionStatus.PARTIAL:
            return ConsequenceEvidenceState.DRIVER_REPORTED_PARTIAL
        if status is DriverExecutionStatus.FAILED:
            return ConsequenceEvidenceState.DRIVER_REPORTED_FAILED
        if status is DriverExecutionStatus.TIMEOUT:
            return ConsequenceEvidenceState.UNKNOWN_AFTER_TIMEOUT
        raise ValueError(f"unsupported driver status for accepted enforcement: {status}")

    def record_compensation(
        self,
        *,
        boot_epoch: str,
        target_entry_digest: str,
        compensation_action_digest: str,
        status: CompensationStatus,
        recorded_at_iso: str,
        observed_output: Optional[dict[str, object]] = None,
        error_code: Optional[str] = None,
    ) -> VeritasChainEntryV1:
        self._require_boot(boot_epoch)
        receipt = CompensationReceiptV1(
            receipt_id=_short_id(
                "compensate",
                {
                    "target": target_entry_digest,
                    "action": compensation_action_digest,
                    "status": status.value,
                    "recorded_at_iso": recorded_at_iso,
                },
            ),
            device_id=self.device_id,
            boot_epoch=boot_epoch,
            target_entry_digest=target_entry_digest,
            compensation_action_digest=compensation_action_digest,
            status=status,
            observed_output=observed_output or {},
            error_code=error_code,
            recorded_at_iso=recorded_at_iso,
        )
        return self._append(
            VeritasRecordType.COMPENSATION,
            receipt,
            boot_epoch=boot_epoch,
            recorded_at_iso=recorded_at_iso,
        )

    def export_package(
        self,
        *,
        exported_at_iso: str,
        from_sequence: Optional[int] = None,
        attester: Optional[HmacEvidenceAttesterV1] = None,
    ) -> EdgeEvidencePackageV1:
        if not self._entries:
            raise ValueError("cannot export an empty Veritas chain")
        first_available = self._entries[0].sequence
        last_available = self._entries[-1].sequence
        start = first_available if from_sequence is None else from_sequence
        if start < first_available or start > last_available:
            raise ValueError("requested sequence is outside the locally available chain")

        selected = [entry.model_copy(deep=True) for entry in self._entries if entry.sequence >= start]
        first = selected[0]
        last = selected[-1]
        assert last.entry_digest is not None
        package = EdgeEvidencePackageV1(
            package_id=_short_id(
                "evidence",
                {
                    "device_id": self.device_id,
                    "from_sequence": first.sequence,
                    "to_sequence": last.sequence,
                    "ending_digest": last.entry_digest,
                    "exported_at_iso": exported_at_iso,
                },
            ),
            device_id=self.device_id,
            from_sequence=first.sequence,
            to_sequence=last.sequence,
            starting_previous_digest=first.previous_entry_digest,
            ending_digest=last.entry_digest,
            entries=selected,
            exported_at_iso=exported_at_iso,
        )
        if attester is not None:
            assert package.package_digest is not None
            package = package.model_copy(
                update={"attestation": attester.sign_digest(package.package_digest)}
            )
        return package

    @staticmethod
    def verify_package_integrity(package: EdgeEvidencePackageV1) -> bool:
        if not package.entries or package.package_digest is None:
            return False
        if package.package_digest != package.compute_digest():
            return False
        first = package.entries[0]
        last = package.entries[-1]
        if first.sequence != package.from_sequence:
            return False
        if last.sequence != package.to_sequence:
            return False
        if first.previous_entry_digest != package.starting_previous_digest:
            return False
        if last.entry_digest != package.ending_digest:
            return False
        if any(entry.record.device_id != package.device_id for entry in package.entries):
            return False
        return verify_chain_entries(
            package.entries,
            starting_previous_digest=package.starting_previous_digest,
            starting_sequence=package.from_sequence,
        )

    @staticmethod
    def verify_package_attestation(
        package: EdgeEvidencePackageV1,
        verifier: AttestationVerifier,
    ) -> bool:
        if not VeritasEdgeV1.verify_package_integrity(package):
            return False
        if package.attestation is None or package.package_digest is None:
            return False
        return verifier(package.package_digest, package.attestation)

    def record_reconciliation(
        self,
        package: EdgeEvidencePackageV1,
        *,
        acknowledged_tail_digest: str,
        remote_receipt_digest: str,
        reconciled_at_iso: str,
    ) -> VeritasChainEntryV1:
        boot_epoch = self._require_active_boot()
        if not self.verify_package_integrity(package):
            raise ValueError("cannot reconcile an invalid evidence package")
        if acknowledged_tail_digest != package.ending_digest:
            raise ValueError("central acknowledgement does not match package tail")
        assert package.package_digest is not None
        receipt = ReconciliationReceiptV1(
            receipt_id=_short_id(
                "reconcile",
                {
                    "package_digest": package.package_digest,
                    "remote_receipt_digest": remote_receipt_digest,
                    "reconciled_at_iso": reconciled_at_iso,
                },
            ),
            device_id=self.device_id,
            boot_epoch=boot_epoch,
            package_digest=package.package_digest,
            acknowledged_tail_digest=acknowledged_tail_digest,
            remote_receipt_digest=remote_receipt_digest,
            reconciled_at_iso=reconciled_at_iso,
        )
        return self._append(
            VeritasRecordType.RECONCILIATION,
            receipt,
            boot_epoch=boot_epoch,
            recorded_at_iso=reconciled_at_iso,
        )

    def _require_active_boot(self) -> str:
        if self.state.current_boot_epoch is None:
            raise ValueError("start_boot must be recorded before consequence evidence")
        return self.state.current_boot_epoch

    def _require_boot(self, boot_epoch: str) -> None:
        current = self._require_active_boot()
        if current != boot_epoch:
            raise ValueError("boot epoch does not match active Veritas boot")

    def _append(
        self,
        record_type: VeritasRecordType,
        receipt: object,
        *,
        boot_epoch: str,
        recorded_at_iso: str,
    ) -> VeritasChainEntryV1:
        if not hasattr(receipt, "model_dump") or not hasattr(receipt, "compute_digest"):
            raise TypeError("Veritas receipt must be a versioned contract")
        payload = receipt.model_dump(mode="json", exclude_none=True)  # type: ignore[attr-defined]
        payload_digest = receipt.compute_digest()  # type: ignore[attr-defined]
        record = VeritasRecordV1(
            record_type=record_type,
            device_id=self.device_id,
            boot_epoch=boot_epoch,
            payload=payload,
            payload_digest=payload_digest,
            recorded_at_iso=recorded_at_iso,
        )
        entry = VeritasChainEntryV1(
            sequence=self.state.next_sequence,
            previous_entry_digest=self.state.tail_digest,
            record=record,
        )
        if self._archive is not None:
            self._archive.append(entry)
        self._entries.append(entry.model_copy(deep=True))
        assert entry.entry_digest is not None
        self.state.next_sequence += 1
        self.state.tail_digest = entry.entry_digest
        return entry


__all__ = [
    "AttestationVerifier",
    "HmacEvidenceAttesterV1",
    "HmacEvidenceVerifierV1",
    "VeritasEdgeV1",
]
