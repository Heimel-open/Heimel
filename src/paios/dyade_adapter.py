"""Read-only Dyade adapter for relAIon.

Dyade is an external continuity/context window, never the relAIon individual.
Imported Dyade material enters relAIon as RAW observation evidence with explicit
provenance. Reading is not memory; external continuation is not local lineage.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol, Sequence
from uuid import uuid4

from paios.peripherals import ObservationEnvelope, SourceRef


class DyadeReadClient(Protocol):
    """Minimal read-only contract expected from a Dyade continuation source."""

    def get_session(self, session_id: str) -> Mapping[str, Any]:
        ...

    def list_events(self, session_id: str) -> Sequence[Mapping[str, Any]]:
        ...


@dataclass(frozen=True)
class DyadeSnapshot:
    session_id: str
    lineage: str | None
    head: str | None
    events: tuple[Mapping[str, Any], ...]


class DyadeAdapter:
    """Normalize Dyade continuation state into relAIon observation envelopes."""

    adapter_name = "dyade_readonly_v1"

    def __init__(self, client: DyadeReadClient, *, provider: str = "dyade") -> None:
        self._client = client
        self._provider = provider

    def read_snapshot(self, session_id: str) -> DyadeSnapshot:
        session = self._client.get_session(session_id)
        events = tuple(self._client.list_events(session_id))
        return DyadeSnapshot(
            session_id=session_id,
            lineage=_optional_str(session.get("lineage")),
            head=_optional_str(session.get("head")),
            events=events,
        )

    def normalize_snapshot(
        self,
        *,
        subject_id: str,
        snapshot: DyadeSnapshot,
        purpose: str | None = None,
        mandate_id: str | None = None,
        received_at: datetime | None = None,
    ) -> ObservationEnvelope:
        now = received_at or datetime.now(timezone.utc)
        observed_at = _latest_event_time(snapshot.events) or now

        payload = {
            "session_id": snapshot.session_id,
            "lineage": snapshot.lineage,
            "head": snapshot.head,
            "events": [dict(event) for event in snapshot.events],
        }
        provenance = {
            "source_kind": "external_continuation",
            "provider": self._provider,
            "adapter": self.adapter_name,
            "session_id": snapshot.session_id,
            "lineage": snapshot.lineage,
            "head": snapshot.head,
            "import_semantics": {
                "reading_is_not_memory": True,
                "external_continuation_is_not_local_lineage": True,
                "external_reasoning_is_not_identity": True,
                "requires_local_admission_before_state_change": True,
            },
        }

        return ObservationEnvelope(
            observation_id=f"dyade:{snapshot.session_id}:{uuid4().hex}",
            subject_id=subject_id,
            observed_at=observed_at,
            received_at=now,
            modality="external_continuation",
            source=SourceRef(provider=self._provider, adapter=self.adapter_name),
            payload=payload,
            provenance=provenance,
            mandate_id=mandate_id,
            purpose=purpose,
        )


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _latest_event_time(events: Sequence[Mapping[str, Any]]) -> datetime | None:
    latest: datetime | None = None
    for event in events:
        raw = event.get("timestamp") or event.get("created_at") or event.get("time")
        parsed = _parse_time(raw)
        if parsed is not None and (latest is None or parsed > latest):
            latest = parsed
    return latest


def _parse_time(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
