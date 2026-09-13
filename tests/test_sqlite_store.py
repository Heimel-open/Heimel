from __future__ import annotations

from pathlib import Path

import pytest

from valo_kernel import IdempotentReplay, KernelEngine
from valo_kernel.storage import SQLiteStore

from .conftest import entity_event


def test_sqlite_store_survives_engine_restart(tmp_path: Path) -> None:
    database = tmp_path / "domain.db"
    first_store = SQLiteStore(database)
    first = KernelEngine("tenant-a", storage=first_store)
    first.append(entity_event("tenant-a", "job-1", state="READY"))
    expected_root = first.state().root_hash()
    expected_event_hash = first.events()[-1].event_hash
    first_store.close()

    second_store = SQLiteStore(database)
    second = KernelEngine("tenant-a", storage=second_store)

    assert second.sequence() == 1
    assert second.state().root_hash() == expected_root
    assert second.events()[-1].event_hash == expected_event_hash
    second.verify_integrity()
    second_store.close()


def test_sqlite_store_persists_idempotency_across_restart(tmp_path: Path) -> None:
    database = tmp_path / "domain.db"
    event = entity_event("tenant-a", "job-1", state="READY").model_copy(
        update={"idempotency_key": "register-job-1"}
    )

    first_store = SQLiteStore(database)
    KernelEngine("tenant-a", storage=first_store).append(event)
    first_store.close()

    second_store = SQLiteStore(database)
    restarted = KernelEngine("tenant-a", storage=second_store)
    with pytest.raises(IdempotentReplay):
        restarted.append(event)
    second_store.close()


def test_sqlite_store_rejects_sequence_gap(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "domain.db")
    engine = KernelEngine("tenant-a", storage=store)
    sealed = engine.append(entity_event("tenant-a", "job-1", state="READY"))

    with pytest.raises(ValueError, match="does not match expected"):
        store.append_event(sealed.model_copy(update={"sequence": 3}), engine.state())
    store.close()
