"""Grant Speider

Aggregates grant and subsidy information from multiple sources.
Composes signals from Allemannsdata (Forskningsrådet, SkatteFUNN, EU) sources.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from ..speider_connectors import SpeiderScanner, ScanResult, Signal


@dataclass
class GrantOpportunity:
    """Grant or subsidy opportunity."""
    grant_id: str
    grant_type: str  # skattefunn, research_council, eu, innovation, etc.
    org_number: str
    company_name: str
    amount: float
    currency: str
    awarded_year: int
    program_name: str
    description: Optional[str] = None
    eligibility_criteria: Optional[List[str]] = None
    source: str = "Grant Speider"
    sources_consulted: List[str] = None


@dataclass
class GrantIntelligence:
    """Aggregated grant intelligence for company."""
    org_number: str
    company_name: str
    total_grants: int
    total_value: float
    grants_by_type: Dict[str, int]
    value_by_type: Dict[str, float]
    grants: List[GrantOpportunity]
    opportunities: List[GrantOpportunity]
    timeline: List[Dict[str, Any]]
    insights: List[str]
    next_actions: List[str]


class GrantSpeider:
    """Speider module for grant discovery and aggregation."""

    def __init__(self, scanner: SpeiderScanner):
        """Initialize Grant Speider.

        Args:
            scanner: SpeiderScanner instance with registered connectors
        """
        self.scanner = scanner
        self.grant_cache: Dict[str, GrantIntelligence] = {}

    def analyze_company_grants(self, org_number: str) -> GrantIntelligence:
        """Analyze grants for a company.

        Args:
            org_number: Organization number

        Returns:
            GrantIntelligence with aggregated grant data
        """
        # Check cache
        if org_number in self.grant_cache:
            return self.grant_cache[org_number]

        # Scan company across all sources
        scan_result = self.scanner.scan_company(org_number)

        # Extract grant signals from observation graph
        grant_signals = self.scanner.observation_graph.get_signals_by_type("grant_award")
        company_grants = [s for s in grant_signals if s.entity_id == org_number]

        # Parse grants
        grants = []
        grants_by_type = {}
        value_by_type = {}

        for signal in company_grants:
            grant_data = signal.value
            grant = GrantOpportunity(
                grant_id=signal.signal_id,
                grant_type=grant_data.get("grant_type", "unknown"),
                org_number=org_number,
                company_name=self._get_company_name(org_number),
                amount=grant_data.get("amount", 0),
                currency=grant_data.get("currency", "NOK"),
                awarded_year=grant_data.get("awarded_year", 0),
                program_name=grant_data.get("program_name", ""),
                source=signal.source,
                sources_consulted=[signal.source],
            )
            grants.append(grant)

            # Aggregate by type
            grant_type = grant.grant_type
            grants_by_type[grant_type] = grants_by_type.get(grant_type, 0) + 1
            value_by_type[grant_type] = value_by_type.get(grant_type, 0) + grant.amount

        # Identify opportunities
        opportunities = self._identify_opportunities(org_number, grants)

        # Generate timeline
        timeline = self._generate_timeline(grants)

        # Generate insights
        insights = self._generate_insights(org_number, grants)

        # Generate next actions
        next_actions = self._generate_next_actions(org_number, grants)

        intelligence = GrantIntelligence(
            org_number=org_number,
            company_name=self._get_company_name(org_number),
            total_grants=len(grants),
            total_value=float(sum(g.amount for g in grants)),
            grants_by_type=grants_by_type,
            value_by_type=value_by_type,
            grants=grants,
            opportunities=opportunities,
            timeline=timeline,
            insights=insights,
            next_actions=next_actions,
        )

        self.grant_cache[org_number] = intelligence
        return intelligence

    def _get_company_name(self, org_number: str) -> str:
        """Get company name from entity intelligence."""
        intelligence = self.scanner.get_entity_intelligence(org_number)

        # Try resolution status clusters first (most reliable)
        resolution = intelligence.get("resolution_status", {})
        clusters = resolution.get("clusters", [])
        if clusters:
            canonical_name = clusters[0].get("canonical_name")
            if canonical_name:
                return canonical_name

        # Fall back to extracting name from signals
        for signal in intelligence.get("signals", []):
            signal_value = signal.get("value", "")
            if isinstance(signal_value, dict) and "name" in signal_value:
                return signal_value.get("name", org_number)
            # Signal values are stringified in get_entity_intelligence
            if isinstance(signal_value, str) and "name" in signal_value:
                try:
                    import ast
                    parsed = ast.literal_eval(signal_value)
                    if isinstance(parsed, dict) and "name" in parsed:
                        return parsed.get("name", org_number)
                except (ValueError, SyntaxError):
                    pass
        return org_number

    def _identify_opportunities(self, org_number: str, grants: List[GrantOpportunity]) -> List[GrantOpportunity]:
        """Identify potential grant opportunities.

        Returns opportunities based on company profile and existing grants.
        """
        opportunities = []

        # Get company intelligence
        intelligence = self.scanner.get_entity_intelligence(org_number)

        # Opportunity 1: If company has SkatteFUNN grants, suggest research council grants
        skattefunn_count = sum(1 for g in grants if g.grant_type == "SkatteFUNN")
        if skattefunn_count > 0:
            opportunities.append(GrantOpportunity(
                grant_id="OPP-RESEARCH-COUNCIL",
                grant_type="research_council",
                org_number=org_number,
                company_name=self._get_company_name(org_number),
                amount=2000000,
                currency="NOK",
                awarded_year=2025,
                program_name="Forsker-prosjekt",
                description="Research project grants from Research Council of Norway",
                eligibility_criteria=["R&D activities", "Norwegian company", "Project timeline 2-4 years"],
                sources_consulted=["Grant Speider Analysis"],
            ))

        # Opportunity 2: EU funding (if company has EU-related signals)
        eu_signals = [s for s in intelligence.get("signals", []) if "EU" in str(s.get("signal_type", ""))]
        if eu_signals or len(grants) > 2:
            opportunities.append(GrantOpportunity(
                grant_id="OPP-HORIZON-EUROPE",
                grant_type="eu",
                org_number=org_number,
                company_name=self._get_company_name(org_number),
                amount=5000000,
                currency="EUR",
                awarded_year=2025,
                program_name="Horizon Europe",
                description="EU framework programme for research and innovation",
                eligibility_criteria=["EU consortium participation", "Eligible research activities", "International collaboration"],
                sources_consulted=["Grant Speider Analysis"],
            ))

        # Opportunity 3: Innovation grants (if company is growing)
        if len(grants) > 0:
            opportunities.append(GrantOpportunity(
                grant_id="OPP-INNOVATION-NORWAY",
                grant_type="innovation",
                org_number=org_number,
                company_name=self._get_company_name(org_number),
                amount=1500000,
                currency="NOK",
                awarded_year=2025,
                program_name="Innovation Norway Grants",
                description="Innovation development and commercialization grants",
                eligibility_criteria=["Business innovation", "Market potential", "Growth plan"],
                sources_consulted=["Grant Speider Analysis"],
            ))

        return opportunities

    def _generate_timeline(self, grants: List[GrantOpportunity]) -> List[Dict[str, Any]]:
        """Generate grant timeline."""
        timeline = []

        # Group by year
        by_year = {}
        for grant in grants:
            year = grant.awarded_year
            if year not in by_year:
                by_year[year] = {"grants": 0, "value": 0}
            by_year[year]["grants"] += 1
            by_year[year]["value"] += grant.amount

        # Convert to timeline
        for year in sorted(by_year.keys()):
            timeline.append({
                "year": year,
                "grant_count": by_year[year]["grants"],
                "total_value": by_year[year]["value"],
                "average_grant": by_year[year]["value"] / by_year[year]["grants"],
            })

        return timeline

    def _generate_insights(self, org_number: str, grants: List[GrantOpportunity]) -> List[str]:
        """Generate insights from grant data."""
        insights = []

        if not grants:
            insights.append("No grants found in current dataset.")
            return insights

        total_value = sum(g.amount for g in grants)
        grant_types = set(g.grant_type for g in grants)

        insights.append(f"Company has received {len(grants)} grants totaling {total_value:,.0f} NOK.")

        if "SkatteFUNN" in grant_types:
            skattefunn_grants = [g for g in grants if g.grant_type == "SkatteFUNN"]
            insights.append(f"Strong R&D profile: {len(skattefunn_grants)} SkatteFUNN grants indicate active innovation.")

        if "EU" in grant_types:
            insights.append("International research engagement: EU grants show participation in European research networks.")

        if len(grant_types) > 1:
            insights.append(f"Diversified funding: Grants from {len(grant_types)} different programs reduce funding concentration risk.")

        # Trend analysis
        if len(grants) >= 2:
            recent_grants = [g for g in grants if g.awarded_year >= max(g.awarded_year for g in grants) - 2]
            if len(recent_grants) > len(grants) / 2:
                insights.append("Upward trend: More than half of grants awarded in last 2 years.")

        return insights

    def _generate_next_actions(self, org_number: str, grants: List[GrantOpportunity]) -> List[str]:
        """Generate recommended next actions."""
        actions = []

        grant_types = set(g.grant_type for g in grants)

        if "SkatteFUNN" in grant_types:
            actions.append("Apply for Research Council of Norway grants - company has proven R&D track record")

        if len(grants) > 0:
            actions.append("Explore EU Horizon Europe program - larger international grants available")
            actions.append("Consider innovation.no grants for commercialization support")

        if len(grants) < 2:
            actions.append("Begin grant application process - company may be under-utilizing available programs")

        actions.append("Set up grant compliance tracking - ensure all grant conditions met")
        actions.append("Document research activities for future grant applications")

        return actions

    def get_grant_summary(self, org_number: str) -> Dict[str, Any]:
        """Get summary of company grants."""
        intelligence = self.analyze_company_grants(org_number)

        return {
            "org_number": org_number,
            "company_name": intelligence.company_name,
            "total_grants": intelligence.total_grants,
            "total_value": intelligence.total_value,
            "grants_by_type": intelligence.grants_by_type,
            "value_by_type": intelligence.value_by_type,
            "timeline": intelligence.timeline,
            "insights": intelligence.insights,
            "next_actions": intelligence.next_actions,
            "opportunities_count": len(intelligence.opportunities),
        }

    def compare_companies(self, org_numbers: List[str]) -> Dict[str, Any]:
        """Compare grant profiles across multiple companies."""
        summaries = [self.get_grant_summary(org) for org in org_numbers]

        return {
            "companies": len(org_numbers),
            "total_grants": sum(s["total_grants"] for s in summaries),
            "total_value": sum(s["total_value"] for s in summaries),
            "average_grants_per_company": sum(s["total_grants"] for s in summaries) / len(org_numbers) if org_numbers else 0,
            "average_value_per_company": sum(s["total_value"] for s in summaries) / len(org_numbers) if org_numbers else 0,
            "company_summaries": summaries,
        }
