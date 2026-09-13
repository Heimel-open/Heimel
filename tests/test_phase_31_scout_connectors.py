"""Tests for Phase 31: Speider Data Connector Integration with Allemannsdata MCP.

Tests the abstraction layer and Firmafakta connector implementation.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, PropertyMock

from src.valo_platform.speider_connectors import (
    BusinessRegistryConnector,
    AllemannsdataFirmafaktaConnector,
    Company,
    Person,
    Shareholder,
    Role,
)
from src.valo_platform.speider_connectors.models import RoleType


class TestBusinessRegistryAbstraction:
    """Test business registry connector abstraction."""

    def test_connector_interface_defined(self):
        """Test that BusinessRegistryConnector is an abstract interface."""
        assert hasattr(BusinessRegistryConnector, 'get_company')
        assert hasattr(BusinessRegistryConnector, 'find_company_by_name')
        assert hasattr(BusinessRegistryConnector, 'get_company_shareholders')
        assert hasattr(BusinessRegistryConnector, 'get_company_roles')

    def test_connector_has_required_methods(self):
        """Test all required methods are defined."""
        required_methods = [
            'get_company',
            'find_company_by_name',
            'get_company_shareholders',
            'get_company_roles',
            'get_person_holdings',
            'get_company_financials',
            'get_company_grants',
            'search_companies',
            'get_connector_name',
            'is_healthy',
            'get_last_updated',
        ]
        for method in required_methods:
            assert hasattr(BusinessRegistryConnector, method)


class TestAllemannsdataFirmafaktaConnector:
    """Test Allemannsdata Firmafakta connector implementation."""

    @pytest.fixture
    def mock_http_client(self):
        """Create a mock HTTP client."""
        with patch(
            "src.valo_platform.speider_connectors.allemannsdata_firmafakta.AllemannsdataHTTPClient"
        ) as mock:
            instance = mock.return_value
            instance.base_url = "https://allemannsdata.com/mcp"
            instance.get_company.return_value = {
                "name": "Test Company AS",
                "short_name": "Test Co",
                "business_code": "62020",
                "business_description": "Software development",
                "municipality": "Oslo",
                "county": "Oslo",
                "founded_year": 2010,
                "employee_count": 50,
                "status": "active",
                "metadata": {},
            }
            instance.find_companies_by_name.return_value = [
                {
                    "org_number": "999000001",
                    "name": "Acme Corp",
                    "business_code": "62020",
                    "metadata": {},
                }
            ]
            instance.get_company_shareholders.return_value = [
                {
                    "shareholder_id": "sh-1",
                    "shareholder_name": "John Doe",
                    "shareholder_type": "person",
                    "ownership_percentage": 50.0,
                    "share_count": 1000,
                }
            ]
            instance.get_company_roles.return_value = [
                {
                    "role_id": "role-1",
                    "person_name": "Jane Smith",
                    "person_id": "person-456",
                    "role_type": "ceo",
                    "start_date": "2020-01-01",
                },
                {
                    "role_id": "role-2",
                    "person_name": "Bob Johnson",
                    "person_id": "person-789",
                    "role_type": "board_member",
                    "start_date": "2019-06-15",
                },
            ]
            instance.get_company_financials.return_value = {
                "revenue": 15000000.0,
                "equity": 5000000.0,
                "assets": 8000000.0,
                "fiscal_year": 2024,
            }
            instance.call_tool.return_value = {
                "grants": [
                    {
                        "grant_id": "grant-1",
                        "grant_type": "SkatteFUNN",
                        "amount": 500000.0,
                        "awarded_year": 2024,
                    }
                ]
            }
            instance.get_person_holdings.return_value = [
                {
                    "org_number": "999000001",
                    "company_name": "Test Company AS",
                    "ownership_percentage": 50.0,
                }
            ]
            instance.list_tools.return_value = [
                {"name": name, "description": name}
                for name in (
                    "organisasjonsnummer_for_selskap",
                    "selskapsdetaljer",
                    "aksjeeiere_for_selskap",
                    "roller_i_enhet",
                    "finn_selskaper",
                    "get_company_last_financial_statement",
                )
            ]
            yield instance

    def test_connector_initialization(self, mock_http_client):
        """Test connector initializes with correct name."""
        connector = AllemannsdataFirmafaktaConnector()
        assert connector.connector_name == "Firmafakta"
        assert connector.get_connector_name() == "Firmafakta"

    def test_get_company(self, mock_http_client):
        """Test retrieving company details."""
        connector = AllemannsdataFirmafaktaConnector()
        company = connector.get_company("999000001")

        assert company is not None
        assert company.org_number == "999000001"
        assert company.source == "Firmafakta"
        assert company.status == "active"
        assert company.name == "Test Company AS"
        mock_http_client.get_company.assert_called_once_with("999000001")

    def test_find_company_by_name(self, mock_http_client):
        """Test searching for companies by name."""
        connector = AllemannsdataFirmafaktaConnector()
        companies = connector.find_company_by_name("Acme Corp")

        assert len(companies) > 0
        assert companies[0].name == "Acme Corp"
        assert companies[0].source == "Firmafakta"
        mock_http_client.find_companies_by_name.assert_called_once_with("Acme Corp")

    def test_get_company_shareholders(self, mock_http_client):
        """Test retrieving shareholders."""
        connector = AllemannsdataFirmafaktaConnector()
        shareholders = connector.get_company_shareholders("999000001")

        assert len(shareholders) > 0
        assert shareholders[0].org_number == "999000001"
        assert shareholders[0].shareholder_type in ["person", "company"]
        mock_http_client.get_company_shareholders.assert_called_once_with("999000001")

    def test_get_company_roles(self, mock_http_client):
        """Test retrieving board members and roles."""
        connector = AllemannsdataFirmafaktaConnector()
        roles = connector.get_company_roles("999000001")

        assert len(roles) > 0
        role_types = [r.role_type for r in roles]
        assert RoleType.CEO in role_types
        assert RoleType.BOARD_MEMBER in role_types
        mock_http_client.get_company_roles.assert_called_once_with("999000001")

    def test_get_person_holdings(self, mock_http_client):
        """Test retrieving stock holdings for a person."""
        mock_http_client.get_company_shareholders.return_value = [
            {
                "org_number": "999000001",
                "shareholder_name": "Test Company AS",
                "ownership_percentage": 50.0,
            }
        ]
        connector = AllemannsdataFirmafaktaConnector()
        holdings = connector.get_person_holdings("person-123")

        assert isinstance(holdings, list)
        assert len(holdings) > 0
        assert "org_number" in holdings[0]
        assert "ownership_percentage" in holdings[0]

    def test_get_company_financials(self, mock_http_client):
        """Test retrieving financial statements."""
        connector = AllemannsdataFirmafaktaConnector()
        financials = connector.get_company_financials("999000001")

        assert "revenue" in financials
        assert "equity" in financials
        assert "assets" in financials
        assert financials["fiscal_year"] == 2024
        mock_http_client.get_company_financials.assert_called_once_with("999000001")

    def test_get_company_grants(self, mock_http_client):
        """Test retrieving grants and subsidies."""
        connector = AllemannsdataFirmafaktaConnector()
        grants = connector.get_company_grants("999000001")

        assert len(grants) > 0
        assert "grant_type" in grants[0]
        assert "amount" in grants[0]

    def test_search_companies(self, mock_http_client):
        """Test searching companies by criteria."""
        connector = AllemannsdataFirmafaktaConnector()
        companies = connector.search_companies(
            location="Oslo",
            business_code="62020",
            min_employees=10,
        )

        assert isinstance(companies, list)

    def test_connector_health(self, mock_http_client):
        """Test connector health check."""
        connector = AllemannsdataFirmafaktaConnector()
        assert connector.is_healthy()

    def test_connector_name(self, mock_http_client):
        """Test getting connector name."""
        connector = AllemannsdataFirmafaktaConnector()
        assert connector.get_connector_name() == "Firmafakta"

    def test_last_updated(self, mock_http_client):
        """Test getting last update timestamp."""
        connector = AllemannsdataFirmafaktaConnector()
        last_updated = connector.get_last_updated()
        assert last_updated is not None
        assert isinstance(last_updated, datetime)


class TestSpeiderDataModels:
    """Test data models for Speider connectors."""

    def test_company_model(self):
        """Test Company data model."""
        company = Company(
            org_number="999000001",
            name="Test Company",
            business_code="62020",
            municipality="Oslo",
            source="Firmafakta",
        )

        assert company.org_number == "999000001"
        assert company.name == "Test Company"
        assert company.status == "active"

    def test_shareholder_model(self):
        """Test Shareholder data model."""
        shareholder = Shareholder(
            shareholder_id="sh-1",
            shareholder_name="John Doe",
            shareholder_type="person",
            ownership_percentage=25.5,
            org_number="999000001",
            source="Firmafakta",
        )

        assert shareholder.ownership_percentage == 25.5
        assert shareholder.shareholder_type == "person"

    def test_role_model(self):
        """Test Role data model."""
        role = Role(
            role_id="role-1",
            person_name="Jane Smith",
            role_type=RoleType.CEO,
            org_number="999000001",
            source="Firmafakta",
        )

        assert role.role_type == RoleType.CEO
        assert role.person_name == "Jane Smith"

    def test_financial_statement_model(self):
        """Test FinancialStatement data model."""
        from src.valo_platform.speider_connectors.models import FinancialStatement

        statement = FinancialStatement(
            org_number="999000001",
            fiscal_year=2024,
            revenue=15000000.0,
            equity=5000000.0,
            equity_ratio=0.25,
            source="Firmafakta",
            last_updated=datetime.now(timezone.utc).replace(tzinfo=None),
        )

        assert statement.equity_ratio == 0.25
        assert statement.fiscal_year == 2024

    def test_grant_model(self):
        """Test Grant data model."""
        from src.valo_platform.speider_connectors.models import Grant

        grant = Grant(
            grant_id="grant-1",
            org_number="999000001",
            grant_type="SkatteFUNN",
            amount=500000.0,
            awarded_year=2024,
            source="Firmafakta",
        )

        assert grant.grant_type == "SkatteFUNN"
        assert grant.amount == 500000.0


class TestConnectorSwappability:
    """Test that connectors can be swapped via interface."""

    def test_connector_implements_interface(self):
        """Test Firmafakta connector implements BusinessRegistryConnector."""
        connector = AllemannsdataFirmafaktaConnector()
        assert isinstance(connector, BusinessRegistryConnector)

    def test_multiple_connector_types(self):
        """Test that different connector types can be used interchangeably."""
        # Create mock alternative connector (for demonstration)
        class MockConnector(BusinessRegistryConnector):
            def get_company(self, org_number):
                return Company(org_number=org_number, name="Mock", source="Mock")

            def find_company_by_name(self, name):
                return [Company(org_number="999", name=name, source="Mock")]

            def get_company_shareholders(self, org_number):
                return []

            def get_company_roles(self, org_number):
                return []

            def get_person_holdings(self, person_id):
                return []

            def get_company_financials(self, org_number):
                return {}

            def get_company_grants(self, org_number):
                return []

            def search_companies(self, location=None, business_code=None, min_employees=None, max_employees=None):
                return []

            def get_connector_name(self):
                return "Mock"

            def is_healthy(self):
                return True

            def get_last_updated(self):
                return datetime.now(timezone.utc).replace(tzinfo=None)

        # Test that MockConnector works through the interface
        connector = MockConnector()
        assert connector.is_healthy()
        assert connector.get_connector_name() == "Mock"
        company = connector.get_company("999000001")
        assert company is not None
        assert company.name == "Mock"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
