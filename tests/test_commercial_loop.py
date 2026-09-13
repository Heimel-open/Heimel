import unittest

from lib.commercial_loop import (
    CommercialLoop,
    CommercialState,
    CustomerAcceptanceRef,
    ExecutionGovernanceRef,
    IndependentVerificationRef,
    OpportunityOrigin,
    PaymentConfirmationRef,
)


def _gov(action: str) -> ExecutionGovernanceRef:
    return ExecutionGovernanceRef(
        action=action,
        vaig_ref=f"vaig:{action}",
        reht_ref=f"reht:{action}",
        racs_ref=f"racs:{action}",
        execution_receipt_ref=f"receipt:{action}",
    )


def _verification(artifact: str) -> IndependentVerificationRef:
    return IndependentVerificationRef(
        artifact_ref=artifact,
        producer_ref="builder-provider-a",
        judge_ref="judge-provider-b",
        verdict="pass",
        evidence_refs=(f"test:{artifact}",),
    )


def _accept(subject: str) -> CustomerAcceptanceRef:
    return CustomerAcceptanceRef(
        subject=subject,
        acceptance_ref=f"customer-acceptance:{subject}",
        accepted_by="customer-authorized-representative",
    )


class CommercialLoopTests(unittest.TestCase):
    def test_full_signal_to_customer_loop(self):
        loop = CommercialLoop(
            "opp-1", origin=OpportunityOrigin.COMPETITOR_PUBLIC_SIGNAL
        )

        loop.transition(CommercialState.IMPACT_EVIDENCED, evidence_refs=["baro:impact"])
        loop.transition(
            CommercialState.PROSPECT_EVIDENCED,
            evidence_refs=["speider:vibe:contact"],
        )
        loop.transition(CommercialState.OUTREACH_READY, evidence_refs=["outreach:package"])
        loop.transition(
            CommercialState.OUTREACH_SENT,
            evidence_refs=["message:receipt"],
            governance_ref=_gov("outreach-send"),
        )
        loop.transition(CommercialState.RESPONSE_OBSERVED, evidence_refs=["reply:1"])
        loop.transition(
            CommercialState.POC_TERMS_PROPOSED,
            evidence_refs=["poc:terms:v1"],
            governance_ref=_gov("poc-terms-send"),
        )
        loop.transition(
            CommercialState.POC_TERMS_ACCEPTED,
            evidence_refs=["poc:terms:v1"],
            acceptance_ref=_accept("poc-terms-v1"),
        )
        loop.transition(CommercialState.POC_MISSION_CREATED, evidence_refs=["mission:poc"])
        loop.transition(
            CommercialState.POC_VERIFIED,
            evidence_refs=["artifact:poc"],
            verification_ref=_verification("poc"),
        )
        loop.transition(
            CommercialState.POC_SUBMITTED,
            evidence_refs=["delivery:poc"],
            governance_ref=_gov("poc-submit"),
        )
        loop.transition(
            CommercialState.POC_APPROVED,
            evidence_refs=["approval:poc"],
            acceptance_ref=_accept("poc-v1"),
        )
        loop.transition(
            CommercialState.PAYMENT_REQUESTED,
            evidence_refs=["invoice:1"],
            governance_ref=_gov("payment-request"),
        )
        loop.transition(
            CommercialState.PAYMENT_CONFIRMED,
            evidence_refs=["payment:webhook:1"],
            payment_ref=PaymentConfirmationRef(
                provider="stripe",
                transaction_ref="pi_123",
                amount="25000.00",
                currency="EUR",
            ),
        )
        loop.transition(
            CommercialState.PRODUCTION_SPEC_ACCEPTED,
            evidence_refs=["spec:v1"],
            acceptance_ref=_accept("production-spec-v1"),
        )
        loop.transition(
            CommercialState.PRODUCTION_MISSION_CREATED,
            evidence_refs=["mission:prod"],
        )
        loop.transition(
            CommercialState.PRODUCTION_VERIFIED,
            evidence_refs=["artifact:prod"],
            verification_ref=_verification("prod"),
        )
        loop.transition(CommercialState.DEPLOYMENT_READY, evidence_refs=["deploy:ready"])
        loop.transition(
            CommercialState.CUSTOMER_ACTIVE,
            evidence_refs=["deploy:receipt"],
            governance_ref=_gov("production-deploy"),
        )
        loop.transition(
            CommercialState.SERVICE_SIGNAL_OBSERVED,
            evidence_refs=["service:signal"],
        )
        loop.transition(
            CommercialState.SUPPORT_MISSION_CREATED,
            evidence_refs=["mission:support"],
        )
        loop.transition(
            CommercialState.SUPPORT_VERIFIED,
            evidence_refs=["artifact:support"],
            verification_ref=_verification("support"),
        )
        loop.transition(
            CommercialState.CUSTOMER_ACTIVE,
            evidence_refs=["support:deployed"],
            governance_ref=_gov("support-deploy"),
        )
        loop.transition(
            CommercialState.OUTCOME_OBSERVED,
            evidence_refs=["baro:outcome"],
        )

        self.assertIs(loop.state, CommercialState.OUTCOME_OBSERVED)
        self.assertFalse(loop.has_authority_surface)

    def test_external_send_fails_without_governance(self):
        loop = CommercialLoop("opp-2")
        loop.transition(CommercialState.IMPACT_EVIDENCED, evidence_refs=["baro:impact"])
        loop.transition(CommercialState.PROSPECT_EVIDENCED, evidence_refs=["prospect:1"])
        loop.transition(CommercialState.OUTREACH_READY, evidence_refs=["package:1"])

        with self.assertRaisesRegex(ValueError, "execution governance"):
            loop.transition(CommercialState.OUTREACH_SENT, evidence_refs=["message:1"])

    def test_poc_cannot_self_attest(self):
        with self.assertRaisesRegex(ValueError, "self-attest"):
            IndependentVerificationRef(
                artifact_ref="poc",
                producer_ref="same-provider",
                judge_ref="same-provider",
                verdict="pass",
            )

    def test_payment_confirmation_requires_provider_receipt(self):
        loop = CommercialLoop("opp-3")
        loop.state = CommercialState.PAYMENT_REQUESTED

        with self.assertRaisesRegex(ValueError, "provider payment confirmation"):
            loop.transition(
                CommercialState.PAYMENT_CONFIRMED,
                evidence_refs=["claimed-paid"],
            )

    def test_customer_acceptance_is_required_for_scope_changes(self):
        loop = CommercialLoop("opp-4")
        loop.state = CommercialState.POC_TERMS_PROPOSED

        with self.assertRaisesRegex(ValueError, "explicit customer acceptance"):
            loop.transition(
                CommercialState.POC_TERMS_ACCEPTED,
                evidence_refs=["terms:v1"],
            )


if __name__ == "__main__":
    unittest.main()
