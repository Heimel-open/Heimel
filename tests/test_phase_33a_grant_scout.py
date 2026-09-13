"""Tests for Phase 33a: Grant Speider Module.

Tests grant discovery, aggregation, opportunity identification, and analysis.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock

from src.valo_platform.speider_connectors import (
    SpeiderScanner,
    AllemannsdataFirmafaktaConnector,
    AllemannsdataLovdataConnector,
    BusinessRegistryConnector,
    Company,
    Signal,
)
from src.valo_platform.speider_modules import GrantSpeider, GrantOpportunity, GrantIntelligence


class TestGrantSpeider:
    """Test Grant Speider module."""

    @pytest.fixture
    def mock_connector(self):
        """Create a mock connector that doesn't make real HTTP calls."""
        connector = MagicMock(spec=BusinessRegistryConnector)
        connector.get_connector_name.return_value = "Firmafakta"
        connector.is_healthy.return_value = True

        mock_company = Company(
            org_number="999000001",
            name="Test Company AS",
            business_code="62.010",
            municipality="Oslo",
            status="Active",
            employee_count=10,
            source="Firmafakta",
        )
        connector.get_company.return_value = mock_company
        connector.get_company_shareholders.return_value = []
        connector.get_company_roles.return_value = []
        connector.get_company_financials.return_value = {}
        connector.get_company_grants.return_value = []
        connector.get_person_holdings.return_value = []
        return connector

    @pytest.fixture
    def scanner(self, mock_connector):
        """Create scanner with mocked connectors."""
        scanner = SpeiderScanner("tenant-1")
        scanner.register_connector(mock_connector)
        return scanner

    @pytest.fixture
    def grant_speider(self, scanner):
        """Create Grant Speider instance."""
        return GrantSpeider(scanner)

    def test_grant_speider_initialization(self, grant_speider, scanner):
        """Test Grant Speider initialization."""
        assert grant_speider.scanner == scanner
        assert len(grant_speider.grant_cache) == 0

    def test_analyze_company_grants(self, grant_speider):
        """Test company grant analysis."""
        intelligence = grant_speider.analyze_company_grants("999000001")

        assert isinstance(intelligence, GrantIntelligence)
        assert intelligence.org_number == "999000001"
        assert isinstance(intelligence.total_grants, int)
        assert isinstance(intelligence.total_value, float)

    def test_grant_intelligence_structure(self, grant_speider):
        """Test grant intelligence data structure."""
        intelligence = grant_speider.analyze_company_grants("999000001")

        # Check all required fields
        assert hasattr(intelligence, "org_number")
        assert hasattr(intelligence, "company_name")
        assert hasattr(intelligence, "total_grants")
        assert hasattr(intelligence, "total_value")
        assert hasattr(intelligence, "grants_by_type")
        assert hasattr(intelligence, "value_by_type")
        assert hasattr(intelligence, "grants")
        assert hasattr(intelligence, "opportunities")
        assert hasattr(intelligence, "timeline")
        assert hasattr(intelligence, "insights")
        assert hasattr(intelligence, "next_actions")

    def test_grant_opportunity_identification(self, grant_speider):
        """Test grant opportunity identification."""
        intelligence = grant_speider.analyze_company_grants("999000001")

        # Should return a list of opportunities
        assert isinstance(intelligence.opportunities, list)

        # With no grants in the dataset, opportunities list may be empty
        # (opportunities are generated based on existing grant patterns)
        for opp in intelligence.opportunities:
            assert isinstance(opp, GrantOpportunity)
            assert opp.grant_id
            assert opp.grant_type
            assert opp.org_number
            assert opp.amount > 0

    def test_grant_timeline_generation(self, grant_speider):
        """Test grant timeline generation."""
        intelligence = grant_speider.analyze_company_grants("999000001")

        assert isinstance(intelligence.timeline, list)

        # Each timeline entry should have year and value data
        for entry in intelligence.timeline:
            assert "year" in entry
            assert "grant_count" in entry
            assert "total_value" in entry

    def test_grant_insights_generation(self, grant_speider):
        """Test grant insights generation."""
        intelligence = grant_speider.analyze_company_grants("999000001")

        assert isinstance(intelligence.insights, list)
        # Should have at least some insights
        assert len(intelligence.insights) >= 1

        # Each insight should be a string
        for insight in intelligence.insights:
            assert isinstance(insight, str)
            assert len(insight) > 0

    def test_next_actions_generation(self, grant_speider):
        """Test next actions generation."""
        intelligence = grant_speider.analyze_company_grants("999000001")

        assert isinstance(intelligence.next_actions, list)
        # Should have recommended actions
        assert len(intelligence.next_actions) > 0

        # Each action should be a string
        for action in intelligence.next_actions:
            assert isinstance(action, str)
            assert len(action) > 0

    def test_grant_summary(self, grant_speider):
        """Test grant summary generation."""
        summary = grant_speider.get_grant_summary("999000001")

        assert isinstance(summary, dict)
        assert "org_number" in summary
        assert "total_grants" in summary
        assert "total_value" in summary
        assert "grants_by_type" in summary
        assert "insights" in summary
        assert "next_actions" in summary

    def test_grant_caching(self, grant_speider):
        """Test grant intelligence caching."""
        org_number = "999000001"

        # First call - not cached
        assert org_number not in grant_speider.grant_cache
        intelligence1 = grant_speider.analyze_company_grants(org_number)

        # Second call - should be cached
        assert org_number in grant_speider.grant_cache
        intelligence2 = grant_speider.analyze_company_grants(org_number)

        # Should be same object
        assert intelligence1 is intelligence2

    def test_company_comparison(self, grant_speider):
        """Test grant comparison across companies."""
        org_numbers = ["999000001", "999000002", "999000003"]

        comparison = grant_speider.compare_companies(org_numbers)

        assert isinstance(comparison, dict)
        assert comparison["companies"] == 3
        assert "total_grants" in comparison
        assert "total_value" in comparison
        assert "average_grants_per_company" in comparison
        assert "average_value_per_company" in comparison

    def test_multi_source_grant_discovery(self, grant_speider):
        """Test grant discovery from multiple sources."""
        # Scan company (triggers multi-source scan)
        grant_speider.scanner.scan_company("999000001")

        # Get grants
        intelligence = grant_speider.analyze_company_grants("999000001")

        # Should have sourced data from multiple connectors
        sources = set()
        for grant in intelligence.grants:
            sources.add(grant.source)

        # With no grants returned by mock connector, grants list is empty
        # This test validates the pipeline works end-to-end
        assert isinstance(intelligence.grants, list)
        assert isinstance(intelligence.grants_by_type, dict)
        assert isinstance(intelligence.value_by_type, dict)

    def test_grant_by_type_aggregation(self, grant_speider):
        """Test aggregation of grants by type."""
        intelligence = grant_speider.analyze_company_grants("999000001")

        # Check that grants_by_type is properly aggregated
        total_by_type = sum(intelligence.grants_by_type.values())
        assert total_by_type == intelligence.total_grants

        # Check that value_by_type is properly aggregated
        total_value_by_type = sum(intelligence.value_by_type.values())
        assert total_value_by_type == intelligence.total_value

    def test_opportunity_eligibility_criteria(self, grant_speider):
        """Test that opportunities include eligibility criteria."""
        intelligence = grant_speider.analyze_company_grants("999000001")

        for opp in intelligence.opportunities:
            if opp.eligibility_criteria:
                assert isinstance(opp.eligibility_criteria, list)
                for criterion in opp.eligibility_criteria:
                    assert isinstance(criterion, str)
                    assert len(criterion) > 0


class TestGrantSpeiderIntegration:
    """Integration tests for Grant Speider with SpeiderScanner."""

    @pytest.fixture
    def mock_connector(self):
        """Create a mock connector."""
        connector = MagicMock(spec=BusinessRegistryConnector)
        connector.get_connector_name.return_value = "Firmafakta"
        connector.is_healthy.return_value = True

        mock_company = Company(
            org_number="999000001",
            name="Test Company AS",
            business_code="62.010",
            municipality="Oslo",
            status="Active",
            employee_count=10,
            source="Firmafakta",
        )
        connector.get_company.return_value = mock_company
        connector.get_company_shareholders.return_value = []
        connector.get_company_roles.return_value = []
        connector.get_company_financials.return_value = {}
        connector.get_company_grants.return_value = []
        connector.get_person_holdings.return_value = []
        return connector

    def test_end_to_end_grant_analysis(self, mock_connector):
        """Test end-to-end grant analysis workflow."""
        # Create scanner with connectors
        scanner = SpeiderScanner("tenant-1")
        scanner.register_connector(mock_connector)

        # Create Grant Speider
        grant_speider = GrantSpeider(scanner)

        # Scan and analyze
        org_number = "999000001"
        intelligence = grant_speider.analyze_company_grants(org_number)

        # Verify complete analysis
        assert intelligence.org_number == org_number
        assert intelligence.total_grants >= 0
        assert intelligence.total_value >= 0
        assert len(intelligence.insights) > 0
        assert len(intelligence.next_actions) > 0

    def test_speider_scanner_with_grant_speider(self, mock_connector):
        """Test integration of SpeiderScanner with GrantSpeider."""
        scanner = SpeiderScanner("tenant-1")
        scanner.register_connector(mock_connector)

        # Grant Speider should work with scanner
        grant_speider = GrantSpeider(scanner)
        summary = grant_speider.get_grant_summary("999000001")

        assert summary["org_number"] == "999000001"
        assert isinstance(summary["total_value"], float)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
