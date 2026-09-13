"""Canonical provider adapter stubs for external payment systems.

These stubs implement only the reference contract. They do not perform live
network I/O, settlement, or any side-effecting operation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from valo_external_adapters.external_execution_binding import (
    ActionDigest,
    ExternalExecutionBinding,
    LeaseEvaluation,
    ProviderResponseStatus,
    RevocationCheckpoint,
)


@dataclass(frozen=True)
class ProviderAdapterResult:
    provider_response_status: ProviderResponseStatus
    provider_response: dict[str, Any] = field(default_factory=dict)
    next_revocation_checkpoint: RevocationCheckpoint | None = None


class BaseExternalPaymentAdapter:
    provider_name: str = "base"

    def evaluate(
        self,
        action_digest: ActionDigest,
        lease_evaluation: LeaseEvaluation,
    ) -> ProviderAdapterResult:
        raise NotImplementedError

    def build_binding(
        self,
        action_digest: ActionDigest,
        lease_evaluation: LeaseEvaluation,
        provider_result: ProviderAdapterResult,
    ) -> ExternalExecutionBinding:
        return ExternalExecutionBinding(
            action_digest=action_digest,
            lease_evaluation=lease_evaluation,
            provider_response=provider_result.provider_response,
            provider_response_status=provider_result.provider_response_status,
            settlement=False,
        )


class SwiftCBPRPlusAdapter(BaseExternalPaymentAdapter):
    provider_name = "swift_cbpr_plus"

    def evaluate(
        self,
        action_digest: ActionDigest,
        lease_evaluation: LeaseEvaluation,
    ) -> ProviderAdapterResult:
        if not lease_evaluation.approved:
            return ProviderAdapterResult(
                provider_response_status=ProviderResponseStatus.REJECTED,
                provider_response={"reason": "lease_evaluation not approved"},
            )
        return ProviderAdapterResult(
            provider_response_status=ProviderResponseStatus.REQUIRES_REVOCATION_CHECK,
            provider_response={
                "message_type": "pacs.008",
                "digest_required": True,
                "status": "awaiting_bank_digest",
            },
        )


class VisaTrustedAgentAdapter(BaseExternalPaymentAdapter):
    provider_name = "visa_trusted_agent"

    def evaluate(
        self,
        action_digest: ActionDigest,
        lease_evaluation: LeaseEvaluation,
    ) -> ProviderAdapterResult:
        if not lease_evaluation.approved:
            return ProviderAdapterResult(
                provider_response_status=ProviderResponseStatus.REJECTED,
                provider_response={"reason": "lease_evaluation not approved"},
            )
        return ProviderAdapterResult(
            provider_response_status=ProviderResponseStatus.REQUIRES_REVOCATION_CHECK,
            provider_response={"trusted_agent_state": "pending_revocation_check"},
        )


class MastercardAgentPayAdapter(BaseExternalPaymentAdapter):
    provider_name = "mastercard_agent_pay"

    def evaluate(
        self,
        action_digest: ActionDigest,
        lease_evaluation: LeaseEvaluation,
    ) -> ProviderAdapterResult:
        if not lease_evaluation.approved:
            return ProviderAdapterResult(
                provider_response_status=ProviderResponseStatus.REJECTED,
                provider_response={"reason": "lease_evaluation not approved"},
            )
        return ProviderAdapterResult(
            provider_response_status=ProviderResponseStatus.REQUIRES_REVOCATION_CHECK,
            provider_response={"agent_pay_state": "pending_revocation_check"},
        )


class StripeAgenticPaymentsAdapter(BaseExternalPaymentAdapter):
    provider_name = "stripe_agentic_payments"

    def evaluate(
        self,
        action_digest: ActionDigest,
        lease_evaluation: LeaseEvaluation,
    ) -> ProviderAdapterResult:
        if not lease_evaluation.approved:
            return ProviderAdapterResult(
                provider_response_status=ProviderResponseStatus.REJECTED,
                provider_response={"reason": "lease_evaluation not approved"},
            )
        return ProviderAdapterResult(
            provider_response_status=ProviderResponseStatus.REQUIRES_REVOCATION_CHECK,
            provider_response={
                "shared_payment_token_state": "pending_revocation_check",
                "action_digest_required": True,
            },
        )
