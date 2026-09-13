import unittest

from lib.opportunity_factory import OpportunityScanner, RevenueLane
from lib.opportunity_sources import (
    JsonFeedSource,
    SourceListing,
    ai_eval_source,
    clipping_source,
    lead_gen_source,
    ugc_source,
)


class OpportunitySourceTests(unittest.TestCase):
    def test_lane_helpers_bind_expected_lanes(self):
        fetcher = lambda: [SourceListing("1", "listing", 100, evidence_refs=("listing:1",))]
        sources = [ai_eval_source(fetcher), ugc_source(fetcher), clipping_source(fetcher), lead_gen_source(fetcher)]
        lanes = [source.discover()[0].lane for source in sources]
        self.assertEqual(lanes, [RevenueLane.AI_EVALS, RevenueLane.UGC_ADS, RevenueLane.CLIPPING, RevenueLane.LEAD_GEN])

    def test_json_feed_maps_provider_fields(self):
        source = JsonFeedSource(
            "market",
            RevenueLane.AI_EVALS,
            lambda: [{
                "job_id": "abc",
                "name": "Evaluate responses",
                "reward": 175,
                "currency": "USD",
                "requirements": ["expert review"],
                "evidence_refs": ["https://example.test/jobs/abc"],
            }],
            id_field="job_id",
            title_field="name",
            payout_field="reward",
        )
        item = source.discover()[0]
        self.assertEqual(item.external_id, "abc")
        self.assertEqual(item.title, "Evaluate responses")
        self.assertEqual(item.payout, 175)
        self.assertEqual(item.requirements, ("expert review",))

    def test_sources_are_read_only_and_do_not_create_effect_path(self):
        calls = []
        def fetcher():
            calls.append("read")
            return [SourceListing("lead-1", "Qualified lead bounty", 300, automation_allowed=True)]

        scanner = OpportunityScanner([lead_gen_source(fetcher, "lead-market")])
        found = scanner.scan()
        self.assertEqual(calls, ["read"])
        self.assertTrue(found[0].automation_allowed)
        self.assertFalse(hasattr(scanner.sources[0], "apply"))
        self.assertFalse(hasattr(scanner.sources[0], "publish"))
        self.assertFalse(hasattr(scanner.sources[0], "spend"))

    def test_unclear_rights_survive_adapter_for_fail_closed_allocator(self):
        source = ugc_source(lambda: [SourceListing("ugc-1", "Reuse creator asset", 500, rights_clear=False)])
        item = source.discover()[0]
        self.assertFalse(item.rights_clear)

    def test_source_output_flows_through_existing_scanner(self):
        source = ai_eval_source(
            lambda: [
                SourceListing("a", "Eval A", 100, evidence_refs=("a",)),
                SourceListing("b", "Eval B", 500, evidence_refs=("b",)),
            ],
            "eval-market",
        )
        found = OpportunityScanner([source]).scan()
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0].external_id, "b")


if __name__ == "__main__":
    unittest.main()
