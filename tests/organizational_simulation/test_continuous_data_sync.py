from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path

from services.organizational_simulation.aiid_public_source import AIIDPublicSource
from services.organizational_simulation.continuous_data_sync import (
    AIIDGraphQLClient,
    IncrementalSpeiderCollector,
    classify_incident,
    sync_aiid,
)
from src.valo_platform.speider_connectors.models import Company


class FakeConnector:
    connector_name = "fake-firmafakta"

    def is_healthy(self):
        return True

    def get_connector_name(self):
        return self.connector_name

    def search_companies(
        self, *, business_code=None, min_employees=None, **_kwargs
    ):
        prefix = str(business_code)
        return [
            Company(
                org_number=f"9{prefix.zfill(2)}000001",
                name=f"Company {prefix}",
                business_code=f"{prefix}.100",
                business_description="Observed company",
                municipality="STAVANGER",
                county="ROGALAND",
                employee_count=max(20, min_employees or 0),
                status="active",
                source=self.connector_name,
            )
        ]

    def get_company_financials(self, _org_number):
        return {
            "revenue": 100_000_000,
            "currency": "NOK",
            "fiscal_year": 2025,
        }

    def get_company_roles(self, _org_number):
        return []

    def get_last_acquisition_receipt(self):
        return {"source": self.connector_name, "digest": "sha256:test"}


class FakeAIIDClient(AIIDGraphQLClient):
    def fetch(self):
        return (
            [
                {
                    "id": 5001,
                    "title": "Hospital diagnosis system harmed patients",
                    "date": "2026-07-01",
                    "summary": "A medical AI produced unsafe recommendations.",
                    "url": "https://incidentdatabase.ai/cite/5001",
                }
            ],
            "query { incidents { incident_id title date description } }",
        )


def test_classifier_marks_direct_vertical_and_risk():
    verticals, risks = classify_incident(
        "Hospital diagnosis system harmed patients",
        "A medical AI produced unsafe recommendations",
    )
    assert "healthcare_social_care" in verticals
    assert "safety" in risks


def test_incremental_collector_rotates_and_persists(tmp_path: Path):
    collector = IncrementalSpeiderCollector(
        FakeConnector(),
        state_path=tmp_path / "state.json",
        company_index_path=tmp_path / "companies.json",
        page_status_path=tmp_path / "status.json",
    )

    first = collector.run(verticals_per_run=2, max_companies_per_vertical=1)
    second = collector.run(verticals_per_run=2, max_companies_per_vertical=1)

    assert first["company_count"] == 2
    assert second["company_count"] == 4
    assert first["last_run"]["verticals"] != second["last_run"]["verticals"]
    assert second["receipt"]["payload_digest"].startswith("sha256:")


def test_aiid_sync_preserves_curated_mapping_and_adds_live_record(
    tmp_path: Path,
):
    incidents_path = tmp_path / "incidents.json"
    incidents_path.write_text(
        '[{"id":101,"title":"Curated","date":"2020-01-01",'
        '"summary":"x","url":"https://incidentdatabase.ai/cite/101",'
        '"directVerticals":["public_administration_defence"],'
        '"riskTags":["bias"]}]',
        encoding="utf-8",
    )
    status = sync_aiid(
        client=FakeAIIDClient(),
        page_incidents_path=incidents_path,
        aiid_index_path=tmp_path / "aiid-index.json",
        page_status_path=tmp_path / "status.json",
    )

    payload = json.loads(incidents_path.read_text(encoding="utf-8"))
    by_id = {str(item["id"]): item for item in payload}
    assert by_id["101"]["directVerticals"] == [
        "public_administration_defence"
    ]
    assert by_id["5001"]["directVerticals"] == [
        "healthcare_social_care"
    ]
    assert status["full_record_count"] == 2


def test_aiid_snapshot_archive_is_normalized(tmp_path: Path):
    archive_path = tmp_path / "backup.tar.bz2"
    records = [
        {
            "incident_id": {"$numberInt": "8123"},
            "title": "Automated hospital recommendation caused harm",
            "date_published": "2026-07-10T00:00:00Z",
            "description": "A medical AI generated an unsafe patient recommendation.",
        }
    ]
    payload = json.dumps(records).encode("utf-8")
    info = tarfile.TarInfo("aiid/reports.json")
    info.size = len(payload)
    with tarfile.open(archive_path, mode="w:bz2") as bundle:
        bundle.addfile(info, io.BytesIO(payload))

    normalized = AIIDPublicSource._read_snapshot_archive(str(archive_path))

    assert normalized == [
        {
            "id": 8123,
            "title": "Automated hospital recommendation caused harm",
            "date": "2026-07-10",
            "summary": "A medical AI generated an unsafe patient recommendation.",
            "url": "https://incidentdatabase.ai/cite/8123",
        }
    ]
