from __future__ import annotations

import pytest

from valo_kernel.contracts import EventType
from valo_kernel.kernel import (
    IdempotentReplay,
    KernelEngine,
    KernelExecutionOutcomeConsumer,
    VerifiedExecutionOutcomeV1,
)


def _outcome(**overrides):
    data = {
        "receipt_id": "sha256:" + "a" * 64,
        "veritas_ref": "worm:abc123",
        "status": "COMMITTED",
        "action_digest": "b" * 64,
        "execution_context_hash": "c" * 64,
        "reht_decision": "ALLOW",
        "clearance_ref": "clearance:1",
        "permit_ref": "permit:1",
        "effect_result_digest": "d" * 64,
        "observed_at": "2026-08-23T20:00:00Z",
        "postconditions_verified": True,
        "authority_granted": False,
    }
    data.update(overrides)
    return VerifiedExecutionOutcomeV1(**data)


def test_verified_execution_outcome_appends_as_non_authoritative_kernel_history() -> None:
    engine = KernelEngine("tenant:1")
    before = engine.state()
    consumer = KernelExecutionOutcomeConsumer(engine)

    ref = consumer.append_verified_execution_outcome(_outcome())

    assert ref
    assert engine.sequence() == 1
    event = engine.events()[0]
    assert event.event_type is EventType.EXTERNAL_EFFECT_OBSERVED
    assert event.source == "veritas"
    assert event.evidence_refs == ["worm:abc123"]
    assert event.payload["authority_granted"] is False
    assert event.payload["verification_basis"] == "VERITAS_WORM"
    assert engine.state() == before
    engine.verify_integrity()


def test_same_verified_receipt_is_idempotent_and_cannot_duplicate_history() -> None:
    engine = KernelEngine("tenant:1")
    consumer = KernelExecutionOutcomeConsumer(engine)
    outcome = _outcome()
    consumer.append_verified_execution_outcome(outcome)

    with pytest.raises(IdempotentReplay):
        consumer.append_verified_execution_outcome(outcome)

    assert engine.sequence() == 1


def test_execution_outcome_requires_veritas_worm_reference() -> None:
    with pytest.raises(ValueError, match="Veritas WORM reference is required"):
        _outcome(veritas_ref="")


def test_execution_outcome_cannot_grant_authority() -> None:
    with pytest.raises(ValueError, match="cannot grant authority"):
        _outcome(authority_granted=True)


def test_allow_outcome_requires_clearance_and_permit() -> None:
    with pytest.raises(ValueError, match="requires clearance and permit"):
        _outcome(clearance_ref=None)


def test_restrictive_non_commit_outcome_is_recordable_without_permit() -> None:
    engine = KernelEngine("tenant:1")
    outcome = _outcome(
        status="NOT_COMMITTED",
        reht_decision="DENY",
        clearance_ref=None,
        permit_ref=None,
        effect_result_digest=None,
        postconditions_verified=None,
    )
    KernelExecutionOutcomeConsumer(engine).append_verified_execution_outcome(outcome)
    assert engine.events()[0].payload["verified_execution_outcome"]["reht_decision"] == "DENY"
