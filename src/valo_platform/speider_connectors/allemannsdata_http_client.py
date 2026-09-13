"""Governed streamable-HTTP MCP client for Allemannsdata.

The client speaks the Model Context Protocol directly: initialize a session,
discover tools, and invoke tools through ``tools/call``.  Every acquisition keeps
an immutable receipt over the exact JSON-RPC result.  The client does not decide
whether returned data is true, independent, admissible, or authoritative.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from itertools import count
from typing import Any, Dict, List, Mapping, Optional, Sequence
from urllib.parse import urlparse, urlunparse

import httpx

from src.valo_platform.canonical import CANONICALIZATION_ALGORITHM, canonical_digest

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AcquisitionReceipt:
    """Exact acquisition metadata for one MCP response."""

    server: str
    tool_name: str
    endpoint: str
    request: Dict[str, Any]
    captured_at: datetime
    raw_response_digest: str
    canonicalization: str
    http_status: int
    from_cache: bool = False
    protocol_version: Optional[str] = None
    session_id_present: bool = False

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MCPResponseError(ValueError):
    """Raised when a remote MCP endpoint returns a JSON-RPC or tool error."""


class AllemannsdataHTTPClient:
    """Synchronous MCP client for Allemannsdata streamable-HTTP servers."""

    DEFAULT_ROOT = "https://allemannsdata.com"
    DEFAULT_PROTOCOL_VERSION = "2025-06-18"

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 20.0,
        cache_ttl_seconds: int = 3600,
        protocol_version: Optional[str] = None,
    ) -> None:
        self.base_url = base_url or os.getenv(
            "ALLEMANNSDATA_BASE_URL", self.DEFAULT_ROOT
        )
        self.api_key = api_key or os.getenv("ALLEMANNSDATA_API_KEY", "")
        self.protocol_version = protocol_version or os.getenv(
            "ALLEMANNSDATA_MCP_PROTOCOL_VERSION", self.DEFAULT_PROTOCOL_VERSION
        )
        self.timeout = timeout
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self._cache: Dict[str, tuple[Any, datetime]] = {}
        self._tool_cache: Dict[str, tuple[List[Dict[str, Any]], datetime]] = {}
        self._client = httpx.Client(timeout=timeout, follow_redirects=True)
        self._request_ids = count(1)
        self._session_ids: Dict[str, str] = {}
        self._negotiated_protocols: Dict[str, str] = {}
        self._initialized_servers: set[str] = set()
        self._last_acquisition_receipt: Optional[AcquisitionReceipt] = None

    def __del__(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass

    def close(self) -> None:
        self._client.close()

    def _server_endpoint(self, server: str) -> str:
        """Resolve either a root URL or an explicitly supplied MCP endpoint."""

        base = self.base_url.rstrip("/")
        if "{server}" in base:
            return base.format(server=server)

        parsed = urlparse(base)
        path = parsed.path.rstrip("/")
        expected_suffix = f"/{server}/mcp"
        if path.endswith(expected_suffix):
            return base

        # The historical VALO default was https://allemannsdata.com/mcp. Treat
        # that as a legacy root alias rather than as a server endpoint.
        if path == "/mcp":
            parsed = parsed._replace(path="")
            root = urlunparse(parsed).rstrip("/")
            return f"{root}/{server}/mcp"

        # A custom endpoint ending in /mcp is assumed to be exact.
        if path.endswith("/mcp"):
            return base
        return f"{base}/{server}/mcp"

    def _headers(self, server: str) -> Dict[str, str]:
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "MCP-Protocol-Version": self._negotiated_protocols.get(
                server, self.protocol_version
            ),
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        session_id = self._session_ids.get(server)
        if session_id:
            headers["Mcp-Session-Id"] = session_id
        return headers

    @staticmethod
    def _decode_sse(text: str) -> List[Any]:
        events: List[Any] = []
        data_lines: List[str] = []

        def flush() -> None:
            if not data_lines:
                return
            payload = "\n".join(data_lines).strip()
            data_lines.clear()
            if not payload or payload == "[DONE]":
                return
            events.append(json.loads(payload))

        for line in text.splitlines():
            if line.startswith("data:"):
                data_lines.append(line[5:].lstrip())
            elif not line.strip():
                flush()
        flush()
        return events

    @classmethod
    def _decode_response(cls, response: httpx.Response) -> Any:
        if not response.content:
            return {}
        text = response.text.strip()
        content_type = response.headers.get("content-type", "").lower()
        if "text/event-stream" in content_type or text.startswith(("event:", "data:")):
            events = cls._decode_sse(text)
            if not events:
                return {}
            # Streamable HTTP may emit progress notifications before the actual
            # response. Prefer the last JSON-RPC response carrying result/error.
            for event in reversed(events):
                if isinstance(event, Mapping) and (
                    "result" in event or "error" in event or "id" in event
                ):
                    return event
            return events[-1]
        return response.json()

    def _receipt(
        self,
        *,
        server: str,
        tool_name: str,
        endpoint: str,
        request: Dict[str, Any],
        result: Any,
        http_status: int,
        from_cache: bool,
    ) -> AcquisitionReceipt:
        receipt = AcquisitionReceipt(
            server=server,
            tool_name=tool_name,
            endpoint=endpoint,
            request=dict(request),
            captured_at=datetime.now(timezone.utc),
            raw_response_digest=canonical_digest(result),
            canonicalization=CANONICALIZATION_ALGORITHM,
            http_status=http_status,
            from_cache=from_cache,
            protocol_version=self._negotiated_protocols.get(server),
            session_id_present=server in self._session_ids,
        )
        self._last_acquisition_receipt = receipt
        return receipt

    def _post_jsonrpc(
        self,
        server: str,
        payload: Dict[str, Any],
        *,
        receipt_name: str,
    ) -> tuple[Any, httpx.Response]:
        endpoint = self._server_endpoint(server)
        try:
            response = self._client.post(
                endpoint,
                json=payload,
                headers=self._headers(server),
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:1000] if exc.response is not None else ""
            raise MCPResponseError(
                f"MCP HTTP error for {server}/{receipt_name}: "
                f"{exc.response.status_code if exc.response else 0} {body}"
            ) from exc
        except httpx.RequestError as exc:
            raise MCPResponseError(
                f"MCP request failed for {server}/{receipt_name}: {exc}"
            ) from exc

        session_id = response.headers.get("mcp-session-id")
        if session_id:
            self._session_ids[server] = session_id

        decoded = self._decode_response(response)
        if isinstance(decoded, Mapping) and decoded.get("error"):
            error = decoded["error"]
            if isinstance(error, Mapping):
                code = error.get("code")
                message = error.get("message", "MCP error")
                data = error.get("data")
                raise MCPResponseError(
                    f"MCP JSON-RPC error {code} for {server}/{receipt_name}: "
                    f"{message}; data={data!r}"
                )
            raise MCPResponseError(
                f"MCP JSON-RPC error for {server}/{receipt_name}: {error!r}"
            )
        result = decoded.get("result", {}) if isinstance(decoded, Mapping) else decoded
        return result, response

    def _initialize(self, server: str) -> None:
        if server in self._initialized_servers:
            return
        request_id = next(self._request_ids)
        result, _ = self._post_jsonrpc(
            server,
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "initialize",
                "params": {
                    "protocolVersion": self.protocol_version,
                    "capabilities": {},
                    "clientInfo": {
                        "name": "valo-speider",
                        "version": "1.0",
                    },
                },
            },
            receipt_name="initialize",
        )
        if not isinstance(result, Mapping):
            raise MCPResponseError("MCP initialize result must be an object")
        negotiated = result.get("protocolVersion")
        if negotiated:
            self._negotiated_protocols[server] = str(negotiated)

        # notifications/initialized is a JSON-RPC notification and may return an
        # empty 202 response.
        self._post_jsonrpc(
            server,
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            },
            receipt_name="notifications/initialized",
        )
        self._initialized_servers.add(server)

    def _rpc(self, server: str, method: str, params: Dict[str, Any]) -> Any:
        self._initialize(server)
        result, _ = self._post_jsonrpc(
            server,
            {
                "jsonrpc": "2.0",
                "id": next(self._request_ids),
                "method": method,
                "params": params,
            },
            receipt_name=method,
        )
        return result

    def _cache_key(self, server: str, tool_name: str, params: Dict[str, Any]) -> str:
        return f"{server}:{tool_name}:{canonical_digest(params)}"

    def _is_cached_valid(self, cache_key: str) -> bool:
        if cache_key not in self._cache:
            return False
        _, timestamp = self._cache[cache_key]
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - timestamp < self.cache_ttl

    def list_tools(self, server: str, *, use_cache: bool = True) -> List[Dict[str, Any]]:
        cached = self._tool_cache.get(server)
        if use_cache and cached:
            tools, captured_at = cached
            if datetime.now(timezone.utc) - captured_at < self.cache_ttl:
                return list(tools)

        tools: List[Dict[str, Any]] = []
        cursor: Optional[str] = None
        while True:
            params: Dict[str, Any] = {}
            if cursor:
                params["cursor"] = cursor
            result = self._rpc(server, "tools/list", params)
            if not isinstance(result, Mapping):
                raise MCPResponseError("MCP tools/list result must be an object")
            page = result.get("tools", [])
            if not isinstance(page, list):
                raise MCPResponseError("MCP tools/list tools field must be a list")
            tools.extend(item for item in page if isinstance(item, dict))
            cursor = result.get("nextCursor")
            if not cursor:
                break
        self._tool_cache[server] = (list(tools), datetime.now(timezone.utc))
        return tools

    def _tool_definition(self, server: str, tool_name: str) -> Optional[Dict[str, Any]]:
        for tool in self.list_tools(server):
            if tool.get("name") == tool_name:
                return tool
        return None

    def resolve_arguments(
        self,
        server: str,
        tool_name: str,
        values: Mapping[str, Any],
        aliases: Optional[Mapping[str, Sequence[str]]] = None,
    ) -> Dict[str, Any]:
        """Map semantic inputs onto the live tool input schema."""

        tool = self._tool_definition(server, tool_name)
        if tool is None:
            raise MCPResponseError(f"Tool '{tool_name}' is not exposed by {server}")
        schema = tool.get("inputSchema") or tool.get("input_schema") or {}
        properties = schema.get("properties", {}) if isinstance(schema, Mapping) else {}
        required = schema.get("required", []) if isinstance(schema, Mapping) else []
        arguments: Dict[str, Any] = {}
        aliases = aliases or {}

        for semantic_name, value in values.items():
            if value is None:
                continue
            candidates = (semantic_name, *aliases.get(semantic_name, ()))
            selected = next((name for name in candidates if name in properties), None)
            if selected is None:
                # Schema-less tools are legal. Use the semantic name rather than
                # guessing a provider-specific alternative.
                selected = semantic_name
            arguments[selected] = value

        missing = [name for name in required if name not in arguments]
        if missing:
            raise MCPResponseError(
                f"Missing required arguments for {tool_name}: {', '.join(missing)}"
            )
        return arguments

    @staticmethod
    def _extract_tool_payload(result: Any) -> Any:
        if not isinstance(result, Mapping):
            return result
        if result.get("isError"):
            text = ""
            content = result.get("content", [])
            if isinstance(content, list):
                text = " ".join(
                    str(item.get("text", ""))
                    for item in content
                    if isinstance(item, Mapping)
                ).strip()
            raise MCPResponseError(text or "Remote MCP tool returned isError=true")

        structured = result.get("structuredContent")
        if structured is not None:
            return structured

        content = result.get("content")
        if isinstance(content, list):
            payloads: List[Any] = []
            for item in content:
                if not isinstance(item, Mapping):
                    continue
                if "json" in item:
                    payloads.append(item["json"])
                    continue
                if item.get("type") == "text" and "text" in item:
                    text = str(item["text"])
                    try:
                        payloads.append(json.loads(text))
                    except json.JSONDecodeError:
                        payloads.append(text)
            if len(payloads) == 1:
                return payloads[0]
            if payloads:
                return payloads
        return dict(result)

    def call_tool_with_receipt(
        self,
        server: str,
        tool_name: str,
        params: Dict[str, Any],
        use_cache: bool = True,
    ) -> tuple[Any, AcquisitionReceipt]:
        cache_key = self._cache_key(server, tool_name, params)
        endpoint = self._server_endpoint(server)
        if use_cache and self._is_cached_valid(cache_key):
            cached_result, _ = self._cache[cache_key]
            receipt = self._receipt(
                server=server,
                tool_name=tool_name,
                endpoint=endpoint,
                request=params,
                result=cached_result,
                http_status=200,
                from_cache=True,
            )
            return cached_result, receipt

        result = self._rpc(
            server,
            "tools/call",
            {"name": tool_name, "arguments": dict(params)},
        )
        payload = self._extract_tool_payload(result)
        self._cache[cache_key] = (payload, datetime.now(timezone.utc))
        receipt = self._receipt(
            server=server,
            tool_name=tool_name,
            endpoint=endpoint,
            request=params,
            result=result,
            http_status=200,
            from_cache=False,
        )
        return payload, receipt

    def call_tool(
        self,
        server: str,
        tool_name: str,
        params: Dict[str, Any],
        use_cache: bool = True,
    ) -> Any:
        payload, _ = self.call_tool_with_receipt(
            server, tool_name, params, use_cache=use_cache
        )
        return payload

    def call_tool_adapted(
        self,
        server: str,
        tool_name: str,
        values: Mapping[str, Any],
        aliases: Optional[Mapping[str, Sequence[str]]] = None,
        *,
        use_cache: bool = True,
    ) -> Any:
        arguments = self.resolve_arguments(server, tool_name, values, aliases)
        return self.call_tool(server, tool_name, arguments, use_cache=use_cache)

    # Firmafakta compatibility wrappers. They invoke the real Norwegian tool
    # names while preserving the older connector-facing method names.
    _ORG_ALIASES = {
        "org_number": ("org_nr", "organisasjonsnummer", "orgnr"),
    }

    def get_company(self, org_number: str) -> Any:
        return self.call_tool_adapted(
            "firmafakta",
            "selskapsdetaljer",
            {"org_number": org_number},
            self._ORG_ALIASES,
        )

    def find_companies_by_name(self, name: str) -> Any:
        return self.call_tool_adapted(
            "firmafakta",
            "organisasjonsnummer_for_selskap",
            {"company_name": name},
            {"company_name": ("name", "selskapsnavn", "navn")},
        )

    def get_company_shareholders(self, org_number: str, limit: int = 100) -> Any:
        return self.call_tool_adapted(
            "firmafakta",
            "aksjeeiere_for_selskap",
            {"org_number": org_number, "limit": limit},
            self._ORG_ALIASES,
        )

    def get_company_roles(self, org_number: str) -> Any:
        return self.call_tool_adapted(
            "firmafakta",
            "roller_i_enhet",
            {"org_number": org_number},
            self._ORG_ALIASES,
        )

    def get_company_financials(self, org_number: str) -> Any:
        return self.call_tool_adapted(
            "firmafakta",
            "get_company_last_financial_statement",
            {"org_number": org_number},
            self._ORG_ALIASES,
        )

    def get_person_holdings(self, person_reference: str) -> Any:
        name = person_reference
        birth_year: Optional[str] = None
        if "|" in person_reference:
            name, birth_year = (
                part.strip() for part in person_reference.rsplit("|", 1)
            )
        return self.call_tool_adapted(
            "firmafakta",
            "aksjeposter_for_person",
            {"person_name": name, "birth_year": birth_year},
            {
                "person_name": ("name", "navn"),
                "birth_year": ("fodselsaar", "fødselsår"),
            },
        )

    def search_companies(
        self,
        *,
        location: Optional[str] = None,
        business_code: Optional[str] = None,
        min_employees: Optional[int] = None,
        max_employees: Optional[int] = None,
    ) -> Any:
        values: Dict[str, Any] = {
            "location": location,
            "business_codes": [business_code] if business_code else None,
            "min_employees": min_employees,
            "max_employees": max_employees,
        }
        return self.call_tool_adapted(
            "firmafakta",
            "finn_selskaper",
            values,
            {
                "location": ("kommune", "fylke"),
                "business_codes": (
                    "naeringskoder",
                    "næringskoder",
                    "business_code",
                    "naeringskode",
                ),
                "min_employees": (
                    "minimum_antall_ansatte",
                    "min_ansatte",
                    "ansatte_fra",
                ),
                "max_employees": (
                    "maksimum_antall_ansatte",
                    "max_ansatte",
                    "ansatte_til",
                ),
            },
        )

    def get_last_acquisition_receipt(self) -> Optional[Dict[str, Any]]:
        if self._last_acquisition_receipt is None:
            return None
        return self._last_acquisition_receipt.as_dict()

    def clear_cache(self) -> None:
        self._cache.clear()
        self._tool_cache.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        valid_count = sum(
            1 for cache_key in self._cache if self._is_cached_valid(cache_key)
        )
        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_count,
            "tool_catalogs": len(self._tool_cache),
            "initialized_servers": sorted(self._initialized_servers),
            "cache_ttl_seconds": int(self.cache_ttl.total_seconds()),
        }


__all__ = [
    "AcquisitionReceipt",
    "AllemannsdataHTTPClient",
    "MCPResponseError",
]
