from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ServiceDefinition:
    service_id: str
    name: str
    category: str
    scope: list[str] = field(default_factory=list)
    required_credentials: list[str] = field(default_factory=list)
    required_resources: list[str] = field(default_factory=list)
    estimated_duration_minutes: int = 0
    pricing_rule_ref: str | None = None
    evidence_requirements: list[str] = field(default_factory=list)
    completion_requirements: list[str] = field(default_factory=list)
    risk_class: str = "R2_OPERATIONAL"


EV_CHARGER_INSTALLATION = ServiceDefinition(
    service_id="EV_CHARGER_INSTALLATION",
    name="EV Charger Installation",
    category="ELECTRICAL",
    scope=["home_ev_charger", "garage_site", "single_phase", "three_phase"],
    required_credentials=["electrician_authorization", "ev_installation_competence"],
    required_resources=["electrician", "charger", "cable", "breaker", "mounting_components"],
    estimated_duration_minutes=240,
    pricing_rule_ref="rule.ev_charger_installation.v1",
    evidence_requirements=["installation_completed", "checklist_complete", "site_relation_verified"],
    completion_requirements=["worker_credential_confirmed", "checklist_complete", "evidence_attached", "customer_site_relation_verified"],
    risk_class="R2_OPERATIONAL",
)


def classify_service(service_request: dict[str, Any]) -> str:
    """Deterministic classification of a service request against the catalog."""
    text = " ".join(str(service_request.get(k, "")).lower() for k in ("description", "service_type", "details"))
    if any(tok in text for tok in ("lader", "charger", "ev charger", "elbillader", "hjemmelader")):
        return EV_CHARGER_INSTALLATION.service_id
    return "UNKNOWN"


def service_definition(service_id: str) -> ServiceDefinition | None:
    if service_id == EV_CHARGER_INSTALLATION.service_id:
        return EV_CHARGER_INSTALLATION
    return None
