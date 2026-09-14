from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from valo_gateway.effect_contract import (
    AsyncEffectRecord,
    AuthorityComposition,
    AuthorityRequirement,
    ClaimRequirement,
    CompensationPolicy,
    ConsequenceOperation,
    EffectContract,
    EffectLifecycleState,
    EffectTargetBinding,
    IdempotencyBinding,
    ProviderCallbackEvidence,
    ReadProvenance,
    RepresentationIntegrity,
    parameters_digest,
)
from valo_gateway.integrations.claims_instrumentation import Status, verify_claim
from valo_gateway.tool_adapters import TripletexEffectTool
from valo_gateway.tool_adapters.providers import CLAIM_STATUSES_KEY, EFFECT_CONTRACT_KEY


def _now():
    return datetime.now(UTC)


def _authority():
    return AuthorityComposition(
        requirements=(
            AuthorityRequirement(authority_type="mandate", evidence_ref="ev:mandate"),
            AuthorityRequirement(authority_type="segregation-of-duties", evidence_ref="ev:sod"),
            AuthorityRequirement(authority_type="funding", evidence_ref="ev:funding"),
        )
    )


def _contract(**updates):
    now = _now()
    params = {"invoice_id": "inv-1", "amount": 100}
    values = dict(
        effect_type="accounting.payment",
        provider="accounting:tripletex",
        tenant="tenant-1",
        environment="production",
        resource="invoice:inv-1",
        subject="supplier:42",
        operation=ConsequenceOperation.PAYMENT_RELEASE,
        parameters_digest=parameters_digest(params),
        authority_requirements=_authority(),
        constraints={"currency": "NOK", "max_amount": 100},
        freshness=now + timedelta(minutes=5),
        idempotency_key="effect-123",
        completion_criteria=("provider reports payment accepted",),
        required_evidence=("provider receipt",),
        compensation_policy=CompensationPolicy.MANUAL,
        credential_authority_ref="credential-authority://finance-prod",
        claim_requirements=(ClaimRequirement(claim_id="invoice-valid"),),
        read_provenance=(
            ReadProvenance(
                source_ref="tripletex://invoice/inv-1",
                source_digest="sha256:" + "a" * 64,
                observed_at=now - timedelta(seconds=5),
                valid_until=now + timedelta(minutes=1),
                representation_integrity=RepresentationIntegrity.VERIFIED,
            ),
        ),
    )
    values.update(updates)
    return EffectContract(**values), params


def _proof():
    return SimpleNamespace(
        effect_allowed=True,
        input_digest="input",
        result_digest="sealed",
        computed_digest="sealed",
    )


def _governed_context(evidence_refs):
    return dict(
        authority=SimpleNamespace(),
        clearance=SimpleNamespace(evidence_refs=list(evidence_refs)),
        permit=SimpleNamespace(),
        action=SimpleNamespace(
            action_type="PAYMENT_RELEASE",
            target="invoice:inv-1",
        ),
        now=_now(),
    )


def test_claim_instrumentation_remains_evidence_only_and_fail_closed():
    supported = verify_claim(
        {"invoice_id": "inv-1", "amount": 100},
        {"invoice_id": "inv-1", "amount": 100},
        required_fields=("invoice_id", "amount"),
    )
    contradicted = verify_claim(
        {"invoice_id": "inv-1", "amount": 100},
        {"invoice_id": "inv-1", "amount": 99},
        required_fields=("invoice_id", "amount"),
    )
    unknown = verify_claim({}, {}, required_fields=("invoice_id",))

    assert supported.status is Status.SUPPORTED
    assert contradicted.status is Status.CONTRADICTED
    assert unknown.status is Status.UNKNOWN

    contract, _ = _contract()
    contract.assert_claims({"invoice-valid": supported})
    with pytest.raises(PermissionError):
        contract.assert_claims({"invoice-valid": contradicted})
    with pytest.raises(PermissionError):
        contract.assert_claims({"invoice-valid": unknown})


def test_effect_contract_binds_parameters_target_freshness_and_authority_composition():
    contract, params = _contract()
    contract.assert_parameters(params)
    contract.assert_target(
        EffectTargetBinding(
            provider="accounting:tripletex",
            tenant="tenant-1",
            environment="production",
            resource="invoice:inv-1",
            credential_authority_ref="credential-authority://finance-prod",
        )
    )
    contract.assert_fresh(_now())
    contract.authority_requirements.assert_satisfied(("ev:mandate", "ev:sod", "ev:funding"))

    with pytest.raises(PermissionError, match="parameters"):
        contract.assert_parameters({**params, "amount": 101})
    with pytest.raises(PermissionError, match="target"):
        contract.assert_target(contract.target_binding.model_copy(update={"tenant": "tenant-2"}))
    with pytest.raises(PermissionError, match="authority"):
        contract.authority_requirements.assert_satisfied(("ev:mandate", "ev:sod"))


def test_consequence_bearing_read_requires_verified_fresh_provenance():
    contract, _ = _contract()
    failed = contract.read_provenance[0].model_copy(update={"representation_integrity": RepresentationIntegrity.UNKNOWN})
    with pytest.raises(PermissionError, match="integrity"):
        contract.model_copy(update={"read_provenance": (failed,)}).assert_fresh(_now())

    stale = contract.read_provenance[0].model_copy(update={"valid_until": _now()})
    with pytest.raises(PermissionError, match="stale"):
        contract.model_copy(update={"read_provenance": (stale,)}).assert_fresh(_now())


def test_tripletex_manifest_and_boundary_require_exact_effect_contract():
    calls = []
    tool = TripletexEffectTool(lambda operation, parameters: calls.append((operation, parameters)))
    contract, params = _contract()

    assert tool.provider == "accounting:tripletex"
    assert tool.manifest is not None
    assert tool.manifest.provider == tool.provider
    assert tool.manifest.assert_operation("PAYMENT_RELEASE") is ConsequenceOperation.PAYMENT_RELEASE

    with pytest.raises(PermissionError, match="unknown consequence operation"):
        tool.manifest.assert_operation("pay-whatever")
    with pytest.raises(PermissionError, match="not declared"):
        tool.manifest.assert_operation("CLINICAL_ORDER_CREATE")
    with pytest.raises(PermissionError, match="NO_DIRECT_EFFECT_PATH"):
        tool.invoke({"operation": "PAYMENT_RELEASE", **params})
    with pytest.raises(PermissionError, match="EFFECT_CONTRACT_REQUIRED"):
        tool._invoke_from_boundary({"operation": "PAYMENT_RELEASE", **params}, _proof())

    arguments = {
        "operation": "PAYMENT_RELEASE",
        **params,
        EFFECT_CONTRACT_KEY: contract.model_dump(mode="json"),
        CLAIM_STATUSES_KEY: {"invoice-valid": "SUPPORTED"},
    }
    tool._validate_governed_effect(
        arguments,
        **_governed_context(("ev:mandate", "ev:sod", "ev:funding")),
    )
    tool._invoke_from_boundary(arguments, _proof())
    assert calls == [("PAYMENT_RELEASE", params)]

    with pytest.raises(PermissionError, match="authority"):
        tool._validate_governed_effect(
            arguments,
            **_governed_context(("ev:mandate", "ev:sod")),
        )

    wrong_provider = contract.model_copy(update={"provider": "accounting:xero"})
    arguments[EFFECT_CONTRACT_KEY] = wrong_provider.model_dump(mode="json")
    with pytest.raises(PermissionError, match="provider"):
        tool._invoke_from_boundary(arguments, _proof())


def test_idempotency_key_cannot_be_reused_for_different_effect():
    first = IdempotencyBinding(
        effect_id="effect-1",
        provider="accounting:tripletex",
        idempotency_key="idem-1",
        parameters_digest="sha256:" + "1" * 64,
    )
    first.assert_same_effect(first.model_copy())

    conflict = first.model_copy(update={"effect_id": "effect-2"})
    with pytest.raises(PermissionError, match="idempotency"):
        first.assert_same_effect(conflict)


def test_async_effect_lifecycle_verifies_callback_before_closeout():
    record = AsyncEffectRecord(effect_id="effect-123", correlation_id="provider-correlation-1", idempotency_key="effect-123")
    processing = record.transition(EffectLifecycleState.ACCEPTED).transition(EffectLifecycleState.PROCESSING)

    with pytest.raises(ValueError, match="receipt"):
        processing.transition(EffectLifecycleState.COMPLETED)

    callback = ProviderCallbackEvidence(
        provider="accounting:tripletex",
        correlation_id="provider-correlation-1",
        event_digest="sha256:" + "2" * 64,
        signature_ref="signature://tripletex/event-1",
        verified=True,
        observed_at=_now(),
    )
    completed = processing.transition(
        EffectLifecycleState.COMPLETED,
        callback=callback,
        provider="accounting:tripletex",
    )
    assert completed.state is EffectLifecycleState.COMPLETED
    assert completed.provider_receipt_ref == callback.signature_ref

    bad_callback = callback.model_copy(update={"verified": False})
    with pytest.raises(PermissionError, match="signature"):
        processing.transition(
            EffectLifecycleState.COMPLETED,
            callback=bad_callback,
            provider="accounting:tripletex",
        )
