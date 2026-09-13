from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .contracts import canonical_digest
from .payments import (
    FORBIDDEN_PROVIDER_OVERRIDE_KEYS,
    ExternalExecutionBinding,
    ProviderOutcomeDisposition,
)

AdapterPayloadValue = str | int | bool


class ExternalAdapterRole(StrEnum):
    EXECUTION_PROJECTION = "EXECUTION_PROJECTION"
    AUTHORITATIVE_STATE_SOURCE = "AUTHORITATIVE_STATE_SOURCE"
    BIDIRECTIONAL = "BIDIRECTIONAL"


class ExternalEcosystem(StrEnum):
    SEPA = "SEPA"
    SEPA_INSTANT = "SEPA_INSTANT"
    CIRCLE = "CIRCLE"
    COINBASE_X402 = "COINBASE_X402"
    SAP = "SAP"
    KYRIBA = "KYRIBA"
    OPEN_BANKING = "OPEN_BANKING"


class EcosystemAdapterManifest(BaseModel):
    schema_version: Literal["ecosystem_adapter_manifest.v2"] = (
        "ecosystem_adapter_manifest.v2"
    )
    ecosystem: ExternalEcosystem
    adapter_id: str
    protocol: str
    role: ExternalAdapterRole
    requires_regulated_bank_acceptance: bool
    migration_target: Literal["valo-external-adapters"] = "valo-external-adapters"
    actual_network_io: Literal[False] = False
    can_execute_external_effects: Literal[False] = False
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)


ECOSYSTEM_MANIFESTS: dict[ExternalEcosystem, EcosystemAdapterManifest] = {
    ExternalEcosystem.SEPA: EcosystemAdapterManifest(
        ecosystem=ExternalEcosystem.SEPA,
        adapter_id="sepa.sct.reference.v1",
        protocol="SEPA Credit Transfer reference projection",
        role=ExternalAdapterRole.EXECUTION_PROJECTION,
        requires_regulated_bank_acceptance=True,
    ),
    ExternalEcosystem.SEPA_INSTANT: EcosystemAdapterManifest(
        ecosystem=ExternalEcosystem.SEPA_INSTANT,
        adapter_id="sepa.sct-inst.reference.v1",
        protocol="SEPA Instant Credit Transfer reference projection",
        role=ExternalAdapterRole.EXECUTION_PROJECTION,
        requires_regulated_bank_acceptance=True,
    ),
    ExternalEcosystem.CIRCLE: EcosystemAdapterManifest(
        ecosystem=ExternalEcosystem.CIRCLE,
        adapter_id="circle.usdc.reference.v1",
        protocol="Circle USDC transfer reference projection",
        role=ExternalAdapterRole.EXECUTION_PROJECTION,
        requires_regulated_bank_acceptance=False,
    ),
    ExternalEcosystem.COINBASE_X402: EcosystemAdapterManifest(
        ecosystem=ExternalEcosystem.COINBASE_X402,
        adapter_id="coinbase.x402.reference.v1",
        protocol="Coinbase x402 HTTP payment reference projection",
        role=ExternalAdapterRole.EXECUTION_PROJECTION,
        requires_regulated_bank_acceptance=False,
    ),
    ExternalEcosystem.SAP: EcosystemAdapterManifest(
        ecosystem=ExternalEcosystem.SAP,
        adapter_id="sap.authoritative-state.reference.v1",
        protocol="SAP business-state observation reference projection",
        role=ExternalAdapterRole.AUTHORITATIVE_STATE_SOURCE,
        requires_regulated_bank_acceptance=False,
    ),
    ExternalEcosystem.KYRIBA: EcosystemAdapterManifest(
        ecosystem=ExternalEcosystem.KYRIBA,
        adapter_id="kyriba.treasury-state.reference.v1",
        protocol="Kyriba treasury-state observation reference projection",
        role=ExternalAdapterRole.AUTHORITATIVE_STATE_SOURCE,
        requires_regulated_bank_acceptance=False,
    ),
    ExternalEcosystem.OPEN_BANKING: EcosystemAdapterManifest(
        ecosystem=ExternalEcosystem.OPEN_BANKING,
        adapter_id="open-banking.payment-initiation.reference.v1",
        protocol="Open Banking payment-initiation reference projection",
        role=ExternalAdapterRole.BIDIRECTIONAL,
        requires_regulated_bank_acceptance=False,
    ),
}


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


def _require_nonempty(value: str, field_name: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"{field_name} is required")


def _require_digest(value: str, field_name: str) -> None:
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 hex digest")


class ExternalAdapterExecutionRequest(BaseModel):
    schema_version: Literal["external_adapter_execution_request.v2"] = (
        "external_adapter_execution_request.v2"
    )
    request_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    ecosystem: ExternalEcosystem
    adapter_id: str
    protocol: str
    binding_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    action_id: str
    action_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_ref: str
    endpoint_id: str
    idempotency_key: str
    provider_payload: dict[str, AdapterPayloadValue]
    provider_payload_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    constructed_at: datetime
    request_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False
    can_execute_external_effects: Literal[False] = False
    live_network_io: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"request_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_request(self) -> ExternalAdapterExecutionRequest:
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
            raise ValueError("external adapter request digest mismatch")
        return self


def _build_execution_request(
    *,
    binding: ExternalExecutionBinding,
    ecosystem: ExternalEcosystem,
    provider_payload: dict[str, AdapterPayloadValue],
    idempotency_key: str,
    constructed_at: datetime,
) -> ExternalAdapterExecutionRequest:
    if binding.binding_digest != binding.computed_digest:
        raise ValueError("external execution binding is unsealed or tampered")
    _require_aware(constructed_at, "constructed_at")
    if not (binding.bound_at <= constructed_at < binding.valid_until):
        raise ValueError("external execution binding is not fresh for adapter projection")
    _require_nonempty(idempotency_key, "idempotency_key")
    manifest = ECOSYSTEM_MANIFESTS[ecosystem]
    if manifest.role is ExternalAdapterRole.AUTHORITATIVE_STATE_SOURCE:
        raise ValueError("state-source adapter cannot create an execution request")
    forbidden = FORBIDDEN_PROVIDER_OVERRIDE_KEYS.intersection(
        key.lower() for key in provider_payload
    )
    if forbidden:
        raise ValueError(
            "provider payload cannot override canonical authority fields: "
            + ", ".join(sorted(forbidden))
        )
    provider_payload_digest = canonical_digest(provider_payload)
    request_id = canonical_digest(
        {
            "ecosystem": ecosystem.value,
            "adapter_id": manifest.adapter_id,
            "binding_digest": binding.binding_digest,
            "provider_payload_digest": provider_payload_digest,
            "idempotency_key": idempotency_key,
        }
    )
    unsealed = ExternalAdapterExecutionRequest(
        request_id=request_id,
        ecosystem=ecosystem,
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
    return ExternalAdapterExecutionRequest.model_validate(
        {
            **unsealed.model_dump(mode="python"),
            "request_digest": unsealed.computed_digest,
        }
    )


def build_sepa_credit_transfer_request(
    *,
    binding: ExternalExecutionBinding,
    instant: bool,
    debtor_account_ref: str,
    creditor_account_ref: str,
    instruction_id: str,
    bank_acceptance_digest: str,
    idempotency_key: str,
    constructed_at: datetime,
) -> ExternalAdapterExecutionRequest:
    if binding.amount_minor is None or binding.currency is None:
        raise ValueError("SEPA projection requires an amount-bound execution binding")
    if binding.currency.upper() != "EUR":
        raise ValueError("SEPA projection requires EUR")
    for value, field_name in (
        (debtor_account_ref, "debtor_account_ref"),
        (creditor_account_ref, "creditor_account_ref"),
        (instruction_id, "instruction_id"),
    ):
        _require_nonempty(value, field_name)
    _require_digest(bank_acceptance_digest, "bank_acceptance_digest")
    ecosystem = ExternalEcosystem.SEPA_INSTANT if instant else ExternalEcosystem.SEPA
    return _build_execution_request(
        binding=binding,
        ecosystem=ecosystem,
        provider_payload={
            "scheme": "SCT_INST" if instant else "SCT",
            "debtor_account_ref": debtor_account_ref,
            "creditor_account_ref": creditor_account_ref,
            "instruction_id": instruction_id,
            "bank_acceptance_digest": bank_acceptance_digest,
        },
        idempotency_key=idempotency_key,
        constructed_at=constructed_at,
    )


def build_circle_usdc_request(
    *,
    binding: ExternalExecutionBinding,
    circle_account_ref: str,
    wallet_ref: str,
    destination_address_ref: str,
    blockchain: str,
    idempotency_key: str,
    constructed_at: datetime,
) -> ExternalAdapterExecutionRequest:
    if binding.amount_minor is None or binding.currency is None:
        raise ValueError("Circle projection requires an amount-bound execution binding")
    if binding.currency.upper() != "USDC":
        raise ValueError("Circle reference projection requires USDC binding currency")
    for value, field_name in (
        (circle_account_ref, "circle_account_ref"),
        (wallet_ref, "wallet_ref"),
        (destination_address_ref, "destination_address_ref"),
        (blockchain, "blockchain"),
    ):
        _require_nonempty(value, field_name)
    return _build_execution_request(
        binding=binding,
        ecosystem=ExternalEcosystem.CIRCLE,
        provider_payload={
            "asset": "USDC",
            "circle_account_ref": circle_account_ref,
            "wallet_ref": wallet_ref,
            "destination_address_ref": destination_address_ref,
            "blockchain": blockchain,
        },
        idempotency_key=idempotency_key,
        constructed_at=constructed_at,
    )


def build_coinbase_x402_request(
    *,
    binding: ExternalExecutionBinding,
    resource_ref: str,
    payment_requirements_digest: str,
    payment_signature_ref: str,
    facilitator_ref: str,
    network: str,
    asset: str,
    idempotency_key: str,
    constructed_at: datetime,
) -> ExternalAdapterExecutionRequest:
    for value, field_name in (
        (resource_ref, "resource_ref"),
        (payment_signature_ref, "payment_signature_ref"),
        (facilitator_ref, "facilitator_ref"),
        (network, "network"),
        (asset, "asset"),
    ):
        _require_nonempty(value, field_name)
    _require_digest(payment_requirements_digest, "payment_requirements_digest")
    return _build_execution_request(
        binding=binding,
        ecosystem=ExternalEcosystem.COINBASE_X402,
        provider_payload={
            "http_status": 402,
            "resource_ref": resource_ref,
            "payment_requirements_digest": payment_requirements_digest,
            "payment_signature_ref": payment_signature_ref,
            "facilitator_ref": facilitator_ref,
            "network": network,
            "asset": asset,
        },
        idempotency_key=idempotency_key,
        constructed_at=constructed_at,
    )


def build_open_banking_payment_request(
    *,
    binding: ExternalExecutionBinding,
    aspsp_ref: str,
    pisp_ref: str,
    consent_ref: str,
    payment_resource_ref: str,
    api_profile_ref: str,
    idempotency_key: str,
    constructed_at: datetime,
) -> ExternalAdapterExecutionRequest:
    if binding.amount_minor is None or binding.currency is None:
        raise ValueError(
            "Open Banking projection requires an amount-bound execution binding"
        )
    for value, field_name in (
        (aspsp_ref, "aspsp_ref"),
        (pisp_ref, "pisp_ref"),
        (consent_ref, "consent_ref"),
        (payment_resource_ref, "payment_resource_ref"),
        (api_profile_ref, "api_profile_ref"),
    ):
        _require_nonempty(value, field_name)
    return _build_execution_request(
        binding=binding,
        ecosystem=ExternalEcosystem.OPEN_BANKING,
        provider_payload={
            "aspsp_ref": aspsp_ref,
            "pisp_ref": pisp_ref,
            "consent_ref": consent_ref,
            "payment_resource_ref": payment_resource_ref,
            "api_profile_ref": api_profile_ref,
        },
        idempotency_key=idempotency_key,
        constructed_at=constructed_at,
    )


class ExternalStateClass(StrEnum):
    BUDGET = "BUDGET"
    MANDATE = "MANDATE"
    PURCHASE_ORDER = "PURCHASE_ORDER"
    COUNTERPARTY = "COUNTERPARTY"
    TREASURY_POSITION = "TREASURY_POSITION"
    CASH_FORECAST = "CASH_FORECAST"
    ACCOUNT_STATE = "ACCOUNT_STATE"
    PAYMENT_CONSENT = "PAYMENT_CONSENT"


class ExternalStateObservation(BaseModel):
    schema_version: Literal["external_state_observation.v1"] = (
        "external_state_observation.v1"
    )
    observation_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    ecosystem: ExternalEcosystem
    adapter_id: str
    source_system_ref: str
    evidence_ref: str
    state_class: ExternalStateClass
    object_ref: str
    source_version: str
    observed_at: datetime
    valid_until: datetime
    source_payload_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    assertions: tuple[str, ...]
    assertions_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    observation_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False
    raw_payload_exported: Literal[False] = False
    external_truth_claim: Literal["NO_EXTERNAL_TRUTH_CLAIM"] = (
        "NO_EXTERNAL_TRUTH_CLAIM"
    )

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"observation_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_observation(self) -> ExternalStateObservation:
        for value, field_name in (
            (self.adapter_id, "adapter_id"),
            (self.source_system_ref, "source_system_ref"),
            (self.evidence_ref, "evidence_ref"),
            (self.object_ref, "object_ref"),
            (self.source_version, "source_version"),
        ):
            _require_nonempty(value, field_name)
        _require_aware(self.observed_at, "observed_at")
        _require_aware(self.valid_until, "valid_until")
        if self.valid_until <= self.observed_at:
            raise ValueError("external state observation requires a positive validity window")
        if not self.assertions or len(set(self.assertions)) != len(self.assertions):
            raise ValueError("assertions must be non-empty and unique")
        if self.assertions_digest != canonical_digest(sorted(self.assertions)):
            raise ValueError("external state assertions digest mismatch")
        if self.observation_digest and self.observation_digest != self.computed_digest:
            raise ValueError("external state observation digest mismatch")
        return self


def seal_external_state_observation(
    *,
    ecosystem: ExternalEcosystem,
    source_system_ref: str,
    evidence_ref: str,
    state_class: ExternalStateClass,
    object_ref: str,
    source_version: str,
    observed_at: datetime,
    valid_until: datetime,
    source_payload_digest: str,
    assertions: tuple[str, ...],
) -> ExternalStateObservation:
    manifest = ECOSYSTEM_MANIFESTS[ecosystem]
    if manifest.role is ExternalAdapterRole.EXECUTION_PROJECTION:
        raise ValueError("execution-only adapter cannot emit authoritative-state observation")
    _require_digest(source_payload_digest, "source_payload_digest")
    normalized_assertions = tuple(sorted(assertions))
    observation_id = canonical_digest(
        {
            "ecosystem": ecosystem.value,
            "adapter_id": manifest.adapter_id,
            "source_system_ref": source_system_ref,
            "evidence_ref": evidence_ref,
            "state_class": state_class.value,
            "object_ref": object_ref,
            "source_version": source_version,
            "observed_at": observed_at.isoformat(),
            "source_payload_digest": source_payload_digest,
        }
    )
    unsealed = ExternalStateObservation(
        observation_id=observation_id,
        ecosystem=ecosystem,
        adapter_id=manifest.adapter_id,
        source_system_ref=source_system_ref,
        evidence_ref=evidence_ref,
        state_class=state_class,
        object_ref=object_ref,
        source_version=source_version,
        observed_at=observed_at,
        valid_until=valid_until,
        source_payload_digest=source_payload_digest,
        assertions=normalized_assertions,
        assertions_digest=canonical_digest(list(normalized_assertions)),
    )
    return ExternalStateObservation.model_validate(
        {
            **unsealed.model_dump(mode="python"),
            "observation_digest": unsealed.computed_digest,
        }
    )


def build_sap_state_observation(
    *,
    source_system_ref: str,
    evidence_ref: str,
    state_class: ExternalStateClass,
    object_ref: str,
    source_version: str,
    observed_at: datetime,
    valid_until: datetime,
    source_payload_digest: str,
    assertions: tuple[str, ...],
) -> ExternalStateObservation:
    if state_class not in {
        ExternalStateClass.BUDGET,
        ExternalStateClass.MANDATE,
        ExternalStateClass.PURCHASE_ORDER,
        ExternalStateClass.COUNTERPARTY,
    }:
        raise ValueError("state_class is outside the SAP reference adapter scope")
    return seal_external_state_observation(
        ecosystem=ExternalEcosystem.SAP,
        source_system_ref=source_system_ref,
        evidence_ref=evidence_ref,
        state_class=state_class,
        object_ref=object_ref,
        source_version=source_version,
        observed_at=observed_at,
        valid_until=valid_until,
        source_payload_digest=source_payload_digest,
        assertions=assertions,
    )


def build_kyriba_state_observation(
    *,
    source_system_ref: str,
    evidence_ref: str,
    state_class: ExternalStateClass,
    object_ref: str,
    source_version: str,
    observed_at: datetime,
    valid_until: datetime,
    source_payload_digest: str,
    assertions: tuple[str, ...],
) -> ExternalStateObservation:
    if state_class not in {
        ExternalStateClass.MANDATE,
        ExternalStateClass.TREASURY_POSITION,
        ExternalStateClass.CASH_FORECAST,
        ExternalStateClass.ACCOUNT_STATE,
    }:
        raise ValueError("state_class is outside the Kyriba reference adapter scope")
    return seal_external_state_observation(
        ecosystem=ExternalEcosystem.KYRIBA,
        source_system_ref=source_system_ref,
        evidence_ref=evidence_ref,
        state_class=state_class,
        object_ref=object_ref,
        source_version=source_version,
        observed_at=observed_at,
        valid_until=valid_until,
        source_payload_digest=source_payload_digest,
        assertions=assertions,
    )


class ExternalAdapterEvidence(BaseModel):
    schema_version: Literal["external_adapter_evidence.v2"] = (
        "external_adapter_evidence.v2"
    )
    evidence_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    ecosystem: ExternalEcosystem
    request_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    binding_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    provider_ref: str
    response_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    disposition: ProviderOutcomeDisposition
    observed_at: datetime
    evidence_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    settlement_claim: Literal["NO_SETTLEMENT_CLAIM"] = "NO_SETTLEMENT_CLAIM"
    external_truth_claim: Literal["NO_EXTERNAL_TRUTH_CLAIM"] = (
        "NO_EXTERNAL_TRUTH_CLAIM"
    )

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"evidence_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_evidence(self) -> ExternalAdapterEvidence:
        _require_nonempty(self.provider_ref, "provider_ref")
        _require_aware(self.observed_at, "observed_at")
        if self.evidence_digest and self.evidence_digest != self.computed_digest:
            raise ValueError("external adapter evidence digest mismatch")
        return self


def record_external_adapter_evidence(
    *,
    request: ExternalAdapterExecutionRequest,
    provider_ref: str,
    response_digest: str,
    disposition: ProviderOutcomeDisposition,
    observed_at: datetime,
) -> ExternalAdapterEvidence:
    if request.request_digest != request.computed_digest:
        raise ValueError("external adapter request is unsealed or tampered")
    _require_digest(response_digest, "response_digest")
    _require_nonempty(provider_ref, "provider_ref")
    _require_aware(observed_at, "observed_at")
    if observed_at < request.constructed_at:
        raise ValueError("provider evidence cannot predate the request")
    evidence_id = canonical_digest(
        {
            "ecosystem": request.ecosystem.value,
            "request_digest": request.request_digest,
            "binding_digest": request.binding_digest,
            "provider_ref": provider_ref,
            "response_digest": response_digest,
            "disposition": disposition.value,
            "observed_at": observed_at.isoformat(),
        }
    )
    unsealed = ExternalAdapterEvidence(
        evidence_id=evidence_id,
        ecosystem=request.ecosystem,
        request_digest=request.request_digest,
        binding_digest=request.binding_digest,
        provider_ref=provider_ref,
        response_digest=response_digest,
        disposition=disposition,
        observed_at=observed_at,
    )
    return ExternalAdapterEvidence.model_validate(
        {
            **unsealed.model_dump(mode="python"),
            "evidence_digest": unsealed.computed_digest,
        }
    )
