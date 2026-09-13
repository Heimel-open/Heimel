from __future__ import annotations

import shutil
from pathlib import Path

from examples.demonstrator_7_personal_compute_v0 import run
from valo_kernel import KernelEngine
from valo_kernel.storage import SQLiteStore


def test_runtime_loss_does_not_destroy_sovereign_domain(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "session-cache.json").write_text(
        '{"worker":"cloud-a","status":"ephemeral"}',
        encoding="utf-8",
    )

    result = run(tmp_path)
    expected_root = result["state_root"]

    shutil.rmtree(runtime)
    assert not runtime.exists()

    store = SQLiteStore(tmp_path / "domain.db")
    recovered = KernelEngine("personal-v0", storage=store)
    recovered.verify_integrity()

    assert recovered.state().root_hash() == expected_root
    assert recovered.state().entities["job-1"].state == "BOOKED"
    assert (tmp_path / "credentials" / "receipt-signer-1.pub").exists()

    store.close()
