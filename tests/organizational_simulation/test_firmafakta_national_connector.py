from services.organizational_simulation.firmafakta_national_connector import (
    NORWAY_COUNTIES_2026,
    NationalFirmafaktaConnector,
)


class FakeHTTPClient:
    def __init__(self):
        self.calls = []

    def call_tool_adapted(
        self,
        server,
        tool_name,
        values,
        aliases,
        *,
        use_cache=True,
    ):
        self.calls.append(
            {
                "server": server,
                "tool_name": tool_name,
                "values": values,
                "aliases": aliases,
                "use_cache": use_cache,
            }
        )
        return {
            "result": """| navn | organisasjonsnummer | næringskode | antall_ansatte | fylke |
|---|---|---|---|---|
| A/S Norske Shell | 914807077 | 06.200 | 427 | Rogaland |
"""
        }

    def close(self):
        return None


def connector_with_fake_client(**kwargs):
    connector = NationalFirmafaktaConnector(**kwargs)
    connector._http_client.close()
    connector._http_client = FakeHTTPClient()
    return connector


def test_national_county_rotation_is_bounded_and_deterministic():
    connector = connector_with_fake_client(
        nationwide_limit=5,
        counties_per_search=3,
        county_rotation_seed=0,
    )

    assert len(NORWAY_COUNTIES_2026) == 15
    assert connector._locations(None) == (
        ("county", "Rogaland"),
        ("county", "Oslo"),
        ("county", "Akershus"),
    )


def test_explicit_county_maps_to_fylke_and_normalizes_company():
    connector = connector_with_fake_client(
        nationwide_limit=5,
        counties_per_search=1,
        county_rotation_seed=0,
    )

    companies = connector.search_companies(
        location="Rogaland",
        business_code="06",
        min_employees=10,
    )

    assert len(companies) == 1
    company = companies[0]
    assert company.org_number == "914807077"
    assert company.name == "A/S Norske Shell"
    assert company.business_code == "06.200"
    assert company.employee_count == 427
    assert company.county == "Rogaland"

    call = connector._http_client.calls[0]
    assert call["server"] == "firmafakta"
    assert call["tool_name"] == "finn_selskaper"
    assert call["values"]["county"] == "Rogaland"
    assert call["values"]["business_codes"] == ["06"]
    assert call["values"]["min_employees"] == 10
    assert call["aliases"]["county"] == ("fylke",)
    assert call["use_cache"] is False
