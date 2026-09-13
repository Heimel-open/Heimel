from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class Provider(str, Enum):
    SHOPIFY = "shopify"
    SAP = "sap"
    ADOBE = "adobe"


class TransportEvidence(str, Enum):
    UCP = "UCP"
    ACP = "ACP"
    AP2 = "AP2"


@dataclass(frozen=True)
class AdapterEnvelopeV1:
    tenant_id: str
    provider: Provider
    request: dict[str, Any]
    transport_evidence: tuple[TransportEvidence, ...] = ()

    @property
    def grants_authority(self) -> bool:
        return False


def require_reht_permit(permit: object | None) -> None:
    if permit is None or not bool(getattr(permit, "valid_at_execution", False)):
        raise PermissionError("adapter boundary requires valid reht permit")
