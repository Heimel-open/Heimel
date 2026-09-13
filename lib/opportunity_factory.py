from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Mapping, Protocol, Sequence


class RevenueLane(str, Enum):
    AI_EVALS = "ai_evals"
    UGC_ADS = "ugc_ads"
    CLIPPING = "clipping"
    AFFILIATE = "affiliate"
    LEAD_GEN = "lead_gen"
    LOCALIZATION = "localization"
    ECOMMERCE_CATALOG = "ecommerce_catalog"
    PAID_RESEARCH = "paid_research"
    ARTICLE_WRITING = "article_writing"
    PR_COMMS = "pr_comms"
    PUBLIC_AFFAIRS = "public_affairs"
    RFP_PROPOSALS = "rfp_proposals"
    GRANT_WRITING = "grant_writing"
    MARKET_INTELLIGENCE = "market_intelligence"
    DUE_DILIGENCE = "due_diligence"
    LEGAL_RESEARCH = "legal_research"
    CONTRACT_REVIEW = "contract_review"
    COMPLIANCE_GRC = "compliance_grc"
    BOOKKEEPING = "bookkeeping"
    TAX_RESEARCH_PREP = "tax_research_prep"
    RECRUITING_SOURCING = "recruiting_sourcing"
    PROCUREMENT_SOURCING = "procurement_sourcing"


@dataclass(frozen=True)
class RawOpportunity:
    source: str
    external_id: str
    title: str
    lane: RevenueLane
    payout: float
    currency: str = "USD"
    deadline: str | None = None
    requirements: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    automation_allowed: bool = False
    rights_clear: bool = True

    def __post_init__(self) -> None:
        if not self.source or not self.external_id or not self.title:
            raise ValueError("raw opportunity requires source, external_id and title")
        if self.payout < 0:
            raise ValueError("payout must be >= 0")


@dataclass(frozen=True)
class Opportunity:
    opportunity_id: str
    source: str
    external_id: str
    title: str
    lane: RevenueLane
    payout: float
    currency: str
    estimated_compute_cost: float
    estimated_human_cost: float
    estimated_other_cost: float
    acceptance_probability: float
    repeatability: float
    payment_reliability: float
    risk_penalty: float
    deadline: str | None = None
    requirements: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    automation_allowed: bool = False
    rights_clear: bool = True

    def __post_init__(self) -> None:
        if not self.opportunity_id:
            raise ValueError("opportunity_id is required")
        for name, value in (("payout", self.payout), ("estimated_compute_cost", self.estimated_compute_cost), ("estimated_human_cost", self.estimated_human_cost), ("estimated_other_cost", self.estimated_other_cost), ("risk_penalty", self.risk_penalty)):
            if value < 0:
                raise ValueError(f"{name} must be >= 0")
        for name, value in (("acceptance_probability", self.acceptance_probability), ("repeatability", self.repeatability), ("payment_reliability", self.payment_reliability)):
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")

    @property
    def total_cost(self) -> float:
        return self.estimated_compute_cost + self.estimated_human_cost + self.estimated_other_cost

    @property
    def expected_revenue(self) -> float:
        return self.payout * self.acceptance_probability * self.payment_reliability

    @property
    def expected_margin(self) -> float:
        return self.expected_revenue - self.total_cost - self.risk_penalty

    @property
    def return_score(self) -> float:
        denominator = self.total_cost + self.risk_penalty
        weighted_return = self.expected_revenue * max(self.repeatability, 0.05)
        return weighted_return if denominator == 0 else weighted_return / denominator


@dataclass(frozen=True)
class LaneProfile:
    lane: RevenueLane
    default_acceptance_probability: float
    default_repeatability: float
    default_payment_reliability: float
    default_compute_cost: float
    default_human_cost: float
    default_other_cost: float = 0.0
    default_risk_penalty: float = 0.0


DEFAULT_LANES: Mapping[RevenueLane, LaneProfile] = {
    RevenueLane.AI_EVALS: LaneProfile(RevenueLane.AI_EVALS, .70, .80, .90, 4, 12),
    RevenueLane.UGC_ADS: LaneProfile(RevenueLane.UGC_ADS, .45, .75, .85, 6, 5, 2),
    RevenueLane.CLIPPING: LaneProfile(RevenueLane.CLIPPING, .55, .90, .80, 3, 2, 1),
    RevenueLane.AFFILIATE: LaneProfile(RevenueLane.AFFILIATE, .25, .95, .75, 2, 1, 2),
    RevenueLane.LEAD_GEN: LaneProfile(RevenueLane.LEAD_GEN, .40, .85, .85, 5, 4, 3),
    RevenueLane.LOCALIZATION: LaneProfile(RevenueLane.LOCALIZATION, .70, .90, .90, 3, 3, 1),
    RevenueLane.ECOMMERCE_CATALOG: LaneProfile(RevenueLane.ECOMMERCE_CATALOG, .65, .95, .90, 3, 2, 1),
    RevenueLane.PAID_RESEARCH: LaneProfile(RevenueLane.PAID_RESEARCH, .55, .55, .90, 5, 20, 1),
    RevenueLane.ARTICLE_WRITING: LaneProfile(RevenueLane.ARTICLE_WRITING, .55, .85, .88, 3, 4, 1),
    RevenueLane.PR_COMMS: LaneProfile(RevenueLane.PR_COMMS, .45, .75, .88, 5, 8, 2, 2),
    RevenueLane.PUBLIC_AFFAIRS: LaneProfile(RevenueLane.PUBLIC_AFFAIRS, .35, .60, .90, 6, 18, 2, 8),
    RevenueLane.RFP_PROPOSALS: LaneProfile(RevenueLane.RFP_PROPOSALS, .45, .80, .90, 6, 10, 2, 3),
    RevenueLane.GRANT_WRITING: LaneProfile(RevenueLane.GRANT_WRITING, .35, .70, .85, 5, 10, 2, 4),
    RevenueLane.MARKET_INTELLIGENCE: LaneProfile(RevenueLane.MARKET_INTELLIGENCE, .60, .80, .90, 5, 7, 1, 1),
    RevenueLane.DUE_DILIGENCE: LaneProfile(RevenueLane.DUE_DILIGENCE, .55, .70, .92, 7, 12, 2, 5),
    RevenueLane.LEGAL_RESEARCH: LaneProfile(RevenueLane.LEGAL_RESEARCH, .55, .75, .92, 5, 12, 1, 6),
    RevenueLane.CONTRACT_REVIEW: LaneProfile(RevenueLane.CONTRACT_REVIEW, .55, .80, .92, 5, 12, 1, 7),
    RevenueLane.COMPLIANCE_GRC: LaneProfile(RevenueLane.COMPLIANCE_GRC, .55, .85, .92, 6, 12, 2, 6),
    RevenueLane.BOOKKEEPING: LaneProfile(RevenueLane.BOOKKEEPING, .70, .95, .95, 3, 5, 1, 3),
    RevenueLane.TAX_RESEARCH_PREP: LaneProfile(RevenueLane.TAX_RESEARCH_PREP, .55, .85, .92, 5, 12, 1, 8),
    RevenueLane.RECRUITING_SOURCING: LaneProfile(RevenueLane.RECRUITING_SOURCING, .45, .90, .85, 4, 5, 2, 2),
    RevenueLane.PROCUREMENT_SOURCING: LaneProfile(RevenueLane.PROCUREMENT_SOURCING, .55, .90, .90, 4, 6, 2, 2),
}


class OpportunitySource(Protocol):
    def discover(self) -> Iterable[RawOpportunity]: ...


class OpportunityNormalizer:
    def __init__(self, lane_profiles: Mapping[RevenueLane, LaneProfile] | None = None) -> None:
        self.lane_profiles = lane_profiles or DEFAULT_LANES

    def normalize(self, raw: RawOpportunity) -> Opportunity:
        profile = self.lane_profiles[raw.lane]
        risk_penalty = profile.default_risk_penalty
        if not raw.rights_clear:
            risk_penalty += max(raw.payout, 1.0)
        return Opportunity(f"{raw.source}:{raw.external_id}", raw.source, raw.external_id, raw.title, raw.lane, raw.payout, raw.currency, profile.default_compute_cost, profile.default_human_cost, profile.default_other_cost, profile.default_acceptance_probability, profile.default_repeatability, profile.default_payment_reliability, risk_penalty, raw.deadline, raw.requirements, raw.evidence_refs, raw.automation_allowed, raw.rights_clear)


class OpportunityScanner:
    """Read-only discovery and normalization. It never applies, publishes or spends."""
    def __init__(self, sources: Sequence[OpportunitySource], normalizer: OpportunityNormalizer | None = None) -> None:
        self.sources = tuple(sources); self.normalizer = normalizer or OpportunityNormalizer()
    def scan(self) -> tuple[Opportunity, ...]:
        found: dict[str, Opportunity] = {}
        for source in self.sources:
            for raw in source.discover():
                opportunity = self.normalizer.normalize(raw); current = found.get(opportunity.opportunity_id)
                if current is None or opportunity.return_score > current.return_score: found[opportunity.opportunity_id] = opportunity
        return tuple(sorted(found.values(), key=lambda item: (-item.return_score, item.opportunity_id)))


class AllocationDecision(str, Enum): TEST="test"; SCALE="scale"; HOLD="hold"; REJECT="reject"
@dataclass(frozen=True)
class Allocation: opportunity_id: str; lane: RevenueLane; decision: AllocationDecision; score: float; budget: float; reason: str
@dataclass(frozen=True)
class CapitalPlan:
    allocations: tuple[Allocation, ...]; unallocated_budget: float; direct_effect_path: bool=False; evidence_refs: tuple[str,...]=field(default_factory=tuple)
@dataclass(frozen=True)
class CapitalPolicy:
    min_margin: float=1; min_score_to_test: float=1; min_score_to_scale: float=3; max_share_per_opportunity: float=.40; exploration_share: float=.20
    def __post_init__(self):
        if self.min_score_to_scale <= self.min_score_to_test: raise ValueError("scale threshold must exceed test threshold")
        if not 0 < self.max_share_per_opportunity <= 1: raise ValueError("max_share_per_opportunity must be in (0, 1]")
        if not 0 <= self.exploration_share <= 1: raise ValueError("exploration_share must be between 0 and 1")
class CapitalAllocator:
    """Ranks expected economics and emits allocation intent only; never spends directly."""
    def __init__(self, policy: CapitalPolicy|None=None): self.policy=policy or CapitalPolicy()
    def classify(self, opportunity):
        if not opportunity.rights_clear: return AllocationDecision.REJECT, "rights are not clear"
        if opportunity.expected_margin < self.policy.min_margin: return AllocationDecision.REJECT, "expected margin below floor"
        if opportunity.return_score >= self.policy.min_score_to_scale: return AllocationDecision.SCALE, "return score above scale threshold"
        if opportunity.return_score >= self.policy.min_score_to_test: return AllocationDecision.TEST, "positive economics require market evidence"
        return AllocationDecision.HOLD, "economics below test threshold"
    def plan(self, opportunities, budget):
        if budget < 0: raise ValueError("budget must be >= 0")
        ranked=sorted(opportunities,key=lambda i:(-i.return_score,-i.expected_margin,i.opportunity_id)); decisions=[(i,*self.classify(i)) for i in ranked]; eligible=[x for x in decisions if x[1] in {AllocationDecision.SCALE,AllocationDecision.TEST}]
        if not eligible or budget==0: return CapitalPlan(tuple(Allocation(i.opportunity_id,i.lane,d,i.return_score,0,r) for i,d,r in decisions),budget,False)
        explore=budget*self.policy.exploration_share; exploit=budget-explore; scalable=[x for x in eligible if x[1] is AllocationDecision.SCALE]; testing=[x for x in eligible if x[1] is AllocationDecision.TEST]; assigned={}; cap=budget*self.policy.max_share_per_opportunity
        if scalable:
            total=sum(i.return_score for i,_,_ in scalable)
            for i,_,_ in scalable: assigned[i.opportunity_id]=min(cap,exploit*(i.return_score/total))
        else: explore=budget
        if testing:
            per=explore/len(testing)
            for i,_,_ in testing: assigned[i.opportunity_id]=min(cap,assigned.get(i.opportunity_id,0)+per)
        allocations=tuple(Allocation(i.opportunity_id,i.lane,d,i.return_score,assigned.get(i.opportunity_id,0),r) for i,d,r in decisions); used=sum(a.budget for a in allocations); evidence=tuple(ref for i in opportunities for ref in i.evidence_refs)
        return CapitalPlan(allocations,max(0,budget-used),False,evidence)
@dataclass(frozen=True)
class OpportunityFactoryRun: opportunities: tuple[Opportunity,...]; capital_plan: CapitalPlan
class OpportunityFactory:
    def __init__(self,scanner,allocator=None): self.scanner=scanner; self.allocator=allocator or CapitalAllocator()
    def run(self,budget):
        opportunities=self.scanner.scan(); return OpportunityFactoryRun(opportunities,self.allocator.plan(opportunities,budget))
