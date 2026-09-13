import unittest

from lib.opportunity_factory import OpportunityScanner, RevenueLane
from lib.public_opportunity_sources import (
    MERCOR_EXPERTS,
    WHOP_CONTENT_REWARDS,
    MercorExpertsSource,
    PublicPageContract,
    WhopContentRewardsSource,
    public_sources,
)


MERCOR_HTML = """
<html><body>
Generalist $80-$160/hr 68 hired recently Apply
Law Experts $110-$150/hr 109 hired recently Apply
Frontend Engineer $90/hr 156 hired recently Apply
</body></html>
"""

WHOP_HTML = """
<html><body>
Perplexity JRE Clipping Budget: $20,000 CPM: $1.50 per 1,000 views Platforms: YouTube, TikTok, Instagram
OBN JAY Clipping Campaign Budget: $1,000 CPM: $1 per 1,000 views Platforms: TikTok
</body></html>
"""


class PublicOpportunitySourceTests(unittest.TestCase):
    def test_mercor_public_page_maps_rates_to_eval_opportunities(self):
        source = MercorExpertsSource(lambda url: MERCOR_HTML)
        found = source.discover()
        self.assertEqual(len(found), 3)
        self.assertTrue(all(item.lane is RevenueLane.AI_EVALS for item in found))
        generalist = next(item for item in found if item.title.lower() == "generalist")
        self.assertEqual(generalist.payout, 120.0)
        self.assertFalse(generalist.automation_allowed)
        self.assertEqual(generalist.evidence_refs, (MERCOR_EXPERTS.url,))

    def test_whop_public_page_maps_campaign_budget_and_cpm(self):
        source = WhopContentRewardsSource(lambda url: WHOP_HTML)
        found = source.discover()
        self.assertEqual(len(found), 2)
        self.assertTrue(all(item.lane is RevenueLane.CLIPPING for item in found))
        perplexity = next(item for item in found if "Perplexity" in item.title)
        self.assertEqual(perplexity.payout, 20000.0)
        self.assertTrue(any("$1.5" in requirement for requirement in perplexity.requirements))
        self.assertFalse(perplexity.automation_allowed)
        self.assertEqual(perplexity.evidence_refs, (WHOP_CONTENT_REWARDS.url,))

    def test_public_source_bundle_flows_through_factory_scanner(self):
        pages = {
            MERCOR_EXPERTS.url: MERCOR_HTML,
            WHOP_CONTENT_REWARDS.url: WHOP_HTML,
        }
        sources = public_sources(lambda url: pages[url])
        found = OpportunityScanner(sources).scan()
        self.assertEqual(len(found), 5)
        self.assertEqual({item.lane for item in found}, {RevenueLane.AI_EVALS, RevenueLane.CLIPPING})

    def test_contract_is_https_and_read_only(self):
        with self.assertRaisesRegex(ValueError, "https"):
            PublicPageContract("bad", "http://example.test", RevenueLane.AI_EVALS)
        with self.assertRaisesRegex(ValueError, "read_only"):
            PublicPageContract("bad", "https://example.test", RevenueLane.AI_EVALS, mode="write")

    def test_adapters_expose_no_consequence_methods(self):
        for source in (MercorExpertsSource(lambda _: MERCOR_HTML), WhopContentRewardsSource(lambda _: WHOP_HTML)):
            for method in ("apply", "publish", "message", "purchase", "spend"):
                self.assertFalse(hasattr(source, method))


if __name__ == "__main__":
    unittest.main()
