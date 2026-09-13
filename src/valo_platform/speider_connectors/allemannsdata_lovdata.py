"""Governed Allemannsdata Lovdata acquisition adapter.

The adapter returns only records present in the upstream payload. It never
creates statute text, case summaries, dates or relevance scores.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .mcp_connector_base import MCPConnectorBase
from .mcp_payload import MCPResponseShapeError, require_list, require_object


class AllemannsdataLovdataConnector(MCPConnectorBase):
    """Connector to Norwegian legal sources exposed through Allemannsdata MCP."""

    def __init__(
        self,
        mcp_endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        super().__init__("Lovdata", api_key=api_key, base_url=mcp_endpoint)

    def register_tools(self) -> None:
        self._tool_registry = {
            "search_legislation": {
                "description": "Search Norwegian legislation by keyword or statute",
                "required_params": ["query"],
                "parameters": {
                    "query": "str",
                    "statute_type": "str|optional",
                    "year_from": "int|optional",
                    "year_to": "int|optional",
                },
            },
            "get_statute": {
                "description": "Retrieve full text of a specific statute",
                "required_params": ["statute_id"],
                "parameters": {
                    "statute_id": "str",
                    "version_date": "str|optional",
                },
            },
            "search_court_decisions": {
                "description": "Search court decisions and case law",
                "required_params": ["query"],
                "parameters": {
                    "query": "str",
                    "court_level": "str|optional",
                    "year_from": "int|optional",
                    "year_to": "int|optional",
                },
            },
            "search_regulatory_decisions": {
                "description": "Search government regulatory decisions and directives",
                "required_params": ["query"],
                "parameters": {
                    "query": "str",
                    "agency": "str|optional",
                    "year_from": "int|optional",
                },
            },
            "search_amendments": {
                "description": "Find amendments to legislation",
                "required_params": ["statute_id"],
                "parameters": {
                    "statute_id": "str",
                    "year_from": "int|optional",
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
                f"Lovdata response {field}={payload[field]!r} "
                f"does not match request {expected!r}"
            )

    def search_legislation(
        self,
        query: str,
        statute_type: Optional[str] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"query": query}
        if statute_type is not None:
            params["statute_type"] = statute_type
        if year_from is not None:
            params["year_from"] = year_from
        if year_to is not None:
            params["year_to"] = year_to
        result = self.call_tool("search_legislation", params)
        return require_list(
            result,
            keys=("legislation", "statutes", "results", "items"),
        )

    def get_statute(
        self,
        statute_id: str,
        version_date: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        params: Dict[str, Any] = {"statute_id": statute_id}
        if version_date is not None:
            params["version_date"] = version_date
        result = self.call_tool("get_statute", params)
        payload = require_object(
            result,
            keys=("statute", "document", "record"),
        )
        self._assert_match(payload, field="statute_id", expected=statute_id)
        if version_date is not None:
            self._assert_match(payload, field="version_date", expected=version_date)
        return payload

    def search_court_decisions(
        self,
        query: str,
        court_level: Optional[str] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"query": query}
        if court_level is not None:
            params["court_level"] = court_level
        if year_from is not None:
            params["year_from"] = year_from
        if year_to is not None:
            params["year_to"] = year_to
        result = self.call_tool("search_court_decisions", params)
        return require_list(
            result,
            keys=("court_decisions", "decisions", "cases", "results", "items"),
        )

    def search_regulatory_decisions(
        self,
        query: str,
        agency: Optional[str] = None,
        year_from: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"query": query}
        if agency is not None:
            params["agency"] = agency
        if year_from is not None:
            params["year_from"] = year_from
        result = self.call_tool("search_regulatory_decisions", params)
        return require_list(
            result,
            keys=("regulatory_decisions", "decisions", "results", "items"),
        )

    def search_amendments(
        self,
        statute_id: str,
        year_from: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"statute_id": statute_id}
        if year_from is not None:
            params["year_from"] = year_from
        result = self.call_tool("search_amendments", params)
        records = require_list(
            result,
            keys=("amendments", "results", "items"),
        )
        for record in records:
            self._assert_match(record, field="statute_id", expected=statute_id)
        return records


__all__ = ["AllemannsdataLovdataConnector"]
