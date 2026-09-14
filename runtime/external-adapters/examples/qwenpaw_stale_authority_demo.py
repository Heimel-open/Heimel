from valo_external_adapters.qwenpaw import (
    AuthoritySnapshot,
    HeimelQwenPawAdapter,
    InMemoryVeritasChain,
    QwenPawEffectMetadata,
    QwenPawEffectRegistry,
    QwenPawMissionEffect,
)


veritas = InMemoryVeritasChain()
registry = QwenPawEffectRegistry([
    QwenPawEffectMetadata("payments.send", "payment", "PAYMENT.SEND"),
])


def fresh_authority(_effect):
    return AuthoritySnapshot(
        authority_digest="authority-v2-limit-25000",
        state_digest="state-09:05",
        allowed_effects=frozenset({"PAYMENT.SEND"}),
        observed_at="09:05",
    )


def qwenpaw_driver(_binding):
    raise RuntimeError("driver must never be reached with stale authority")


adapter = HeimelQwenPawAdapter(
    registry=registry,
    authority_resolver=fresh_authority,
    veritas=veritas,
)

attempt = QwenPawMissionEffect(
    mission_id="mission-pay-invoice",
    worker_id="delegated-worker-7",
    source="qwenpaw.mission.worker",
    tool_name="payments.send",
    effect_type="payment",
    resource="invoice-42",
    payload={"amount": 45000, "currency": "USD"},
    approval_authority_digest="authority-v1-limit-50000",
    approval_id="mission-approval-08:00",
)

decision = adapter.execute(attempt, qwenpaw_driver)

assert decision.allowed is False
assert decision.reason == "STALE_AUTHORITY"
assert veritas.verify()

print({
    "mission": attempt.mission_id,
    "worker": attempt.worker_id,
    "old_approval": attempt.approval_authority_digest,
    "fresh_authority": decision.receipt.record["fresh_authority_digest"],
    "decision": decision.reason,
    "driver_reached": False,
    "veritas_receipt": decision.receipt.receipt_id,
})
