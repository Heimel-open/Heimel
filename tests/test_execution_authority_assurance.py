from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from valo_kernel.authority_projection import AuthorityStateReference
from valo_kernel.contracts import (
    Authority,
    Delegation,
    ProposedAction,
    Purpose,
    TimeWindow,
    canonical_digest,
)
from valo_kernel.execution_authority_assurance import (
    BankAcceptanceDisposition,
    Ed25519ExecutionArtifactSigner,
    LeaseEvaluationDisposition,
    RevocationCheckpointStatus,
    SettlementStatus,
    assess_revocation_checkpoint,
    evaluate_execution_authority_lease,
    issue_bank_execution_acceptance,
    issue_execution_authority_lease,
    issue_revocation_acknowledgement,
    issue_revocation_notice,
    issue_settlement_evidence,
    seal_authority_lease_basis,
    seal_execution_assurance_chain,
    seal_revocation_epoch_state,
    verify_bank_execution_acceptance,
    verify_execution_authority_lease,
    verify_revocation_acknowledgement,
    verify_revocation_epoch_state,
    verify_revocation_notice,
    verify_settlement_evidence,
)


def _signer(identity: str, byte: int):
    return Ed25519ExecutionArtifactSigner.from_private_key_bytes(
        signer_id=identity,
        key_id=f"key:{identity}:1",
        private_key_bytes=bytes([byte]) * 32,
    )


def _basis(now: datetime):
    authority = Authority(
        authority_id="authority:treasury",
        principal="cfo",
        capability="PAY",
        scope=["supplier:42", "supplier:84"],
        constraints={"max_amount_eur": "500000"},
        basis="board-resolution:2026-08",
        validity=TimeWindow(
            valid_from=now - timedelta(hours=1),
            valid_until=now + timedelta(hours=2),
        ),
        delegable=True,
    )
    delegation = Delegation(
        delegation_id="delegation:cfo:treasury-agent",
        delegator="cfo",
        delegate="treasury-agent",
        authority_ref=authority.authority_id,
        scope_reduction=["supplier:42"],
        purpose_restriction=["purpose:approved-supplier-payment"],
        validity=TimeWindow(
            valid_from=now - timedelta(minutes=30),
            valid_until=now + timedelta(hours=1),
        ),
    )
    purpose = Purpose(
        purpose_id="purpose:approved-supplier-payment",
        purpose_type="supplier-payment",
        scope=["supplier:42"],
        basis="invoice-batch:aug-16",
        permitted_data=["invoice-batch:aug-16"],
        permitted_actions=["PAY"],
        validity=TimeWindow(
            valid_from=now - timedelta(hours=1),
            valid_until=now + timedelta(hours=3),
        ),
    )
    state = AuthorityStateReference(
        tenant_id="acme",
        state_root="a" * 64,
        dependency_digest="b" * 64,
        observed_at=now - timedelta(seconds=2),
        valid_until=now + timedelta(minutes=20),
    )
    return seal_authority_lease_basis(
        executor_id="treasury-agent",
        authority=authority,
        delegations=(delegation,),
        purpose=purpose,
        authority_state=state,
        evaluated_at=now,
    )


def _action(action_id: str = "payment:1001"):
    return ProposedAction(
        action_id=action_id,
        capability="PAY",
        target="supplier:42",
        purpose_id="purpose:approved-supplier-payment",
        parameters={"amount_minor": "34000000", "currency": "EUR"},
        declared_effects=("TRANSFER_FUNDS",),
    )


def _initial_epoch(now: datetime, authority_signer):
    return seal_revocation_epoch_state(
        scope_id="revocation:acme:treasury",
        epoch=0,
        observed_at=now,
        valid_until=now + timedelta(seconds=30),
        source_ref="authority-service:revocations",
        signer=authority_signer,
    )


def _checkpoint(now: datetime):
    authority_signer = _signer("authority-service", 2)
    node_signer = _signer("pep:bank-a", 3)
    source = _initial_epoch(now, authority_signer)
    acknowledgement = issue_revocation_acknowledgement(
        node_id="pep:bank-a",
        source_state=source,
        source_public_key=authority_signer.public_key(),
        acknowledged_at=now + timedelta(milliseconds=100),
        signer=node_signer,
    )
    checkpoint = assess_revocation_checkpoint(
        source_state=source,
        source_public_key=authority_signer.public_key(),
        acknowledgement=acknowledgement,
        node_public_key=node_signer.public_key(),
        checked_at=now + timedelta(seconds=1),
        max_sync_age_seconds=10,
    )
    return authority_signer, node_signer, source, acknowledgement, checkpoint


def _lease_setup(now: datetime):
    basis = _basis(now)
    lease_signer = _signer("authority-lease-service", 1)
    authority_signer, _, epoch, _, checkpoint = _checkpoint(now)
    lease = issue_execution_authority_lease(
        basis=basis,
        revocation_state=epoch,
        revocation_public_key=authority_signer.public_key(),
        signer=lease_signer,
        allowed_targets=("supplier:42",),
        audience=("pep:bank-a", "pep:stablecoin-a"),
        issued_at=now + timedelta(milliseconds=200),
        nonce="lease-nonce:1",
        requested_expires_at=now + timedelta(seconds=20),
        currency="EUR",
        max_single_amount_minor=50_000_000,
        max_cumulative_amount_minor=100_000_000,
        max_actions=5,
    )
    return basis, lease_signer, authority_signer, lease, checkpoint


def test_bounded_signed_lease_is_valid_but_does_not_issue_clearance():
    now = datetime(2026, 8, 16, 13, 0, tzinfo=UTC)
    basis, lease_signer, _, lease, _ = _lease_setup(now)

    verify_execution_authority_lease(
        lease,
        basis=basis,
        public_key=lease_signer.public_key(),
    )
    assert lease.authority_effect == "NO_AUTHORITY_CREATION"
    assert lease.can_issue_clearance is False
    assert lease.can_execute_external_effects is False
    assert lease.expires_at <= basis.valid_until


def test_lease_cannot_widen_delegated_scope():
    now = datetime(2026, 8, 16, 13, 0, tzinfo=UTC)
    basis = _basis(now)
    authority_signer = _signer("authority-service", 2)
    with pytest.raises(ValueError, match="widen principal authority"):
        issue_execution_authority_lease(
            basis=basis,
            revocation_state=_initial_epoch(now, authority_signer),
            revocation_public_key=authority_signer.public_key(),
            signer=_signer("authority-lease-service", 1),
            allowed_targets=("supplier:84",),
            audience=("pep:bank-a",),
            issued_at=now + timedelta(milliseconds=200),
            nonce="lease-nonce:widen",
        )


def test_tampered_lease_payload_fails_verification():
    now = datetime(2026, 8, 16, 13, 0, tzinfo=UTC)
    basis, lease_signer, _, lease, _ = _lease_setup(now)
    tampered = lease.model_copy(update={"max_actions": 99})
    with pytest.raises(ValueError, match="unsealed or tampered"):
        verify_execution_authority_lease(
            tampered,
            basis=basis,
            public_key=lease_signer.public_key(),
        )


def test_signed_epoch_state_and_ack_are_verified_end_to_end():
    now = datetime(2026, 8, 16, 13, 0, tzinfo=UTC)
    authority_signer, node_signer, source, acknowledgement, checkpoint = _checkpoint(now)

    verify_revocation_epoch_state(source, public_key=authority_signer.public_key())
    verify_revocation_acknowledgement(
        acknowledgement,
        public_key=node_signer.public_key(),
    )
    assert checkpoint.status is RevocationCheckpointStatus.CURRENT


def test_forged_ack_cannot_make_checkpoint_current():
    now = datetime(2026, 8, 16, 13, 0, tzinfo=UTC)
    authority_signer, node_signer, source, acknowledgement, _ = _checkpoint(now)
    forged = acknowledgement.model_copy(update={"epoch": acknowledgement.epoch + 1})
    forged = forged.model_copy(
        update={"acknowledgement_digest": forged.computed_digest}
    )
    checkpoint = assess_revocation_checkpoint(
        source_state=source,
        source_public_key=authority_signer.public_key(),
        acknowledgement=forged,
        node_public_key=node_signer.public_key(),
        checked_at=now + timedelta(seconds=1),
        max_sync_age_seconds=10,
    )
    assert checkpoint.status is RevocationCheckpointStatus.UNKNOWN
    assert "ACKNOWLEDGEMENT_SIGNATURE_INVALID" in checkpoint.failure_reasons


def test_tampered_epoch_state_cannot_make_checkpoint_current():
    now = datetime(2026, 8, 16, 13, 0, tzinfo=UTC)
    authority_signer, node_signer, source, acknowledgement, _ = _checkpoint(now)
    tampered = source.model_copy(update={"valid_until": now + timedelta(minutes=5)})
    tampered = tampered.model_copy(update={"state_digest": tampered.computed_digest})
    checkpoint = assess_revocation_checkpoint(
        source_state=tampered,
        source_public_key=authority_signer.public_key(),
        acknowledgement=acknowledgement,
        node_public_key=node_signer.public_key(),
        checked_at=now + timedelta(seconds=1),
        max_sync_age_seconds=10,
    )
    assert checkpoint.status is RevocationCheckpointStatus.UNKNOWN
    assert "REVOCATION_SOURCE_SIGNATURE_INVALID" in checkpoint.failure_reasons


def test_partition_or_missing_ack_fails_closed():
    now = datetime(2026, 8, 16, 13, 0, tzinfo=UTC)
    authority_signer = _signer("authority-service", 2)
    source = _initial_epoch(now, authority_signer)
    checkpoint = assess_revocation_checkpoint(
        source_state=source,
        source_public_key=authority_signer.public_key(),
        acknowledgement=None,
        node_public_key=None,
        checked_at=now + timedelta(seconds=1),
        max_sync_age_seconds=10,
    )
    assert checkpoint.status is RevocationCheckpointStatus.UNKNOWN
    assert "MISSING_NODE_ACKNOWLEDGEMENT" in checkpoint.failure_reasons
    assert checkpoint.valid_until is None


def test_lease_evaluation_requires_fresh_checkpoint_and_replay_protection():
    now = datetime(2026, 8, 16, 13, 0, tzinfo=UTC)
    basis, lease_signer, _, lease, checkpoint = _lease_setup(now)
    evaluation = evaluate_execution_authority_lease(
        lease=lease,
        basis=basis,
        lease_public_key=lease_signer.public_key(),
        checkpoint=checkpoint,
        action=_action(),
        endpoint_id="pep:bank-a",
        action_nonce="action-nonce:1",
        evaluated_at=now + timedelta(seconds=2),
        amount_minor=34_000_000,
    )
    assert evaluation.disposition is LeaseEvaluationDisposition.ELIGIBLE
    assert evaluation.requires_fresh_reht is True

    replay = evaluate_execution_authority_lease(
        lease=lease,
        basis=basis,
        lease_public_key=lease_signer.public_key(),
        checkpoint=checkpoint,
        action=_action(),
        endpoint_id="pep:bank-a",
        action_nonce="action-nonce:1",
        evaluated_at=now + timedelta(seconds=2),
        amount_minor=34_000_000,
        seen_action_nonces=frozenset({"action-nonce:1"}),
    )
    assert replay.disposition is LeaseEvaluationDisposition.NOT_ELIGIBLE
    assert "ACTION_NONCE_REPLAY" in replay.failure_reasons


def test_expired_checkpoint_blocks_action_even_when_lease_signature_is_valid():
    now = datetime(2026, 8, 16, 13, 0, tzinfo=UTC)
    basis, lease_signer, _, lease, checkpoint = _lease_setup(now)
    evaluation = evaluate_execution_authority_lease(
        lease=lease,
        basis=basis,
        lease_public_key=lease_signer.public_key(),
        checkpoint=checkpoint,
        action=_action(),
        endpoint_id="pep:bank-a",
        action_nonce="action-nonce:stale",
        evaluated_at=now + timedelta(seconds=12),
        amount_minor=34_000_000,
    )
    assert evaluation.disposition is LeaseEvaluationDisposition.NOT_ELIGIBLE
    assert "REVOCATION_CHECKPOINT_NOT_FRESH" in evaluation.failure_reasons


def test_revocation_epoch_invalidates_old_lease_even_if_signature_stays_valid():
    now = datetime(2026, 8, 16, 13, 0, tzinfo=UTC)
    basis, lease_signer, authority_signer, lease, _ = _lease_setup(now)
    node_signer = _signer("pep:bank-a", 3)
    notice = issue_revocation_notice(
        scope_id=lease.revocation_scope_id,
        prior_epoch=0,
        revoked_refs=(basis.delegations[0].delegation_id,),
        effective_at=now + timedelta(seconds=3),
        signer=authority_signer,
    )
    verify_revocation_notice(notice, public_key=authority_signer.public_key())
    source = seal_revocation_epoch_state(
        scope_id=lease.revocation_scope_id,
        epoch=1,
        observed_at=now + timedelta(seconds=3),
        valid_until=now + timedelta(seconds=30),
        source_ref="authority-service:revocations",
        signer=authority_signer,
        latest_notice=notice,
        notice_public_key=authority_signer.public_key(),
    )
    acknowledgement = issue_revocation_acknowledgement(
        node_id="pep:bank-a",
        source_state=source,
        source_public_key=authority_signer.public_key(),
        acknowledged_at=now + timedelta(seconds=3, milliseconds=100),
        signer=node_signer,
    )
    checkpoint = assess_revocation_checkpoint(
        source_state=source,
        source_public_key=authority_signer.public_key(),
        acknowledgement=acknowledgement,
        node_public_key=node_signer.public_key(),
        checked_at=now + timedelta(seconds=4),
        max_sync_age_seconds=10,
    )
    assert checkpoint.status is RevocationCheckpointStatus.CURRENT

    evaluation = evaluate_execution_authority_lease(
        lease=lease,
        basis=basis,
        lease_public_key=lease_signer.public_key(),
        checkpoint=checkpoint,
        action=_action(),
        endpoint_id="pep:bank-a",
        action_nonce="action-nonce:2",
        evaluated_at=now + timedelta(seconds=4),
        amount_minor=34_000_000,
    )
    assert evaluation.disposition is LeaseEvaluationDisposition.NOT_ELIGIBLE
    assert "LEASE_REVOCATION_EPOCH_MISMATCH" in evaluation.failure_reasons
    assert "LEASE_REVOCATION_STATE_MISMATCH" in evaluation.failure_reasons


def test_spend_and_action_limits_are_enforced_before_reht():
    now = datetime(2026, 8, 16, 13, 0, tzinfo=UTC)
    basis, lease_signer, _, lease, checkpoint = _lease_setup(now)
    evaluation = evaluate_execution_authority_lease(
        lease=lease,
        basis=basis,
        lease_public_key=lease_signer.public_key(),
        checkpoint=checkpoint,
        action=_action(),
        endpoint_id="pep:bank-a",
        action_nonce="action-nonce:limits",
        evaluated_at=now + timedelta(seconds=2),
        amount_minor=50_000_001,
        cumulative_amount_minor_before=90_000_000,
        actions_used_before=5,
    )
    assert evaluation.disposition is LeaseEvaluationDisposition.NOT_ELIGIBLE
    assert "SINGLE_ACTION_AMOUNT_EXCEEDED" in evaluation.failure_reasons
    assert "CUMULATIVE_AMOUNT_EXCEEDED" in evaluation.failure_reasons
    assert "ACTION_COUNT_EXCEEDED" in evaluation.failure_reasons


def _eligible_evaluation(now: datetime):
    basis, lease_signer, _, lease, checkpoint = _lease_setup(now)
    action = _action()
    evaluation = evaluate_execution_authority_lease(
        lease=lease,
        basis=basis,
        lease_public_key=lease_signer.public_key(),
        checkpoint=checkpoint,
        action=action,
        endpoint_id="pep:bank-a",
        action_nonce="action-nonce:bank",
        evaluated_at=now + timedelta(seconds=2),
        amount_minor=34_000_000,
    )
    return basis, lease, checkpoint, action, evaluation


def _bank_acceptance(now: datetime, lease, action, evaluation, bank_signer):
    return issue_bank_execution_acceptance(
        signer=bank_signer,
        lease=lease,
        lease_evaluation=evaluation,
        action=action,
        execution_ref="execution:1001",
        customer_ref="customer:acme",
        account_binding_digest="1" * 64,
        reht_decision_ref="reht:1001",
        reht_decision_digest="2" * 64,
        reht_disposition="ALLOW",
        racs_decision_ref="racs:1001",
        racs_decision_digest="3" * 64,
        racs_disposition="ALLOW",
        bank_policy_version="bank-policy:42",
        aml_state_digest="4" * 64,
        sanctions_state_digest="5" * 64,
        evaluated_at=now + timedelta(seconds=3),
    )


def test_bank_acceptance_is_separate_and_requires_reht_and_racs_allow():
    now = datetime(2026, 8, 16, 13, 0, tzinfo=UTC)
    _, lease, _, action, evaluation = _eligible_evaluation(now)
    bank_signer = _signer("bank:a", 4)
    acceptance = _bank_acceptance(now, lease, action, evaluation, bank_signer)

    verify_bank_execution_acceptance(
        acceptance,
        public_key=bank_signer.public_key(),
    )
    assert acceptance.disposition is BankAcceptanceDisposition.ACCEPTED
    assert acceptance.authority_effect == "NO_AUTHORITY_CREATION"
    assert acceptance.can_execute_external_effects is False

    with pytest.raises(ValueError, match="requires REHT ALLOW"):
        issue_bank_execution_acceptance(
            signer=bank_signer,
            lease=lease,
            lease_evaluation=evaluation,
            action=action,
            execution_ref="execution:1002",
            customer_ref="customer:acme",
            account_binding_digest="1" * 64,
            reht_decision_ref="reht:deny",
            reht_decision_digest="2" * 64,
            reht_disposition="DENY",
            racs_decision_ref="racs:deny",
            racs_decision_digest="3" * 64,
            racs_disposition="DENY",
            bank_policy_version="bank-policy:42",
            aml_state_digest="4" * 64,
            sanctions_state_digest="5" * 64,
            evaluated_at=now + timedelta(seconds=3),
        )


def test_settlement_and_assurance_chain_bind_exact_action_execution_and_effect():
    now = datetime(2026, 8, 16, 13, 0, tzinfo=UTC)
    basis, lease, checkpoint, action, evaluation = _eligible_evaluation(now)
    bank_signer = _signer("bank:a", 4)
    settlement_signer = _signer("settlement:bank-a", 5)
    acceptance = _bank_acceptance(now, lease, action, evaluation, bank_signer)
    settlement = issue_settlement_evidence(
        signer=settlement_signer,
        bank_acceptance=acceptance,
        bank_public_key=bank_signer.public_key(),
        action=action,
        execution_ref="execution:1001",
        rail="SEPA",
        effect_ref="effect:1001",
        status=SettlementStatus.COMMITTED,
        committed_at=now + timedelta(seconds=4),
        recorded_at=now + timedelta(seconds=5),
        external_receipt_digest="6" * 64,
    )
    verify_settlement_evidence(
        settlement,
        public_key=settlement_signer.public_key(),
    )
    chain = seal_execution_assurance_chain(
        basis=basis,
        lease=lease,
        checkpoint=checkpoint,
        lease_evaluation=evaluation,
        bank_acceptance=acceptance,
        settlement=settlement,
        sealed_at=now + timedelta(seconds=6),
        outcome_evidence_digest="7" * 64,
    )
    assert chain.execution_ref == "execution:1001"
    assert chain.action_digest == canonical_digest(action.model_dump(mode="json"))
    assert chain.settlement_digest == settlement.settlement_digest


def test_settlement_rejects_execution_drift():
    now = datetime(2026, 8, 16, 13, 0, tzinfo=UTC)
    _, lease, _, action, evaluation = _eligible_evaluation(now)
    bank_signer = _signer("bank:a", 4)
    acceptance = _bank_acceptance(now, lease, action, evaluation, bank_signer)
    with pytest.raises(ValueError, match="execution_ref differs"):
        issue_settlement_evidence(
            signer=_signer("settlement:bank-a", 5),
            bank_acceptance=acceptance,
            bank_public_key=bank_signer.public_key(),
            action=action,
            execution_ref="execution:other",
            rail="SEPA",
            effect_ref="effect:other",
            status=SettlementStatus.COMMITTED,
            committed_at=now + timedelta(seconds=4),
            recorded_at=now + timedelta(seconds=5),
            external_receipt_digest="6" * 64,
        )
