import unittest

from lib.opportunity_factory import AllocationDecision, CapitalAllocator, CapitalPolicy, DEFAULT_LANES, OpportunityFactory, OpportunityNormalizer, OpportunityScanner, RawOpportunity, RevenueLane

class StaticSource:
    def __init__(self, items): self.items=tuple(items)
    def discover(self): return self.items

class OpportunityFactoryTests(unittest.TestCase):
    def test_scanner_normalizes_and_ranks_all_lanes(self):
        raw=[RawOpportunity("market",lane.value,lane.value,lane,500,evidence_refs=(f"src:{lane.value}",)) for lane in RevenueLane]
        found=OpportunityScanner([StaticSource(raw)]).scan()
        self.assertEqual(len(found),len(RevenueLane)); self.assertEqual({i.lane for i in found},set(RevenueLane))
    def test_every_lane_has_economics_profile(self): self.assertEqual(set(DEFAULT_LANES),set(RevenueLane))
    def test_professional_services_lanes_are_explicit(self):
        expected={RevenueLane.ARTICLE_WRITING,RevenueLane.PR_COMMS,RevenueLane.PUBLIC_AFFAIRS,RevenueLane.RFP_PROPOSALS,RevenueLane.GRANT_WRITING,RevenueLane.MARKET_INTELLIGENCE,RevenueLane.DUE_DILIGENCE,RevenueLane.LEGAL_RESEARCH,RevenueLane.CONTRACT_REVIEW,RevenueLane.COMPLIANCE_GRC,RevenueLane.BOOKKEEPING,RevenueLane.TAX_RESEARCH_PREP,RevenueLane.RECRUITING_SOURCING,RevenueLane.PROCUREMENT_SOURCING}
        self.assertTrue(expected.issubset(set(RevenueLane)))
    def test_duplicate_source_identity_is_collapsed(self):
        d=RawOpportunity("market","42","Same",RevenueLane.LEAD_GEN,300); self.assertEqual(len(OpportunityScanner([StaticSource([d]),StaticSource([d])]).scan()),1)
    def test_unclear_rights_are_rejected(self):
        o=OpportunityNormalizer().normalize(RawOpportunity("market","rights","Unclear",RevenueLane.UGC_ADS,500,rights_clear=False)); d,r=CapitalAllocator().classify(o); self.assertIs(d,AllocationDecision.REJECT); self.assertIn("rights",r)
    def test_high_return_scales_low_return_does_not(self):
        n=OpportunityNormalizer(); winner=n.normalize(RawOpportunity("market","winner","Lead",RevenueLane.LEAD_GEN,1000)); weak=n.normalize(RawOpportunity("market","weak","Tiny",RevenueLane.CLIPPING,5)); a=CapitalAllocator(CapitalPolicy(min_margin=1,min_score_to_test=1,min_score_to_scale=3)); self.assertIs(a.classify(winner)[0],AllocationDecision.SCALE); self.assertIn(a.classify(weak)[0],{AllocationDecision.HOLD,AllocationDecision.REJECT})
    def test_allocator_never_creates_direct_effect_path(self):
        o=OpportunityNormalizer().normalize(RawOpportunity("market","winner","Lead",RevenueLane.LEAD_GEN,1000,automation_allowed=True)); p=CapitalAllocator().plan([o],100); self.assertFalse(p.direct_effect_path); self.assertLessEqual(p.allocations[0].budget,40)
    def test_market_evidence_is_carried_into_plan(self):
        o=OpportunityNormalizer().normalize(RawOpportunity("market","eval","Eval",RevenueLane.AI_EVALS,500,evidence_refs=("listing:123",))); self.assertIn("listing:123",CapitalAllocator().plan([o],50).evidence_refs)
    def test_factory_run_is_deterministic(self):
        f=OpportunityFactory(OpportunityScanner([StaticSource([RawOpportunity("market","a","A",RevenueLane.LEAD_GEN,500)])])); self.assertEqual(f.run(100),f.run(100))
    def test_invalid_probabilities_fail_closed(self):
        from lib.opportunity_factory import Opportunity
        with self.assertRaisesRegex(ValueError,"acceptance_probability"):
            Opportunity("x","s","e","t",RevenueLane.AI_EVALS,10,"USD",1,1,0,1.1,.5,.5,0)

if __name__ == "__main__": unittest.main()
