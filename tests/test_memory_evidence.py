from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.valo_platform.memory_evidence import (
    MemoryAdmissionReason,
    MemoryUseEvidence,
    admitted_records,
    build_memory_use_evidence,
    verify_memory_replay,
)
from src.valo_platform.memory_lifecycle import MemoryContextItem, MemorySession
from src.valo_platform.memory_provider import MemoryRecord, MemoryStatus, canonical_digest


NOW = datetime(2026, 7, 26, 20, 30, tzinfo=timezone.utc)
SESSION = MemorySession(
    branch="agent/hermes/session/s-1/task/t-1",
    snapshot_id="snap-1",
    agent_id="hermes",
    session_id="s-1",
    task_id="t-1",
)


def record(
    memory_id: str,
    *,
    status: MemoryStatus = MemoryStatus.VALIDATED,
    branch: str = SESSION.branch,
    snapshot_id: str = SESSION.snapshot_id,
    principal_id: str = "principal-1",
    agent_id: str = SESSION.agent_id,
    session_id: str = SESSION.session_id,
    digest: str | None = None,
) -> MemoryRecord:
    return MemoryRecord(
        memory_id=memory_id,
        provider="memoria",
        provider_ref=f"memoria:{memory_id}",
        branch=branch,
        snapshot_id=snapshot_id,
        memory_type="task_context",
        content_digest=digest or canonical_digest({"memory_id": memory_id}),
        source_refs=("source:1",),
        principal_id=principal_id,
        agent_id=agent_id,
        session_id=session_id,
        created_at=NOW,
        confidence=0.9,
        status=status,
        retention_class="session",
    )


def evidence(*items: MemoryContextItem) -> MemoryUseEvidence:
    return build_memory_use_evidence(
        evidence_id="evidence-1",
        action_ref="action:sha256:abc",
        principal_id="principal-1",
        session=SESSION,
        context=items,
        created_at=NOW,
    )


def test_validated_fresh_scoped_memory_is_admitted() -> None:
    result = evidence(MemoryContextItem(record=record("m-1"), stale=False))

    assert result.admitted_memory_ids == ("m-1",)
    assert result.entries[0].admitted is True
    assert result.entries[0].reason is MemoryAdmissionReason.ADMITTED
    assert result.grants_authority is False
    assert result.grants_clearance is False
    assert result.promotes_to_sol is False


@pytest.mark.parametrize(
    ("item", "reason"),
    [
        (MemoryContextItem(record=record("stale"), stale=True), MemoryAdmissionReason.STALE),
        (
            MemoryContextItem(record=record("candidate", status=MemoryStatus.CANDIDATE), stale=False),
            MemoryAdmissionReason.NOT_VALIDATED,
        ),
        (
            MemoryContextItem(record=record("authority"), stale=False, authoritative=True),
            MemoryAdmissionReason.AUTHORITATIVE_FLAG,
        ),
        (
            MemoryContextItem(record=record("branch", branch="other"), stale=False),
            MemoryAdmissionReason.BRANCH_MISMATCH,
        ),
        (
            MemoryContextItem(record=record("snapshot", snapshot_id="snap-other"), stale=False),
            MemoryAdmissionReason.SNAPSHOT_MISMATCH,
        ),
        (
            MemoryContextItem(record=record("principal", principal_id="other"), stale=False),
            MemoryAdmissionReason.PRINCIPAL_MISMATCH,
        ),
        (
            MemoryContextItem(record=record("agent", agent_id="other"), stale=False),
            MemoryAdmissionReason.AGENT_MISMATCH,
        ),
        (
            MemoryContextItem(record=record("session", session_id="other"), stale=False),
            MemoryAdmissionReason.SESSION_MISMATCH,
        ),
    ],
)
def test_non_admissible_memory_is_disclosed_not_silently_used(
    item: MemoryContextItem,
    reason: MemoryAdmissionReason,
) -> None:
    result = evidence(item)

    assert result.admitted_memory_ids == ()
    assert result.entries[0].admitted is False
    assert result.entries[0].reason is reason


def test_entry_order_and_rejections_are_bound_into_digest() -> None:
    accepted = MemoryContextItem(record=record("accepted"), stale=False)
    stale = MemoryContextItem(record=record("stale"), stale=True)

    first = evidence(accepted, stale)
    second = build_memory_use_evidence(
        evidence_id="evidence-1",
        action_ref="action:sha256:abc",
        principal_id="principal-1",
        session=SESSION,
        context=(stale, accepted),
        created_at=NOW,
    )

    assert first.evidence_digest != second.evidence_digest
    assert first.admitted_memory_ids == ("accepted",)
    assert second.admitted_memory_ids == ("accepted",)


def test_materialization_rejects_changed_content_digest() -> None:
    original = record("m-1")
    result = evidence(MemoryContextItem(record=original, stale=False))
    changed = record("m-1", digest=canonical_digest({"memory_id": "m-1", "changed": True}))

    with pytest.raises(ValueError, match="digest changed"):
        admitted_records(result, (changed,))


def test_materialization_rejects_missing_admitted_memory() -> None:
    result = evidence(MemoryContextItem(record=record("m-1"), stale=False))

    with pytest.raises(ValueError, match="missing"):
        admitted_records(result, ())


def test_replay_is_deterministic_for_identical_snapshot_and_context() -> None:
    item = MemoryContextItem(record=record("m-1"), stale=False)
    expected = evidence(item)
    observed = evidence(item)

    replay = verify_memory_replay(expected, observed)

    assert replay.valid is True
    assert replay.errors == ()
    assert replay.expected_digest == replay.observed_digest


def test_replay_fails_when_memory_selection_changes() -> None:
    expected = evidence(MemoryContextItem(record=record("m-1"), stale=False))
    observed = build_memory_use_evidence(
        evidence_id="evidence-1",
        action_ref="action:sha256:abc",
        principal_id="principal-1",
        session=SESSION,
        context=(MemoryContextItem(record=record("m-2"), stale=False),),
        created_at=NOW,
    )

    replay = verify_memory_replay(expected, observed)

    assert replay.valid is False
    assert "admitted memory set or order mismatch" in replay.errors
    assert "evidence digest mismatch" in replay.errors


def test_memory_evidence_cannot_claim_authority_clearance_or_sol_promotion() -> None:
    valid = evidence(MemoryContextItem(record=record("m-1"), stale=False))
    payload = valid.model_dump()
    payload["grants_authority"] = True

    with pytest.raises(ValidationError, match="cannot grant authority"):
        MemoryUseEvidence(**payload)


def test_tampered_digest_is_rejected() -> None:
    valid = evidence(MemoryContextItem(record=record("m-1"), stale=False))
    payload = valid.model_dump()
    payload["evidence_digest"] = "sha256:" + "f" * 64

    with pytest.raises(ValidationError, match="does not match"):
        MemoryUseEvidence(**payload)
