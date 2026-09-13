from unittest.mock import patch

from src.valo_platform.speider_connectors.allemannsdata_firmafakta import (
    AllemannsdataFirmafaktaConnector,
    _markdown_table_records,
)


RAW_SEARCH = """| Company | Org Number | Type of company |
|---|---|---|
| EQUINOR ASA | 923609016 | Allmennaksjeselskap - Utvinning av råolje |
| EQUINOR INSURANCE AS | 836771192 | Aksjeselskap - Skadeforsikring |
"""


def test_markdown_table_is_parsed_without_inventing_fields():
    records = _markdown_table_records(RAW_SEARCH)

    assert records == [
        {
            "name": "EQUINOR ASA",
            "org_number": "923609016",
            "company_type": "Allmennaksjeselskap - Utvinning av råolje",
        },
        {
            "name": "EQUINOR INSURANCE AS",
            "org_number": "836771192",
            "company_type": "Aksjeselskap - Skadeforsikring",
        },
    ]


def test_connector_normalizes_live_wrapped_markdown_search_result():
    with patch(
        "src.valo_platform.speider_connectors.allemannsdata_firmafakta.AllemannsdataHTTPClient"
    ) as client_class:
        client = client_class.return_value
        client.find_companies_by_name.return_value = {"result": RAW_SEARCH}

        companies = AllemannsdataFirmafaktaConnector().find_company_by_name("Equinor")

    assert [company.org_number for company in companies] == [
        "923609016",
        "836771192",
    ]
    assert companies[0].name == "EQUINOR ASA"
    assert companies[0].metadata["company_type"].startswith("Allmennaksjeselskap")
