from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .contracts import ProposedAction, canonical_digest
from .execution_authority_assurance import (
    ExecutionLeaseEvaluation,
    LeaseEvaluationDisposition,
)


class ExternalPaymentProvider(StrEnum):
    SWIFT = "SWIFT"
    VISA = "VISA"
    MASTERCARD = "MASTERCARD"
    STRIPE = "STRIPE"


class ProviderOutcomeDisposition(StrEnum):
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    PENDING = "PENDING"
    STEP_UP = "STEP_UP"


class ExternalAdapterManifest(BaseModel):
    schema_version: Literal["external_adapter_manifest.v1"] = (
        "external_adapter_manifest.v1"
    )
    provider: ExternalPaymentProvider
    adapter_id: str
    protocol: str
    requires_regulated_bank_acceptance: bool
    migration_target: Literal["valo-external-adapters"] = "valo-external-adapters"
    actual_network_io: Literal[False] = False
    can_execute_external_effects: Literal[False] = False
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"

    model_config = ConfigDict(extra="forbid", frozen=True)


PROVIDER_MANIFESTS: dict[ExternalPaymentProvider, ExternalAdapterManifest] = {
    ExternalPaymentProvider.SWIFT: ExternalAdapterManifest(
        provider=ExternalPaymentProvider.SWIFT,
        adapter_id="swift.cbpr-plus.reference.v1",
        protocol="SWIFT ISO 20022 CBPR+ reference projection",
        requires_regulated_bank_acceptance=True,
    ),
    ExternalPaymentProvider.VISA: ExternalAdapterManifest(
        provider=ExternalPaymentProvider.VISA,
        adapter_id="visa.trusted-agent.reference.v1",
        protocol="Visa Trusted Agent reference projection",
        requires_regulated_bank_acceptance=False,
    ),
    ExternalPaymentProvider.MASTERCARD: ExternalAdapterManifest(
        provider=ExternalPaymentProvider.MASTERCARD,
        adapter_id="mastercard.agent-pay.reference.v1",
        protocol="Mastercard Agent Pay reference projection",
        requires_regulated_bank_acceptance=False,
    ),
    ExternalPaymentProvider.STRIPE: ExternalAdapterManifest(
        provider=ExternalPaymentProvider.STRIPE,
        adapter_id="stripe.agentic-payments.reference.v1",
        protocol="Stripe agentic payment reference projection",
        requires_regulated_bank_acceptance=False,
    ),
}


FORBIDDEN_PROVIDER_OVERRIDE_KEYS = frozenset(
    {
        "authority",
        "authority_id",
        "authority_state",
        "authority_state_digest",
        "delegation",
        "delegation_chain",
        "lease_digest",
        "lease_evaluation_digest",
        "revocation_checkpoint_digest",
        "reht_decision",
        "reht_decision_ref",
        "reht_decision_digest",
        "reht_disposition",
        "racs_decision",
        "racs_decision_ref",
        "racs_decision_digest",
        "racs_disposition",
        "action_digest",
        "execution_ref",
    }
)


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


def _require_digest(value: str, field_name: str) -> None:
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 hex digest")


def _require_nonempty(value: str, field_name: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"{field_name} is required")


class ExternalExecutionBinding(BaseModel):
    """Canonical execution context that provider adapters may only project.

    This object is deliberately provider-neutral. It binds one eligible lease
    evaluation to the exact action and to fresh REHT/RACS decision evidence.
    Provider adapters cannot alter any of these fields.
    """

    schema_version: Literal["external_execution_binding.v1"] = (
        "external_execution_binding.v1"
    )
    action_id: str
    action_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_ref: str
    endpoint_id: str
    lease_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    lease_evaluation_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    revocation_checkpoint_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    reht_decision_ref: str
    reht_decision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    reht_disposition: Literal["ALLOW"] = "ALLOW"
    racs_decision_ref: str
    racs_decision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    racs_disposition: Literal["ALLOW", "MODIFY"]
    target_ref: str
    amount_minor: int | None = Field(default=None, ge=0)
    currency: str | None = None
    bound_at: datetime
    valid_until: datetime
    binding_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False
    can_execute_external_effects: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"binding_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_binding(self) -> ExternalExecutionBinding:
        for value, field_name in (
            (self.action_id, "action_id"),
            (self.execution_ref, "execution_ref"),
            (self.endpoint_id, "endpoint_id"),
            (self.reht_decision_ref, "reht_decision_ref"),
            (self.racs_decision_ref, "racs_decision_ref"),
            (self.target_ref, "target_ref"),
        ):
            _require_nonempty(value, field_name)
        _require_aware(self.bound_at, "bound_at")
        _require_aware(self.valid_until, "valid_until")
        if self.valid_until <= self.bound_at:
            raise ValueError("external execution binding requires a positive validity window")
        if (self.amount_minor is None) != (self.currency is None):
            raise ValueError("amount_minor and currency must be supplied together")
        if self.currency is not None and not self.currency.strip():
            raise ValueError("currency cannot be blank")
        if self.binding_digest and self.binding_digest != self.computed_digest:
            raise ValueError("external execution binding digest mismatch")
        return self


def seal_external_execution_binding(
    *,
    lease_evaluation: ExecutionLeaseEvaluation,
    action: ProposedAction,
    execution_ref: str,
    reht_decision_ref: str,
    reht_decision_digest: str,
    reht_disposition: str,
    racs_decision_ref: str,
    racs_decision_digest: str,
    racs_disposition: str,
    bound_at: datetime,
    amount_minor: int | None = None,
    currency: str | None = None,
) -> ExternalExecutionBinding:
    if lease_evaluation.evaluation_digest != lease_evaluation.computed_digest:
        raise ValueError("execution lease evaluation is unsealed or tampered")
    if lease_evaluation.disposition is not LeaseEvaluationDisposition.ELIGIBLE:
        raise ValueError("external execution requires an eligible lease evaluation")
    if lease_evaluation.valid_until is None:
        raise ValueError("eligible lease evaluation has no validity window")
    action_digest = canonical_digest(action.model_dump(mode="json"))
    if lease_evaluation.action_id != action.action_id:
        raise ValueError("external execution action_id differs from lease evaluation")
    if lease_evaluation.action_digest != action_digest:
        raise ValueError("external execution action differs from lease evaluation")
    _require_aware(bound_at, "bound_at")
    if not (
        lease_evaluation.evaluated_at
        <= bound_at
        < lease_evaluation.valid_until
    ):
        raise ValueError("lease evaluation is not fresh at external binding time")
    if reht_disposition != "ALLOW":
        raise ValueError("external execution binding requires REHT ALLOW")
    if racs_disposition not in {"ALLOW", "MODIFY"}:
        raise ValueError("external execution binding requires RACS ALLOW or MODIFY")
    _require_digest(reht_decision_digest, "reht_decision_digest")
    _require_digest(racs_decision_digest, "racs_decision_digest")

    unsealed = ExternalExecutionBinding(
        action_id=action.action_id,
        action_digest=action_digest,
        execution_ref=execution_ref,
        endpoint_id=lease_evaluation.endpoint_id,
        lease_digest=lease_evaluation.lease_digest,
        lease_evaluation_digest=lease_evaluation.evaluation_digest,
        revocation_checkpoint_digest=lease_evaluation.revocation_checkpoint_digest,
        reht_decision_ref=reht_decision_ref,
        reht_decision_digest=reht_decision_digest,
        reht_disposition="ALLOW",
        racs_decision_ref=racs_decision_ref,
        racs_decision_digest=racs_decision_digest,
        racs_disposition=racs_disposition,
        target_ref=action.target,
        amount_minor=amount_minor,
        currency=currency,
        bound_at=bound_at,
        valid_until=lease_evaluation.valid_until,
    )
    return ExternalExecutionBinding.model_validate(
        {
            **unsealed.model_dump(mode="python"),
            "binding_digest": unsealed.computed_digest,
        }
    )


ProviderPayloadValue = str | int | bool


class ExternalProviderRequest(BaseModel):
    schema_version: Literal["external_provider_request.v1"] = (
        "external_provider_request.v1"
    )
    request_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    provider: ExternalPaymentProvider
    adapter_id: str
    protocol: str
    binding_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    action_id: str
    action_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_ref: str
    endpoint_id: str
    idempotency_key: str
    provider_payload: dict[str, ProviderPayloadValue]
    provider_payload_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    constructed_at: datetime
    request_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False
    can_execute_external_effects: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"request_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_request(self) -> ExternalProviderRequest:
        for value, field_name in (
            (self.adapter_id, "adapter_id"),
            (self.protocol, "protocol"),
            (self.action_id, "action_id"),
            (self.execution_ref, "execution_ref"),
            (self.endpoint_id, "endpoint_id"),
            (self.idempotency_key, "idempotency_key"),
        ):
            _require_nonempty(value, field_name)
        _require_aware(self.constructed_at, "constructed_at")
        if not self.provider_payload:
            raise ValueError("provider_payload must not be empty")
        forbidden = FORBIDDEN_PROVIDER_OVERRIDE_KEYS.intersection(
            key.lower() for key in self.provider_payload
        )
        if forbidden:
            raise ValueError(
                "provider payload cannot override canonical authority fields: "
                + ", ".join(sorted(forbidden))
            )
        if self.provider_payload_digest != canonical_digest(self.provider_payload):
            raise ValueError("provider payload digest mismatch")
        if self.request_digest and self.request_digest != self.computed_digest:
            raise ValueError("external provider request digest mismatch")
        return self


def _build_provider_request(
    *,
    binding: ExternalExecutionBinding,
    manifest: ExternalAdapterManifest,
    provider_payload: dict[str, ProviderPayloadValue],
    idempotency_key: str,
    constructed_at: datetime,
) -> ExternalProviderRequest:
    if binding.binding_digest != binding.computed_digest:
        raise ValueError("external execution binding is unsealed or tampered")
    _require_aware(constructed_at, "constructed_at")
    if not (binding.bound_at <= constructed_at < binding.valid_until):
        raise ValueError("external execution binding is not fresh for provider projection")
    _require_nonempty(idempotency_key, "idempotency_key")
    provider_payload_digest = canonical_digest(provider_payload)
    request_id = canonical_digest(
        {
            "provider": manifest.provider.value,
            "adapter_id": manifest.adapter_id,
            "binding_digest": binding.binding_digest,
            "provider_payload_digest": provider_payload_digest,
            "idempotency_key": idempotency_key,
        }
    )
    unsealed = ExternalProviderRequest(
        request_id=request_id,
        provider=manifest.provider,
        adapter_id=manifest.adapter_id,
        protocol=manifest.protocol,
        binding_digest=binding.binding_digest,
        action_id=binding.action_id,
        action_digest=binding.action_digest,
        execution_ref=binding.execution_ref,
        endpoint_id=binding.endpoint_id,
        idempotency_key=idempotency_key,
        provider_payload=provider_payload,
        provider_payload_digest=provider_payload_digest,
        constructed_at=constructed_at,
    )
    return ExternalProviderRequest.model_validate(
        {
            **unsealed.model_dump(mode="python"),
            "request_digest": unsealed.computed_digest,
        }
    )


def build_swift_cbpr_plus_request(
    *,
    binding: ExternalExecutionBinding,
    debtor_agent_bic: str,
    creditor_agent_bic: str,
    message_type: Literal["pacs.008", "pacs.009"],
    instruction_id: str,
    bank_acceptance_digest: str,
    idempotency_key: str,
    constructed_at: datetime,
) -> ExternalProviderRequest:
    _require_nonempty(debtor_agent_bic, "debtor_agent_bic")
    _require_nonempty(creditor_agent_bic, "creditor_agent_bic")
    _require_nonempty(instruction_id, "instruction_id")
    _require_digest(bank_acceptance_digest, "bank_acceptance_digest")
    return _build_provider_request(
        binding=binding,
        manifest=PROVIDER_MANIFESTS[ExternalPaymentProvider.SWIFT],
        provider_payload={
            "network": "SWIFT",
            "standard": "ISO20022",
            "usage": "CBPR+",
            "message_type": message_type,
            "debtor_agent_bic": debtor_agent_bic,
            "creditor_agent_bic": creditor_agent_bic,
            "instruction_id": instruction_id,
            "bank_acceptance_digest": bank_acceptance_digest,
        },
        idempotency_key=idempotency_key,
        constructed_at=constructed_at,
    )


def build_visa_trusted_agent_request(
    *,
    binding: ExternalExecutionBinding,
    trusted_agent_assertion_ref: str,
    merchant_ref: str,
    commerce_intent_ref: str,
    payment_container_ref: str,
    idempotency_key: str,
    constructed_at: datetime,
) -> ExternalProviderRequest:
    for value, field_name in (
        (trusted_agent_assertion_ref, "trusted_agent_assertion_ref"),
        (merchant_ref, "merchant_ref"),
        (commerce_intent_ref, "commerce_intent_ref"),
        (payment_container_ref, "payment_container_ref"),
    ):
        _require_nonempty(value, field_name)
    return _build_provider_request(
        binding=binding,
        manifest=PROVIDER_MANIFESTS[ExternalPaymentProvider.VISA],
        provider_payload={
            "trusted_agent_assertion_ref": trusted_agent_assertion_ref,
            "merchant_ref": merchant_ref,
            "commerce_intent_ref": commerce_intent_ref,
            "payment_container_ref": payment_container_ref,
        },
        idempotency_key=idempotency_key,
        constructed_at=constructed_at,
    )


def build_mastercard_agent_pay_request(
    *,
    binding: ExternalExecutionBinding,
    agent_credential_ref: str,
    merchant_ref: str,
    verifiable_intent_ref: str,
    payment_credential_ref: str,
    idempotency_key: str,
    constructed_at: datetime,
) -> ExternalProviderRequest:
    for value, field_name in (
        (agent_credential_ref, "agent_credential_ref"),
        (merchant_ref, "merchant_ref"),
        (verifiable_intent_ref, "verifiable_intent_ref"),
        (payment_credential_ref, "payment_credential_ref"),
    ):
        _require_nonempty(value, field_name)
    return _build_provider_request(
        binding=binding,
        manifest=PROVIDER_MANIFESTS[ExternalPaymentProvider.MASTERCARD],
        provider_payload={
            "agent_credential_ref": agent_credential_ref,
            "merchant_ref": merchant_ref,
            "verifiable_intent_ref": verifiable_intent_ref,
            "payment_credential_ref": payment_credential_ref,
        },
        idempotency_key=idempotency_key,
        constructed_at=constructed_at,
    )


def build_stripe_agentic_payment_request(
    *,
    binding: ExternalExecutionBinding,
    shared_payment_token_ref: str,
    payment_intent_ref: str,
    merchant_ref: str,
    idempotency_key: str,
    constructed_at: datetime,
) -> ExternalProviderRequest:
    for value, field_name in (
        (shared_payment_token_ref, "shared_payment_token_ref"),
        (payment_intent_ref, "payment_intent_ref"),
        (merchant_ref, "merchant_ref"),
    ):
        _require_nonempty(value, field_name)
    return _build_provider_request(
        binding=binding,
        manifest=PROVIDER_MANIFESTS[ExternalPaymentProvider.STRIPE],
        provider_payload={
            "shared_payment_token_ref": shared_payment_token_ref,
            "payment_intent_ref": payment_intent_ref,
            "merchant_ref": merchant_ref,
        },
        idempotency_key=idempotency_key,
        constructed_at=constructed_at,
    )


class ExternalProviderEvidence(BaseModel):
    schema_version: Literal["external_provider_evidence.v1"] = (
        "external_provider_evidence.v1"
    )
    evidence_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    provider: ExternalPaymentProvider
    request_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    request_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    binding_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    action_id: str
    execution_ref: str
    provider_reference: str
    disposition: ProviderOutcomeDisposition
    raw_evidence_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    observed_at: datetime
    evidence_digest: str = ""
    settlement_claim: Literal["NO_SETTLEMENT_CLAIM"] = "NO_SETTLEMENT_CLAIM"
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"evidence_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_evidence(self) -> ExternalProviderEvidence:
        _require_nonempty(self.action_id, "action_id")
        _require_nonempty(self.execution_ref, "execution_ref")
        _require_nonempty(self.provider_reference, "provider_reference")
        _require_aware(self.observed_at, "observed_at")
        if self.evidence_digest and self.evidence_digest != self.computed_digest:
            raise ValueError("external provider evidence digest mismatch")
        return self


def record_provider_evidence(
    *,
    request: ExternalProviderRequest,
    provider_reference: str,
    disposition: ProviderOutcomeDisposition,
    raw_evidence_digest: str,
    observed_at: datetime,
) -> ExternalProviderEvidence:
    if request.request_digest != request.computed_digest:
        raise ValueError("external provider request is unsealed or tampered")
    _require_nonempty(provider_reference, "provider_reference")
    _require_digest(raw_evidence_digest, "raw_evidence_digest")
    _require_aware(observed_at, "observed_at")
    if observed_at < request.constructed_at:
        raise ValueError("provider evidence cannot predate the provider request")
    evidence_id = canonical_digest(
        {
            "provider": request.provider.value,
            "request_digest": request.request_digest,
            "provider_reference": provider_reference,
            "disposition": disposition.value,
            "raw_evidence_digest": raw_evidence_digest,
            "observed_at": observed_at.isoformat(),
        }
    )
    unsealed = ExternalProviderEvidence(
        evidence_id=evidence_id,
        provider=request.provider,
        request_id=request.request_id,
        request_digest=request.request_digest,
        binding_digest=request.binding_digest,
        action_id=request.action_id,
        execution_ref=request.execution_ref,
        provider_reference=provider_reference,
        disposition=disposition,
        raw_evidence_digest=raw_evidence_digest,
        observed_at=observed_at,
    )
    return ExternalProviderEvidence.model_validate(
        {
            **unsealed.model_dump(mode="python"),
            "evidence_digest": unsealed.computed_digest,
        }
    )
