import sqlite3

import pytest

from valo_edge.lastseen import LastSeenService, MemoryScope


def test_remember_find_and_forget(tmp_path):
    db_path = tmp_path / "lastseen.db"

    with LastSeenService(db_path) as service:
        stored = service.remember(
            "keys",
            "kitchen counter",
            image_ref="crops/keys.jpg",
            confidence=0.98,
            observed_at_iso="2026-08-04T08:42:00Z",
        )

        assert stored.location == "kitchen counter"
        assert stored.source_id.startswith("obs-")
        assert stored.policy_version == "lastseen-policy-v1"
        assert len(stored.receipt_digest) == 64
        assert service.count() == 1
        assert service.count_index_entries() == 1

        found = service.find("nøkler", aliases=["keys"])
        assert found is not None
        assert found.object_name == "keys"
        assert found.location == "kitchen counter"
        assert found.image_ref == "crops/keys.jpg"
        assert found.source_id == stored.source_id
        assert found.source_receipt_digest == stored.receipt_digest
        assert len(found.receipt_digest) == 64

        assert service.forget("keys") == 1
        assert service.find("keys") is None
        assert service.count() == 0
        assert service.count_index_entries() == 0


def test_newest_observation_wins_and_temporal_history_is_scoped(tmp_path):
    with LastSeenService(tmp_path / "lastseen.db") as service:
        first = service.remember(
            "glasses",
            "desk",
            observed_at_iso="2026-08-04T08:00:00Z",
            camera_id="office-01",
            zone_id="desk",
        )
        latest = service.remember(
            "glasses",
            "under the blue cushion",
            observed_at_iso="2026-08-04T09:11:00Z",
            camera_id="living-room-01",
            zone_id="sofa",
        )

        result = service.find("glasses")
        assert result is not None
        assert result.source_id == latest.source_id

        office_result = service.find(
            "glasses",
            scope=MemoryScope(camera_ids=("office-01",)),
        )
        assert office_result is not None
        assert office_result.source_id == first.source_id

        history = service.history(
            "glasses",
            scope=MemoryScope(
                since_iso="2026-08-04T07:30:00Z",
                until_iso="2026-08-04T08:30:00Z",
            ),
        )
        assert [item.source_id for item in history] == [first.source_id]


def test_persisted_aliases_are_rebuildable_derived_indexes(tmp_path):
    with LastSeenService(tmp_path / "lastseen.db") as service:
        stored = service.remember(
            "keys",
            "hallway shelf",
            observed_at_iso="2026-08-04T10:00:00Z",
            aliases=["nøkler", "keyring"],
        )
        original_manifest = service.index_manifest_digest()

        assert service.find("nøkler").source_id == stored.source_id
        assert service.find("keyring").source_id == stored.source_id
        assert service.count_index_entries() == 3

        rebuilt = service.rebuild_indexes()
        assert rebuilt.indexed_observations == 1
        assert rebuilt.index_entries == 3
        assert rebuilt.manifest_digest == original_manifest
        assert len(rebuilt.receipt_digest) == 64


def test_complete_deletion_keeps_only_non_reversible_receipt(tmp_path):
    db_path = tmp_path / "lastseen.db"
    with LastSeenService(db_path, policy_version="lastseen-policy-v2") as service:
        service.remember(
            "wallet",
            "hallway shelf, inside the green tray",
            image_ref="crops/wallet.jpg",
            observed_at_iso="2026-08-04T10:30:00Z",
            aliases=["lommebok"],
        )
        deletion = service.forget_with_receipt("wallet")

        assert deletion.deleted_observations == 1
        assert deletion.object_name_hash != "wallet"
        assert len(deletion.object_name_hash) == 64
        assert len(deletion.receipt_digest) == 64
        assert deletion.policy_version == "lastseen-policy-v2"
        assert service.get_deletion_receipt(deletion.receipt_digest) == deletion
        assert service.count() == 0
        assert service.count_index_entries() == 0

    with sqlite3.connect(db_path) as connection:
        dump = "\n".join(connection.iterdump())
    assert "hallway shelf, inside the green tray" not in dump
    assert "crops/wallet.jpg" not in dump
    assert "lommebok" not in dump


def test_legacy_database_is_migrated_without_losing_source_evidence(tmp_path):
    db_path = tmp_path / "legacy.db"
    connection = sqlite3.connect(db_path)
    connection.execute(
        """
        CREATE TABLE observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            object_name TEXT NOT NULL,
            normalized_name TEXT NOT NULL,
            location TEXT NOT NULL,
            image_ref TEXT,
            confidence REAL NOT NULL,
            observed_at_iso TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            receipt_digest TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        INSERT INTO observations (
            object_name, normalized_name, location, image_ref, confidence,
            observed_at_iso, metadata_json, receipt_digest
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "keys",
            "keys",
            "desk",
            None,
            1.0,
            "2026-08-04T08:00:00Z",
            '{"camera_id": "office-01", "zone_id": "desk"}',
            "a" * 64,
        ),
    )
    connection.commit()
    connection.close()

    with LastSeenService(db_path) as service:
        result = service.find("keys")
        assert result is not None
        assert result.source_id.startswith("legacy-")
        assert result.source_type == "legacy-observation"
        assert result.camera_id == "office-01"
        assert result.zone_id == "desk"
        assert result.source_receipt_digest == "a" * 64
        assert service.count_index_entries() == 1


def test_duplicate_source_id_and_invalid_scope_fail_closed(tmp_path):
    with LastSeenService(tmp_path / "lastseen.db") as service:
        service.remember(
            "keys",
            "desk",
            source_id="camera-event-42",
            observed_at_iso="2026-08-04T08:00:00Z",
        )
        with pytest.raises(ValueError, match="source_id already exists"):
            service.remember(
                "keys",
                "desk",
                source_id="camera-event-42",
                observed_at_iso="2026-08-04T08:00:01Z",
            )

        with pytest.raises(ValueError, match="since_iso"):
            service.find(
                "keys",
                scope=MemoryScope(
                    since_iso="2026-08-04T09:00:00Z",
                    until_iso="2026-08-04T08:00:00Z",
                ),
            )


def test_invalid_observation_is_rejected(tmp_path):
    with LastSeenService(tmp_path / "lastseen.db") as service:
        with pytest.raises(ValueError, match="confidence"):
            service.remember("keys", "kitchen", confidence=1.5)
        with pytest.raises(ValueError, match="timezone"):
            service.remember(
                "keys",
                "kitchen",
                observed_at_iso="2026-08-04T08:42:00",
            )


def test_index_repair_requires_explicit_governed_rebuild(tmp_path):
    db_path = tmp_path / "lastseen.db"
    with LastSeenService(db_path) as service:
        service.remember(
            "keys",
            "desk",
            observed_at_iso="2026-08-04T08:00:00Z",
            aliases=["nøkler"],
        )

    with sqlite3.connect(db_path) as connection:
        connection.execute("DELETE FROM memory_index")
        connection.commit()

    with LastSeenService(db_path) as service:
        assert service.count_index_entries() == 0
        assert service.find("nøkler") is None

        rebuilt = service.rebuild_indexes()
        assert rebuilt.index_entries == 2
        assert service.find("nøkler") is not None
