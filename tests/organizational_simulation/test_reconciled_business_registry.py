import json

import httpx

from services.organizational_simulation.brreg_connector import BrregOpenDataConnector
from services.organizational_simulation.composite_business_registry import (
    CompositeBusinessRegistryConnector,
)
from src.valo_platform.speider_connectors.models import Company


def test_brreg_uses_official_api_path_and_nace_filter():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/enhetsregisteret/api/":
            return httpx.Response(200, json={"_links": {}})
        if request.url.path == "/enhetsregisteret/api/enheter":
            return httpx.Response(
                200,
                json={
                    "_embedded": {
                        "enheter": [
                            {
                                "organisasjonsnummer": "923609016",
                                "navn": "EQUINOR ASA",
                                "naeringskode1": {
                                    "kode": "06.100",
                                    "beskrivelse": "Utvinning av råolje",
                                },
                                "antallAnsatte": 21393,
                                "forretningsadresse": {
                                    "kommune": "STAVANGER",
                                    "kommunenummer": "1103",
                                },
                            }
                        ]
                    }
                },
            )
        raise AssertionError(str(request.url))

    connector = BrregOpenDataConnector(page_size=10)
    connector._client.close()
    connector._client = httpx.Client(
        base_url=connector.BASE_URL,
        transport=httpx.MockTransport(handler),
        headers={"Accept": connector.ENTITY_MEDIA_TYPE},
    )

    assert connector.is_healthy()
    companies = connector.search_companies(
        business_code="06",
        min_employees=10,
    )

    assert len(companies) == 1
    company = companies[0]
    assert company.org_number == "923609016"
    assert company.business_code == "06.100"
    assert company.employee_count == 21393
    assert company.municipality == "STAVANGER"
    assert company.county is None

    search_request = requests[-1]
    assert search_request.url.params["naeringskode"] == "06"
    assert search_request.url.params["sort"] == "antallAnsatte,DESC"
    assert search_request.url.params["size"] == "10"


class FakeConnector:
    def __init__(self, name, *, rows=None, financials=None):
        self.name = name
        self.rows = rows or []
        self.financials = financials
        self.search_calls = 0

    def get_connector_name(self):
        return self.name

    def is_healthy(self):
        return True

    def search_companies(self, **_kwargs):
        self.search_calls += 1
        return list(self.rows)

    def find_company_by_name(self, _name):
        return list(self.rows)

    def get_company(self, _org_number):
        return self.rows[0] if self.rows else None

    def get_company_financials(self, _org_number):
        return self.financials

    def get_company_roles(self, _org_number):
        return []

    def get_company_shareholders(self, _org_number):
        return []

    def get_person_holdings(self, _person_id):
        return []

    def get_company_grants(self, _org_number):
        return []

    def get_last_updated(self):
        return None

    def get_last_acquisition_receipt(self):
        return {"source": self.name}


def test_composite_stops_after_primary_discovery_and_uses_enrichment_fallback():
    company = Company(
        org_number="923609016",
        name="EQUINOR ASA",
        business_code="06.100",
        employee_count=21393,
        status="active",
        source="Brønnøysundregistrene",
    )
    primary = FakeConnector("Brønnøysundregistrene", rows=[company])
    enrichment = FakeConnector(
        "Firmafakta",
        rows=[company],
        financials={"revenue": 1_000_000, "currency": "NOK"},
    )
    connector = CompositeBusinessRegistryConnector([primary, enrichment])

    rows = connector.search_companies(business_code="06", min_employees=10)
    financials = connector.get_company_financials("923609016")

    assert rows == [company]
    assert primary.search_calls == 1
    assert enrichment.search_calls == 0
    assert financials == {"revenue": 1_000_000, "currency": "NOK"}
    assert connector.get_last_acquisition_receipt()["used_source"] == "Firmafakta"
