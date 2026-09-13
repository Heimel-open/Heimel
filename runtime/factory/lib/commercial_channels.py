"""Provider-neutral channel events for the autonomous commercial loop.

Inbound web/email/SMS/voice events are observations. Outbound channel actions
remain governed egress. This module normalizes evidence only; it never infers
customer acceptance or permission to contact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CommercialChannel(str, Enum):
    WEB = "web"
    EMAIL = "email"
    SMS = "sms"
    PHONE = "phone"
    LINKEDIN = "linkedin"
    API = "api"
    OTHER = "other"


class ChannelDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


@dataclass(frozen=True)
class CommercialChannelEvent:
    event_ref: str
    direction: ChannelDirection
    channel: CommercialChannel
    counterparty_ref: str
    provider_ref: str
    payload_digest: str
    endpoint_ref: str | None = None
    received_or_sent_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        for name in ("event_ref", "counterparty_ref", "provider_ref", "payload_digest"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} is required")

    @property
    def is_observation_only(self) -> bool:
        return self.direction is ChannelDirection.INBOUND

    @property
    def grants_authority(self) -> bool:
        return False


__all__ = [
    "ChannelDirection",
    "CommercialChannel",
    "CommercialChannelEvent",
]
