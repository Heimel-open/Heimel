from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from valo_external_adapters.contracts import canonical_digest
from valo_external_adapters.ecosystems import (
    ECOSYSTEM_MANIFESTS,
    ExternalAdapterExecutionRequest,
    ExternalEcosystem,
    ExternalStateClass,
    ExternalStateObservation,
    build_circle_usdc_request,
    build_coinbase_x402_request,
    build_kyriba_state_observation,
    build_open_banking_payment_request,
    build_sap_state_observation,
    build_sepa_credit_transfer_request,
    record_external_adapter_evidence,
)
from valo_external_adapters.payments import (
    ExternalExecutionBinding,
    ProviderOutcomeDisposition,
)

NOW = datetime(2026, 8, 16, 14, 30, tzinfo=UTC)


def _binding(*, currency: str = "EUR") -> ExternalExecutionBinding:
    unsealed = ExternalExecutionBinding(
        action_id="action-001",
        action_digest="a" * 64,
        execution_ref="exec-001",
        endpoint_id="endpoint-001",
        lease_digest="b" * 64,
        lease_evaluation_digest="c" * 64,
        revocation_checkpoint_digest="d" * 64,
        reht_decision_ref="reht-001",
        reht_decision_digest="e" * 64,
        reht_disposition="ALLOW",
        racs_decision_ref="racs-001",
        racs_decision_digest="f" * 64,
        racs_disposition="ALLOW",
        target_ref="supplier-001",
        amount_minor=34_000_000,
        currency=currency,
        bound_at=NOW,
        valid_until=NOW + timedelta(minutes=5),
    )
    return ExternalExecutionBinding.model_validate(
        {
            **unsealed.model_dump(mode="python"),
            "binding_digest": unsealed.computed_digest,
        }
    )


def test_sepa_and_instant_share_the_same_canonical_binding() -> None:
    binding = _binding()
    bank_acceptance_digest = canonical_digest({"bank": "acceptance-001"})
    sct = build_sepa_credit_transfer_request(
        binding=binding,
        instant=False,
        debtor_account_ref="iban:debtor",
        creditor_account_ref="iban:creditor",
        instruction_id="instr-001",
        bank_acceptance_digest=bank_acceptance_digest,
        idempotency_key="idem-sct",
        constructed_at=NOW + timedelta(seconds=1),
    )
    instant = build_sepa_credit_transfer_request(
        binding=binding,
        instant=True,
        debtor_account_ref="iban:debtor",
        creditor_account_ref="iban:creditor",
        instruction_id="instr-002",
        bank_acceptance_digest=bank_acceptance_digest,
        idempotency_key="idem-inst",
        constructed_at=NOW + timedelta(seconds=1),
    )

    assert sct.ecosystem is ExternalEcosystem.SEPA
    assert instant.ecosystem is ExternalEcosystem.SEPA_INSTANT
    assert sct.binding_digest == instant.binding_digest == binding.binding_digest
    assert sct.provider_payload["scheme"] == "SCT"
    assert instant.provider_payload["scheme"] == "SCT_INST"
    assert sct.can_execute_external_effects is False
    assert instant.authority_effect == "NO_AUTHORITY_CREATION"


def test_sepa_requires_regulated_bank_acceptance_and_eur() -> None:
    with pytest.raises(ValueError, match="bank_acceptance_digest"):
        build_sepa_credit_transfer_request(
            binding=_binding(),
            instant=False,
            debtor_account_ref="iban:debtor",
            creditor_account_ref="iban:creditor",
            instruction_id="instr-001",
            bank_acceptance_digest="not-a-digest",
            idempotency_key="idem",
            constructed_at=NOW + timedelta(seconds=1),
        )

    with pytest.raises(ValueError, match="requires EUR"):
        build_sepa_credit_transfer_request(
            binding=_binding(currency="USD"),
            instant=False,
            debtor_account_ref="iban:debtor",
            creditor_account_ref="iban:creditor",
            instruction_id="instr-001",
            bank_acceptance_digest="1" * 64,
            idempotency_key="idem",
            constructed_at=NOW + timedelta(seconds=1),
        )


def test_circle_and_x402_preserve_the_same_execution_authority_binding() -> None:
    circle_binding = _binding(currency="USDC")
    circle = build_circle_usdc_request(
        binding=circle_binding,
        circle_account_ref="circle-account-001",
        wallet_ref="wallet-001",
        destination_address_ref="address-001",
        blockchain="BASE",
        idempotency_key="circle-idem",
        constructed_at=NOW + timedelta(seconds=1),
    )
    x402 = build_coinbase_x402_request(
        binding=circle_binding,
        resource_ref="resource-api-001",
        payment_requirements_digest=canonical_digest({"required": "1 USDC"}),
        payment_signature_ref="payment-signature-001",
        facilitator_ref="cdp-facilitator",
        network="BASE",
        asset="USDC",
        idempotency_key="x402-idem",
        constructed_at=NOW + timedelta(seconds=1),
    )

    assert circle.binding_digest == x402.binding_digest == circle_binding.binding_digest
    assert circle.provider_payload["asset"] == "USDC"
    assert x402.provider_payload["http_status"] == 402
    assert x402.authority_effect == "NO_AUTHORITY_CREATION"


def test_open_banking_consent_is_provider_context_not_authority() -> None:
    binding = _binding(currency="GBP")
    request = build_open_banking_payment_request(
        binding=binding,
        aspsp_ref="aspsp-001",
        pisp_ref="pisp-001",
        consent_ref="consent-001",
        payment_resource_ref="payment-001",
        api_profile_ref="UK-OB-RW-4.0",
        idempotency_key="openbanking-idem",
        constructed_at=NOW + timedelta(seconds=1),
    )

    assert request.provider_payload["consent_ref"] == "consent-001"
    assert request.binding_digest == binding.binding_digest
    assert request.authority_effect == "NO_AUTHORITY_CREATION"
    assert request.can_issue_clearance is False


def test_provider_payload_cannot_override_canonical_authority_fields() -> None:
    request = build_circle_usdc_request(
        binding=_binding(currency="USDC"),
        circle_account_ref="circle-account-001",
        wallet_ref="wallet-001",
        destination_address_ref="address-001",
        blockchain="BASE",
        idempotency_key="circle-idem",
        constructed_at=NOW + timedelta(seconds=1),
    )
    data = request.model_dump(mode="python")
    data["provider_payload"] = {
        **request.provider_payload,
        "authority_id": "provider-wants-to-widen-authority",
    }
    data["provider_payload_digest"] = canonical_digest(data["provider_payload"])
    data["request_digest"] = ""

    with pytest.raises(ValidationError, match="cannot override canonical authority fields"):
        ExternalAdapterExecutionRequest.model_validate(data)


def test_stale_execution_binding_fails_closed() -> None:
    with pytest.raises(ValueError, match="not fresh"):
        build_circle_usdc_request(
            binding=_binding(currency="USDC"),
            circle_account_ref="circle-account-001",
            wallet_ref="wallet-001",
            destination_address_ref="address-001",
            blockchain="BASE",
            idempotency_key="circle-idem",
            constructed_at=NOW + timedelta(minutes=6),
        )


def test_sap_and_kyriba_export_only_opaque_state_evidence() -> None:
    sap = build_sap_state_observation(
        source_system_ref="sap-s4-001",
        evidence_ref="sap-evidence-001",
        state_class=ExternalStateClass.BUDGET,
        object_ref="cost-center-4100",
        source_version="etag:4711",
        observed_at=NOW,
        valid_until=NOW + timedelta(minutes=2),
        source_payload_digest=canonical_digest({"sensitive": "not-exported"}),
        assertions=("BUDGET_AVAILABLE", "SUPPLIER_ACTIVE"),
    )
    kyriba = build_kyriba_state_observation(
        source_system_ref="kyriba-prod-001",
        evidence_ref="kyriba-evidence-001",
        state_class=ExternalStateClass.TREASURY_POSITION,
        object_ref="treasury-pool-emea",
        source_version="snapshot:20260816T143000Z",
        observed_at=NOW,
        valid_until=NOW + timedelta(minutes=1),
        source_payload_digest=canonical_digest({"cash": "not-exported"}),
        assertions=("LIQUIDITY_AVAILABLE", "ACCOUNT_ACTIVE"),
    )

    for observation in (sap, kyriba):
        assert observation.raw_payload_exported is False
        assert observation.authority_effect == "NO_AUTHORITY_CREATION"
        assert observation.can_issue_clearance is False
        assert observation.external_truth_claim == "NO_EXTERNAL_TRUTH_CLAIM"
        assert "sensitive" not in observation.model_dump_json()
        assert observation.observation_digest == observation.computed_digest


def test_state_observation_tamper_is_rejected() -> None:
    observation = build_sap_state_observation(
        source_system_ref="sap-s4-001",
        evidence_ref="sap-evidence-001",
        state_class=ExternalStateClass.PURCHASE_ORDER,
        object_ref="po-4500012345",
        source_version="etag:22",
        observed_at=NOW,
        valid_until=NOW + timedelta(minutes=2),
        source_payload_digest="2" * 64,
        assertions=("PO_RELEASED",),
    )
    tampered = observation.model_dump(mode="python")
    tampered["source_version"] = "etag:23"

    with pytest.raises(ValidationError, match="observation digest mismatch"):
        ExternalStateObservation.model_validate(tampered)


def test_state_adapter_scope_is_explicit() -> None:
    with pytest.raises(ValueError, match="outside the SAP"):
        build_sap_state_observation(
            source_system_ref="sap-s4-001",
            evidence_ref="sap-evidence-001",
            state_class=ExternalStateClass.TREASURY_POSITION,
            object_ref="wrong-class",
            source_version="v1",
            observed_at=NOW,
            valid_until=NOW + timedelta(minutes=1),
            source_payload_digest="3" * 64,
            assertions=("SOME_ASSERTION",),
        )


def test_provider_evidence_is_not_settlement_or_authority() -> None:
    request = build_open_banking_payment_request(
        binding=_binding(currency="GBP"),
        aspsp_ref="aspsp-001",
        pisp_ref="pisp-001",
        consent_ref="consent-001",
        payment_resource_ref="payment-001",
        api_profile_ref="UK-OB-RW-4.0",
        idempotency_key="openbanking-idem",
        constructed_at=NOW + timedelta(seconds=1),
    )
    evidence = record_external_adapter_evidence(
        request=request,
        provider_ref="aspsp-response-001",
        response_digest=canonical_digest({"status": "AcceptedSettlementInProcess"}),
        disposition=ProviderOutcomeDisposition.ACCEPTED,
        observed_at=NOW + timedelta(seconds=2),
    )

    assert evidence.settlement_claim == "NO_SETTLEMENT_CLAIM"
    assert evidence.authority_effect == "NO_AUTHORITY_CREATION"
    assert evidence.external_truth_claim == "NO_EXTERNAL_TRUTH_CLAIM"
    assert evidence.binding_digest == request.binding_digest


def test_manifests_are_migration_safe_and_reference_only() -> None:
    assert set(ECOSYSTEM_MANIFESTS) == set(ExternalEcosystem)
    for manifest in ECOSYSTEM_MANIFESTS.values():
        assert manifest.migration_target == "valo-external-adapters"
        assert manifest.actual_network_io is False
        assert manifest.can_execute_external_effects is False
        assert manifest.authority_effect == "NO_AUTHORITY_CREATION"
