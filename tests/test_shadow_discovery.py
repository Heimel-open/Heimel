import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from lib.shadow_discovery import (
    DiscoveryOpportunity,
    DiscoveryProposal,
    ShadowDiscoveryGrant,
    ShadowObservation,
    default_shadow_roles,
    validate_observation_against_grant,
)


class ShadowDiscoveryTests(unittest.TestCase):
    def _grant(self):
        now = datetime.now(timezone.utc)
        return ShadowDiscoveryGrant(
            grant_ref="shadow:grant:1",
            customer_ref="customer:acme",
            allowed_sources=("repo:app", "jira:ops", "docs:process"),
            allowed_roles=default_shadow_roles(),
            starts_at=now - timedelta(minutes=1),
            expires_at=now + timedelta(days=3),
            read_only=True,
        )

    def test_shadow_grant_is_read_only_and_non_authoritative(self):
        grant = self._grant()
        self.assertTrue(grant.active())
        self.assertFalse(grant.grants_execution_authority)
        self.assertTrue(grant.read_only)

    def test_observation_must_be_inside_source_and_role_scope(self):
        grant = self._grant()
        observation = ShadowObservation(
            observation_ref="obs:1",
            role="process-shadow",
            source_ref="jira:ops",
            finding="manual re-entry occurs between two systems",
            evidence_refs=("ticket:123", "ticket:124"),
        )
        ok, problems = validate_observation_against_grant(grant, observation)
        self.assertTrue(ok)
        self.assertEqual(problems, ())

    def test_out_of_scope_shadow_observation_fails_closed(self):
        grant = self._grant()
        observation = ShadowObservation(
            observation_ref="obs:2",
            role="unknown-shadow",
            source_ref="prod-db:secret",
            finding="out of scope",
            evidence_refs=("evidence:1",),
        )
        ok, problems = validate_observation_against_grant(grant, observation)
        self.assertFalse(ok)
        self.assertIn("role_not_allowed", problems)
        self.assertIn("source_not_allowed", problems)

    def test_discovery_can_produce_full_scope_price_and_delivery_proposal(self):
        opportunity = DiscoveryOpportunity(
            opportunity_ref="opp:1",
            title="Automate duplicate case entry",
            problem="staff re-enter the same case in two systems",
            proposed_outcome="single governed workflow updates both systems",
            evidence_refs=("obs:1",),
            estimated_annual_value=Decimal("73000"),
            confidence=Decimal("0.82"),
        )
        proposal = DiscoveryProposal(
            proposal_ref="proposal:1",
            customer_ref="customer:acme",
            opportunity_refs=(opportunity.opportunity_ref,),
            scope=("build integration", "migrate workflow", "deploy monitoring"),
            acceptance_criteria=("case completes end to end",),
            price=Decimal("18500"),
            currency="EUR",
            delivery_days=11,
            required_customer_actions=("approve API access",),
            evidence_refs=("obs:1",),
        )
        self.assertEqual(proposal.delivery_days, 11)
        self.assertEqual(proposal.price, Decimal("18500"))
        self.assertFalse(proposal.grants_authority)

    def test_write_capable_shadow_grant_is_rejected(self):
        now = datetime.now(timezone.utc)
        with self.assertRaisesRegex(ValueError, "read-only"):
            ShadowDiscoveryGrant(
                grant_ref="shadow:grant:bad",
                customer_ref="customer:acme",
                allowed_sources=("repo:app",),
                allowed_roles=("software-shadow",),
                starts_at=now,
                expires_at=now + timedelta(hours=1),
                read_only=False,
            )


if __name__ == "__main__":
    unittest.main()
