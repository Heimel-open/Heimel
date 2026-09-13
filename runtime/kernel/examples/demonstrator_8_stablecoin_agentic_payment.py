"""Demonstrator 8: stablecoin + agentic payment authority drift.

An agent prepares a 45,000 USDC payment while it has authority up to 50,000.
Before consequence time the mandate is replaced with a 25,000 ceiling. The
Kernel execution context is rebuilt from current state. Deterministic payment
authorization DENYs the stale 45,000 action, so the Gateway is never called.
A fresh 20,000 action is then allowed through the same boundary.

The stablecoin/provider rail transports an authorized effect. It never creates
or widens enterprise authority.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from valo_kernel import KernelEngine, build_execution_context
from valo_kernel.contracts import (
    Authority,
    CanonicalEvent,
    EntityType,
    EventType,
    IdentityClaim,
    TimeWindow,
    VerificationStatus,
    utcnow,
)


CAPABILITY = "PAY_STABLECOIN"
CURRENCY = "USDC"
SUPPLIER = "supplier-42"


def _requested_payment(*, tenant: str, amount: str, event_id: str) -> CanonicalEvent:
    return CanonicalEvent(
        event_id=event_id,
        event_type=EventType.EXECUTION_PHASE_UPDATED,
        tenant_id=tenant,
        subject=SUPPLIER,
        actor="treasury-agent",
        source="agent",
        effective_at=utcnow(),
        idempotency_key=event_id,
        payload={
            "process_ref": event_id,
            "phase": "INTENDED",
            "effect": "STABLECOIN_PAYMENT",
            "rail": "circle.usdc.reference.v1",
            "amount": amount,
            "currency": CURRENCY,
            "destination": SUPPLIER,
        },
    )


def _reht_payment_decision(context: dict, *, amount: str, currency: str, target: str) -> str:
    """Minimal deterministic demonstrator policy over fresh Kernel context.

    Production REHT remains the authorization boundary. This helper only makes
    the consequence-time decision leg visible in this standalone example.
    """
    requested_amount = Decimal(amount)
    for authority in context["authority"]:
        if target not in authority["scope"]:
            continue
        constraints = authority["constraints"]
        if constraints.get("currency") != currency:
            continue
        max_amount = constraints.get("max_amount")
        if max_amount is None:
            continue
        if requested_amount <= Decimal(max_amount):
            return "ALLOW"
    return "DENY"


class MockStablecoinGateway:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def send(self, *, amount: str, currency: str, target: str) -> dict[str, str]:
        self.calls.append({"amount": amount, "currency": currency, "target": target})
        return {
            "provider": "circle.usdc.reference.v1",
            "provider_disposition": "ACCEPTED",
            "authority_effect": "NO_AUTHORITY_CREATION",
            "settlement_claim": "NO_SETTLEMENT_CLAIM",
        }


def run() -> dict:
    tenant = "demo-8"
    engine = KernelEngine(tenant)
    gateway = MockStablecoinGateway()
    now = utcnow()
    provenance = {
        "source_type": "system",
        "source_id": "bootstrap",
        "source_system": "valo-kernel",
    }

    for entity_id, entity_type in [
        ("treasury-agent", EntityType.AGENT),
        (SUPPLIER, EntityType.ORGANIZATION),
    ]:
        engine.append(
            CanonicalEvent(
                event_id=f"entity-{entity_id}",
                event_type=EventType.ENTITY_REGISTERED,
                tenant_id=tenant,
                subject=entity_id,
                source="kernel",
                effective_at=now,
                payload={
                    "entity": {
                        "entity_id": entity_id,
                        "entity_type": entity_type,
                        "tenant_id": tenant,
                        "provenance": provenance,
                    }
                },
            )
        )

    engine.append(
        CanonicalEvent(
            event_id="id-treasury-agent",
            event_type=EventType.IDENTITY_CLAIMED,
            tenant_id=tenant,
            subject="treasury-agent",
            source="kernel",
            effective_at=now,
            payload={
                "identity": IdentityClaim(
                    identity_id="id-treasury-agent",
                    entity_id="treasury-agent",
                    tenant_id=tenant,
                    claim_type="service_identity",
                    value="treasury-agent",
                    verification_status=VerificationStatus.VERIFIED,
                )
            },
        )
    )

    def grant(authority_id: str, max_amount: str) -> None:
        engine.append(
            CanonicalEvent(
                event_id=authority_id,
                event_type=EventType.AUTHORITY_GRANTED,
                tenant_id=tenant,
                subject="treasury-agent",
                source="kernel",
                effective_at=utcnow(),
                payload={
                    "authority": Authority(
                        authority_id=authority_id,
                        principal="treasury-agent",
                        capability=CAPABILITY,
                        scope=[SUPPLIER],
                        constraints={"currency": CURRENCY, "max_amount": max_amount},
                        basis="treasury-mandate",
                        validity=TimeWindow(
                            valid_from=now,
                            valid_until=now + timedelta(days=1),
                        ),
                    )
                },
            )
        )

    grant("auth-pay-50k", "50000")

    stale_action = _requested_payment(
        tenant=tenant,
        amount="45000",
        event_id="payment-45k",
    )
    context_at_workflow_start = build_execution_context(
        engine.state(),
        actor="treasury-agent",
        capability=CAPABILITY,
        target=SUPPLIER,
        requested_transition=stale_action,
        identity_id="id-treasury-agent",
    )
    assert _reht_payment_decision(
        context_at_workflow_start,
        amount="45000",
        currency=CURRENCY,
        target=SUPPLIER,
    ) == "ALLOW"

    # Authority changes before consequence time: revoke 50k, replace with 25k.
    engine.append(
        CanonicalEvent(
            event_id="revoke-auth-pay-50k",
            event_type=EventType.AUTHORITY_REVOKED,
            tenant_id=tenant,
            subject="treasury-agent",
            source="kernel",
            effective_at=utcnow(),
            payload={
                "authority_id": "auth-pay-50k",
                "revocation_ref": "treasury-policy-25k",
            },
        )
    )
    grant("auth-pay-25k", "25000")

    fresh_context = build_execution_context(
        engine.state(),
        actor="treasury-agent",
        capability=CAPABILITY,
        target=SUPPLIER,
        requested_transition=stale_action,
        identity_id="id-treasury-agent",
    )
    stale_decision = _reht_payment_decision(
        fresh_context,
        amount="45000",
        currency=CURRENCY,
        target=SUPPLIER,
    )
    assert stale_decision == "DENY"
    assert gateway.calls == [], "denied payment must produce zero provider effect"

    fresh_action = _requested_payment(
        tenant=tenant,
        amount="20000",
        event_id="payment-20k",
    )
    fresh_allowed_context = build_execution_context(
        engine.state(),
        actor="treasury-agent",
        capability=CAPABILITY,
        target=SUPPLIER,
        requested_transition=fresh_action,
        identity_id="id-treasury-agent",
    )
    fresh_decision = _reht_payment_decision(
        fresh_allowed_context,
        amount="20000",
        currency=CURRENCY,
        target=SUPPLIER,
    )
    assert fresh_decision == "ALLOW"

    provider_evidence = gateway.send(
        amount="20000",
        currency=CURRENCY,
        target=SUPPLIER,
    )
    assert len(gateway.calls) == 1
    assert provider_evidence["authority_effect"] == "NO_AUTHORITY_CREATION"
    assert provider_evidence["settlement_claim"] == "NO_SETTLEMENT_CLAIM"

    return {
        "workflow_start_limit": context_at_workflow_start["authority"][0]["constraints"]["max_amount"],
        "consequence_time_limit": fresh_context["authority"][0]["constraints"]["max_amount"],
        "stale_payment": {"amount": "45000", "decision": stale_decision},
        "fresh_payment": {"amount": "20000", "decision": fresh_decision},
        "gateway_calls": len(gateway.calls),
        "provider_evidence": provider_evidence,
    }


def test_demonstrator_8_stablecoin_agentic_payment() -> None:
    result = run()
    assert result["workflow_start_limit"] == "50000"
    assert result["consequence_time_limit"] == "25000"
    assert result["stale_payment"]["decision"] == "DENY"
    assert result["fresh_payment"]["decision"] == "ALLOW"
    assert result["gateway_calls"] == 1


if __name__ == "__main__":
    print(run())
