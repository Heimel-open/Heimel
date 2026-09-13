import json

import httpx
import pytest

from src.valo_platform.canonical import canonical_digest
from src.valo_platform.speider_connectors.allemannsdata_http_client import (
    AllemannsdataHTTPClient,
)
from src.valo_platform.speider_connectors.allemannsdata_lovdata import (
    AllemannsdataLovdataConnector,
)
from src.valo_platform.speider_connectors.allemannsdata_ssb import (
    AllemannsdataSSBConnector,
)
from src.valo_platform.speider_connectors.mcp_payload import (
    MCPResponseShapeError,
    require_list,
    require_object,
    unwrap_mcp_payload,
)


def test_ssb_returns_exact_upstream_company_statistics(monkeypatch) -> None:
    connector = AllemannsdataSSBConnector()
    upstream = {
        "data": {
            "statistics": {
                "org_number": "123456789",
                "year": 2026,
                "employees": 73,
                "revenue": 42000000,
            }
        }
    }
    monkeypatch.setattr(connector, "call_tool", lambda *_args, **_kwargs: upstream)

    result = connector.get_company_statistics("123456789", 2026)

    assert result == upstream["data"]["statistics"]
    assert result["employees"] == 73
    assert result["employees"] != 45


def test_ssb_result_changes_when_upstream_changes(monkeypatch) -> None:
    connector = AllemannsdataSSBConnector()
    payloads = iter(
        [
            {"statistics": {"org_number": "123", "employees": 7}},
            {"statistics": {"org_number": "123", "employees": 91}},
        ]
    )
    monkeypatch.setattr(connector, "call_tool", lambda *_args, **_kwargs: next(payloads))

    first = connector.get_company_statistics("123")
    second = connector.get_company_statistics("123")

    assert first["employees"] == 7
    assert second["employees"] == 91


def test_ssb_rejects_mismatched_identity(monkeypatch) -> None:
    connector = AllemannsdataSSBConnector()
    monkeypatch.setattr(
        connector,
        "call_tool",
        lambda *_args, **_kwargs: {
            "statistics": {"org_number": "different", "employees": 10}
        },
    )

    with pytest.raises(MCPResponseShapeError, match="does not match"):
        connector.get_company_statistics("expected")


def test_ssb_rejects_unmappable_payload(monkeypatch) -> None:
    connector = AllemannsdataSSBConnector()
    monkeypatch.setattr(connector, "call_tool", lambda *_args, **_kwargs: "not-json-object")

    with pytest.raises(MCPResponseShapeError):
        connector.get_company_statistics("123")


def test_lovdata_returns_exact_statute_without_placeholder_text(monkeypatch) -> None:
    connector = AllemannsdataLovdataConnector()
    upstream = {
        "statute": {
            "statute_id": "LOV-2026-01",
            "title": "Exact upstream title",
            "full_text": "Exact upstream legal text",
            "effective_date": "2026-07-01",
        }
    }
    monkeypatch.setattr(connector, "call_tool", lambda *_args, **_kwargs: upstream)

    result = connector.get_statute("LOV-2026-01")

    assert result == upstream["statute"]
    assert result["full_text"] == "Exact upstream legal text"
    assert "would be here" not in result["full_text"]


def test_lovdata_search_returns_only_upstream_records(monkeypatch) -> None:
    connector = AllemannsdataLovdataConnector()
    upstream = {
        "results": [
            {"statute_id": "LOV-A", "title": "A"},
            {"statute_id": "LOV-B", "title": "B"},
        ]
    }
    monkeypatch.setattr(connector, "call_tool", lambda *_args, **_kwargs: upstream)

    assert connector.search_legislation("AI") == upstream["results"]


def test_mcp_text_envelope_preserves_embedded_json() -> None:
    raw = {
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": '{"statistics":{"employees":12}}',
                }
            ]
        }
    }

    assert unwrap_mcp_payload(raw) == {"statistics": {"employees": 12}}
    assert require_object(raw, keys=("statistics",)) == {"employees": 12}


def test_mcp_list_rejects_non_object_items() -> None:
    with pytest.raises(MCPResponseShapeError):
        require_list({"results": [{"id": 1}, "invented"]}, keys=("results",))


def _streamable_mcp_client(
    tool_payloads: list[dict],
    *,
    cache_ttl_seconds: int = 3600,
) -> tuple[AllemannsdataHTTPClient, list[dict]]:
    payloads = iter(tool_payloads)
    requests: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        requests.append(body)
        method = body.get("method")
        if method == "initialize":
            return httpx.Response(
                200,
                headers={"mcp-session-id": "source-integrity-session"},
                json={
                    "jsonrpc": "2.0",
                    "id": body["id"],
                    "result": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "test", "version": "1"},
                    },
                },
            )
        if method == "notifications/initialized":
            return httpx.Response(202)
        if method == "tools/call":
            payload = next(payloads)
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": body["id"],
                    "result": {"structuredContent": payload},
                },
            )
        raise AssertionError(f"unexpected MCP method: {method}")

    client = AllemannsdataHTTPClient(
        base_url="https://example.test/mcp",
        cache_ttl_seconds=cache_ttl_seconds,
    )
    client._client.close()
    client._client = httpx.Client(transport=httpx.MockTransport(handler))
    return client, requests


def test_http_client_records_exact_acquisition_digest_and_cache() -> None:
    payload = {"data": {"value": 17}}
    client, requests = _streamable_mcp_client([payload])

    first, first_receipt = client.call_tool_with_receipt(
        "ssb",
        "get_statistics",
        {"organisasjonsnummer": "123"},
    )
    second, second_receipt = client.call_tool_with_receipt(
        "ssb",
        "get_statistics",
        {"organisasjonsnummer": "123"},
    )

    assert first == second == payload
    assert first_receipt.raw_response_digest == canonical_digest(
        {"structuredContent": payload}
    )
    assert first_receipt.from_cache is False
    assert first_receipt.session_id_present is True
    assert second_receipt.from_cache is True
    assert [request.get("method") for request in requests] == [
        "initialize",
        "notifications/initialized",
        "tools/call",
    ]


def test_http_client_digest_changes_with_payload() -> None:
    client, requests = _streamable_mcp_client(
        [{"value": 1}, {"value": 2}],
        cache_ttl_seconds=0,
    )

    _, first_receipt = client.call_tool_with_receipt(
        "ssb", "get_statistics", {"organisasjonsnummer": "123"}, use_cache=False
    )
    _, second_receipt = client.call_tool_with_receipt(
        "ssb", "get_statistics", {"organisasjonsnummer": "123"}, use_cache=False
    )

    assert first_receipt.raw_response_digest != second_receipt.raw_response_digest
    assert [request.get("method") for request in requests].count("initialize") == 1
    assert [request.get("method") for request in requests].count("tools/call") == 2
