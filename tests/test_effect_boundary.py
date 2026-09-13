from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Lock
from typing import Any

import pytest

from valo_reht import BoundaryEffect, ExecutionRecoveryRequired, RecoveryClassification
from valo_reht.contracts import DecisionResult
from valo_reht.effect_boundary import EffectBoundary, EffectDenied, InMemoryPermitStore


def _digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class StaticReht:
    def __init__(
        self,
        decision: str,
        *,
        permit_ref: str = "permit:test",
        bad_context_binding: bool = False,
    ) -> None:
        self.decision = decision
        self.permit_ref = permit_ref
        self.bad_context_binding = bad_context_binding
        self.seen_actions: list[dict[str, Any]] = []

    def authorize(
        self,
        execution_context: dict[str, Any],
        action_contract: dict[str, Any],
    ) -> DecisionResult:
        self.seen_actions.append(deepcopy(action_contract))
        if self.decision != "ALLOW":
            return DecisionResult(decision=self.decision, reason="test gate")
        return DecisionResult(
            decision="ALLOW",
            permit_ref=self.permit_ref,
            clearance_ref="clearance:test",
            execution_context_hash=(
                "bad-binding" if self.bad_context_binding else _digest(execution_context)
            ),
        )


def _context(_: dict[str, Any]) -> dict[str, Any]:
    return {"kernel_sequence": 7, "state": "READY"}


def _action() -> dict[str, Any]:
    return {
        "action_id": "action:test",
        "capability": "DO_EFFECT",
        "target": "target-1",
        "payload": {"value": 1},
    }


def _boundary() -> tuple[EffectBoundary, InMemoryPermitStore]:
    store = InMemoryPermitStore()
    return EffectBoundary.for_development(store), store


def _effect(fn, name: str = "test-effect") -> BoundaryEffect:
    return BoundaryEffect.seal(name, fn)


@pytest.mark.parametrize("decision", ["DENY", "STEP_UP"])
def test_non_allow_never_invokes_effect(decision: str) -> None:
    boundary, _ = _boundary()
    calls: list[dict[str, Any]] = []

    result = boundary.commit(
        reht=StaticReht(decision),
        context_factory=_context,
        action_contract=_action(),
        effect=_effect(lambda action: calls.append(action)),
    )

    assert result.decision.decision == decision
    assert result.effect_committed is False
    assert result.valid_completion is False
    assert result.receipt is not None
    assert result.receipt.status == "NOT_COMMITTED"
    assert result.evidence_closure is not None
    assert result.evidence_closure.closed is False
    assert calls == []


def test_allow_invokes_effect_with_exact_authorized_snapshot() -> None:
    boundary, _ = _boundary()
    reht = StaticReht("ALLOW")
    proposed = _action()
    effects: list[dict[str, Any]] = []

    def context_factory(action: dict[str, Any]) -> dict[str, Any]:
        assert action["payload"]["value"] == 1
        proposed["payload"]["value"] = 999
        return _context(action)

    result = boundary.commit(
        reht=reht,
        context_factory=context_factory,
        action_contract=proposed,
        effect=_effect(lambda action: effects.append(deepcopy(action)) or {"ok": True}),
    )

    assert result.effect_committed is True
    assert result.valid_completion is True
    assert result.receipt is not None
    assert result.receipt.status == "COMMITTED"
    assert result.evidence_closure is not None
    assert result.evidence_closure.closed is False
    assert reht.seen_actions == [_action()]
    assert effects == [_action()]
    assert proposed["payload"]["value"] == 999


def test_allow_without_permit_fails_closed() -> None:
    class MissingPermitReht:
        def authorize(self, execution_context: dict[str, Any], action_contract: dict[str, Any]) -> DecisionResult:
            return DecisionResult(
                decision="ALLOW",
                execution_context_hash=_digest(execution_context),
            )

    boundary, _ = _boundary()
    with pytest.raises(EffectDenied, match="ALLOW_WITHOUT_REHT_PERMIT") as excinfo:
        boundary.commit(
            reht=MissingPermitReht(),
            context_factory=_context,
            action_contract=_action(),
            effect=_effect(lambda action: {"unexpected": action}),
        )
    assert excinfo.value.receipt is not None
    assert excinfo.value.receipt.status == "BLOCKED"
    assert excinfo.value.evidence_closure is not None


def test_context_binding_mismatch_fails_closed() -> None:
    boundary, _ = _boundary()
    calls: list[dict[str, Any]] = []

    with pytest.raises(EffectDenied, match="EXECUTION_CONTEXT_BINDING_MISMATCH"):
        boundary.commit(
            reht=StaticReht("ALLOW", bad_context_binding=True),
            context_factory=_context,
            action_contract=_action(),
            effect=_effect(lambda action: calls.append(action)),
        )

    assert calls == []


def test_permit_is_single_use_and_closed_attempt_is_not_replayed() -> None:
    boundary, store = _boundary()
    reht = StaticReht("ALLOW", permit_ref="permit:single")
    calls: list[dict[str, Any]] = []

    first = boundary.commit(
        reht=reht,
        context_factory=_context,
        action_contract=_action(),
        effect=_effect(lambda action: calls.append(action) or {"ok": True}),
    )
    assert first.effect_committed is True

    with pytest.raises(ExecutionRecoveryRequired) as excinfo:
        boundary.commit(
            reht=reht,
            context_factory=_context,
            action_contract=_action(),
            effect=_effect(lambda action: calls.append(action)),
        )
    assert excinfo.value.recovery.classification is RecoveryClassification.CLOSED
    assert len(calls) == 1
    assert store.is_consumed("permit:single") is True


def test_concurrent_replay_commits_exactly_once() -> None:
    boundary, _ = _boundary()
    reht = StaticReht("ALLOW", permit_ref="permit:race")
    effect_count = 0
    effect_lock = Lock()
    sealed: BoundaryEffect

    def raw_effect(_: dict[str, Any]) -> dict[str, Any]:
        nonlocal effect_count
        with effect_lock:
            effect_count += 1
        return {"ok": True}

    sealed = _effect(raw_effect)

    def attempt(_: int) -> str:
        try:
            result = boundary.commit(
                reht=reht,
                context_factory=_context,
                action_contract=_action(),
                effect=sealed,
            )
        except ExecutionRecoveryRequired:
            return "RECOVERY_REQUIRED"
        assert result.effect_committed is True
        return "COMMITTED"

    with ThreadPoolExecutor(max_workers=12) as pool:
        outcomes = list(pool.map(attempt, range(12)))

    assert outcomes.count("COMMITTED") == 1
    assert outcomes.count("RECOVERY_REQUIRED") == 11
    assert effect_count == 1


def test_effect_exception_is_indeterminate_and_does_not_rearm_permit() -> None:
    boundary, store = _boundary()
    reht = StaticReht("ALLOW", permit_ref="permit:failure")

    def fail(_: dict[str, Any]) -> None:
        raise RuntimeError("external failure")

    with pytest.raises(RuntimeError, match="external failure"):
        boundary.commit(
            reht=reht,
            context_factory=_context,
            action_contract=_action(),
            effect=_effect(fail),
        )

    assert store.is_consumed("permit:failure") is True
    receipts = boundary.evidence_sink.receipts()  # type: ignore[attr-defined]
    assert receipts[-1].status == "INDETERMINATE"
    assert receipts[-1].reason is not None
    assert receipts[-1].reason.startswith("EFFECT_EXCEPTION:RuntimeError")

    with pytest.raises(ExecutionRecoveryRequired) as excinfo:
        boundary.commit(
            reht=reht,
            context_factory=_context,
            action_contract=_action(),
            effect=_effect(lambda action: {"unexpected": action}),
        )
    assert excinfo.value.recovery.classification is RecoveryClassification.CLOSED
    assert excinfo.value.recovery.receipt is not None
    assert excinfo.value.recovery.receipt.status == "INDETERMINATE"


def test_raw_callable_is_not_a_valid_production_effect() -> None:
    boundary, _ = _boundary()
    with pytest.raises(TypeError, match="requires BoundaryEffect"):
        boundary.commit(
            reht=StaticReht("ALLOW"),
            context_factory=_context,
            action_contract=_action(),
            effect=lambda action: action,  # type: ignore[arg-type]
        )
