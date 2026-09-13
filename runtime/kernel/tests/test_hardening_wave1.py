from __future__ import annotations

import pytest

from valo_kernel import IntegrityError, KernelEngine, replay
from valo_kernel.contracts import (
    CanonicalEvent,
    Entity,
    EntityType,
    EventType,
    Provenance,
    utcnow,
)


def _entity_event(entity_id: str = "entity-1") -> CanonicalEvent:
    now = utcnow()
    return CanonicalEvent(
        event_id=f"event-{entity_id}",
        event_type=EventType.ENTITY_REGISTERED,
        tenant_id="tenant-a",
        subject=entity_id,
        source="hardening-test",
        timestamp=now,
        effective_at=now,
        payload={
            "entity": Entity(
                entity_id=entity_id,
                entity_type=EntityType.PERSON,
                tenant_id="tenant-a",
                provenance=Provenance(
                    source_type="system",
                    source_id=entity_id,
                    source_system="hardening-test",
                ),
            )
        },
    )


def test_replay_rejects_tampered_event_before_reducing_it() -> None:
    engine = KernelEngine("tenant-a")
    engine.append(_entity_event())
    sealed = engine.events()[0]
    tampered = sealed.model_copy(
        update={
            "payload": {
                "entity": Entity(
                    entity_id="attacker-controlled",
                    entity_type=EntityType.PERSON,
                    tenant_id="tenant-a",
                    provenance=Provenance(
                        source_type="system",
                        source_id="attacker-controlled",
                        source_system="hardening-test",
                    ),
                )
            }
        }
    )

    with pytest.raises(IntegrityError):
        replay([tampered])
