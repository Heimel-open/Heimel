from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from valo_external_adapters import (
    PROVIDER_MANIFESTS,
    ExternalPaymentProvider,
    ExternalProviderRequest,
    ProviderOutcomeDisposition,
    build_mastercard_agent_pay_request,
    build_stripe_agentic_payment_request,
    build_swift_cbpr_plus_request,
    build_visa_trusted_agent_request,
    record_provider_evidence,
    seal_external_execution_binding,
)
from valo_external_adapters.contracts import ProposedAction, canonical_digest
from valo_external_adapters.execution_authority_assurance import (
    ExecutionLeaseEvaluation,
    LeaseEvaluationDisposition,
)


def _action() -> ProposedAction:
    return ProposedAction(
        action_id="payment:1001",
        capability="PAY_SUPPLIER",
        target="supplier:42",
        purpose_id="purpose:approved-procurement",
        parameters={"amount_minor": "34000000", "currency": "EUR"},
        declared_effects=("TRANSFER_FUNDS",),
    )


def _eligible_evaluation(now: datetime) -> ExecutionLeaseEvaluation:
    action = _action()
    unsealed = ExecutionLeaseEvaluation(
        lease_digest="a" * 64,
        basis_digest="b" * 64,
        revocation_checkpoint_digest="c" * 64,
        action_id=action.action_id,
        action_digest=canonical_digest(action.model_dump(mode="json")),
        action_nonce="action-nonce-1",
        endpoint_id="payments:external",
        evaluated_at=now,
        valid_until=now + timedelta(minutes=2),
        disposition=LeaseEvaluationDisposition.ELIGIBLE,
    )
    return ExecutionLeaseEvaluation.model_validate(
        {
            **unsealed.model_dump(mode="python"),
            "evaluation_digest": unsealed.computed_digest,
        }
    )


def _binding(now: datetime):
    return seal_external_execution_binding(
        lease_evaluation=_eligible_evaluation(now),
        action=_action(),
        execution_ref="execution:payment:1001",
        reht_decision_ref="reht:decision:1001",
        reht_decision_digest="d" * 64,
        reht_disposition="ALLOW",
        racs_decision_ref="racs:decision:1001",
        racs_decision_digest="e" * 64,
        racs_disposition="ALLOW",
        bound_at=now + timedelta(seconds=1),
        amount_minor=34_000_000,
        currency="EUR",
    )


def test_same_canonical_binding_projects_to_all_four_providers():
    now = datetime(2026, 8, 16, 14, 0, tzinfo=UTC)
    binding = _binding(now)
    constructed_at = now + timedelta(seconds=2)

    requests = (
        build_swift_cbpr_plus_request(
            binding=binding,
            debtor_agent_bic="BANKDEFFXXX",
            creditor_agent_bic="BANKNL2AXXX",
            message_type="pacs.008",
            instruction_id="instr-1001",
            bank_acceptance_digest="f" * 64,
            idempotency_key="idem-swift-1001",
            constructed_at=constructed_at,
        ),
        build_visa_trusted_agent_request(
            binding=binding,
            trusted_agent_assertion_ref="visa-agent-assertion:1001",
            merchant_ref="merchant:42",
            commerce_intent_ref="visa-intent:1001",
            payment_container_ref="visa-container:1001",
            idempotency_key="idem-visa-1001",
            constructed_at=constructed_at,
        ),
        build_mastercard_agent_pay_request(
            binding=binding,
            agent_credential_ref="mc-agent-credential:1001",
            merchant_ref="merchant:42",
            verifiable_intent_ref="mc-intent:1001",
            payment_credential_ref="mc-payment-credential:1001",
            idempotency_key="idem-mastercard-1001",
            constructed_at=constructed_at,
        ),
        build_stripe_agentic_payment_request(
            binding=binding,
            shared_payment_token_ref="stripe-spt:1001",
            payment_intent_ref="stripe-pi:1001",
            merchant_ref="merchant:42",
            idempotency_key="idem-stripe-1001",
            constructed_at=constructed_at,
        ),
    )

    assert {request.provider for request in requests} == {
        ExternalPaymentProvider.SWIFT,
        ExternalPaymentProvider.VISA,
        ExternalPaymentProvider.MASTERCARD,
        ExternalPaymentProvider.STRIPE,
    }
    assert {request.binding_digest for request in requests} == {
        binding.binding_digest
    }
    assert {request.action_digest for request in requests} == {binding.action_digest}
    assert {request.execution_ref for request in requests} == {
        binding.execution_ref
    }
    assert all(request.can_execute_external_effects is False for request in requests)
    assert all(request.authority_effect == "NO_AUTHORITY_CREATION" for request in requests)


def test_external_binding_fails_closed_when_reht_does_not_allow():
    now = datetime(2026, 8, 16, 14, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="requires REHT ALLOW"):
        seal_external_execution_binding(
            lease_evaluation=_eligible_evaluation(now),
            action=_action(),
            execution_ref="execution:payment:1001",
            reht_decision_ref="reht:decision:1001",
            reht_decision_digest="d" * 64,
            reht_disposition="DENY",
            racs_decision_ref="racs:decision:1001",
            racs_decision_digest="e" * 64,
            racs_disposition="ALLOW",
            bound_at=now + timedelta(seconds=1),
            amount_minor=34_000_000,
            currency="EUR",
        )


def test_external_binding_fails_closed_when_racs_does_not_allow_effect():
    now = datetime(2026, 8, 16, 14, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="requires RACS ALLOW or MODIFY"):
        seal_external_execution_binding(
            lease_evaluation=_eligible_evaluation(now),
            action=_action(),
            execution_ref="execution:payment:1001",
            reht_decision_ref="reht:decision:1001",
            reht_decision_digest="d" * 64,
            reht_disposition="ALLOW",
            racs_decision_ref="racs:decision:1001",
            racs_decision_digest="e" * 64,
            racs_disposition="DENY",
            bound_at=now + timedelta(seconds=1),
            amount_minor=34_000_000,
            currency="EUR",
        )


def test_external_binding_rejects_ineligible_or_stale_lease_evaluation():
    now = datetime(2026, 8, 16, 14, 0, tzinfo=UTC)
    eligible = _eligible_evaluation(now)
    ineligible = ExecutionLeaseEvaluation.model_validate(
        {
            **eligible.model_dump(mode="python"),
            "disposition": LeaseEvaluationDisposition.NOT_ELIGIBLE,
            "failure_reasons": ("REVOCATION_STALE",),
            "valid_until": None,
            "evaluation_digest": "",
        }
    )
    ineligible = ExecutionLeaseEvaluation.model_validate(
        {
            **ineligible.model_dump(mode="python"),
            "evaluation_digest": ineligible.computed_digest,
        }
    )

    with pytest.raises(ValueError, match="eligible lease evaluation"):
        seal_external_execution_binding(
            lease_evaluation=ineligible,
            action=_action(),
            execution_ref="execution:payment:1001",
            reht_decision_ref="reht:decision:1001",
            reht_decision_digest="d" * 64,
            reht_disposition="ALLOW",
            racs_decision_ref="racs:decision:1001",
            racs_decision_digest="e" * 64,
            racs_disposition="ALLOW",
            bound_at=now + timedelta(seconds=1),
        )

    with pytest.raises(ValueError, match="not fresh"):
        seal_external_execution_binding(
            lease_evaluation=eligible,
            action=_action(),
            execution_ref="execution:payment:1001",
            reht_decision_ref="reht:decision:1001",
            reht_decision_digest="d" * 64,
            reht_disposition="ALLOW",
            racs_decision_ref="racs:decision:1001",
            racs_decision_digest="e" * 64,
            racs_disposition="ALLOW",
            bound_at=now + timedelta(minutes=3),
        )


def test_provider_payload_cannot_override_canonical_authority_fields():
    now = datetime(2026, 8, 16, 14, 0, tzinfo=UTC)
    payload = {"merchant_ref": "merchant:42", "reht_disposition": "ALLOW"}
    with pytest.raises(ValidationError, match="cannot override canonical authority"):
        ExternalProviderRequest(
            request_id="1" * 64,
            provider=ExternalPaymentProvider.VISA,
            adapter_id="visa.test",
            protocol="test",
            binding_digest="2" * 64,
            action_id="payment:1001",
            action_digest="3" * 64,
            execution_ref="execution:payment:1001",
            endpoint_id="payments:external",
            idempotency_key="idem-1",
            provider_payload=payload,
            provider_payload_digest=canonical_digest(payload),
            constructed_at=now,
        )


def test_swift_projection_requires_regulated_bank_acceptance_digest():
    now = datetime(2026, 8, 16, 14, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="bank_acceptance_digest"):
        build_swift_cbpr_plus_request(
            binding=_binding(now),
            debtor_agent_bic="BANKDEFFXXX",
            creditor_agent_bic="BANKNL2AXXX",
            message_type="pacs.008",
            instruction_id="instr-1001",
            bank_acceptance_digest="not-a-digest",
            idempotency_key="idem-swift-1001",
            constructed_at=now + timedelta(seconds=2),
        )


def test_provider_evidence_is_bound_but_does_not_claim_settlement():
    now = datetime(2026, 8, 16, 14, 0, tzinfo=UTC)
    request = build_stripe_agentic_payment_request(
        binding=_binding(now),
        shared_payment_token_ref="stripe-spt:1001",
        payment_intent_ref="stripe-pi:1001",
        merchant_ref="merchant:42",
        idempotency_key="idem-stripe-1001",
        constructed_at=now + timedelta(seconds=2),
    )
    evidence = record_provider_evidence(
        request=request,
        provider_reference="stripe-provider-ref:1001",
        disposition=ProviderOutcomeDisposition.ACCEPTED,
        raw_evidence_digest="9" * 64,
        observed_at=now + timedelta(seconds=3),
    )

    assert evidence.request_digest == request.request_digest
    assert evidence.binding_digest == request.binding_digest
    assert evidence.settlement_claim == "NO_SETTLEMENT_CLAIM"
    assert evidence.authority_effect == "NO_AUTHORITY_CREATION"


def test_tampered_provider_request_cannot_be_used_as_evidence_basis():
    now = datetime(2026, 8, 16, 14, 0, tzinfo=UTC)
    request = build_visa_trusted_agent_request(
        binding=_binding(now),
        trusted_agent_assertion_ref="visa-agent-assertion:1001",
        merchant_ref="merchant:42",
        commerce_intent_ref="visa-intent:1001",
        payment_container_ref="visa-container:1001",
        idempotency_key="idem-visa-1001",
        constructed_at=now + timedelta(seconds=2),
    )
    tampered = request.model_copy(update={"request_digest": "0" * 64})
    with pytest.raises(ValueError, match="unsealed or tampered"):
        record_provider_evidence(
            request=tampered,
            provider_reference="visa-provider-ref:1001",
            disposition=ProviderOutcomeDisposition.ACKNOWLEDGED,
            raw_evidence_digest="9" * 64,
            observed_at=now + timedelta(seconds=3),
        )


def test_reference_manifests_cannot_execute_and_are_marked_for_migration():
    assert set(PROVIDER_MANIFESTS) == set(ExternalPaymentProvider)
    for manifest in PROVIDER_MANIFESTS.values():
        assert manifest.actual_network_io is False
        assert manifest.can_execute_external_effects is False
        assert manifest.authority_effect == "NO_AUTHORITY_CREATION"
        assert manifest.migration_target == "valo-external-adapters"
    assert (
        PROVIDER_MANIFESTS[
            ExternalPaymentProvider.SWIFT
        ].requires_regulated_bank_acceptance
        is True
    )
