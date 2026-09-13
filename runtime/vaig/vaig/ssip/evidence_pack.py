"""Evidence pack model for SSIP forensic review."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class EvidencePack:
    """Minimal post-incident forensic review packet.

    This is a lightweight v0.1 data model. External auditor workflows,
    signatures and hard deadlines are policy-layer concerns.
    """

    incident_id: str
    evidence_core: str
    system_context: str
    hear_chain: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    packet_id: str = field(default_factory=lambda: f"pifr_{uuid4().hex}")
    external_analysis: str | None = None
    root_cause: str | None = None
    remediation: str | None = None
    closure_signature: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
