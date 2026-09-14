import pytest

from heimel_stripe_funding import FundingError, StripeFundingAdapter


class Ledger:
    def __init__(self):
        self.credits = {}

    def credit(self, *, ledger_account, amount_minor, currency, funding_id, provider_reference):
        if funding_id in self.credits:
            return False
        self.credits[funding_id] = {
            "ledger_account": ledger_account,
            "amount_minor": amount_minor,
            "currency": currency,
            "provider_reference": provider_reference,
        }
        return True


def paid_event(**overrides):
    obj = {
        "id": "cs_test_1",
        "payment_status": "paid",
        "amount_total": 10000,
        "currency": "usd",
        "metadata": {
            "heimel_funding_id": "fund_1",
            "heimel_ledger_account": "org_1",
            "heimel_funding_kind": "prepaid_consequence_balance",
        },
    }
    obj.update(overrides)
    return {"type": "checkout.session.completed", "data": {"object": obj}}


def test_verified_paid_event_credits_ledger_once():
    ledger = Ledger()
    event = paid_event()
    assert StripeFundingAdapter.apply_verified_checkout_event(event, ledger) is True
    assert StripeFundingAdapter.apply_verified_checkout_event(event, ledger) is False
    assert ledger.credits["fund_1"]["amount_minor"] == 10000
    assert ledger.credits["fund_1"]["currency"] == "USD"


def test_unrelated_event_does_not_credit():
    ledger = Ledger()
    assert StripeFundingAdapter.apply_verified_checkout_event(
        {"type": "payment_intent.created", "data": {"object": {}}}, ledger
    ) is False
    assert ledger.credits == {}


def test_unpaid_completed_session_fails_closed():
    ledger = Ledger()
    with pytest.raises(FundingError, match="not paid"):
        StripeFundingAdapter.apply_verified_checkout_event(
            paid_event(payment_status="unpaid"), ledger
        )
    assert ledger.credits == {}


def test_missing_heimel_binding_fails_closed():
    ledger = Ledger()
    with pytest.raises(FundingError, match="missing Heimel funding binding"):
        StripeFundingAdapter.apply_verified_checkout_event(
            paid_event(metadata={"heimel_funding_kind": "prepaid_consequence_balance"}),
            ledger,
        )
    assert ledger.credits == {}


def test_wrong_funding_kind_fails_closed():
    ledger = Ledger()
    metadata = {
        "heimel_funding_id": "fund_1",
        "heimel_ledger_account": "org_1",
        "heimel_funding_kind": "something_else",
    }
    with pytest.raises(FundingError, match="unexpected funding kind"):
        StripeFundingAdapter.apply_verified_checkout_event(
            paid_event(metadata=metadata), ledger
        )


def test_currency_mismatch_fails_closed():
    ledger = Ledger()
    with pytest.raises(FundingError, match="currency mismatch"):
        StripeFundingAdapter.apply_verified_checkout_event(
            paid_event(currency="eur"), ledger
        )
