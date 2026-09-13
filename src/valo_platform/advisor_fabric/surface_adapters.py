"""OLAV and app surface adapters for Advisor Fabric.

These adapters translate surface data into validated Advisor context packages.
They do not call existing capture routes, dashboard routes or runtime code.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .context_gateway import (
    AdvisorConsentBasis,
    AdvisorContextGateway,
    AdvisorContextPackage,
    AdvisorContextRef,
    AdvisorContextScope,
)


class AdvisorSurfaceKind(str, Enum):
    """Work surfaces that can feed Advisor Fabric."""

    OLAV_CAPTURE = "olav_capture"
    DASHBOARD_ENTRY = "dashboard_entry"


class AdvisorSurfacePackage(BaseModel):
    """Validated surface package ready for Advisor Fabric services."""

    package_id: str
    role: str
    surface_kind: AdvisorSurfaceKind
    context_package: AdvisorContextPackage
    surface_summary: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(use_enum_values=False)


class OlavCaptureSurfaceInput(BaseModel):
    """Minimal OLAV capture input used by the adapter."""

    capture_id: str
    selected_text: str
    source: str
    url: Optional[str] = None
    page_title: Optional[str] = None
    app_name: Optional[str] = None
    user_intent: Optional[str] = None
    suggested_actions: List[str] = Field(default_factory=list)
    tenant: str = "default"
    consent_basis: AdvisorConsentBasis = AdvisorConsentBasis.CUSTOMER_CONSENT
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(use_enum_values=False)


class DashboardSurfaceInput(BaseModel):
    """Minimal dashboard entry input used by the adapter."""

    signal_id: str
    title: str
    decision: str
    authority_required: str
    total_exposure_usd: float
    advisor_consensus: str
    timestamp: Optional[str] = None
    tenant: str = "default"
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(use_enum_values=False)


class AdvisorSurfaceAdapter:
    """Convert OLAV and dashboard surfaces into Advisor context packages."""

    def __init__(self, gateway: Optional[AdvisorContextGateway] = None):
        self._gateway = gateway or AdvisorContextGateway()

    def from_olav_capture(
        self,
        *,
        package_id: str,
        role: str,
        capture: OlavCaptureSurfaceInput,
    ) -> AdvisorSurfacePackage:
        if not capture.selected_text.strip():
            raise ValueError("OLAV capture text cannot be empty")

        context_package = self._gateway.build_package(
            package_id=package_id,
            role=role,
            context_refs=[
                AdvisorContextRef(
                    ref_id=f"{capture.capture_id}:surface",
                    source_type="olav_surface_context",
                    scope=AdvisorContextScope.TENANT,
                    consent_basis=capture.consent_basis,
                    source_ref=capture.capture_id,
                    evidence_refs=[capture.capture_id],
                    metadata={
                        "source": capture.source,
                        "url": capture.url,
                        "page_title": capture.page_title,
                        "app_name": capture.app_name,
                        "user_intent": capture.user_intent,
                    },
                )
            ],
            limitations=capture.suggested_actions,
        )

        return AdvisorSurfacePackage(
            package_id=package_id,
            role=role,
            surface_kind=AdvisorSurfaceKind.OLAV_CAPTURE,
            context_package=context_package,
            surface_summary={
                "capture_id": capture.capture_id,
                "source": capture.source,
                "url": capture.url,
                "page_title": capture.page_title,
                "app_name": capture.app_name,
                "selected_text_excerpt": capture.selected_text[:280],
                "user_intent": capture.user_intent,
                "suggested_actions": list(capture.suggested_actions),
            },
        )

    def from_dashboard_entry(
        self,
        *,
        package_id: str,
        role: str,
        entry: DashboardSurfaceInput,
    ) -> AdvisorSurfacePackage:
        context_package = self._gateway.build_package(
            package_id=package_id,
            role=role,
            context_refs=[
                AdvisorContextRef(
                    ref_id=f"{entry.signal_id}:dashboard",
                    source_type="enterprise_context",
                    scope=AdvisorContextScope.TENANT,
                    consent_basis=AdvisorConsentBasis.INTERNAL_OPERATIONAL,
                    source_ref=entry.signal_id,
                    evidence_refs=[entry.signal_id],
                    metadata={
                        "title": entry.title,
                        "decision": entry.decision,
                        "authority_required": entry.authority_required,
                        "total_exposure_usd": entry.total_exposure_usd,
                        "advisor_consensus": entry.advisor_consensus,
                        "timestamp": entry.timestamp,
                    },
                )
            ],
        )

        return AdvisorSurfacePackage(
            package_id=package_id,
            role=role,
            surface_kind=AdvisorSurfaceKind.DASHBOARD_ENTRY,
            context_package=context_package,
            surface_summary={
                "signal_id": entry.signal_id,
                "title": entry.title,
                "decision": entry.decision,
                "authority_required": entry.authority_required,
                "total_exposure_usd": entry.total_exposure_usd,
                "advisor_consensus": entry.advisor_consensus,
            },
        )
