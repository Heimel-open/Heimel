from valo_external_adapters.qwenpaw import (
    AuthoritySnapshot,
    HeimelQwenPawAdapter,
    InMemoryVeritasChain,
    QwenPawEffectMetadata,
    QwenPawEffectRegistry,
    QwenPawMissionEffect,
)


def registry():
    return QwenPawEffectRegistry([
        QwenPawEffectMetadata("payments.send", "payment", "PAYMENT.SEND"),
    ])


def effect(approval_digest="auth-v1", *, tool="payments.send"):
    return QwenPawMissionEffect(
        mission_id="mission-7",
        worker_id="worker-3",
        source="qwenpaw.mission.worker",
        tool_name=tool,
        effect_type="payment",
        resource="invoice-42",
        payload={"amount": 45000, "currency": "USD"},
        approval_authority_digest=approval_digest,
        approval_id="approval-1",
    )


def test_stale_mission_approval_never_reaches_driver_and_records_receipt():
    veritas = InMemoryVeritasChain()
    calls = []

    def authority(_):
        return AuthoritySnapshot("auth-v2", "state-v2", frozenset({"PAYMENT.SEND"}), "09:05")

    adapter = HeimelQwenPawAdapter(registry=registry(), authority_resolver=authority, veritas=veritas)
    decision = adapter.execute(effect("auth-v1"), lambda binding: calls.append(binding))

    assert decision.allowed is False
    assert decision.reason == "STALE_AUTHORITY"
    assert calls == []
    assert decision.receipt.record["approval_authority_digest"] == "auth-v1"
    assert decision.receipt.record["fresh_authority_digest"] == "auth-v2"
    assert veritas.verify()


def test_registered_effect_with_fresh_authority_commits_once():
    veritas = InMemoryVeritasChain()
    calls = []

    def authority(_):
        return AuthoritySnapshot("auth-v1", "state-v1", frozenset({"PAYMENT.SEND"}), "09:00")

    adapter = HeimelQwenPawAdapter(registry=registry(), authority_resolver=authority, veritas=veritas)
    decision = adapter.execute(effect(), lambda binding: calls.append(binding.digest) or "ok")

    assert decision.allowed is True
    assert decision.driver_result == "ok"
    assert len(calls) == 1
    assert [r.record["reason"] for r in veritas.receipts] == ["ALLOW", "EFFECT_COMMITTED"]
    assert veritas.verify()


def test_unknown_tool_fails_closed_even_with_valid_looking_approval():
    veritas = InMemoryVeritasChain()
    calls = []

    def authority(_):
        raise AssertionError("unknown effects must fail before authority resolution")

    adapter = HeimelQwenPawAdapter(registry=registry(), authority_resolver=authority, veritas=veritas)
    decision = adapter.execute(effect(tool="attacker.direct_shell"), lambda binding: calls.append(binding))

    assert decision.allowed is False
    assert decision.reason == "UNKNOWN_EFFECT_FAIL_CLOSED"
    assert calls == []
    assert veritas.verify()


def test_authority_change_between_admission_and_effect_blocks_driver():
    veritas = InMemoryVeritasChain()
    calls = []
    snapshots = iter([
        AuthoritySnapshot("auth-v1", "state-v1", frozenset({"PAYMENT.SEND"}), "09:00"),
        AuthoritySnapshot("auth-v2", "state-v2", frozenset({"PAYMENT.SEND"}), "09:00:01"),
    ])

    adapter = HeimelQwenPawAdapter(registry=registry(), authority_resolver=lambda _: next(snapshots), veritas=veritas)

    try:
        adapter.execute(effect(), lambda binding: calls.append(binding))
    except Exception as exc:
        assert "changed before effect" in str(exc)
    else:
        raise AssertionError("expected consequence-time recheck to fail")

    assert calls == []
    assert [r.record["reason"] for r in veritas.receipts] == ["ALLOW", "AUTHORITY_CHANGED_BEFORE_EFFECT"]
    assert veritas.verify()
