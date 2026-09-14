from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from stripe import StripeClient


class FundingError(RuntimeError):
    pass


class FundingLedger(Protocol):
    def credit(
        self,
        *,
        ledger_account: str,
        amount_minor: int,
        currency: str,
        funding_id: str,
        provider_reference: str,
    ) -> bool: ...


@dataclass(frozen=True)
class TopUpRequest:
    funding_id: str
    ledger_account: str
    stripe_customer_id: str
    amount_minor: int
    currency: str = "usd"

    def __post_init__(self) -> None:
        if not self.funding_id:
            raise FundingError("funding_id is required")
        if not self.ledger_account:
            raise FundingError("ledger_account is required")
        if not self.stripe_customer_id:
            raise FundingError("stripe_customer_id is required")
        if self.amount_minor <= 0:
            raise FundingError("amount_minor must be positive")
        if self.currency.lower() != "usd":
            raise FundingError("reference adapter currently requires USD")


@dataclass(frozen=True)
class TopUpSession:
    funding_id: str
    stripe_session_id: str
    checkout_url: str
    amount_minor: int
    currency: str


class StripeFundingAdapter:
    """Optional provider adapter for funding a Heimel prepaid consequence ledger.

    Stripe is used to move money into the funded balance. Consequence-level
    settlement remains inside Heimel; this adapter MUST NOT create a Stripe
    transaction per governed consequence.
    """

    INTEGRATION_IDENTIFIER = "heimel_settlement_qtmrjvka"

    def __init__(self, api_key: str, *, min_topup_minor: int = 500) -> None:
        if not api_key:
            raise FundingError("Stripe API key is required")
        if min_topup_minor <= 0:
            raise FundingError("min_topup_minor must be positive")
        self._client = StripeClient(api_key)
        self._min_topup_minor = min_topup_minor

    def create_topup_session(
        self,
        request: TopUpRequest,
        *,
        success_url: str,
        cancel_url: str,
    ) -> TopUpSession:
        if request.amount_minor < self._min_topup_minor:
            raise FundingError("top-up amount is below configured minimum")
        if not success_url or not cancel_url:
            raise FundingError("success_url and cancel_url are required")

        session = self._client.checkout.sessions.create(
            {
                "mode": "payment",
                "customer": request.stripe_customer_id,
                "success_url": success_url,
                "cancel_url": cancel_url,
                "integration_identifier": self.INTEGRATION_IDENTIFIER,
                "line_items": [
                    {
                        "quantity": 1,
                        "price_data": {
                            "currency": request.currency.lower(),
                            "unit_amount": request.amount_minor,
                            "product_data": {
                                "name": "Heimel Enterprise consequence balance top-up"
                            },
                        },
                    }
                ],
                "metadata": {
                    "heimel_funding_id": request.funding_id,
                    "heimel_ledger_account": request.ledger_account,
                    "heimel_funding_kind": "prepaid_consequence_balance",
                },
            },
            options={"idempotency_key": f"heimel-funding:{request.funding_id}"},
        )

        if not session.id or not session.url:
            raise FundingError("Stripe returned an incomplete Checkout Session")

        return TopUpSession(
            funding_id=request.funding_id,
            stripe_session_id=session.id,
            checkout_url=session.url,
            amount_minor=request.amount_minor,
            currency=request.currency.lower(),
        )

    @staticmethod
    def apply_verified_checkout_event(event: dict, ledger: FundingLedger) -> bool:
        """Credit the Heimel ledger from a signature-verified Stripe event.

        Webhook signature verification belongs at the HTTP boundary. This
        method accepts only an already verified event and performs strict
        semantic checks before admitting funds to the Heimel ledger.
        """
        if event.get("type") != "checkout.session.completed":
            return False

        obj = ((event.get("data") or {}).get("object") or {})
        if obj.get("payment_status") != "paid":
            raise FundingError("completed Checkout Session is not paid")

        metadata = obj.get("metadata") or {}
        funding_id = metadata.get("heimel_funding_id")
        ledger_account = metadata.get("heimel_ledger_account")
        funding_kind = metadata.get("heimel_funding_kind")
        provider_reference = obj.get("id")
        amount_minor = obj.get("amount_total")
        currency = (obj.get("currency") or "").lower()

        if funding_kind != "prepaid_consequence_balance":
            raise FundingError("unexpected funding kind")
        if not funding_id or not ledger_account or not provider_reference:
            raise FundingError("Stripe event is missing Heimel funding binding")
        if not isinstance(amount_minor, int) or amount_minor <= 0:
            raise FundingError("Stripe event has invalid amount_total")
        if currency != "usd":
            raise FundingError("Stripe event currency mismatch")

        return ledger.credit(
            ledger_account=ledger_account,
            amount_minor=amount_minor,
            currency=currency.upper(),
            funding_id=funding_id,
            provider_reference=provider_reference,
        )


__all__ = [
    "FundingError",
    "FundingLedger",
    "StripeFundingAdapter",
    "TopUpRequest",
    "TopUpSession",
]
