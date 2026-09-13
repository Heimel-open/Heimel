from pathlib import Path

import pytest

from valo_edge.lastseen.retention import (
    GovernedRetentionService,
    RetentionScopeError,
)
from valo_edge.lastseen.service import LastSeenService


_SALT = b"lastseen-retention-test-salt-32b"


def _remember(
    service: LastSeenService,
    *,
    name: str,
    source_id: str,
    image_ref: str | None,
    observed_at: str,
) -> None:
    service.remember(
        name,
        "kitchen counter",
        image_ref=image_ref,
        confidence=0.98,
        observed_at_iso=observed_at,
        source_id=source_id,
        camera_id="kitchen-01",
        zone_id="counter",
    )


def test_complete_delete_removes_memory_indexes_and_crop(tmp_path):
    crop_root = tmp_path / "crops"
    crop_root.mkdir()
    crop = crop_root / "keys.png"
    crop.write_bytes(b"private-object-crop")

    with LastSeenService(tmp_path / "lastseen.db") as memory:
        _remember(
            memory,
            name="keys",
            source_id="obs-keys-1",
            image_ref=str(crop),
            observed_at="2026-08-01T10:00:00Z",
        )
        retention = GovernedRetentionService(
            memory,
            crop_root,
            subject_salt=_SALT,
        )

        result = retention.delete_object("keys")

        assert result.status == "DELETED"
        assert result.complete is True
        assert result.deleted_observations == 1
        assert result.crops_deleted == 1
        assert result.crops_missing == 0
        assert len(result.memory_receipt_digest) == 64
        assert [receipt.action_type for receipt in result.crop_receipts] == [
            "STAGE_OBJECT_CROP_DELETE",
            "COMMIT_OBJECT_CROP_DELETE",
            "FINALIZE_OBJECT_CROP_DELETE",
        ]
        assert all(len(receipt.receipt_digest) == 64 for receipt in result.crop_receipts)
        assert not crop.exists()
        assert memory.find("keys") is None
        assert memory.count() == 0
        assert not list((crop_root / ".retention-quarantine").glob("*"))


def test_retention_cutoff_is_noop_when_any_newer_observation_exists(tmp_path):
    crop_root = tmp_path / "crops"
    crop_root.mkdir()
    old_crop = crop_root / "keys-old.png"
    new_crop = crop_root / "keys-new.png"
    old_crop.write_bytes(b"old")
    new_crop.write_bytes(b"new")

    with LastSeenService(tmp_path / "lastseen.db") as memory:
        _remember(
            memory,
            name="keys",
            source_id="obs-old",
            image_ref=str(old_crop),
            observed_at="2026-07-01T10:00:00Z",
        )
        _remember(
            memory,
            name="keys",
            source_id="obs-new",
            image_ref=str(new_crop),
            observed_at="2026-08-08T10:00:00Z",
        )
        retention = GovernedRetentionService(memory, crop_root, subject_salt=_SALT)

        result = retention.delete_object("keys", cutoff_iso="2026-08-01T00:00:00Z")

        assert result.status == "RETAINED"
        assert result.deleted_observations == 0
        assert old_crop.exists()
        assert new_crop.exists()
        assert memory.find("keys") is not None
        assert memory.count() == 2


def test_expired_object_deletes_all_history_and_unique_crops(tmp_path):
    crop_root = tmp_path / "crops"
    crop_root.mkdir()
    shared = crop_root / "keys-shared.png"
    shared.write_bytes(b"same-crop")

    with LastSeenService(tmp_path / "lastseen.db") as memory:
        _remember(
            memory,
            name="keys",
            source_id="obs-1",
            image_ref=str(shared),
            observed_at="2026-06-01T10:00:00Z",
        )
        _remember(
            memory,
            name="keys",
            source_id="obs-2",
            image_ref=str(shared),
            observed_at="2026-06-02T10:00:00Z",
        )
        retention = GovernedRetentionService(memory, crop_root, subject_salt=_SALT)

        result = retention.delete_object("keys", cutoff_iso="2026-07-01T00:00:00Z")

        assert result.status == "DELETED"
        assert result.deleted_observations == 2
        assert result.crops_deleted == 1
        assert len(result.crop_receipts) == 3
        assert not shared.exists()
        assert memory.count() == 0


def test_missing_crop_is_explicit_but_final_private_state_is_complete(tmp_path):
    crop_root = tmp_path / "crops"
    crop_root.mkdir()
    missing = crop_root / "already-gone.png"

    with LastSeenService(tmp_path / "lastseen.db") as memory:
        _remember(
            memory,
            name="wallet",
            source_id="obs-wallet",
            image_ref=str(missing),
            observed_at="2026-06-01T10:00:00Z",
        )
        retention = GovernedRetentionService(memory, crop_root, subject_salt=_SALT)

        result = retention.delete_object("wallet")

        assert result.status == "DELETED_WITH_MISSING_CROPS"
        assert result.complete is True
        assert result.crops_deleted == 0
        assert result.crops_missing == 1
        assert len(result.missing_crops) == 1
        assert len(result.missing_crops[0].path_digest) == 64
        assert memory.find("wallet") is None


def test_crop_path_escape_fails_closed_before_memory_deletion(tmp_path):
    crop_root = tmp_path / "crops"
    crop_root.mkdir()
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"must-stay")

    with LastSeenService(tmp_path / "lastseen.db") as memory:
        _remember(
            memory,
            name="keys",
            source_id="obs-outside",
            image_ref=str(outside),
            observed_at="2026-06-01T10:00:00Z",
        )
        retention = GovernedRetentionService(memory, crop_root, subject_salt=_SALT)

        with pytest.raises(RetentionScopeError, match="escapes configured crop root"):
            retention.delete_object("keys")

        assert outside.read_bytes() == b"must-stay"
        assert memory.find("keys") is not None
        assert memory.count() == 1


def test_memory_failure_restores_staged_crop_under_new_authorization(tmp_path):
    crop_root = tmp_path / "crops"
    crop_root.mkdir()
    crop = crop_root / "keys.png"
    crop.write_bytes(b"restore-me")

    with LastSeenService(tmp_path / "lastseen.db") as delegate:
        _remember(
            delegate,
            name="keys",
            source_id="obs-restore",
            image_ref=str(crop),
            observed_at="2026-06-01T10:00:00Z",
        )

        class FailingMemory:
            def history(self, object_name: str, *, limit: int = 100):
                return delegate.history(object_name, limit=limit)

            def forget_with_receipt(self, object_name: str):
                raise RuntimeError("injected-memory-delete-failure")

        retention = GovernedRetentionService(FailingMemory(), crop_root, subject_salt=_SALT)

        with pytest.raises(RuntimeError, match="injected-memory-delete-failure"):
            retention.delete_object("keys")

        assert crop.read_bytes() == b"restore-me"
        assert delegate.find("keys") is not None
        assert not list((crop_root / ".retention-quarantine").glob("*"))


def test_history_cap_fails_closed_without_touching_crop(tmp_path):
    crop_root = tmp_path / "crops"
    crop_root.mkdir()
    crop = crop_root / "keys.png"
    crop.write_bytes(b"keep")

    with LastSeenService(tmp_path / "lastseen.db") as memory:
        _remember(
            memory,
            name="keys",
            source_id="obs-cap-1",
            image_ref=str(crop),
            observed_at="2026-06-01T10:00:00Z",
        )
        _remember(
            memory,
            name="keys",
            source_id="obs-cap-2",
            image_ref=str(crop),
            observed_at="2026-06-02T10:00:00Z",
        )
        retention = GovernedRetentionService(
            memory,
            crop_root,
            subject_salt=_SALT,
            max_history=2,
        )

        with pytest.raises(RetentionScopeError, match="max_history"):
            retention.delete_object("keys")

        assert crop.exists()
        assert memory.count() == 2


def test_subject_digest_does_not_expose_plain_object_name(tmp_path):
    crop_root = tmp_path / "crops"
    with LastSeenService(tmp_path / "lastseen.db") as memory:
        retention = GovernedRetentionService(memory, crop_root, subject_salt=_SALT)
        result = retention.delete_object("My Secret Wallet")

    assert result.status == "NO_MATCH"
    assert len(result.subject_digest) == 64
    assert "wallet" not in result.subject_digest.lower()
