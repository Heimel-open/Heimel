"""Governed Allemannsdata SSB acquisition adapter.

The adapter returns only values present in the upstream payload. It never fills
missing statistics with examples, projections or fixtures.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .mcp_connector_base import MCPConnectorBase
from .mcp_payload import MCPResponseShapeError, require_list, require_object


class AllemannsdataSSBConnector(MCPConnectorBase):
    """Connector to Statistics Norway data exposed through Allemannsdata MCP."""

    def __init__(
        self,
        mcp_endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        super().__init__("SSB", api_key=api_key, base_url=mcp_endpoint)

    def register_tools(self) -> None:
        self._tool_registry = {
            "get_company_statistics": {
                "description": "Get employment, revenue, and economic statistics for company",
                "required_params": ["org_number"],
                "parameters": {
                    "org_number": "str",
                    "year": "int|optional",
                },
            },
            "search_industry_statistics": {
                "description": "Get industry-wide statistics by industry code",
                "required_params": ["industry_code"],
                "parameters": {
                    "industry_code": "str",
                    "year_from": "int|optional",
                    "year_to": "int|optional",
                },
            },
            "get_municipality_statistics": {
                "description": "Get economic statistics by municipality",
                "required_params": ["municipality_name"],
                "parameters": {
                    "municipality_name": "str",
                    "year": "int|optional",
                },
            },
            "get_employment_statistics": {
                "description": "Get employment data by industry and region",
                "required_params": ["industry_code"],
                "parameters": {
                    "industry_code": "str",
                    "region": "str|optional",
                    "year": "int|optional",
                },
            },
        }

    @staticmethod
    def _assert_match(
        payload: Dict[str, Any],
        *,
        field: str,
        expected: Any,
    ) -> None:
        if field in payload and str(payload[field]) != str(expected):
            raise MCPResponseShapeError(
                f"SSB response {field}={payload[field]!r} does not match request {expected!r}"
            )

    def get_company_statistics(
        self,
        org_number: str,
        year: Optional[int] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"org_number": org_number}
        if year is not None:
            params["year"] = year
        result = self.call_tool("get_company_statistics", params)
        payload = require_object(
            result,
            keys=("company_statistics", "statistics", "company"),
        )
        self._assert_match(payload, field="org_number", expected=org_number)
        if year is not None:
            self._assert_match(payload, field="year", expected=year)
        return payload

    def search_industry_statistics(
        self,
        industry_code: str,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"industry_code": industry_code}
        if year_from is not None:
            params["year_from"] = year_from
        if year_to is not None:
            params["year_to"] = year_to
        result = self.call_tool("search_industry_statistics", params)
        records = require_list(
            result,
            keys=("industry_statistics", "statistics", "series", "results", "items"),
        )
        for record in records:
            self._assert_match(record, field="industry_code", expected=industry_code)
        return records

    def get_municipality_statistics(
        self,
        municipality_name: str,
        year: Optional[int] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"municipality_name": municipality_name}
        if year is not None:
            params["year"] = year
        result = self.call_tool("get_municipality_statistics", params)
        payload = require_object(
            result,
            keys=("municipality_statistics", "statistics", "municipality"),
        )
        municipality_field = (
            "municipality_name"
            if "municipality_name" in payload
            else "municipality"
        )
        if municipality_field in payload:
            self._assert_match(
                payload,
                field=municipality_field,
                expected=municipality_name,
            )
        if year is not None:
            self._assert_match(payload, field="year", expected=year)
        return payload

    def get_employment_statistics(
        self,
        industry_code: str,
        region: Optional[str] = None,
        year: Optional[int] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"industry_code": industry_code}
        if region is not None:
            params["region"] = region
        if year is not None:
            params["year"] = year
        result = self.call_tool("get_employment_statistics", params)
        payload = require_object(
            result,
            keys=("employment_statistics", "statistics", "employment"),
        )
        self._assert_match(payload, field="industry_code", expected=industry_code)
        if region is not None:
            self._assert_match(payload, field="region", expected=region)
        if year is not None:
            self._assert_match(payload, field="year", expected=year)
        return payload


__all__ = ["AllemannsdataSSBConnector"]
