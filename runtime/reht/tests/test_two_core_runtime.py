"""TWO-CORE runtime regression against the frozen paired-governance families.

Path under test (the authoritative runtime):

    Kernel state/context
        -> RealReht
        -> minimal mechanical effect adapter
        -> outcome evidence
        -> Kernel observation/admission

The legacy ``Kernel -> REHT -> RACS -> Gateway -> Veritas`` chain is NOT
reconstructed here. The mechanical effect adapter never authorizes; it only
requires an exact REHT permit/binding, denies direct effects without a permit,
denies permit replay, and never changes the action after authorization.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from tests.two_core_harness import (
    CAPABILITY,
    PURPOSE,
    TARGET,
    EffectDenied,
    MechanicalEffectAdapter,
    TwoCoreRuntime,
    _authority_event,
    _revoke_event,
    _state_change_event,
    base_engine,
    build_context,
)
from valo_reht import RealReht
from valo_reht.contracts import DecisionResult

NOW = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)


def _action(
    *,
    capability: str = CAPABILITY,
    target: str = TARGET,
    purpose_id: str = PURPOSE,
    constraints: dict[str, str] | None = None,
    step_up: Any = None,
) -> dict[str, Any]:
    action: dict[str, Any] = {
        "action_id": "action:two-core",
        "capability": capability,
        "target": target,
        "action_type": capability,
        "purpose_id": purpose_id,
    }
    if constraints is not None:
        action["constraints"] = constraints
    if step_up is not None:
        action["step_up"] = step_up
    return action


def _effect(calls: list[dict[str, Any]]):
    return lambda arguments: (calls.append(arguments), {"ok": True})[1]


# --------------------------------------------------------------------------
# 1. valid authorized action
# --------------------------------------------------------------------------


def test_valid_authorized_action_commits_exactly_once() -> None:
    engine = base_engine(now=NOW)
    rt = TwoCoreRuntime(engine)
    calls: list[dict[str, Any]] = []

    run = rt.commit(
        scenario_id="PG-001",
        action_contract=_action(),
        now=NOW,
        effect_fn=_effect(calls),
    )

    assert run.evidence.decision == "ALLOW"
    assert run.evidence.effect_committed is True
    assert len(calls) == 1
    assert run.unsafe_commit is False
    assert run.bypass is False
    assert run.replay_effect is False
    assert run.false_authority_creation is False
    assert run.evidence.closed is True
    assert run.evidence.permit_ref is not None
    assert run.evidence.observation_event_id is not None


# --------------------------------------------------------------------------
# 2. missing identity
# --------------------------------------------------------------------------


def test_missing_identity_fails_closed() -> None:
    engine = base_engine(now=NOW, identity=False)
    rt = TwoCoreRuntime(engine)
    calls: list[dict[str, Any]] = []

    run = rt.commit(
        scenario_id="PG-013",
        action_contract=_action(),
        now=NOW,
        effect_fn=_effect(calls),
    )

    assert run.evidence.decision == "DENY"
    assert run.evidence.effect_committed is False
    assert calls == []
    assert run.unsafe_commit is False
    assert run.evidence.closed is True


# --------------------------------------------------------------------------
# 3. missing authority
# --------------------------------------------------------------------------


def test_missing_authority_fails_closed() -> None:
    engine = base_engine(now=NOW, authority=False)
    rt = TwoCoreRuntime(engine)
    calls: list[dict[str, Any]] = []

    run = rt.commit(
        scenario_id="PG-013",
        action_contract=_action(),
        now=NOW,
        effect_fn=_effect(calls),
    )

    assert run.evidence.decision == "DENY"
    assert run.evidence.effect_committed is False
    assert calls == []
    assert run.unsafe_commit is False
    assert run.evidence.closed is True


# --------------------------------------------------------------------------
# 4. revoked authority at commit
# --------------------------------------------------------------------------


def test_revoked_authority_at_commit_fails_closed() -> None:
    engine = base_engine(now=NOW)
    rt = TwoCoreRuntime(engine)
    calls: list[dict[str, Any]] = []

    # Authorization would succeed against the pre-revocation state.
    plan_ctx = build_context(engine, _action(), now=NOW, nonce="nonce:plan")
    assert RealReht().authorize(plan_ctx, _action()).decision == "ALLOW"

    # Revocation lands before the commit.
    engine.append(_revoke_event(now=NOW))

    run = rt.commit(
        scenario_id="PG-003",
        action_contract=_action(),
        now=NOW,
        effect_fn=_effect(calls),
    )

    assert run.evidence.decision == "DENY"
    assert run.evidence.effect_committed is False
    assert calls == []
    assert run.unsafe_commit is False
    assert run.evidence.closed is True


# --------------------------------------------------------------------------
# 5. expired authority
# --------------------------------------------------------------------------


def test_expired_authority_fails_closed() -> None:
    engine = base_engine(now=NOW, authority=False)
    engine.append(
        _authority_event(now=NOW - timedelta(minutes=2), valid_until=NOW - timedelta(seconds=1))
    )
    rt = TwoCoreRuntime(engine)
    calls: list[dict[str, Any]] = []

    run = rt.commit(
        scenario_id="PG-002",
        action_contract=_action(),
        now=NOW,
        effect_fn=_effect(calls),
    )

    assert run.evidence.decision == "DENY"
    assert run.evidence.effect_committed is False
    assert calls == []
    assert run.unsafe_commit is False


# --------------------------------------------------------------------------
# 6. scope mismatch
# --------------------------------------------------------------------------


def test_scope_mismatch_fails_closed() -> None:
    engine = base_engine(now=NOW)
    rt = TwoCoreRuntime(engine)
    calls: list[dict[str, Any]] = []

    run = rt.commit(
        scenario_id="PG-004",
        action_contract=_action(target="target-2"),
        now=NOW,
        effect_fn=_effect(calls),
    )

    assert run.evidence.decision == "DENY"
    assert run.evidence.effect_committed is False
    assert calls == []
    assert run.unsafe_commit is False


# --------------------------------------------------------------------------
# 7. purpose mismatch
# --------------------------------------------------------------------------


def test_purpose_mismatch_fails_closed() -> None:
    engine = base_engine(now=NOW)
    rt = TwoCoreRuntime(engine)
    calls: list[dict[str, Any]] = []

    run = rt.commit(
        scenario_id="PG-005",
        action_contract=_action(purpose_id="PURPOSE_B"),
        now=NOW,
        effect_fn=_effect(calls),
    )

    assert run.evidence.decision == "DENY"
    assert run.evidence.effect_committed is False
    assert calls == []
    assert run.unsafe_commit is False


# --------------------------------------------------------------------------
# 8. constraint mismatch
# --------------------------------------------------------------------------


def test_constraint_mismatch_fails_closed() -> None:
    engine = base_engine(now=NOW)
    rt = TwoCoreRuntime(engine)
    calls: list[dict[str, Any]] = []

    run = rt.commit(
        scenario_id="PG-006",
        action_contract=_action(constraints={"limit": "HIGH"}),
        now=NOW,
        effect_fn=_effect(calls),
    )

    assert run.evidence.decision == "DENY"
    assert run.evidence.effect_committed is False
    assert calls == []
    assert run.unsafe_commit is False


# --------------------------------------------------------------------------
# 9. stale Kernel state/context
# --------------------------------------------------------------------------


def test_stale_kernel_context_fails_closed() -> None:
    engine = base_engine(now=NOW)
    rt = TwoCoreRuntime(engine)
    calls: list[dict[str, Any]] = []
    stale = build_context(engine, _action(), now=NOW, nonce="nonce:stale")
    stale["time"] = {}

    run = rt.commit(
        scenario_id="PG-007",
        action_contract=_action(),
        now=NOW,
        effect_fn=_effect(calls),
        stale_context=stale,
    )

    assert run.evidence.decision == "DENY"
    assert run.evidence.effect_committed is False
    assert calls == []
    assert run.unsafe_commit is False


# --------------------------------------------------------------------------
# 10. action substitution after authorization
# --------------------------------------------------------------------------


def test_action_substitution_after_authorization_is_blocked() -> None:
    engine = base_engine(now=NOW)
    rt = TwoCoreRuntime(engine)
    calls: list[dict[str, Any]] = []

    run = rt.commit(
        scenario_id="PG-011",
        action_contract=_action(),
        now=NOW,
        effect_fn=_effect(calls),
        presented_action=_action(target="target-2", constraints={"limit": "HIGH"}),
    )

    assert run.evidence.decision == "ALLOW"
    assert run.evidence.effect_committed is False
    assert calls == []
    assert run.unsafe_commit is False
    assert "changed after authorization" in (run.evidence.reason or "")


# --------------------------------------------------------------------------
# 11. material state change before commit
# --------------------------------------------------------------------------


def test_material_state_change_before_commit_is_blocked() -> None:
    engine = base_engine(now=NOW)
    rt = TwoCoreRuntime(engine)
    calls: list[dict[str, Any]] = []

    # The effect is bound to the pre-change context.
    plan_ctx = build_context(engine, _action(), now=NOW, nonce="nonce:plan")
    plan_decision = RealReht().authorize(plan_ctx, _action())
    assert plan_decision.decision == "ALLOW"
    rt.adapter.bind(plan_decision, _action(), plan_ctx)

    # Material state change lands before commit.
    engine.append(_state_change_event(now=NOW))
    fresh_ctx = build_context(engine, _action(), now=NOW, nonce="nonce:commit")

    with pytest.raises(EffectDenied, match="context changed after authorization"):
        rt.adapter.execute(
            decision=plan_decision,
            action_contract=_action(),
            ctx=fresh_ctx,
            effect_fn=_effect(calls),
        )
    assert calls == []


# --------------------------------------------------------------------------
# 12. direct-effect bypass
# --------------------------------------------------------------------------


def test_direct_effect_bypass_is_blocked() -> None:
    engine = base_engine(now=NOW)
    rt = TwoCoreRuntime(engine)
    calls: list[dict[str, Any]] = []

    run = rt.commit(
        scenario_id="PG-010",
        action_contract=_action(),
        now=NOW,
        effect_fn=_effect(calls),
        force_direct_effect=True,
    )

    assert run.evidence.effect_committed is False
    assert calls == []
    assert run.bypass is True
    assert run.unsafe_commit is False


def test_adapter_denies_effect_without_permit() -> None:
    adapter = MechanicalEffectAdapter()
    calls: list[dict[str, Any]] = []
    with pytest.raises(EffectDenied, match="without REHT permit"):
        adapter.execute(
            decision=DecisionResult(decision="DENY", reason="no permit"),
            action_contract=_action(),
            ctx={},
            effect_fn=_effect(calls),
        )
    assert calls == []


# --------------------------------------------------------------------------
# 13. permit replay / single-use
# --------------------------------------------------------------------------


def test_permit_replay_single_use_blocks_second_effect() -> None:
    engine = base_engine(now=NOW)
    rt = TwoCoreRuntime(engine)
    calls: list[dict[str, Any]] = []

    # Authorize exactly once and obtain the bound permit.
    ctx = build_context(engine, _action(), now=NOW, nonce="nonce")
    decision = RealReht().authorize(ctx, _action())
    assert decision.decision == "ALLOW"
    rt.adapter.bind(decision, _action(), ctx)

    # The same permit commits exactly one effect.
    rt.adapter.execute(decision=decision, action_contract=_action(), ctx=ctx, effect_fn=_effect(calls))
    assert len(calls) == 1

    # Replaying the same permit against the same exact binding is denied.
    with pytest.raises(EffectDenied, match="permit replay"):
        rt.adapter.execute(decision=decision, action_contract=_action(), ctx=ctx, effect_fn=_effect(calls))
    assert len(calls) == 1


def test_adapter_denies_replay_of_consumed_permit() -> None:
    engine = base_engine(now=NOW)
    rt = TwoCoreRuntime(engine)
    calls: list[dict[str, Any]] = []
    ctx = build_context(engine, _action(), now=NOW, nonce="nonce")
    decision = RealReht().authorize(ctx, _action())
    assert decision.decision == "ALLOW"
    rt.adapter.bind(decision, _action(), ctx)

    rt.adapter.execute(decision=decision, action_contract=_action(), ctx=ctx, effect_fn=_effect(calls))
    with pytest.raises(EffectDenied, match="permit replay"):
        rt.adapter.execute(decision=decision, action_contract=_action(), ctx=ctx, effect_fn=_effect(calls))
    assert calls == [{}]


# --------------------------------------------------------------------------
# 14. governed consequential state/memory write
# --------------------------------------------------------------------------


def test_governed_consequential_memory_write_fails_closed() -> None:
    engine = base_engine(now=NOW)
    rt = TwoCoreRuntime(engine)
    calls: list[dict[str, Any]] = []

    run = rt.commit(
        scenario_id="PG-009",
        action_contract=_action(capability="WRITE_GOVERNED_MEMORY", target="future-policy-state"),
        now=NOW,
        effect_fn=_effect(calls),
    )

    assert run.evidence.decision == "DENY"
    assert run.evidence.effect_committed is False
    assert calls == []
    assert run.unsafe_commit is False


# --------------------------------------------------------------------------
# 15. STEP_UP requirement
# --------------------------------------------------------------------------


def test_step_up_requirement_emits_no_permit_and_no_effect() -> None:
    engine = base_engine(now=NOW)
    rt = TwoCoreRuntime(engine)
    calls: list[dict[str, Any]] = []

    run = rt.commit(
        scenario_id="PG-014",
        action_contract=_action(
            step_up={"required": True, "reason": "material ambiguity requires authorized decision"}
        ),
        now=NOW,
        effect_fn=_effect(calls),
    )

    assert run.evidence.decision == "STEP_UP"
    assert run.evidence.effect_committed is False
    assert run.evidence.permit_ref is None
    assert calls == []
    assert run.unsafe_commit is False


# --------------------------------------------------------------------------
# Aggregate PASS criteria
# --------------------------------------------------------------------------


def test_two_core_aggregate_has_zero_unsafe_bypass_replay_and_no_false_authority() -> None:
    engine = base_engine(now=NOW)
    rt = TwoCoreRuntime(engine)
    calls: list[dict[str, Any]] = []

    scenarios = [
        ("valid", _action(), {}),
        ("missing_identity", _action(), {"identity": False}),
        ("missing_authority", _action(), {"authority": False}),
        ("scope", _action(target="target-2"), {}),
        ("purpose", _action(purpose_id="PURPOSE_B"), {}),
        ("constraint", _action(constraints={"limit": "HIGH"}), {}),
        ("memory_write", _action(capability="WRITE_GOVERNED_MEMORY", target="future-policy-state"), {}),
        ("step_up", _action(step_up={"required": True, "reason": "gate"}), {}),
    ]

    for scenario_id, action, kwargs in scenarios:
        engine = base_engine(now=NOW, identity=kwargs.get("identity", True), authority=kwargs.get("authority", True))
        rt = TwoCoreRuntime(engine)
        run = rt.commit(
            scenario_id=scenario_id,
            action_contract=action,
            now=NOW,
            effect_fn=_effect(calls),
        )
        assert run.unsafe_commit is False, scenario_id
        assert run.bypass is False, scenario_id
        assert run.replay_effect is False, scenario_id
        assert run.false_authority_creation is False, scenario_id
        assert run.evidence.closed is True, scenario_id
        if action.get("step_up"):
            assert run.evidence.decision == "STEP_UP"
        elif (
            kwargs.get("identity") is False
            or kwargs.get("authority") is False
            or action.get("target") != TARGET
            or action.get("purpose_id") != PURPOSE
            or action.get("constraints")
            or action.get("capability") != CAPABILITY
        ):
            assert run.evidence.decision == "DENY"
            assert run.evidence.effect_committed is False
        else:
            assert run.evidence.decision == "ALLOW"
            assert run.evidence.effect_committed is True