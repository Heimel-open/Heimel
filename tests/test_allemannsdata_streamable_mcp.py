import json
from unittest.mock import patch

import httpx

from src.valo_platform.speider_connectors.allemannsdata_firmafakta import (
    AllemannsdataFirmafaktaConnector,
    FIRMAFAKTA_REQUIRED_TOOLS,
)
from src.valo_platform.speider_connectors.allemannsdata_http_client import (
    AllemannsdataHTTPClient,
)
from src.valo_platform.speider_connectors.models import RoleType


def test_streamable_http_initializes_discovers_and_calls_real_tool_name():
    requests = []
    tools = [
        {
            "name": "selskapsdetaljer",
            "inputSchema": {
                "type": "object",
                "properties": {"org_nr": {"type": "string"}},
                "required": ["org_nr"],
            },
        }
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode())
        requests.append((request, payload))
        method = payload.get("method")
        if method == "initialize":
            return httpx.Response(
                200,
                headers={"mcp-session-id": "session-1"},
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
            body = (
                "event: message\n"
                "data: "
                + json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": payload["id"],
                        "result": {"tools": tools},
                    }
                )
                + "\n\n"
            )
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                text=body,
            )
        if method == "tools/call":
            assert payload["params"] == {
                "name": "selskapsdetaljer",
                "arguments": {"org_nr": "923609016"},
            }
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "organisasjonsnummer": "923609016",
                                        "navn": "Eksempel AS",
                                    }
                                ),
                            }
                        ]
                    },
                },
            )
        raise AssertionError(method)

    client = AllemannsdataHTTPClient(base_url="https://allemannsdata.com")
    client._client.close()
    client._client = httpx.Client(transport=httpx.MockTransport(handler))

    result = client.get_company("923609016")

    assert result["navn"] == "Eksempel AS"
    assert all(request.url.path == "/firmafakta/mcp" for request, _ in requests)
    tools_request = next(
        request for request, body in requests if body.get("method") == "tools/list"
    )
    assert tools_request.headers["mcp-session-id"] == "session-1"
    assert client.get_last_acquisition_receipt()["tool_name"] == "selskapsdetaljer"


def test_firmafakta_connector_maps_norwegian_payloads_without_inventing_fields():
    with patch(
        "src.valo_platform.speider_connectors.allemannsdata_firmafakta.AllemannsdataHTTPClient"
    ) as client_class:
        client = client_class.return_value
        client.get_company.return_value = {
            "organisasjonsnummer": "923609016",
            "navn": "Eksempel AS",
            "naeringskode1": {"kode": "62.010", "beskrivelse": "Programmering"},
            "antallAnsatte": 73,
            "forretningsadresse": {
                "kommune": "STAVANGER",
                "fylke": "ROGALAND",
            },
            "stiftelsesdato": "2019-08-01",
            "status": "aktiv",
        }
        client.get_company_roles.return_value = {
            "roller": [
                {
                    "id": "r1",
                    "navn": "Ada Leder",
                    "rollebeskrivelse": "Daglig leder",
                }
            ]
        }
        client.get_company_financials.return_value = {
            "open": {
                "regnskapsaar": 2025,
                "sum_driftsinntekter": 125000000,
                "driftsresultat": 15000000,
                "egenkapital": 45000000,
                "sum_eiendeler": 90000000,
            }
        }
        client.list_tools.return_value = [
            {"name": name} for name in sorted(FIRMAFAKTA_REQUIRED_TOOLS)
        ]

        connector = AllemannsdataFirmafaktaConnector()
        company = connector.get_company("923609016")
        roles = connector.get_company_roles("923609016")
        financials = connector.get_company_financials("923609016")

        assert company.name == "Eksempel AS"
        assert company.business_code == "62.010"
        assert company.employee_count == 73
        assert company.municipality == "STAVANGER"
        assert company.founded_year == 2019
        assert roles[0].role_type == RoleType.CEO
        assert financials["revenue"] == 125000000.0
        assert financials["currency"] == "NOK"
        assert connector.is_healthy()


def test_legacy_root_is_rewritten_to_server_specific_endpoint():
    client = AllemannsdataHTTPClient(
        base_url="https://allemannsdata.com/mcp"
    )
    assert (
        client._server_endpoint("firmafakta")
        == "https://allemannsdata.com/firmafakta/mcp"
    )
