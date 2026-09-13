import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from lib.commercial_terms import NegotiationMandate, POCProposal, validate_proposal


def _mandate() -> NegotiationMandate:
    return NegotiationMandate(
        mandate_ref="mandate:smb:poc:v1",
        currency="EUR",
        min_poc_price=Decimal("2500"),
        max_poc_price=Decimal("25000"),
        max_discount_percent=Decimal("15"),
        max_delivery_days=21,
        allowed_payment_methods=("stripe", "bank_transfer", "smart_contract"),
        allowed_channels=("email", "sms", "phone", "web"),
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )


def _proposal(**overrides) -> POCProposal:
    values = {
        "proposal_ref": "proposal:1",
        "mandate_ref": "mandate:smb:poc:v1",
        "customer_ref": "customer:acme",
        "problem_ref": "baro:problem:1",
        "spec_ref": "spec:poc:v1",
        "price": Decimal("7500"),
        "currency": "EUR",
        "discount_percent": Decimal("5"),
        "delivery_days": 10,
        "payment_method": "stripe",
        "channel": "email",
        "acceptance_criteria": ("scenario passes", "customer accepts output"),
        "terms": (),
    }
    values.update(overrides)
    return POCProposal(**values)


class CommercialTermsTests(unittest.TestCase):
    def test_valid_proposal_is_inside_mandate(self):
        ok, problems = validate_proposal(_mandate(), _proposal())
        self.assertTrue(ok)
        self.assertEqual(problems, ())
        self.assertFalse(_mandate().grants_authority)

    def test_price_discount_delivery_and_channel_are_bounded(self):
        ok, problems = validate_proposal(
            _mandate(),
            _proposal(
                price=Decimal("50000"),
                discount_percent=Decimal("25"),
                delivery_days=60,
                payment_method="unknown-provider",
                channel="carrier-pigeon",
            ),
        )
        self.assertFalse(ok)
        self.assertIn("price_out_of_bounds", problems)
        self.assertIn("discount_out_of_bounds", problems)
        self.assertIn("delivery_out_of_bounds", problems)
        self.assertIn("payment_method_not_allowed", problems)
        self.assertIn("channel_not_allowed", problems)

    def test_expired_mandate_fails_closed(self):
        mandate = _mandate()
        future = mandate.expires_at + timedelta(seconds=1)
        ok, problems = validate_proposal(mandate, _proposal(), now=future)
        self.assertFalse(ok)
        self.assertIn("mandate_expired", problems)

    def test_prohibited_commercial_term_is_rejected(self):
        ok, problems = validate_proposal(
            _mandate(),
            _proposal(terms=("uncapped_liability",)),
        )
        self.assertFalse(ok)
        self.assertIn("prohibited_term:uncapped_liability", problems)


if __name__ == "__main__":
    unittest.main()
