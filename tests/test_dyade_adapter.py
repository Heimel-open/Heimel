from __future__ import annotations

from datetime import datetime, timezone

from paios.dyade_adapter import DyadeAdapter
from paios.peripherals import EvidenceStage, admit_observation


class FakeDyade:
    def get_session(self, session_id: str):
        return {
            "session_id": session_id,
            "lineage": "lineage-123",
            "head": "head-456",
        }

    def list_events(self, session_id: str):
        return [
            {
                "event_id": "e1",
                "timestamp": "2026-09-07T07:00:00Z",
                "content": "first",
            },
            {
                "event_id": "e2",
                "timestamp": "2026-09-07T07:05:00Z",
                "content": "second",
            },
        ]


def test_dyade_adapter_is_read_only_window_into_external_continuation() -> None:
    adapter = DyadeAdapter(FakeDyade())
    snapshot = adapter.read_snapshot("research")

    assert snapshot.session_id == "research"
    assert snapshot.lineage == "lineage-123"
    assert snapshot.head == "head-456"
    assert len(snapshot.events) == 2


def test_dyade_snapshot_enters_as_raw_external_observation() -> None:
    adapter = DyadeAdapter(FakeDyade())
    snapshot = adapter.read_snapshot("research")

    observation = adapter.normalize_snapshot(
        subject_id="alpha-1",
        snapshot=snapshot,
        received_at=datetime(2026, 9, 7, 7, 10, tzinfo=timezone.utc),
    )

    assert observation.stage is EvidenceStage.RAW
    assert observation.modality == "external_continuation"
    assert observation.payload["session_id"] == "research"
    assert observation.payload["lineage"] == "lineage-123"
    assert observation.payload["head"] == "head-456"
    assert observation.provenance["source_kind"] == "external_continuation"
    assert observation.provenance["import_semantics"]["reading_is_not_memory"] is True
    assert observation.provenance["import_semantics"]["external_continuation_is_not_local_lineage"] is True
    assert observation.provenance["import_semantics"]["external_reasoning_is_not_identity"] is True


def test_dyade_observation_does_not_become_canonical_by_adapter_action() -> None:
    adapter = DyadeAdapter(FakeDyade())
    observation = adapter.normalize_snapshot(
        subject_id="alpha-1",
        snapshot=adapter.read_snapshot("research"),
        received_at=datetime(2026, 9, 7, 7, 10, tzinfo=timezone.utc),
    )

    result = admit_observation(observation)

    # No mandate/purpose: structurally admissible only with retained uncertainty.
    assert result.status.value == "AMBER"
    assert result.observation is observation
    assert result.admitted is False
