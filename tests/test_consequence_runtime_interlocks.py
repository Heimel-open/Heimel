from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

import pytest

from valo_reht import (
    BoundaryEffect,
    EffectBoundary,
    EffectDenied,
    InMemoryPermitStore,
    PostconditionResult,
    ProbeDisposition,
    ProbeResult,
    ResourceBudget,
    ResourceBudgetLedger,
    ResourceReservation,
    RuntimeControlPlane,
)
from valo_reht.contracts import DecisionResult
from valo_reht.runtime_interlocks import MechanicalBlock, canonical_digest


def _digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _action(**extra: Any) -> dict[str, Any]:
    action = {
        "action_id": "action:interlock",
        "capability": "SEND_PAYMENT",
        "action_type": "SEND_PAYMENT",
        "target": "merchant:1",
        "actor_id": "actor:1",
        "principal_id": "principal:1",
    }
    action.update(extra)
    return action


def _context(action: dict[str, Any]) -> dict[str, Any]:
    return {
        "state": "READY",
        "actor_id": action.get("actor_id"),
        "principal_id": action.get("principal_id"),
        "authority_state_id": "authority:1",
    }


class StaticReht:
    def __init__(
        self,
        decision: str = "ALLOW",
        *,
        permit_ref: str = "permit:1",
        before_return=None,
    ) -> None:
        self.decision = decision
        self.permit_ref = permit_ref
        self.before_return = before_return
        self.calls = 0

    def authorize(
        self,
        execution_context: dict[str, Any],
        action_contract: dict[str, Any],
    ) -> DecisionResult:
        self.calls += 1
        if self.before_return is not None:
            self.before_return()
        if self.decision != "ALLOW":
            return DecisionResult(decision=self.decision, reason="test restriction")
        return DecisionResult(
            decision="ALLOW",
            clearance_ref="clearance:1",
            permit_ref=self.permit_ref,
            execution_context_hash=_digest(execution_context),
        )


def _sealed(calls: list[dict[str, Any]] | None = None) -> BoundaryEffect:
    calls = calls if calls is not None else []
    return BoundaryEffect.seal(
        "payment-adapter",
        lambda action: calls.append(action) or {"ok": True, "effect": action["action_id"]},
    )


def _dev_boundary(
    store: InMemoryPermitStore | None = None,
    **kwargs: Any,
) -> EffectBoundary:
    return EffectBoundary.for_development(store or InMemoryPermitStore(), **kwargs)


def test_boundary_effect_has_no_direct_invocation_path() -> None:
    effect = _sealed()
    with pytest.raises(MechanicalBlock, match="NO_DIRECT_EFFECT_PATH"):
        effect.invoke(_action())


@pytest.mark.parametrize(
    "configure,match",
    [
        (lambda cp: cp.halt_global(), "HALT_GLOBAL"),
        (lambda cp: cp.halt_scope("SEND_PAYMENT"), "HALT_SCOPE:SEND_PAYMENT"),
        (lambda cp: cp.revoke_authority("authority:1"), "REVOKED_AUTHORITY"),
        (lambda cp: cp.revoke_principal("principal:1"), "REVOKED_PRINCIPAL"),
        (lambda cp: cp.revoke_actor("actor:1"), "REVOKED_ACTOR"),
    ],
)
def test_runtime_control_blocks_without_calling_reht_or_effect(configure, match: str) -> None:
    control = RuntimeControlPlane()
    configure(control)
    reht = StaticReht()
    calls: list[dict[str, Any]] = []
    boundary = _dev_boundary(runtime_control=control)

    with pytest.raises(EffectDenied, match=match) as excinfo:
        boundary.commit(
            reht=reht,
            context_factory=_context,
            action_contract=_action(),
            effect=_sealed(calls),
        )

    assert reht.calls == 0
    assert calls == []
    assert excinfo.value.receipt is not None
    assert excinfo.value.receipt.status == "BLOCKED"
    assert excinfo.value.evidence_closure is not None
    assert excinfo.value.evidence_closure.closed is False


def test_late_halt_after_reht_allow_blocks_before_permit_consumption() -> None:
    control = RuntimeControlPlane()
    store = InMemoryPermitStore()
    calls: list[dict[str, Any]] = []
    reht = StaticReht(before_return=control.halt_global)
    boundary = _dev_boundary(store, runtime_control=control)

    with pytest.raises(EffectDenied, match="HALT_GLOBAL"):
        boundary.commit(
            reht=reht,
            context_factory=_context,
            action_contract=_action(),
            effect=_sealed(calls),
        )

    assert calls == []
    assert store.is_consumed("permit:1") is False


def test_halt_arriving_during_permit_consumption_blocks_before_effect() -> None:
    control = RuntimeControlPlane()
    calls: list[dict[str, Any]] = []

    class HaltingPermitStore(InMemoryPermitStore):
        def consume_once(self, permit_ref: str) -> bool:
            consumed = super().consume_once(permit_ref)
            if consumed:
                control.halt_global()
            return consumed

    store = HaltingPermitStore()
    boundary = _dev_boundary(store, runtime_control=control)

    with pytest.raises(EffectDenied, match="HALT_GLOBAL") as excinfo:
        boundary.commit(
            reht=StaticReht(),
            context_factory=_context,
            action_contract=_action(),
            effect=_sealed(calls),
        )

    assert store.is_consumed("permit:1") is True
    assert calls == []
    assert excinfo.value.receipt is not None
    assert excinfo.value.receipt.status == "BLOCKED"
    assert excinfo.value.receipt.reason == "HALT_GLOBAL"


@dataclass
class FixedProbe:
    disposition: ProbeDisposition
    reason: str

    def evaluate(
        self,
        action: Mapping[str, Any],
        execution_context: Mapping[str, Any],
    ) -> ProbeResult:
        return ProbeResult(self.disposition, self.reason, {"probe": "fixed"})


@pytest.mark.parametrize("disposition", [ProbeDisposition.BLOCK, ProbeDisposition.STEP_UP])
def test_probe_can_stop_but_never_authorize(disposition: ProbeDisposition) -> None:
    reht = StaticReht()
    calls: list[dict[str, Any]] = []
    boundary = _dev_boundary(
        probes=(FixedProbe(disposition, f"PROBE_{disposition.value}"),),
    )
    with pytest.raises(EffectDenied, match=f"PROBE_{disposition.value}"):
        boundary.commit(
            reht=reht,
            context_factory=_context,
            action_contract=_action(),
            effect=_sealed(calls),
        )
    assert reht.calls == 0
    assert calls == []


def test_probe_result_rejects_authority_creation() -> None:
    with pytest.raises(ValueError, match="cannot grant execution authority"):
        ProbeResult(ProbeDisposition.PASS, execution_authority=True)


def _contained_context(action: dict[str, Any]) -> dict[str, Any]:
    ctx = _context(action)
    ctx["containment"] = {
        "status": "VALID",
        "revoked": False,
        "breached": False,
        "egress_mode": "ADAPTER",
        "credential_lease_active": True,
        "runtime_id": "runtime:1",
        "environment_digest": "sha256:env",
        "egress_adapter": "payment-adapter",
        "credential_lease_id": "lease:1",
        "path_head_digest": "sha256:path",
        "epoch": 7,
    }
    return ctx


def _contained_action(**extra: Any) -> dict[str, Any]:
    return _action(
        containment_required=True,
        containment_binding={
            "runtime_id": "runtime:1",
            "environment_digest": "sha256:env",
            "egress_adapter": "payment-adapter",
            "credential_lease_id": "lease:1",
            "path_head_digest": "sha256:path",
            "epoch": 7,
        },
        **extra,
    )


def test_containment_exact_adapter_path_allows_commit() -> None:
    calls: list[dict[str, Any]] = []
    result = _dev_boundary().commit(
        reht=StaticReht(),
        context_factory=_contained_context,
        action_contract=_contained_action(),
        effect=_sealed(calls),
    )
    assert result.effect_committed is True
    assert len(calls) == 1


def test_direct_network_egress_is_blocked() -> None:
    calls: list[dict[str, Any]] = []

    def bad_context(action: dict[str, Any]) -> dict[str, Any]:
        ctx = _contained_context(action)
        ctx["containment"]["egress_mode"] = "NETWORK"
        return ctx

    with pytest.raises(EffectDenied, match="DIRECT_EGRESS_FORBIDDEN"):
        _dev_boundary().commit(
            reht=StaticReht(),
            context_factory=bad_context,
            action_contract=_contained_action(),
            effect=_sealed(calls),
        )
    assert calls == []


def test_containment_binding_mismatch_is_blocked() -> None:
    action = _contained_action()
    action["containment_binding"]["runtime_id"] = "runtime:other"
    with pytest.raises(EffectDenied, match="CONTAINMENT_BINDING_MISMATCH:runtime_id"):
        _dev_boundary().commit(
            reht=StaticReht(),
            context_factory=_contained_context,
            action_contract=action,
            effect=_sealed(),
        )


def test_child_budget_cannot_widen_parent() -> None:
    ledger = ResourceBudgetLedger()
    ledger.register_budget(ResourceBudget("parent", {"usd": 10.0}))
    with pytest.raises(ValueError, match="cannot widen parent"):
        ledger.register_budget(ResourceBudget("child", {"usd": 11.0}, parent_id="parent"))


def test_sibling_reservations_share_parent_hard_ceiling() -> None:
    ledger = ResourceBudgetLedger()
    ledger.register_budget(ResourceBudget("parent", {"usd": 10.0}))
    ledger.register_budget(ResourceBudget("a", {"usd": 10.0}, parent_id="parent"))
    ledger.register_budget(ResourceBudget("b", {"usd": 10.0}, parent_id="parent"))
    digest = canonical_digest(_action())
    ledger.reserve(ResourceReservation("ra", "a", digest, {"usd": 6.0}))
    with pytest.raises(ValueError, match="parent:usd"):
        ledger.reserve(ResourceReservation("rb", "b", digest, {"usd": 5.0}))


def test_boundary_consumes_action_bound_resource_reservation_once() -> None:
    action = _action(resource_bounds_required=True, resource_reservation_id="res:1")
    ledger = ResourceBudgetLedger()
    ledger.register_budget(ResourceBudget("budget:1", {"usd": 10.0}))
    ledger.reserve(
        ResourceReservation(
            "res:1",
            "budget:1",
            canonical_digest(action),
            {"usd": 2.0},
        )
    )
    boundary = _dev_boundary(resource_ledger=ledger)
    result = boundary.commit(
        reht=StaticReht(),
        context_factory=_context,
        action_contract=action,
        effect=_sealed(),
    )
    assert result.effect_committed is True
    assert ledger.is_consumed("res:1") is True


def test_resource_reservation_must_match_exact_action() -> None:
    action = _action(resource_bounds_required=True, resource_reservation_id="res:1")
    ledger = ResourceBudgetLedger()
    ledger.register_budget(ResourceBudget("budget:1", {"usd": 10.0}))
    ledger.reserve(
        ResourceReservation(
            "res:1",
            "budget:1",
            canonical_digest(_action(target="merchant:other")),
            {"usd": 2.0},
        )
    )
    with pytest.raises(EffectDenied, match="RESOURCE_ACTION_BINDING_MISMATCH"):
        _dev_boundary(resource_ledger=ledger).commit(
            reht=StaticReht(),
            context_factory=_context,
            action_contract=action,
            effect=_sealed(),
        )


class MatchingPostcondition:
    def check(
        self,
        action: Mapping[str, Any],
        execution_context: Mapping[str, Any],
        effect_result: Any,
    ) -> PostconditionResult:
        return PostconditionResult(
            verified=bool(effect_result.get("ok")),
            reason="effect observed",
            evidence={"effect": effect_result.get("effect")},
        )


class FailingPostcondition:
    def check(
        self,
        action: Mapping[str, Any],
        execution_context: Mapping[str, Any],
        effect_result: Any,
    ) -> PostconditionResult:
        return PostconditionResult(verified=False, reason="REALITY_DIVERGENCE")


def test_required_postcondition_verified_closes_completion() -> None:
    result = _dev_boundary(
        postcondition_checker=MatchingPostcondition(),
    ).commit(
        reht=StaticReht(),
        context_factory=_context,
        action_contract=_action(postconditions_required=True),
        effect=_sealed(),
    )
    assert result.effect_committed is True
    assert result.valid_completion is True
    assert result.receipt is not None
    assert result.receipt.postconditions_verified is True


def test_reality_divergence_commits_effect_but_not_valid_completion() -> None:
    result = _dev_boundary(
        postcondition_checker=FailingPostcondition(),
    ).commit(
        reht=StaticReht(),
        context_factory=_context,
        action_contract=_action(postconditions_required=True),
        effect=_sealed(),
    )
    assert result.effect_committed is True
    assert result.valid_completion is False
    assert result.receipt is not None
    assert result.receipt.status == "COMMITTED_WITH_DEVIATION"
    assert result.receipt.reason == "REALITY_DIVERGENCE"


def test_missing_required_postcondition_checker_is_not_valid_completion() -> None:
    result = _dev_boundary().commit(
        reht=StaticReht(),
        context_factory=_context,
        action_contract=_action(postconditions_required=True),
        effect=_sealed(),
    )
    assert result.effect_committed is True
    assert result.valid_completion is False
    assert result.receipt is not None
    assert result.receipt.status == "COMMITTED_UNVERIFIED"


def test_success_receipt_binds_reht_artifacts_and_grants_no_authority() -> None:
    action = _action()
    boundary = _dev_boundary()
    result = boundary.commit(
        reht=StaticReht(),
        context_factory=_context,
        action_contract=action,
        effect=_sealed(),
    )
    receipt = result.receipt
    assert receipt is not None
    assert receipt.action_digest == canonical_digest(action)
    assert receipt.reht_decision == "ALLOW"
    assert receipt.clearance_ref == "clearance:1"
    assert receipt.permit_ref == "permit:1"
    assert receipt.effect_name == "payment-adapter"
    assert receipt.authority_granted is False
    assert result.evidence_closure is not None
    assert result.evidence_closure.closed is False
    assert boundary.evidence_sink.receipts() == [receipt]  # type: ignore[attr-defined]
