"""Tests for VALO Edge contracts and deterministic digests."""

import pytest
from valo_edge.contracts import (
    EdgeActionProposal,
    OfflineAuthorityEnvelope,
    EdgeClearance,
    EdgeExecutionReceipt,
    EdgeEvidenceEnvelope,
    EdgeCommitmentV1,
    EdgeDecision,
)


def test_proposal_digest_computation():
    proposal = EdgeActionProposal(
        proposal_id="prop-1",
        device_id="dev-1",
        action_type="TEST_ACTION",
        parameters={"param1": "value1"},
        timestamp_iso="2026-08-04T10:00:00Z",
        nonce="nonce-1",
    )
    assert proposal.proposal_hash is not None
    assert len(proposal.proposal_hash) == 64
    assert proposal.compute_hash() == proposal.proposal_hash


def test_authority_envelope_digest_computation():
    envelope = OfflineAuthorityEnvelope(
        envelope_id="env-1",
        device_id="dev-1",
        allowed_action_types=["TEST_ACTION"],
        valid_until_iso="2026-08-05T10:00:00Z",
    )
    assert envelope.authority_digest is not None
    assert len(envelope.authority_digest) == 64
    assert envelope.compute_digest() == envelope.authority_digest


def test_clearance_digest_computation():
    clearance = EdgeClearance(
        clearance_id="clr-1",
        proposal_id="prop-1",
        decision=EdgeDecision.ALLOW,
        reason="Test clearance",
        envelope_id="env-1",
        timestamp_iso="2026-08-04T10:00:00Z",
    )
    assert clearance.decision_digest is not None
    assert len(clearance.decision_digest) == 64
    assert clearance.compute_digest() == clearance.decision_digest


def test_receipt_digest_computation():
    receipt = EdgeExecutionReceipt(
        receipt_id="rcpt-1",
        proposal_id="prop-1",
        clearance_id="clr-1",
        device_id="dev-1",
        decision=EdgeDecision.ALLOW,
        executed=True,
        timestamp_iso="2026-08-04T10:00:00Z",
    )
    assert receipt.receipt_digest is not None
    assert len(receipt.receipt_digest) == 64
    assert receipt.compute_digest() == receipt.receipt_digest


def test_evidence_envelope_digest_computation():
    evidence = EdgeEvidenceEnvelope(
        evidence_id="ev-1",
        proposal_id="prop-1",
        device_attestation_hash="sha256:aaa",
        model_manifest_hash="sha256:bbb",
        firmware_hash="sha256:ccc",
        sensor_digest="sha256:ddd",
    )
    assert evidence.evidence_digest is not None
    assert len(evidence.evidence_digest) == 64
    assert evidence.compute_digest() == evidence.evidence_digest


def test_commitment_v1_digest_computation():
    proposal = EdgeActionProposal(
        proposal_id="prop-1",
        device_id="dev-1",
        action_type="TEST_ACTION",
        parameters={"param1": "value1"},
        timestamp_iso="2026-08-04T10:00:00Z",
        nonce="nonce-1",
    )
    envelope = OfflineAuthorityEnvelope(
        envelope_id="env-1",
        device_id="dev-1",
        allowed_action_types=["TEST_ACTION"],
        valid_until_iso="2026-08-05T10:00:00Z",
    )
    evidence = EdgeEvidenceEnvelope(
        evidence_id="ev-1",
        proposal_id="prop-1",
        device_attestation_hash="sha256:aaa",
        model_manifest_hash="sha256:bbb",
        firmware_hash="sha256:ccc",
        sensor_digest="sha256:ddd",
    )
    clearance = EdgeClearance(
        clearance_id="clr-1",
        proposal_id="prop-1",
        decision=EdgeDecision.ALLOW,
        reason="ok",
        envelope_id="env-1",
        timestamp_iso="2026-08-04T10:00:00Z",
    )
    receipt = EdgeExecutionReceipt(
        receipt_id="rcpt-1",
        proposal_id="prop-1",
        clearance_id="clr-1",
        device_id="dev-1",
        decision=EdgeDecision.ALLOW,
        executed=True,
        timestamp_iso="2026-08-04T10:00:00Z",
    )
    commitment = EdgeCommitmentV1(
        commitment_id="comm-1",
        proposal=proposal,
        evidence=evidence,
        envelope=envelope,
        clearance=clearance,
        receipt=receipt,
    )
    assert commitment.commitment_hash is not None
    assert len(commitment.commitment_hash) == 64
    assert commitment.compute_digest() == commitment.commitment_hash


def test_contract_deterministic_across_instantiations():
    proposal_a = EdgeActionProposal(
        proposal_id="prop-1",
        device_id="dev-1",
        action_type="TEST_ACTION",
        parameters={"param1": "value1"},
        timestamp_iso="2026-08-04T10:00:00Z",
        nonce="nonce-1",
    )
    proposal_b = EdgeActionProposal(
        proposal_id="prop-1",
        device_id="dev-1",
        action_type="TEST_ACTION",
        parameters={"param1": "value1"},
        timestamp_iso="2026-08-04T10:00:00Z",
        nonce="nonce-1",
    )
    assert proposal_a.proposal_hash == proposal_b.proposal_hash

    envelope_a = OfflineAuthorityEnvelope(
        envelope_id="env-1",
        device_id="dev-1",
        allowed_action_types=["TEST_ACTION"],
        valid_until_iso="2026-08-05T10:00:00Z",
    )
    envelope_b = OfflineAuthorityEnvelope(
        envelope_id="env-1",
        device_id="dev-1",
        allowed_action_types=["TEST_ACTION"],
        valid_until_iso="2026-08-05T10:00:00Z",
    )
    assert envelope_a.authority_digest == envelope_b.authority_digest


def test_new_contract_fields_are_versioned_and_bound():
    proposal = EdgeActionProposal(
        proposal_id="prop-versioned",
        device_id="dev-1",
        action_type="TEST_ACTION",
        timestamp_iso="2026-08-04T10:00:00Z",
        nonce="nonce-1",
        boot_epoch="boot-1",
        sequence=7,
        key_id="key-1",
        signature="sig-1",
        model_manifest_hash="sha256:model",
        firmware_hash="sha256:firmware",
        sensor_digest="sha256:sensor",
        device_attestation_hash="sha256:device",
        evidence_digest="sha256:evidence",
        physical_state={"temperature_c": 25.0},
    )
    assert proposal.boot_epoch == "boot-1"
    assert proposal.sequence == 7
    assert proposal.signature == "sig-1"
    assert proposal.evidence_digest == "sha256:evidence"
    assert proposal.proposal_hash is not None

    envelope = OfflineAuthorityEnvelope(
        envelope_id="env-versioned",
        device_id="dev-1",
        allowed_action_types=["TEST_ACTION"],
        valid_until_iso="2026-08-05T10:00:00Z",
        valid_from_iso="2026-08-04T10:00:00Z",
        key_id="key-1",
        boot_epoch="boot-1",
        version="1",
        policy_version="policy-1",
    )
    assert envelope.version == "1"
    assert envelope.policy_version == "policy-1"
    assert envelope.authority_digest is not None
