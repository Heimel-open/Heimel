from __future__ import annotations

import hashlib
import json
from typing import Any

from valo_kernel.causal_capacity import GovernedEffectBoundary, assess_causal_capacity
from valo_kernel.effect_boundary import BoundaryDisposition, EffectChannel, EffectChannelKind
from valo_reht import BoundaryEffect
from valo_reht.contracts import DecisionResult
from valo_reht.effect_boundary import EffectBoundary, InMemoryPermitStore


def _digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class StaticReht:
    def __init__(self, decision: str) -> None:
        self.decision = decision

    def authorize(
        self,
        execution_context: dict[str, Any],
        action_contract: dict[str, Any],
    ) -> DecisionResult:
        if self.decision != "ALLOW":
            return DecisionResult(decision=self.decision, reason="integration gate")
        return DecisionResult(
            decision="ALLOW",
            permit_ref="permit:causal-integration",
            clearance_ref="clearance:causal-integration",
            execution_context_hash=_digest(execution_context),
        )


def _governed_boundary() -> GovernedEffectBoundary:
    return GovernedEffectBoundary(
        boundary_ref="reht-boundary",
        explicit_declared=True,
        exact_effect_bound=True,
        authorized_now=True,
        deny_enforceable=True,
        fail_closed=True,
        evidence_capable=True,
    )


def _channel(kind: EffectChannelKind, *, boundary: str | None) -> EffectChannel:
    return EffectChannel(
        channel_id=kind.value.lower(),
        kind=kind,
        source_domain="untrusted-compute",
        target_domain="external-world",
        crosses_trust_boundary=True,
        governed_boundary_ref=boundary,
    )


def _action() -> dict[str, Any]:
    return {
        "action_id": "action:causal-integration",
        "capability": "DO_EFFECT",
        "target": "target-1",
        "payload": {"value": 1},
    }


def _context(_: dict[str, Any]) -> dict[str, Any]:
    return {"kernel_sequence": 1, "state": "READY"}


def test_kernel_rejects_ungoverned_human_relay_before_runtime_effect() -> None:
    assessment = assess_causal_capacity(
        (_channel(EffectChannelKind.HUMAN_RELAY, boundary=None),),
        boundaries=(_governed_boundary(),),
    )
    assert assessment.disposition is BoundaryDisposition.DENY
    assert assessment.reason_codes == ("NO_UNGOVERNED_CAUSAL_EFFECT_PATH_VIOLATION",)


def test_reht_deny_has_null_effect_even_when_effect_object_exists() -> None:
    boundary = EffectBoundary.for_development(InMemoryPermitStore())
    calls: list[dict[str, Any]] = []
    result = boundary.commit(
        reht=StaticReht("DENY"),
        context_factory=_context,
        action_contract=_action(),
        effect=BoundaryEffect.seal("causal-integration", lambda action: calls.append(action)),
    )
    assert result.effect_committed is False
    assert calls == []


def test_governed_kernel_path_plus_reht_allow_can_commit_exact_effect() -> None:
    assessment = assess_causal_capacity(
        (_channel(EffectChannelKind.DIRECT_API, boundary="reht-boundary"),),
        boundaries=(_governed_boundary(),),
    )
    assert assessment.disposition is BoundaryDisposition.GOVERNED

    boundary = EffectBoundary.for_development(InMemoryPermitStore())
    calls: list[dict[str, Any]] = []
    result = boundary.commit(
        reht=StaticReht("ALLOW"),
        context_factory=_context,
        action_contract=_action(),
        effect=BoundaryEffect.seal(
            "causal-integration",
            lambda action: calls.append(action) or {"ok": True},
        ),
    )
    assert result.effect_committed is True
    assert result.valid_completion is True
    assert calls == [_action()]
