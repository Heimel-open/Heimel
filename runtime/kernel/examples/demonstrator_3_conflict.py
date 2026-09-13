"""Demonstrator 3: conflicted reality.

Two authoritative sources state different bank accounts. WorldState sets the
account fact to CONFLICTED. A PAY workflow tries to execute. The kernel returns
the unresolved state; REHT sees conflicted facts and must DEFER/DENY. No money
moves.
"""

from __future__ import annotations

from valo_kernel import KernelEngine, Queries
from valo_kernel.contracts import (
    CanonicalEvent,
    EntityType,
    EventType,
    Fact,
    TruthStatus,
    utcnow,
)


def run() -> dict:
    tenant = "demo-3"
    engine = KernelEngine(tenant)
    now = utcnow()
    prov = {"source_type": "external", "source_id": "s", "source_system": "bank"}

    engine.append(
        CanonicalEvent(
            event_id="entity-account",
            event_type=EventType.ENTITY_REGISTERED,
            tenant_id=tenant,
            subject="account-1",
            source="kernel",
            effective_at=now,
            payload={"entity": {"entity_id": "account-1", "entity_type": EntityType.ACCOUNT, "tenant_id": tenant, "provenance": prov}},
        )
    )

    def assert_account(fact_id: str, value: str, source_id: str) -> None:
        engine.append(
            CanonicalEvent(
                event_id=f"fact-{fact_id}",
                event_type=EventType.FACT_ASSERTED,
                tenant_id=tenant,
                subject="account-1",
                source="veritas",
                effective_at=now,
                payload={
                    "fact": Fact(
                        fact_id=fact_id,
                        subject="account-1",
                        predicate="bank_account",
                        object=value,
                        tenant_id=tenant,
                        provenance={
                            "source_type": "external",
                            "source_id": source_id,
                            "source_system": "bank",
                        },
                    )
                },
            )
        )

    # two authoritative sources disagree
    assert_account("f-acc-1", "NO-1111", "bank-a")
    assert_account("f-acc-2", "NO-2222", "bank-b")

    # admission detects the disagreement -> conflicted reality
    engine.append(
        CanonicalEvent(
            event_id="conflict-account",
            event_type=EventType.FACT_CONFLICTED,
            tenant_id=tenant,
            subject="account-1",
            source="kernel",
            effective_at=now,
            payload={"fact_id": "f-acc-1", "conflicting_value": "NO-2222"},
        )
    )

    conflicted = Queries(engine.state()).conflicted()
    assert len(conflicted) == 1, "account must be conflicted"

    # PAY workflow reads the unresolved state -> REHT must DEFER/DENY
    facts = Queries(engine.state()).facts_about("account-1")
    pay_target = next(f for f in facts if f["predicate"] == "bank_account")
    assert pay_target["truth_status"] == "CONFLICTED", "no payment may target a conflicted account"

    return {"status": pay_target["truth_status"], "conflicted": len(conflicted)}


def test_demonstrator_3_conflicted_reality() -> None:
    result = run()
    assert result["status"] == TruthStatus.CONFLICTED.value


if __name__ == "__main__":
    print(run())
