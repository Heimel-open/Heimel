"""Tests for Phase 37: Real Allemannsdata Integration

Tests the HTTP client and updated Firmafakta connector for real API integration.
"""

import pytest
import json
import httpx
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta

from src.valo_platform.speider_connectors.allemannsdata_http_client import AllemannsdataHTTPClient
from src.valo_platform.speider_connectors.allemannsdata_firmafakta import (
    AllemannsdataFirmafaktaConnector,
    FIRMAFAKTA_REQUIRED_TOOLS,
)
from src.valo_platform.speider_connectors.models import Company, RoleType


def _make_client(result_payload):
    tools = [
        {
            "name": "selskapsdetaljer",
            "inputSchema": {
                "type": "object",
                "properties": {"org_nr": {"type": "string"}},
                "required": [],
            },
        }
    ]
    request_log = []

    def handler(request):
        payload = json.loads(request.content.decode())
        request_log.append(payload)
        method = payload.get("method")
        if method == "initialize":
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "result": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "firmafakta", "version": "1"},
                    },
                },
            )
        if method == "notifications/initialized":
            return httpx.Response(202)
        if method == "tools/list":
            return httpx.Response(
                200,
                json={"jsonrpc": "2.0", "id": payload["id"], "result": {"tools": tools}},
            )
        if method == "tools/call":
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result_payload)}]
                    },
                },
            )
        raise AssertionError(method)

    client = AllemannsdataHTTPClient(base_url="https://allemannsdata.com")
    client._client.close()
    client._client = httpx.Client(transport=httpx.MockTransport(handler))
    return client, request_log


class TestAllemannsdataHTTPClient:
    """Test AllemannsdataHTTPClient."""

    def test_init_defaults(self):
        """Test client initialization with defaults."""
        client = AllemannsdataHTTPClient()
        assert client.base_url == "https://allemannsdata.com"
        assert client.timeout == 20.0

    def test_init_with_custom_url(self):
        """Test client initialization with custom URL."""
        client = AllemannsdataHTTPClient(base_url="http://localhost:8000")
        assert client.base_url == "http://localhost:8000"

    def test_cache_key_generation(self):
        """Test cache key generation."""
        client = AllemannsdataHTTPClient()
        key1 = client._cache_key("server-a", "tool-a", {"param": "value"})
        key2 = client._cache_key("server-a", "tool-a", {"param": "value"})
        assert key1 == key2

    def test_cache_hit(self):
        """Test cache hit detection."""
        client = AllemannsdataHTTPClient()
        cache_key = "/test:params"
        client._cache[cache_key] = ({"result": "data"}, datetime.now(timezone.utc))

        assert client._is_cached_valid(cache_key) is True
        assert client._cache[cache_key][0] == {"result": "data"}

    def test_cache_miss_on_expired(self):
        """Test cache miss on expired entry."""
        client = AllemannsdataHTTPClient(cache_ttl_seconds=1)
        cache_key = "/test:params"

        old_time = datetime.now(timezone.utc) - timedelta(seconds=10)
        client._cache[cache_key] = ({"result": "data"}, old_time)

        assert client._is_cached_valid(cache_key) is False

    def test_clear_cache(self):
        """Test cache clearing."""
        client = AllemannsdataHTTPClient()
        client._cache["key1"] = ({"data": 1}, datetime.now(timezone.utc).replace(tzinfo=None))
        client._cache["key2"] = ({"data": 2}, datetime.now(timezone.utc).replace(tzinfo=None))

        client.clear_cache()

        assert len(client._cache) == 0

    def test_get_cache_stats(self):
        """Test cache statistics."""
        client = AllemannsdataHTTPClient()
        client._cache["key1"] = ({"data": 1}, datetime.now(timezone.utc).replace(tzinfo=None))

        stats = client.get_cache_stats()

        assert stats["total_entries"] == 1
        assert stats["valid_entries"] == 1

    def test_call_tool_success(self):
        """Test successful tool call."""
        client, _ = _make_client({"status": "success", "data": {"name": "Test Co"}})
        result = client.call_tool("firmafakta", "selskapsdetaljer", {"org_number": "123"})

        assert result["status"] == "success"
        assert result["data"]["name"] == "Test Co"

    def test_call_tool_with_caching(self):
        """Test that successful responses are cached."""
        client, request_log = _make_client({"data": {"name": "Test Co"}})

        def call_count():
            return sum(1 for payload in request_log if payload.get("method") == "tools/call")

        # First call should hit API
        result1 = client.call_tool("firmafakta", "selskapsdetaljer", {"org_number": "123"})
        assert call_count() == 1

        # Second call should use cache
        result2 = client.call_tool("firmafakta", "selskapsdetaljer", {"org_number": "123"})
        assert call_count() == 1  # Still 1, not 2
        assert result1 == result2

    def test_call_tool_bypass_cache(self):
        """Test that cache can be bypassed."""
        client, request_log = _make_client({"data": {"name": "Test Co"}})

        def call_count():
            return sum(1 for payload in request_log if payload.get("method") == "tools/call")

        # Call with cache
        client.call_tool("firmafakta", "selskapsdetaljer", {"org_number": "123"})
        assert call_count() == 1

        # Call without cache
        client.call_tool(
            "firmafakta", "selskapsdetaljer", {"org_number": "123"}, use_cache=False
        )
        assert call_count() == 2

    def test_get_company(self):
        """Test get_company convenience method."""
        client, _ = _make_client({"org_number": "123", "name": "Acme Co"})
        result = client.get_company("123")

        assert result["name"] == "Acme Co"


class TestAllemannsdataFirmafaktaConnectorWithRealHTTP:
    """Test Firmafakta connector with HTTP client."""

    def test_init(self):
        """Test connector initialization."""
        connector = AllemannsdataFirmafaktaConnector()
        assert connector.connector_name == "Firmafakta"
        assert connector._http_client is not None

    def test_get_connector_name(self):
        """Test getting connector name."""
        connector = AllemannsdataFirmafaktaConnector()
        assert connector.get_connector_name() == "Firmafakta"

    def test_get_last_updated(self):
        """Test getting last update timestamp."""
        connector = AllemannsdataFirmafaktaConnector()
        last_update = connector.get_last_updated()
        assert isinstance(last_update, datetime)

    @patch.object(AllemannsdataHTTPClient, "get_company")
    def test_get_company_success(self, mock_get_company):
        """Test successful company retrieval."""
        mock_get_company.return_value = {
            "org_number": "123456789",
            "name": "Acme Corporation",
            "business_code": "62020",
            "municipality": "Oslo",
            "county": "Oslo",
            "founded_year": 2015,
            "employee_count": 45,
            "status": "active",
            "metadata": {},
        }

        connector = AllemannsdataFirmafaktaConnector()
        company = connector.get_company("123456789")

        assert company is not None
        assert company.name == "Acme Corporation"
        assert company.org_number == "123456789"
        assert company.employee_count == 45

    @patch.object(AllemannsdataHTTPClient, "get_company")
    def test_get_company_not_found(self, mock_get_company):
        """Test company not found returns None."""
        mock_get_company.return_value = None

        connector = AllemannsdataFirmafaktaConnector()
        company = connector.get_company("999999999")

        assert company is None

    @patch.object(AllemannsdataHTTPClient, "get_company")
    def test_get_company_error_handling(self, mock_get_company):
        """Test error handling in get_company."""
        mock_get_company.side_effect = Exception("API error")

        connector = AllemannsdataFirmafaktaConnector()
        company = connector.get_company("123456789")

        assert company is None

    @patch.object(AllemannsdataHTTPClient, "find_companies_by_name")
    def test_find_company_by_name(self, mock_find):
        """Test finding companies by name."""
        mock_find.return_value = [
            {"org_number": "123", "name": "Acme Co", "business_code": "62020", "metadata": {}},
            {"org_number": "456", "name": "Acme Ltd", "business_code": "62030", "metadata": {}},
        ]

        connector = AllemannsdataFirmafaktaConnector()
        companies = connector.find_company_by_name("Acme")

        assert len(companies) == 2
        assert companies[0].name == "Acme Co"
        assert companies[1].org_number == "456"

    @patch.object(AllemannsdataHTTPClient, "find_companies_by_name")
    def test_find_company_by_name_empty(self, mock_find):
        """Test finding no companies."""
        mock_find.return_value = []

        connector = AllemannsdataFirmafaktaConnector()
        companies = connector.find_company_by_name("NonExistent")

        assert companies == []

    @patch.object(AllemannsdataHTTPClient, "get_company_shareholders")
    def test_get_company_shareholders(self, mock_get_shareholders):
        """Test retrieving shareholders."""
        mock_get_shareholders.return_value = [
            {
                "shareholder_id": "sh-1",
                "shareholder_name": "John Doe",
                "shareholder_type": "person",
                "ownership_percentage": 50.0,
                "metadata": {},
            },
            {
                "shareholder_id": "sh-2",
                "shareholder_name": "Jane Corp",
                "shareholder_type": "company",
                "ownership_percentage": 50.0,
                "metadata": {},
            },
        ]

        connector = AllemannsdataFirmafaktaConnector()
        shareholders = connector.get_company_shareholders("123456789")

        assert len(shareholders) == 2
        assert shareholders[0].shareholder_name == "John Doe"
        assert shareholders[1].ownership_percentage == 50.0

    @patch.object(AllemannsdataHTTPClient, "get_company_roles")
    def test_get_company_roles(self, mock_get_roles):
        """Test retrieving company roles."""
        mock_get_roles.return_value = [
            {
                "role_id": "r-1",
                "person_name": "Alice Smith",
                "role_type": "ceo",
                "metadata": {},
            },
            {
                "role_id": "r-2",
                "person_name": "Bob Jones",
                "role_type": "board_member",
                "metadata": {},
            },
        ]

        connector = AllemannsdataFirmafaktaConnector()
        roles = connector.get_company_roles("123456789")

        assert len(roles) == 2
        assert roles[0].person_name == "Alice Smith"
        assert roles[1].role_type == RoleType.BOARD_MEMBER

    @patch.object(AllemannsdataHTTPClient, "get_company_financials")
    def test_get_company_financials(self, mock_get_financials):
        """Test retrieving company financials."""
        mock_get_financials.return_value = {
            "org_number": "123456789",
            "fiscal_year": 2024,
            "revenue": 15000000.0,
            "operating_profit": 2500000.0,
            "equity": 5000000.0,
            "assets": 20000000.0,
            "liabilities": 15000000.0,
            "equity_ratio": 0.25,
        }

        connector = AllemannsdataFirmafaktaConnector()
        financials = connector.get_company_financials("123456789")

        assert financials["revenue"] == 15000000.0
        assert financials["equity"] == 5000000.0
        assert financials["assets"] == 20000000.0

    @patch.object(AllemannsdataHTTPClient, "list_tools")
    def test_is_healthy(self, mock_list_tools):
        """Test health check."""
        mock_list_tools.return_value = [
            {"name": name} for name in sorted(FIRMAFAKTA_REQUIRED_TOOLS)
        ]

        connector = AllemannsdataFirmafaktaConnector()
        is_healthy = connector.is_healthy()

        assert is_healthy is True

    @patch.object(AllemannsdataHTTPClient, "list_tools")
    def test_is_healthy_error(self, mock_list_tools):
        """Test health check with error."""
        mock_list_tools.side_effect = Exception("Connection error")

        connector = AllemannsdataFirmafaktaConnector()
        is_healthy = connector.is_healthy()

        assert is_healthy is False


class TestPhase37Integration:
    """Integration tests for Phase 37."""

    @patch.object(AllemannsdataHTTPClient, "get_company")
    @patch.object(AllemannsdataHTTPClient, "get_company_shareholders")
    @patch.object(AllemannsdataHTTPClient, "get_company_roles")
    @patch.object(AllemannsdataHTTPClient, "get_company_financials")
    def test_full_company_discovery(
        self,
        mock_financials,
        mock_roles,
        mock_shareholders,
        mock_company,
    ):
        """Test complete company discovery workflow."""
        # Mock company data
        mock_company.return_value = {
            "org_number": "910418327",
            "name": "TechCorp AS",
            "business_code": "62020",
            "founded_year": 2010,
            "employee_count": 150,
            "status": "active",
            "metadata": {},
        }

        mock_shareholders.return_value = [
            {
                "shareholder_id": "sh-1",
                "shareholder_name": "Founder Inc",
                "shareholder_type": "company",
                "ownership_percentage": 60.0,
                "metadata": {},
            }
        ]

        mock_roles.return_value = [
            {
                "role_id": "r-1",
                "person_name": "John Doe",
                "role_type": "ceo",
                "metadata": {},
            }
        ]

        mock_financials.return_value = {
            "fiscal_year": 2024,
            "revenue": 50000000.0,
            "equity": 10000000.0,
        }

        # Execute discovery workflow
        connector = AllemannsdataFirmafaktaConnector()

        company = connector.get_company("910418327")
        assert company.name == "TechCorp AS"

        shareholders = connector.get_company_shareholders("910418327")
        assert len(shareholders) == 1
        assert shareholders[0].shareholder_name == "Founder Inc"

        roles = connector.get_company_roles("910418327")
        assert len(roles) == 1
        assert roles[0].person_name == "John Doe"

        financials = connector.get_company_financials("910418327")
        assert financials["revenue"] == 50000000.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
