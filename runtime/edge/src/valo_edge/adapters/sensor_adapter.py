"""Sensor claim adapter for local sensors (cameras, thermal, pressure, vibration)."""

from datetime import datetime, timezone
import uuid
from typing import Any, Dict
from valo_edge.contracts import EdgeActionProposal


class SensorAdapter:
    """Adapts raw sensor telemetry into structured EdgeActionProposal objects."""

    def __init__(self, device_id: str) -> None:
        self.device_id = device_id

    def create_proposal(
        self,
        action_type: str,
        parameters: Dict[str, Any],
        timestamp_iso: str,
    ) -> EdgeActionProposal:
        proposal_id = f"prop-sensor-{uuid.uuid4().hex[:8]}"
        nonce = f"nonce-{uuid.uuid4().hex[:12]}"
        return EdgeActionProposal(
            proposal_id=proposal_id,
            device_id=self.device_id,
            action_type=action_type,
            parameters=parameters,
            timestamp_iso=timestamp_iso,
            nonce=nonce,
        )
