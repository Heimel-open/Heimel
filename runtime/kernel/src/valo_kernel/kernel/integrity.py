from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

from ..contracts.common import SCHEMA_VERSION, canonical_digest
from ..contracts.events import CanonicalEvent
from .errors import IntegrityError

GENESIS_HASH = "0" * 64


def digest_event_content(event: CanonicalEvent) -> str:
    """Deterministic digest over the event's own content. The event_hash field
    itself is excluded so sealing is well-defined."""
    data = event.model_dump(mode="json")
    data.pop("event_hash", None)
    return canonical_digest(data)


def seal_event(event: CanonicalEvent, sequence: int, previous_hash: str) -> CanonicalEvent:
    """Seal an event into the append-only chain: assigns sequence and
    previous_hash, then computes event_hash over the content."""
    content = event.model_dump(mode="json")
    content["sequence"] = sequence
    content["previous_hash"] = previous_hash
    content.pop("event_hash", None)
    return event.model_copy(
        update={
            "sequence": sequence,
            "previous_hash": previous_hash,
            "event_hash": canonical_digest(content),
        }
    )


def verify_event(event: CanonicalEvent) -> str:
    """Recompute and verify an event's hash. Raises IntegrityError on tamper."""
    if event.event_hash is None or event.sequence is None or event.previous_hash is None:
        raise IntegrityError("event is not sealed")
    expected = digest_event_content(event)
    if expected != event.event_hash:
        raise IntegrityError(
            f"event hash mismatch for {event.event_id}: expected {expected}, got {event.event_hash}"
        )
    return event.event_hash


def verify_chain(events: list[CanonicalEvent]) -> None:
    """Verify a full event chain. Raises IntegrityError on any break."""
    prev = GENESIS_HASH
    for event in events:
        verify_event(event)
        if event.previous_hash != prev:
            raise IntegrityError(
                f"chain break at {event.event_id}: expected previous {prev}, got {event.previous_hash}"
            )
        prev = event.event_hash


def state_root_digest(state: BaseModel) -> str:
    """Deterministic state root hash over a WorldState. Ordering is stable via
    canonical JSON (sorted keys)."""
    return canonical_digest(state.model_dump(mode="json"))


@dataclass(frozen=True)
class WorldSnapshot:
    world_snapshot_id: str
    tenant: str
    timestamp: str
    state_root_hash: str
    event_position: int
    schema_version: str = SCHEMA_VERSION


def make_snapshot(
    state: BaseModel,
    *,
    snapshot_id: str,
    tenant: str,
    timestamp: str,
    event_position: int,
) -> WorldSnapshot:
    return WorldSnapshot(
        world_snapshot_id=snapshot_id,
        tenant=tenant,
        timestamp=timestamp,
        state_root_hash=state_root_digest(state),
        event_position=event_position,
    )
