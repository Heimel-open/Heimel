from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from valo_reht import (
    ExecutionJournalError,
    RecoveryClassification,
    SQLiteExecutionJournal,
    SQLitePermitStore,
    inspect_recovery,
)
from valo_reht.runtime_interlocks import build_execution_receipt, canonical_digest


def _intent(journal: SQLiteExecutionJournal, *, permit: str = "permit:1") -> dict[str, str]:
    bindings = {
        "permit_ref": permit,
        "action_digest": canonical_digest({"action_id": "action:1"}),
        "execution_context_hash": canonical_digest({"state": 1}),
        "clearance_ref": "clearance:1",
        "effect_name": "effect:1",
    }
    assert journal.open_intent(**bindings)
    journal.mark_effect_invoking(permit)
    return bindings


def _receipt(bindings: dict[str, str]):
    return build_execution_receipt(
        status="COMMITTED",
        action={"action_id": "action:1"},
        execution_context_hash=bindings["execution_context_hash"],
        reht_decision="ALLOW",
        clearance_ref=bindings["clearance_ref"],
        permit_ref=bindings["permit_ref"],
        effect_name=bindings["effect_name"],
        effect_result={"ok": True},
    )


def test_exact_receipt_binding_is_accepted(tmp_path: Path) -> None:
    journal = SQLiteExecutionJournal(tmp_path / "journal.sqlite3")
    bindings = _intent(journal)
    journal.mark_receipt_ready(bindings["permit_ref"], _receipt(bindings))
    entry = journal.get(bindings["permit_ref"])
    assert entry is not None
    assert entry.receipt is not None
    assert entry.receipt.permit_ref == bindings["permit_ref"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("permit_ref", "permit:other"),
        ("action_digest", "0" * 64),
        ("execution_context_hash", "1" * 64),
        ("clearance_ref", "clearance:other"),
        ("effect_name", "effect:other"),
        ("reht_decision", "DENY"),
    ],
)
def test_receipt_binding_substitution_is_rejected(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    journal = SQLiteExecutionJournal(tmp_path / "journal.sqlite3")
    bindings = _intent(journal)
    forged = replace(_receipt(bindings), **{field: value})
    with pytest.raises(ExecutionJournalError, match="intent bindings"):
        journal.mark_receipt_ready(bindings["permit_ref"], forged)


def test_receipt_id_tampering_is_rejected(tmp_path: Path) -> None:
    journal = SQLiteExecutionJournal(tmp_path / "journal.sqlite3")
    bindings = _intent(journal)
    forged = replace(_receipt(bindings), receipt_id="sha256:" + "0" * 64)
    with pytest.raises(ExecutionJournalError, match="digest mismatch"):
        journal.mark_receipt_ready(bindings["permit_ref"], forged)


def test_consumed_permit_without_prior_terminal_journal_cannot_be_rewritten_as_blocked(
    tmp_path: Path,
) -> None:
    permit = "permit:legacy-orphan"
    action = {"action_id": "action:1"}
    context_hash = canonical_digest({"state": 1})
    journal = SQLiteExecutionJournal(tmp_path / "journal.sqlite3")
    store = SQLitePermitStore(tmp_path / "permits.sqlite3")
    assert store.consume_once(permit) is True
    assert journal.open_intent(
        permit_ref=permit,
        action_digest=canonical_digest(action),
        execution_context_hash=context_hash,
        clearance_ref="clearance:1",
        effect_name="effect:1",
    )
    replay_receipt = build_execution_receipt(
        status="BLOCKED",
        action=action,
        execution_context_hash=context_hash,
        reht_decision="ALLOW",
        clearance_ref="clearance:1",
        permit_ref=permit,
        effect_name="effect:1",
        reason="PERMIT_REPLAY",
    )
    with pytest.raises(ExecutionJournalError, match="indeterminate"):
        journal.mark_receipt_ready(permit, replay_receipt)
    recovery = inspect_recovery(journal=journal, permit_store=store, permit_ref=permit)
    assert recovery.classification is RecoveryClassification.INDETERMINATE_EFFECT
