"""Speider business-registry connector for Allemannsdata Firmafakta MCP.

The connector maps the provider's Norwegian tool/result vocabulary into VALO's
normalized Speider models. Retrieval remains evidence-only: it does not infer
missing company facts or turn source output into authority.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional

from .allemannsdata_http_client import AllemannsdataHTTPClient
from .business_registry import BusinessRegistryConnector
from .models import Company, Role, RoleType, Shareholder

logger = logging.getLogger(__name__)


FIRMAFAKTA_REQUIRED_TOOLS = {
    "organisasjonsnummer_for_selskap",
    "selskapsdetaljer",
    "aksjeeiere_for_selskap",
    "roller_i_enhet",
    "finn_selskaper",
    "get_company_last_financial_statement",
}


def _first(payload: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        if name in payload and payload[name] not in (None, ""):
            return payload[name]
    return None


def _normalize_header(value: str) -> str:
    normalized = value.strip().lower()
    normalized = (
        normalized.replace("æ", "ae")
        .replace("ø", "o")
        .replace("å", "a")
    )
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
    aliases = {
        "company": "name",
        "company_name": "name",
        "selskap": "name",
        "navn": "name",
        "org_number": "org_number",
        "organisation_number": "org_number",
        "organization_number": "org_number",
        "organisasjonsnummer": "org_number",
        "org_nr": "org_number",
        "type_of_company": "company_type",
        "company_type": "company_type",
        "selskapsform": "company_type",
    }
    return aliases.get(normalized, normalized)


def _markdown_table_records(text: str) -> List[Dict[str, Any]]:
    """Parse provider markdown tables into normalized records.

    Firmafakta wraps several read-only results as a markdown table inside the
    MCP ``structuredContent.result`` field. This parser consumes only explicit
    table cells; it never infers missing values.
    """

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    table_lines = [
        line for line in lines if line.startswith("|") and line.endswith("|")
    ]
    if len(table_lines) < 2:
        return []

    def cells(line: str) -> List[str]:
        return [cell.strip() for cell in line.strip("|").split("|")]

    headers = [_normalize_header(item) for item in cells(table_lines[0])]
    separator = cells(table_lines[1])
    if not separator or not all(
        re.fullmatch(r":?-{3,}:?", item.replace(" ", "")) for item in separator
    ):
        return []

    rows: List[Dict[str, Any]] = []
    for line in table_lines[2:]:
        values = cells(line)
        if len(values) != len(headers):
            continue
        rows.append({header: value for header, value in zip(headers, values)})
    return rows


def _mapping(payload: Any, *container_names: str) -> Dict[str, Any]:
    if isinstance(payload, str):
        records = _markdown_table_records(payload)
        if len(records) == 1:
            return records[0]
        if records and set(records[0]).issuperset({"field", "value"}):
            return {
                str(row["field"]): row["value"]
                for row in records
                if row.get("field") not in (None, "")
            }
        return {}
    if isinstance(payload, Mapping):
        for name in container_names:
            nested = payload.get(name)
            if isinstance(nested, Mapping):
                return dict(nested)
            if isinstance(nested, str):
                parsed = _mapping(nested)
                if parsed:
                    return parsed
        return dict(payload)
    if isinstance(payload, list) and len(payload) == 1:
        if isinstance(payload[0], Mapping):
            return dict(payload[0])
        if isinstance(payload[0], str):
            return _mapping(payload[0])
    return {}


def _records(payload: Any, *container_names: str) -> List[Dict[str, Any]]:
    if isinstance(payload, str):
        return _markdown_table_records(payload)
    if isinstance(payload, list):
        records: List[Dict[str, Any]] = []
        for item in payload:
            if isinstance(item, Mapping):
                records.append(dict(item))
            elif isinstance(item, str):
                records.extend(_markdown_table_records(item))
        return records
    if isinstance(payload, Mapping):
        for name in container_names:
            nested = payload.get(name)
            if isinstance(nested, list):
                return _records(nested)
            if isinstance(nested, Mapping):
                return [dict(nested)]
            if isinstance(nested, str):
                return _markdown_table_records(nested)
        return [dict(payload)]
    return []


def _as_int(value: Any) -> Optional[int]:
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        return int(float(str(value).replace(" ", "").replace(",", ".")))
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> Optional[float]:
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        return float(str(value).replace(" ", "").replace(",", "."))
    except (TypeError, ValueError):
        return None


def _year(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    text = str(value)
    for token in text.replace("/", "-").split("-"):
        if len(token) == 4 and token.isdigit():
            return int(token)
    return _as_int(value)


def _code_and_description(
    payload: Mapping[str, Any],
) -> tuple[Optional[str], Optional[str]]:
    candidate = _first(
        payload,
        "business_code",
        "naeringskode",
        "næringskode",
        "naeringskode1",
        "næringskode1",
        "naeringskode_1",
        "næringskode_1",
    )
    description = _first(
        payload,
        "business_description",
        "naeringsbeskrivelse",
        "næringsbeskrivelse",
        "beskrivelse",
    )
    if isinstance(candidate, Mapping):
        description = description or _first(
            candidate, "beskrivelse", "description", "navn"
        )
        candidate = _first(candidate, "kode", "code", "id")
    if isinstance(candidate, list) and candidate:
        item = candidate[0]
        if isinstance(item, Mapping):
            description = description or _first(
                item, "beskrivelse", "description", "navn"
            )
            candidate = _first(item, "kode", "code", "id")
        else:
            candidate = item
    return (
        str(candidate) if candidate not in (None, "") else None,
        str(description) if description not in (None, "") else None,
    )


def _address_field(payload: Mapping[str, Any], field: str) -> Any:
    direct = _first(payload, field)
    if direct is not None:
        return direct
    for name in ("forretningsadresse", "business_address", "adresse", "address"):
        nested = payload.get(name)
        if isinstance(nested, Mapping):
            value = _first(nested, field)
            if value is not None:
                return value
    return None


def _acquisition_metadata(
    client: AllemannsdataHTTPClient,
    provider_tool: str,
) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {"provider_tool": provider_tool}
    receipt = client.get_last_acquisition_receipt()
    if isinstance(receipt, Mapping):
        metadata["acquisition_receipt"] = dict(receipt)
    return metadata


def _role_type(value: Any) -> RoleType:
    text = str(value or "").strip().lower()
    normalized = (
        text.replace("æ", "ae")
        .replace("ø", "o")
        .replace("å", "a")
        .replace("_", " ")
    )
    if any(token in normalized for token in ("daglig leder", "ceo", "dagl")):
        return RoleType.CEO
    if any(
        token in normalized
        for token in ("styreleder", "board chair", "leder av styret")
    ):
        return RoleType.BOARD_CHAIR
    if any(
        token in normalized
        for token in ("styremedlem", "board member", "varamedlem")
    ):
        return RoleType.BOARD_MEMBER
    if "revisor" in normalized or "auditor" in normalized:
        return RoleType.AUDITOR
    if "regnskap" in normalized or "accountant" in normalized:
        return RoleType.ACCOUNTANT
    if "eier" in normalized or "owner" in normalized:
        return RoleType.OWNER
    if "direktor" in normalized or "director" in normalized:
        return RoleType.DIRECTOR
    try:
        return RoleType(text)
    except ValueError:
        return RoleType.BOARD_MEMBER


class AllemannsdataFirmafaktaConnector(BusinessRegistryConnector):
    """BusinessRegistryConnector backed by Firmafakta's 18-tool MCP server."""

    def __init__(
        self,
        mcp_endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        self.connector_name = "Firmafakta"
        self.last_update = datetime.now(timezone.utc).replace(tzinfo=None)
        self._http_client = AllemannsdataHTTPClient(
            base_url=mcp_endpoint,
            api_key=api_key,
        )

    def _touch(self) -> None:
        self.last_update = datetime.now(timezone.utc).replace(tzinfo=None)

    def get_company(self, org_number: str) -> Optional[Company]:
        try:
            raw = self._http_client.get_company(org_number)
            data = _mapping(raw, "selskap", "company", "enhet", "result")
            if not data:
                return None
            business_code, business_description = _code_and_description(data)
            observed_org_number = _first(
                data, "org_number", "org_nr", "orgnr", "organisasjonsnummer"
            )
            name = _first(data, "name", "navn", "organisasjonsnavn")
            if not name:
                return None
            company = Company(
                org_number=str(observed_org_number or org_number),
                name=str(name),
                short_name=_first(data, "short_name", "kortnavn"),
                business_code=business_code,
                business_description=business_description,
                municipality=_address_field(data, "kommune")
                or _first(data, "municipality"),
                county=_address_field(data, "fylke") or _first(data, "county"),
                founded_year=_year(
                    _first(
                        data,
                        "founded_year",
                        "stiftelsesdato",
                        "registreringsdato",
                    )
                ),
                employee_count=_as_int(
                    _first(
                        data,
                        "employee_count",
                        "antall_ansatte",
                        "antallAnsatte",
                        "ansatte",
                    )
                ),
                status=str(
                    _first(data, "status", "organisasjonsstatus") or "active"
                ),
                source=self.connector_name,
                last_updated=datetime.now(timezone.utc).replace(tzinfo=None),
                metadata=_acquisition_metadata(
                    self._http_client, "selskapsdetaljer"
                ),
            )
            self._touch()
            return company
        except Exception as exc:
            logger.error("Error fetching company %s: %s", org_number, exc)
            return None

    def find_company_by_name(self, name: str) -> List[Company]:
        try:
            raw = self._http_client.find_companies_by_name(name)
            records = _records(
                raw,
                "companies",
                "selskaper",
                "resultater",
                "results",
                "result",
            )
            companies: List[Company] = []
            for data in records:
                org_number = _first(
                    data, "org_number", "org_nr", "orgnr", "organisasjonsnummer"
                )
                company_name = (
                    _first(data, "name", "navn", "organisasjonsnavn") or name
                )
                if not org_number:
                    continue
                business_code, business_description = _code_and_description(data)
                companies.append(
                    Company(
                        org_number=str(org_number),
                        name=str(company_name),
                        business_code=business_code,
                        business_description=business_description,
                        employee_count=_as_int(
                            _first(
                                data,
                                "employee_count",
                                "antall_ansatte",
                                "antallAnsatte",
                            )
                        ),
                        source=self.connector_name,
                        last_updated=datetime.now(timezone.utc).replace(tzinfo=None),
                        metadata={
                            "provider_tool": "organisasjonsnummer_for_selskap",
                            "company_type": _first(
                                data, "company_type", "type_of_company"
                            ),
                        },
                    )
                )
            self._touch()
            return companies
        except Exception as exc:
            logger.error("Error searching for company by name %r: %s", name, exc)
            return []

    def get_company_shareholders(self, org_number: str) -> List[Shareholder]:
        try:
            raw = self._http_client.get_company_shareholders(org_number)
            records = _records(
                raw,
                "shareholders",
                "aksjeeiere",
                "eiere",
                "results",
                "result",
            )
            shareholders: List[Shareholder] = []
            for index, data in enumerate(records):
                holder_name = _first(
                    data,
                    "shareholder_name",
                    "navn",
                    "aksjeeier",
                    "eiernavn",
                    "name",
                )
                if not holder_name:
                    continue
                holder_id = _first(
                    data,
                    "shareholder_id",
                    "id",
                    "aksjeeier_id",
                    "organisasjonsnummer",
                    "fodselsaar",
                )
                holder_type = _first(
                    data,
                    "shareholder_type",
                    "type",
                    "eiertype",
                    "aksjeeiertype",
                )
                shareholders.append(
                    Shareholder(
                        shareholder_id=str(holder_id or f"{org_number}:{index}"),
                        shareholder_name=str(holder_name),
                        shareholder_type=str(holder_type or "unknown").lower(),
                        ownership_percentage=_as_float(
                            _first(
                                data,
                                "ownership_percentage",
                                "eierandel",
                                "andel_prosent",
                            )
                        ),
                        share_count=_as_int(
                            _first(data, "share_count", "antall_aksjer", "aksjer")
                        ),
                        org_number=org_number,
                        source=self.connector_name,
                        metadata={"provider_tool": "aksjeeiere_for_selskap"},
                    )
                )
            self._touch()
            return shareholders
        except Exception as exc:
            logger.error("Error fetching shareholders for %s: %s", org_number, exc)
            return []

    def get_company_roles(self, org_number: str) -> List[Role]:
        try:
            raw = self._http_client.get_company_roles(org_number)
            records = _records(raw, "roles", "roller", "results", "result")
            roles: List[Role] = []
            for index, data in enumerate(records):
                person = (
                    data.get("person")
                    if isinstance(data.get("person"), Mapping)
                    else {}
                )
                person_name = _first(
                    data,
                    "person_name",
                    "navn",
                    "personnavn",
                    "fullt_navn",
                    "name",
                ) or _first(person, "navn", "name")
                if not person_name:
                    continue
                raw_role = _first(
                    data,
                    "role_type",
                    "rolle",
                    "type",
                    "rollebeskrivelse",
                    "kode",
                )
                role_id = _first(data, "role_id", "id", "rolle_id")
                person_id = _first(
                    data, "person_id", "personidentifikator"
                ) or _first(person, "id", "person_id")
                roles.append(
                    Role(
                        role_id=str(role_id or f"{org_number}:{index}"),
                        person_name=str(person_name),
                        person_id=str(person_id) if person_id else None,
                        role_type=_role_type(raw_role),
                        org_number=org_number,
                        start_date=_first(
                            data, "start_date", "fra_dato", "fradato"
                        ),
                        end_date=_first(
                            data, "end_date", "til_dato", "tildato"
                        ),
                        source=self.connector_name,
                        metadata={
                            "provider_tool": "roller_i_enhet",
                            "provider_role": raw_role,
                        },
                    )
                )
            self._touch()
            return roles
        except Exception as exc:
            logger.error("Error fetching roles for %s: %s", org_number, exc)
            return []

    def get_person_holdings(self, person_id: str) -> List[Dict[str, Any]]:
        try:
            raw = self._http_client.get_person_holdings(person_id)
            records = _records(
                raw, "holdings", "aksjeposter", "results", "result"
            )
            return [
                {
                    "org_number": _first(
                        data, "org_number", "org_nr", "organisasjonsnummer"
                    ),
                    "company_name": _first(
                        data, "company_name", "selskap", "navn", "name"
                    ),
                    "ownership_percentage": _as_float(
                        _first(
                            data,
                            "ownership_percentage",
                            "eierandel",
                            "andel_prosent",
                        )
                    ),
                    "source": self.connector_name,
                }
                for data in records
            ]
        except Exception as exc:
            logger.error("Error fetching holdings for person %s: %s", person_id, exc)
            return []

    def get_company_financials(self, org_number: str) -> Dict[str, Any]:
        try:
            raw = self._http_client.get_company_financials(org_number)
            data = _mapping(
                raw,
                "financial_statement",
                "regnskap",
                "aarsregnskap",
                "årsregnskap",
                "open",
                "result",
            )
            if not data:
                return {}
            normalized = {
                "org_number": org_number,
                "fiscal_year": _year(
                    _first(
                        data,
                        "fiscal_year",
                        "year",
                        "regnskapsaar",
                        "regnskapsår",
                    )
                ),
                "revenue": _as_float(
                    _first(
                        data,
                        "revenue",
                        "operating_revenue",
                        "turnover",
                        "driftsinntekter",
                        "sum_driftsinntekter",
                    )
                ),
                "operating_profit": _as_float(
                    _first(data, "operating_profit", "driftsresultat")
                ),
                "equity": _as_float(_first(data, "equity", "egenkapital")),
                "assets": _as_float(
                    _first(data, "assets", "sum_eiendeler", "eiendeler")
                ),
                "liabilities": _as_float(
                    _first(data, "liabilities", "gjeld")
                ),
                "currency": str(
                    _first(data, "currency", "valuta") or "NOK"
                ).upper(),
                "source": self.connector_name,
                "provider_tool": "get_company_last_financial_statement",
            }
            self._touch()
            return normalized
        except Exception as exc:
            logger.error("Error fetching financials for %s: %s", org_number, exc)
            return {}

    def get_company_grants(self, org_number: str) -> List[Dict[str, Any]]:
        tools = (
            "tildelinger_for_selskap",
            "eu_tildelinger_for_selskap",
            "forskningsradet_tildelinger_for_selskap",
            "skattefunnprosjekter_for_selskap",
        )
        results: List[Dict[str, Any]] = []
        for tool_name in tools:
            try:
                args = self._http_client.resolve_arguments(
                    "firmafakta",
                    tool_name,
                    {"org_number": org_number},
                    {
                        "org_number": (
                            "org_nr",
                            "organisasjonsnummer",
                            "orgnr",
                        )
                    },
                )
                raw = self._http_client.call_tool(
                    "firmafakta", tool_name, args
                )
                for record in _records(
                    raw,
                    "grants",
                    "tildelinger",
                    "prosjekter",
                    "results",
                    "result",
                ):
                    record.setdefault("provider_tool", tool_name)
                    record.setdefault("source", self.connector_name)
                    results.append(record)
            except Exception as exc:
                logger.debug("Firmafakta tool %s unavailable: %s", tool_name, exc)
        if results:
            self._touch()
        return results

    def search_companies(
        self,
        location: Optional[str] = None,
        business_code: Optional[str] = None,
        min_employees: Optional[int] = None,
        max_employees: Optional[int] = None,
    ) -> List[Company]:
        try:
            raw = self._http_client.search_companies(
                location=location,
                business_code=business_code,
                min_employees=min_employees,
                max_employees=max_employees,
            )
            records = _records(
                raw,
                "companies",
                "selskaper",
                "results",
                "resultater",
                "result",
            )
            companies: List[Company] = []
            for data in records:
                org_number = _first(
                    data, "org_number", "org_nr", "orgnr", "organisasjonsnummer"
                )
                name = _first(data, "name", "navn", "organisasjonsnavn")
                if not org_number or not name:
                    continue
                code, description = _code_and_description(data)
                companies.append(
                    Company(
                        org_number=str(org_number),
                        name=str(name),
                        business_code=code,
                        business_description=description,
                        municipality=_address_field(data, "kommune") or location,
                        county=_address_field(data, "fylke"),
                        employee_count=_as_int(
                            _first(
                                data,
                                "employee_count",
                                "antall_ansatte",
                                "antallAnsatte",
                            )
                        ),
                        status=str(
                            _first(data, "status", "organisasjonsstatus")
                            or "active"
                        ),
                        source=self.connector_name,
                        last_updated=datetime.now(timezone.utc).replace(tzinfo=None),
                        metadata={"provider_tool": "finn_selskaper"},
                    )
                )
            self._touch()
            return companies
        except Exception as exc:
            logger.error("Error searching companies: %s", exc)
            return []

    def get_connector_name(self) -> str:
        return self.connector_name

    def is_healthy(self) -> bool:
        try:
            tools = self._http_client.list_tools("firmafakta")
            names = {
                str(tool.get("name"))
                for tool in tools
                if isinstance(tool, Mapping) and tool.get("name")
            }
            return FIRMAFAKTA_REQUIRED_TOOLS.issubset(names)
        except Exception as exc:
            logger.error("Firmafakta health check failed: %s", exc)
            return False

    def get_last_updated(self) -> Optional[datetime]:
        return self.last_update

    def get_last_acquisition_receipt(self) -> Optional[Dict[str, Any]]:
        return self._http_client.get_last_acquisition_receipt()


__all__ = [
    "AllemannsdataFirmafaktaConnector",
    "FIRMAFAKTA_REQUIRED_TOOLS",
]
