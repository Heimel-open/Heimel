from __future__ import annotations

import pytest

from valo_kernel import KernelInvariantViolation
from valo_kernel.contracts import (
    CanonicalEvent,
    EventType,
    Fact,
    TruthStatus,
    utcnow,
)

from .conftest import entity_event, make_provenance


def fact_event(engine, fact_id: str, subject: str, predicate: str, obj: str, event_type=EventType.FACT_ASSERTED) -> None:
    engine.append(
        CanonicalEvent(
            event_id=f"fact-{fact_id}",
            event_type=event_type,
            tenant_id="tenant-a",
            subject=subject,
            source="kernel",
            effective_at=utcnow(),
            payload={
                "fact": Fact(
                    fact_id=fact_id,
                    subject=subject,
                    predicate=predicate,
                    object=obj,
                    tenant_id="tenant-a",
                    provenance=make_provenance(fact_id),
                )
            },
        )
    )


def test_conflicted_reality(engine) -> None:
    """Two authoritative sources disagree on a bank account. WorldState must
    represent CONFLICTED, never guess."""
    engine.append(entity_event("tenant-a", "account-1"))
    fact_event(engine, "f-acc-1", "account-1", "bank_account", "NO-1111")
    fact_event(engine, "f-acc-2", "account-1", "bank_account", "NO-2222")
    # the authoritative admission detects the disagreement -> conflict
    now = utcnow()
    engine.append(
        CanonicalEvent(
            event_id="conflict",
            event_type=EventType.FACT_CONFLICTED,
            tenant_id="tenant-a",
            subject="account-1",
            source="kernel",
            effective_at=now,
            payload={"fact_id": "f-acc-1", "conflicting_value": "NO-2222"},
        )
    )
    fact = engine.state().facts["f-acc-1"]
    assert fact.truth_status == TruthStatus.CONFLICTED
    assert fact.object == "NO-2222"

    from valo_kernel import Queries

    conflicted = Queries(engine.state()).conflicted()
    assert len(conflicted) == 1


def test_probabilistic_fact_not_confirmed(engine) -> None:
    """VAIG/LLM inference must be marked INFERRED, never CONFIRMED, until it
    passes explicit admission/verification."""
    engine.append(entity_event("tenant-a", "account-1"))
    engine.append(
        CanonicalEvent(
            event_id="infer-1",
            event_type=EventType.FACT_ASSERTED,
            tenant_id="tenant-a",
            subject="account-1",
            source="vaig",
            effective_at=utcnow(),
            payload={
                "fact": Fact(
                    fact_id="f-infer",
                    subject="account-1",
                    predicate="risk",
                    object="HIGH",
                    tenant_id="tenant-a",
                    truth_status=TruthStatus.INFERRED,
                    model="vaig-v3",
                    confidence=0.87,
                    provenance=make_provenance("f-infer"),
                )
            },
        )
    )
    assert engine.state().facts["f-infer"].truth_status == TruthStatus.INFERRED
    assert engine.state().facts["f-infer"].truth_status != TruthStatus.CONFIRMED

    # confirming an INFERRED fact without prior ASSERTED admission is rejected

    with pytest.raises(KernelInvariantViolation, match="cannot confirm"):
        engine.append(
            CanonicalEvent(
                event_id="bad-confirm",
                event_type=EventType.FACT_CONFIRMED,
                tenant_id="tenant-a",
                subject="account-1",
                source="kernel",
                effective_at=utcnow(),
                payload={"fact_id": "f-infer"},
            )
        )

