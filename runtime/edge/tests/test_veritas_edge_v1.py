from __future__ import annotations

from pathlib import Path

import pytest

from valo_edge.contracts import (
    ConsequenceDecision,
    EdgeActionCommitmentV1,
    EdgeClearanceV1,
    EdgeEnforcementV1,
)
from valo_edge.gateway import (
    DriverExecutionStatus,
    DriverOutcomeV1,
    GatewayExecutionResultV1,
)
from valo_edge.veritas import (
    CompensationStatus,
    ConsequenceEvidenceState,
    HmacEvidenceAttesterV1,
    HmacEvidenceVerifierV1,
    VERITAS_GENESIS_DIGEST,
    VeritasEdgeV1,
    VeritasJsonlArchiveV1,
    VeritasRecordType,
)


def _proposal(*, boot_epoch: str = "boot-1", sequence: int = 1) -> EdgeActionCommitmentV1:
    return EdgeActionCommitmentV1(
        proposal_id=f"proposal-{sequence}",
        device_id="pump-7",
        action_type="SET_FLOW",
        parameters={"litres_per_minute": 2.5},
        model_hash="sha256:model",
        firmware_hash="sha256:firmware",
        runtime_hash="sha256:runtime",
        sensor_evidence_digest="sha256:sensors",
        physical_state_digest="sha256:state",
        authority_envelope_digest="sha256:authority",
        boot_epoch=boot_epoch,
        sequence=sequence,
        nonce=f"nonce-{sequence}",
        issued_at_iso="2026-08-08T16:00:00Z",
        valid_until_iso="2026-08-08T16:10:00Z",
        signer_key_id="device-key",
    )


def _clearance(
    proposal: EdgeActionCommitmentV1,
    *,
    decision: ConsequenceDecision = ConsequenceDecision.ALLOW,
) -> EdgeClearanceV1:
    return EdgeClearanceV1(
        clearance_id=f"clearance-{proposal.sequence}",
        proposal_digest=proposal.compute_digest(),
        evidence_digest="sha256:evidence",
        authority_envelope_digest=proposal.authority_envelope_digest,
        decision=decision,
        reason_codes=["TEST"],
        issued_at_iso="2026-08-08T16:00:01Z",
        valid_until_iso="2026-08-08T16:05:00Z",
        boot_epoch=proposal.boot_epoch,
        sequence=proposal.sequence,
        permit_id="permit-1" if decision is ConsequenceDecision.ALLOW else None,
        permit_uses=1 if decision is ConsequenceDecision.ALLOW else 0,
        signer_key_id="micro-reht-key",
    )


def _gateway_result(
    proposal: EdgeActionCommitmentV1,
    clearance: EdgeClearanceV1,
    *,
    accepted: bool,
    status: DriverExecutionStatus,
) -> GatewayExecutionResultV1:
    enforcement = EdgeEnforcementV1(
        enforcement_id=f"enforcement-{proposal.sequence}-{status.value}",
        proposal_digest=proposal.compute_digest(),
        clearance_digest=clearance.compute_digest(),
        device_command_digest="sha256:command",
        permit_id=clearance.permit_id,
        permit_use_index=0 if clearance.permit_id else None,
        accepted=accepted,
        gateway_id="gateway-1",
        enforced_at_iso="2026-08-08T16:00:02Z",
    )
    outcome = DriverOutcomeV1(
        status=status,
        observed_output={"actual_flow": 2.48} if status is DriverExecutionStatus.EXECUTED else {},
        error_code="TIMEOUT" if status is DriverExecutionStatus.TIMEOUT else None,
    )
    return GatewayExecutionResultV1(enforcement=enforcement, driver_outcome=outcome)


def _started_recorder() -> VeritasEdgeV1:
    recorder = VeritasEdgeV1(device_id="pump-7")
    recorder.start_boot(boot_epoch="boot-1", recorded_at_iso="2026-08-08T16:00:00Z")
    return recorder


def test_boot_and_authorization_form_one_hash_chain():
    recorder = _started_recorder()
    proposal = _proposal()
    clearance = _clearance(proposal)

    authorization = recorder.record_authorization(
        proposal,
        clearance,
        recorded_at_iso="2026-08-08T16:00:01Z",
    )

    entries = recorder.get_entries()
    assert len(entries) == 2
    assert entries[0].record.record_type is VeritasRecordType.BOOT_CONTINUITY
    assert authorization.record.record_type is VeritasRecordType.AUTHORIZATION
    assert authorization.previous_entry_digest == entries[0].entry_digest
    assert recorder.verify_local_chain()


def test_veritas_records_deny_without_turning_it_into_authority():
    recorder = _started_recorder()
    proposal = _proposal()
    clearance = _clearance(proposal, decision=ConsequenceDecision.DENY)

    entry = recorder.record_authorization(
        proposal,
        clearance,
        recorded_at_iso="2026-08-08T16:00:01Z",
    )

    assert entry.record.payload["decision"] == "DENY"
    assert entry.record.record_type is VeritasRecordType.AUTHORIZATION


def test_authorization_requires_exact_proposal_binding():
    recorder = _started_recorder()
    proposal = _proposal()
    clearance = _clearance(proposal).model_copy(update={"proposal_digest": "sha256:wrong"})

    with pytest.raises(ValueError, match="bind"):
        recorder.record_authorization(
            proposal,
            clearance,
            recorded_at_iso="2026-08-08T16:00:01Z",
        )


def test_gateway_rejection_evidences_no_driver_call():
    recorder = _started_recorder()
    proposal = _proposal()
    clearance = _clearance(proposal, decision=ConsequenceDecision.DENY)
    result = _gateway_result(
        proposal,
        clearance,
        accepted=False,
        status=DriverExecutionStatus.REJECTED,
    )

    _, observation = recorder.record_gateway_result(
        result,
        boot_epoch="boot-1",
        observed_at_iso="2026-08-08T16:00:02Z",
    )

    assert (
        observation.record.payload["consequence_state"]
        == ConsequenceEvidenceState.GATEWAY_REJECTED_NO_DRIVER_CALL.value
    )


def test_timeout_is_unknown_not_false_non_execution():
    recorder = _started_recorder()
    proposal = _proposal()
    clearance = _clearance(proposal)
    result = _gateway_result(
        proposal,
        clearance,
        accepted=True,
        status=DriverExecutionStatus.TIMEOUT,
    )

    _, observation = recorder.record_gateway_result(
        result,
        boot_epoch="boot-1",
        observed_at_iso="2026-08-08T16:00:03Z",
    )

    assert (
        observation.record.payload["consequence_state"]
        == ConsequenceEvidenceState.UNKNOWN_AFTER_TIMEOUT.value
    )


def test_driver_executed_is_recorded_as_driver_report_not_physical_truth():
    recorder = _started_recorder()
    proposal = _proposal()
    clearance = _clearance(proposal)
    result = _gateway_result(
        proposal,
        clearance,
        accepted=True,
        status=DriverExecutionStatus.EXECUTED,
    )

    _, observation = recorder.record_gateway_result(
        result,
        boot_epoch="boot-1",
        observed_at_iso="2026-08-08T16:00:03Z",
        physical_observation_digest="sha256:physical-sensor",
    )

    assert (
        observation.record.payload["consequence_state"]
        == ConsequenceEvidenceState.DRIVER_REPORTED_EXECUTED.value
    )
    assert observation.record.payload["physical_observation_digest"] == "sha256:physical-sensor"


def test_partial_and_failed_remain_distinct_states():
    for status, expected in [
        (DriverExecutionStatus.PARTIAL, ConsequenceEvidenceState.DRIVER_REPORTED_PARTIAL),
        (DriverExecutionStatus.FAILED, ConsequenceEvidenceState.DRIVER_REPORTED_FAILED),
    ]:
        recorder = _started_recorder()
        proposal = _proposal()
        clearance = _clearance(proposal)
        _, observation = recorder.record_gateway_result(
            _gateway_result(proposal, clearance, accepted=True, status=status),
            boot_epoch="boot-1",
            observed_at_iso="2026-08-08T16:00:03Z",
        )
        assert observation.record.payload["consequence_state"] == expected.value


def test_inconsistent_gateway_evidence_fails_before_append():
    recorder = _started_recorder()
    proposal = _proposal()
    clearance = _clearance(proposal)
    before = len(recorder.get_entries())

    with pytest.raises(ValueError, match="rejected enforcement"):
        recorder.record_gateway_result(
            _gateway_result(
                proposal,
                clearance,
                accepted=False,
                status=DriverExecutionStatus.EXECUTED,
            ),
            boot_epoch="boot-1",
            observed_at_iso="2026-08-08T16:00:03Z",
        )

    assert len(recorder.get_entries()) == before


def test_compensation_is_a_linked_evidence_record():
    recorder = _started_recorder()
    target = recorder.get_entries()[-1]
    assert target.entry_digest is not None

    compensation = recorder.record_compensation(
        boot_epoch="boot-1",
        target_entry_digest=target.entry_digest,
        compensation_action_digest="sha256:compensation-action",
        status=CompensationStatus.EXECUTED,
        recorded_at_iso="2026-08-08T16:01:00Z",
        observed_output={"valve": "closed"},
    )

    assert compensation.record.record_type is VeritasRecordType.COMPENSATION
    assert compensation.record.payload["target_entry_digest"] == target.entry_digest
    assert recorder.verify_local_chain()


def test_jsonl_archive_is_durable_and_boots_link_across_restart(tmp_path: Path):
    path = tmp_path / "veritas.jsonl"
    archive = VeritasJsonlArchiveV1(path)
    first = VeritasEdgeV1(device_id="pump-7", archive=archive)
    first.start_boot(boot_epoch="boot-1", recorded_at_iso="2026-08-08T16:00:00Z")
    proposal = _proposal()
    first.record_authorization(
        proposal,
        _clearance(proposal),
        recorded_at_iso="2026-08-08T16:00:01Z",
    )
    previous_tail = first.snapshot_state().tail_digest

    reopened_archive = VeritasJsonlArchiveV1(path)
    second = VeritasEdgeV1(device_id="pump-7", archive=reopened_archive)
    boot_entry = second.start_boot(
        boot_epoch="boot-2",
        recorded_at_iso="2026-08-08T17:00:00Z",
    )

    assert boot_entry is not None
    assert boot_entry.previous_entry_digest == previous_tail
    assert boot_entry.record.payload["previous_boot_epoch"] == "boot-1"
    assert boot_entry.record.payload["previous_tail_digest"] == previous_tail
    assert reopened_archive.verify()
    assert second.verify_local_chain()


def test_archive_tampering_fails_closed(tmp_path: Path):
    path = tmp_path / "veritas.jsonl"
    archive = VeritasJsonlArchiveV1(path)
    recorder = VeritasEdgeV1(device_id="pump-7", archive=archive)
    recorder.start_boot(boot_epoch="boot-1", recorded_at_iso="2026-08-08T16:00:00Z")

    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("pump-7", "pump-X", 1), encoding="utf-8")

    with pytest.raises(ValueError, match="integrity"):
        VeritasJsonlArchiveV1(path)


def test_evidence_package_is_self_verifiable_and_attested():
    recorder = _started_recorder()
    proposal = _proposal()
    recorder.record_authorization(
        proposal,
        _clearance(proposal),
        recorded_at_iso="2026-08-08T16:00:01Z",
    )
    attester = HmacEvidenceAttesterV1(key_id="edge-attest-1", key=b"secret")
    verifier = HmacEvidenceVerifierV1({"edge-attest-1": b"secret"})

    package = recorder.export_package(
        exported_at_iso="2026-08-08T16:02:00Z",
        attester=attester,
    )

    assert package.starting_previous_digest == VERITAS_GENESIS_DIGEST
    assert VeritasEdgeV1.verify_package_integrity(package)
    assert VeritasEdgeV1.verify_package_attestation(package, verifier.verify)


def test_package_tampering_breaks_integrity_and_attestation():
    recorder = _started_recorder()
    package = recorder.export_package(exported_at_iso="2026-08-08T16:02:00Z")
    tampered = package.model_copy(deep=True)
    tampered.entries[0].record.payload["device_id"] = "other-device"

    assert not VeritasEdgeV1.verify_package_integrity(tampered)


def test_partial_package_preserves_chain_seed():
    recorder = _started_recorder()
    proposal = _proposal()
    recorder.record_authorization(
        proposal,
        _clearance(proposal),
        recorded_at_iso="2026-08-08T16:00:01Z",
    )
    all_entries = recorder.get_entries()

    package = recorder.export_package(
        exported_at_iso="2026-08-08T16:02:00Z",
        from_sequence=1,
    )

    assert package.from_sequence == 1
    assert package.starting_previous_digest == all_entries[0].entry_digest
    assert VeritasEdgeV1.verify_package_integrity(package)


def test_reconciliation_requires_exact_central_tail_acknowledgement():
    recorder = _started_recorder()
    package = recorder.export_package(exported_at_iso="2026-08-08T16:02:00Z")

    with pytest.raises(ValueError, match="does not match"):
        recorder.record_reconciliation(
            package,
            acknowledged_tail_digest="sha256:wrong",
            remote_receipt_digest="sha256:central-receipt",
            reconciled_at_iso="2026-08-08T16:03:00Z",
        )

    entry = recorder.record_reconciliation(
        package,
        acknowledged_tail_digest=package.ending_digest,
        remote_receipt_digest="sha256:central-receipt",
        reconciled_at_iso="2026-08-08T16:03:00Z",
    )
    assert entry.record.record_type is VeritasRecordType.RECONCILIATION
    assert recorder.verify_local_chain()


def test_evidence_requires_explicit_boot_boundary():
    recorder = VeritasEdgeV1(device_id="pump-7")
    proposal = _proposal()

    with pytest.raises(ValueError, match="start_boot"):
        recorder.record_authorization(
            proposal,
            _clearance(proposal),
            recorded_at_iso="2026-08-08T16:00:01Z",
        )
