from __future__ import annotations

from datetime import datetime

from services.organizational_simulation.composite_business_registry import (
    CompositeBusinessRegistryConnector,
)
from src.valo_platform.speider_connectors.models import Company


class FakeConnector:
    def __init__(self, name, companies, healthy=True):
        self.name = name
        self.companies = companies
        self.healthy = healthy

    def is_healthy(self): return self.healthy
    def get_connector_name(self): return self.name
    def get_last_updated(self): return datetime(2026, 7, 24)
    def get_last_acquisition_receipt(self): return {"source": self.name}
    def get_company(self, org):
        return next((c for c in self.companies if c.org_number == org), None)
    def find_company_by_name(self, _name): return self.companies
    def search_companies(self, **_kwargs): return self.companies
    def get_company_roles(self, _org): return []
    def get_company_financials(self, _org): return {}
    def get_company_shareholders(self, _org): return []
    def get_person_holdings(self, _person): return []
    def get_company_grants(self, _org): return []


def company(source, employees=None, code=None):
    return Company(
        org_number="923609016",
        name="EQUINOR ASA",
        business_code=code,
        business_description=None,
        municipality="STAVANGER" if source == "brreg" else None,
        county=None,
        employee_count=employees,
        status="active",
        source=source,
        metadata={"source_field": source},
    )


def test_reconciles_official_primary_and_enrichment_secondary():
    connector = CompositeBusinessRegistryConnector(
        [
            FakeConnector("brreg", [company("brreg", employees=21393, code="06.100")]),
            FakeConnector("firmafakta", [company("firmafakta")]),
        ]
    )
    rows = connector.find_company_by_name("Equinor")
    assert len(rows) == 1
    assert rows[0].employee_count == 21393
    assert rows[0].business_code == "06.100"
    assert rows[0].source == "brreg"
    assert rows[0].metadata["reconciled_sources"] == ["brreg", "firmafakta"]


def test_unavailable_source_does_not_stop_healthy_source():
    connector = CompositeBusinessRegistryConnector(
        [
            FakeConnector("offline", [], healthy=False),
            FakeConnector("brreg", [company("brreg", employees=10)]),
        ]
    )
    assert connector.is_healthy()
    assert connector.search_companies()[0].name == "EQUINOR ASA"
    assert any(item["state"] == "UNAVAILABLE" for item in connector.diagnostics)
