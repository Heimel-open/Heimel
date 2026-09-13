import unittest

from lib.commercial_channels import (
    ChannelDirection,
    CommercialChannel,
    CommercialChannelEvent,
)
from lib.commercial_loop import CommercialLoop, CommercialState
from lib.commercial_missions import CommercialMissionKind, CommercialMissionSpec
from lib.commercial_runtime import CommercialRuntime, ServiceCheckResult


def _event(ref: str) -> CommercialChannelEvent:
    return CommercialChannelEvent(
        event_ref=ref,
        direction=ChannelDirection.INBOUND,
        channel=CommercialChannel.EMAIL,
        counterparty_ref="customer:acme",
        provider_ref="mail-provider",
        payload_digest="a" * 64,
    )


def _spec(kind: CommercialMissionKind) -> CommercialMissionSpec:
    return CommercialMissionSpec(
        kind=kind,
        customer_ref="customer:acme",
        spec_ref=f"spec:{kind.value}:v1",
        spec_digest="b" * 64,
        target_repo="nsolland/customer-acme",
        objective=f"Build {kind.value}",
        owned_files=("src/**", "tests/**"),
        acceptance_criteria=("tests green",),
    )


class CommercialRuntimeTests(unittest.TestCase):
    def test_inbound_reply_advances_outreach_to_response_observed(self):
        loop = CommercialLoop("opp-1")
        loop.state = CommercialState.OUTREACH_SENT
        runtime = CommercialRuntime()

        state = runtime.observe_inbound(loop, _event("email:reply:1"))

        self.assertIs(state, CommercialState.RESPONSE_OBSERVED)
        self.assertEqual(loop.history[-1].evidence_refs, ("email:reply:1",))
        self.assertFalse(runtime.has_authority_surface)

    def test_inbound_customer_event_opens_service_signal(self):
        loop = CommercialLoop("opp-2")
        loop.state = CommercialState.CUSTOMER_ACTIVE
        runtime = CommercialRuntime()

        state = runtime.observe_inbound(loop, _event("support:email:1"))

        self.assertIs(state, CommercialState.SERVICE_SIGNAL_OBSERVED)

    def test_outbound_event_cannot_be_treated_as_observation(self):
        loop = CommercialLoop("opp-3")
        loop.state = CommercialState.OUTREACH_SENT
        event = CommercialChannelEvent(
            event_ref="email:send:1",
            direction=ChannelDirection.OUTBOUND,
            channel=CommercialChannel.EMAIL,
            counterparty_ref="prospect:1",
            provider_ref="mail-provider",
            payload_digest="c" * 64,
        )

        with self.assertRaisesRegex(ValueError, "only inbound"):
            CommercialRuntime().observe_inbound(loop, event)

    def test_accepted_poc_scope_becomes_normal_factory_build_order(self):
        loop = CommercialLoop("opp-4")
        loop.state = CommercialState.POC_TERMS_ACCEPTED

        order = CommercialRuntime().create_build_mission(
            loop,
            _spec(CommercialMissionKind.POC),
            principal="commercial-orchestrator",
            authority_basis="accepted-poc-terms",
        )

        self.assertIs(loop.state, CommercialState.POC_MISSION_CREATED)
        self.assertTrue(order.requires_independent_qc)
        self.assertIn(order.build_order_id, loop.history[-1].evidence_refs)

    def test_failed_service_check_opens_support_path(self):
        loop = CommercialLoop("opp-5")
        loop.state = CommercialState.CUSTOMER_ACTIVE
        result = ServiceCheckResult(
            service_ref="service:acme",
            check_ref="synthetic:checkout:42",
            healthy=False,
            evidence_refs=("trace:42", "metric:availability"),
        )

        state = CommercialRuntime().observe_service_check(loop, result)

        self.assertIs(state, CommercialState.SERVICE_SIGNAL_OBSERVED)
        self.assertIn("trace:42", loop.history[-1].evidence_refs)

    def test_healthy_service_check_creates_no_false_work(self):
        loop = CommercialLoop("opp-6")
        loop.state = CommercialState.CUSTOMER_ACTIVE
        result = ServiceCheckResult(
            service_ref="service:acme",
            check_ref="synthetic:checkout:43",
            healthy=True,
            evidence_refs=("trace:43",),
        )

        state = CommercialRuntime().observe_service_check(loop, result)

        self.assertIs(state, CommercialState.CUSTOMER_ACTIVE)
        self.assertEqual(loop.history, [])


if __name__ == "__main__":
    unittest.main()
