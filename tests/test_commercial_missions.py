import unittest

from lib.commercial_loop import CommercialLoop, CommercialState
from lib.commercial_missions import (
    CommercialMissionKind,
    CommercialMissionSpec,
    build_order_from_commercial_spec,
)


def _spec(kind: CommercialMissionKind) -> CommercialMissionSpec:
    return CommercialMissionSpec(
        kind=kind,
        customer_ref="customer:acme",
        spec_ref=f"spec:{kind.value}:v1",
        spec_digest="a" * 64,
        target_repo="nsolland/customer-acme",
        objective=f"Build {kind.value} implementation to accepted spec",
        owned_files=("src/**", "tests/**"),
        acceptance_criteria=("tests green", "matches accepted spec"),
        dependencies=("customer-spec-v1",),
        canonical_base_sha="b" * 40,
    )


class CommercialMissionTests(unittest.TestCase):
    def test_poc_build_order_requires_accepted_poc_terms(self):
        loop = CommercialLoop("opp-1")
        loop.state = CommercialState.POC_TERMS_ACCEPTED

        order = build_order_from_commercial_spec(
            loop,
            _spec(CommercialMissionKind.POC),
            principal="commercial-orchestrator",
            authority_basis="customer-accepted-poc-terms",
        )

        self.assertEqual(order.target_repo, "nsolland/customer-acme")
        self.assertTrue(order.requires_independent_qc)
        self.assertTrue(order.requires_receipt)
        self.assertEqual(order.authority_effect, "none")
        self.assertEqual(order.scope.paths, ("src/**", "tests/**"))
        self.assertTrue(order.idempotency_key)

    def test_production_cannot_start_before_customer_accepts_production_spec(self):
        loop = CommercialLoop("opp-2")
        loop.state = CommercialState.PAYMENT_CONFIRMED

        with self.assertRaisesRegex(ValueError, "PRODUCTION_SPEC_ACCEPTED"):
            build_order_from_commercial_spec(
                loop,
                _spec(CommercialMissionKind.PRODUCTION),
                principal="commercial-orchestrator",
                authority_basis="payment-confirmed",
            )

    def test_support_mission_uses_same_factory_governance(self):
        loop = CommercialLoop("opp-3")
        loop.state = CommercialState.SERVICE_SIGNAL_OBSERVED

        order = build_order_from_commercial_spec(
            loop,
            _spec(CommercialMissionKind.SUPPORT),
            principal="customer-ops-orchestrator",
            authority_basis="support-policy",
        )

        self.assertEqual(
            order.risk_hints,
            ("commercial-customer-delivery", "support"),
        )
        self.assertTrue(order.requires_independent_qc)

    def test_commercial_spec_requires_bounded_scope(self):
        with self.assertRaisesRegex(ValueError, "owned_files"):
            CommercialMissionSpec(
                kind=CommercialMissionKind.POC,
                customer_ref="customer:acme",
                spec_ref="spec:poc:v1",
                spec_digest="a" * 64,
                target_repo="nsolland/customer-acme",
                objective="Build POC",
                owned_files=(),
                acceptance_criteria=("works",),
            )


if __name__ == "__main__":
    unittest.main()
