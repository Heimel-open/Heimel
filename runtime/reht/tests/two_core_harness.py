"""TEST-ONLY two-core runtime harness.

Exercises the authoritative runtime path:

    Kernel state/context
        -> RealReht
        -> minimal mechanical effect adapter
        -> outcome evidence
        -> Kernel observation/admission

This is NOT a production layer and it does NOT reconstruct the legacy
``Kernel -> REHT -> RACS -> Gateway -> Veritas`` chain. It exists only so the
two-core path can be regression-tested against the frozen paired-governance
scenario families.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from valo_kernel import KernelEngine, build_execution_context
from valo_kernel.contracts import (
    Authority,
    CanonicalEvent,
    Entity,
    EntityType,
    EventType,
    IdentityClaim,
    Provenance,
    TimeWindow,
    VerificationStatus,
)
from valo_kernel.kernel.errors import ExecutionContextError

from valo_reht import RealReht
from valo_reht.contracts import DecisionResult

TENANT = "tenant:two-core"
ACTOR = "agent:two-core"
TARGET = "target-1"
CAPABILITY = "DO_EFFECT"
PURPOSE = "PURPOSE_A"

EffectFn = Callable[[dict[str, Any]], dict[str, Any]]


def _digest(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Kernel fixture builders (Kernel is the only authoritative state owner).
# --------------------------------------------------------------------------


def _provenance(source_id: str) -> Provenance:
    return Provenance(source_type="system", source_id=source_id, source_system="two-core")


def _entity_event(entity_id: str, entity_type: EntityType, *, now: datetime) -> CanonicalEvent:
    return CanonicalEvent(
        event_id=f"entity:{entity_id}",
        event_type=EventType.ENTITY_REGISTERED,
        tenant_id=TENANT,
        subject=entity_id,
        source="kernel",
        timestamp=now,
        effective_at=now,
        payload={
            "entity": Entity(
                entity_id=entity_id,
                entity_type=entity_type,
                tenant_id=TENANT,
                state="READY",
                provenance=_provenance(entity_id),
            )
        },
    )


def _identity_event(*, now: datetime) -> CanonicalEvent:
    return CanonicalEvent(
        event_id="identity:agent",
        event_type=EventType.IDENTITY_CLAIMED,
        tenant_id=TENANT,
        subject=ACTOR,
        source="kernel",
        timestamp=now,
        effective_at=now,
        payload={
            "identity": IdentityClaim(
                identity_id="identity:agent",
                entity_id=ACTOR,
                tenant_id=TENANT,
                claim_type="service_identity",
                value=ACTOR,
                verification_status=VerificationStatus.VERIFIED,
            )
        },
    )


def _authority_event(
    *,
    now: datetime,
    valid_until: datetime,
    scope: list[str] | None = None,
    constraints: dict[str, str] | None = None,
    capability: str = CAPABILITY,
) -> CanonicalEvent:
    return CanonicalEvent(
        event_id="authority:agent",
        event_type=EventType.AUTHORITY_GRANTED,
        tenant_id=TENANT,
        subject=ACTOR,
        source="kernel",
        timestamp=now,
        effective_at=now,
        payload={
            "authority": Authority(
                authority_id="authority:agent",
                principal=ACTOR,
                capability=capability,
                scope=scope or [TARGET],
                constraints=constraints or {"purpose_id": PURPOSE, "limit": "LOW"},
                basis="two-core-benchmark",
                validity=TimeWindow(valid_from=now - timedelta(minutes=1), valid_until=valid_until),
            )
        },
    )


def _revoke_event(*, now: datetime) -> CanonicalEvent:
    return CanonicalEvent(
        event_id="authority:revoke",
        event_type=EventType.AUTHORITY_REVOKED,
        tenant_id=TENANT,
        subject=ACTOR,
        source="kernel",
        timestamp=now,
        effective_at=now,
        payload={"authority_id": "authority:agent", "revocation_ref": "revocation:two-core"},
    )


def _state_change_event(*, now: datetime) -> CanonicalEvent:
    return CanonicalEvent(
        event_id="target:material-change",
        event_type=EventType.ENTITY_UPDATED,
        tenant_id=TENANT,
        subject=TARGET,
        source="kernel",
        timestamp=now,
        effective_at=now,
        payload={"entity_id": TARGET, "state": "BUSY"},
    )


def _request_event(*, capability: str, target: str, now: datetime, nonce: str) -> CanonicalEvent:
    return CanonicalEvent(
        event_id=f"request:{nonce}",
        event_type=EventType.RESOURCE_RESERVED,
        tenant_id=TENANT,
        subject=target,
        actor=ACTOR,
        source="benchmark",
        timestamp=now,
        effective_at=now,
        idempotency_key=nonce,
        payload={"capability": capability},
    )


def base_engine(*, now: datetime, identity: bool = True, authority: bool = True) -> KernelEngine:
    engine = KernelEngine(TENANT)
    engine.append(_entity_event(ACTOR, EntityType.AGENT, now=now - timedelta(seconds=2)))
    engine.append(_entity_event(TARGET, EntityType.JOB, now=now - timedelta(seconds=2)))
    if identity:
        engine.append(_identity_event(now=now - timedelta(seconds=2)))
    if authority:
        engine.append(_authority_event(now=now - timedelta(seconds=2), valid_until=now + timedelta(minutes=10)))
    return engine


def build_context(
    engine: KernelEngine,
    action_contract: dict[str, Any],
    *,
    now: datetime,
    nonce: str,
) -> dict[str, Any]:
    request = _request_event(
        capability=action_contract["capability"],
        target=action_contract["target"],
        now=now,
        nonce=nonce,
    )
    return build_execution_context(
        engine.state(),
        actor=ACTOR,
        capability=action_contract["capability"],
        target=action_contract["target"],
        requested_transition=request,
        identity_id=None,
        purpose_id=action_contract.get("purpose_id"),
        moment=now,
        event_position=engine.sequence(),
        execution_nonce=nonce,
    )


# --------------------------------------------------------------------------
# Minimal mechanical effect adapter (TEST-ONLY).
#
# - requires an exact REHT permit/binding;
# - denies any effect without a permit (direct-effect bypass);
# - denies permit replay (single-use);
# - never changes the action after authorization;
# - performs NO authorization itself and creates NO authority.
# --------------------------------------------------------------------------


class EffectDenied(Exception):
    """Mechanical effect refusal. The adapter authorizes nothing."""


class MechanicalEffectAdapter:
    def __init__(self) -> None:
        self._consumed: set[str] = set()
        self._bound: dict[str, dict[str, str]] = {}
        self.effects: list[dict[str, Any]] = []

    def bind(self, decision: DecisionResult, action_contract: dict[str, Any], ctx: dict[str, Any]) -> None:
        if decision.decision != "ALLOW" or not decision.permit_ref:
            raise EffectDenied("no REHT permit to bind")
        self._bound[decision.permit_ref] = {
            "action_digest": _digest(action_contract),
            "ctx_hash": decision.execution_context_hash or _digest(ctx),
        }

    def execute(
        self,
        *,
        decision: DecisionResult,
        action_contract: dict[str, Any],
        ctx: dict[str, Any],
        effect_fn: EffectFn,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if decision.decision != "ALLOW" or not decision.permit_ref:
            raise EffectDenied("direct effect without REHT permit")
        if decision.permit_ref in self._consumed:
            raise EffectDenied("permit replay")
        binding = self._bound.get(decision.permit_ref)
        if binding is None:
            raise EffectDenied("unbound permit")
        if _digest(action_contract) != binding["action_digest"]:
            raise EffectDenied("action changed after authorization")
        if _digest(ctx) != binding["ctx_hash"]:
            raise EffectDenied("execution context changed after authorization")
        self._consumed.add(decision.permit_ref)
        result = effect_fn(arguments or {})
        self.effects.append({"permit_ref": decision.permit_ref, "arguments": arguments or {}, "result": result})
        return result


# --------------------------------------------------------------------------
# Outcome evidence + Kernel observation/admission (TEST-ONLY).
# --------------------------------------------------------------------------


@dataclass
class OutcomeEvidence:
    scenario_id: str
    decision: str
    permit_ref: str | None
    clearance_ref: str | None
    execution_context_hash: str | None
    action_digest: str
    effect_committed: bool
    effect_result: dict[str, Any] | None
    observation_event_id: str | None
    evidence_digest: str
    reason: str | None = None

    @property
    def closed(self) -> bool:
        if self.decision not in ("ALLOW", "STEP_UP", "DENY"):
            return False
        if not self.action_digest:
            return False
        if self.effect_committed:
            return self.permit_ref is not None and self.observation_event_id is not None
        return True


def record_evidence(
    *,
    scenario_id: str,
    decision: DecisionResult,
    action_contract: dict[str, Any],
    ctx: dict[str, Any],
    engine: KernelEngine,
    committed: bool,
    effect_result: dict[str, Any] | None,
    observation_event_id: str | None,
    reason: str | None = None,
) -> OutcomeEvidence:
    evidence = {
        "scenario_id": scenario_id,
        "decision": decision.decision,
        "permit_ref": decision.permit_ref,
        "clearance_ref": decision.clearance_ref,
        "execution_context_hash": decision.execution_context_hash,
        "action_digest": _digest(action_contract),
        "effect_committed": committed,
        "effect_result": effect_result,
        "observation_event_id": observation_event_id,
    }
    return OutcomeEvidence(
        scenario_id=scenario_id,
        decision=decision.decision,
        permit_ref=decision.permit_ref,
        clearance_ref=decision.clearance_ref,
        execution_context_hash=decision.execution_context_hash,
        action_digest=evidence["action_digest"],
        effect_committed=committed,
        effect_result=effect_result,
        observation_event_id=observation_event_id,
        evidence_digest=_digest(evidence),
        reason=reason,
    )


def kernel_observe(
    engine: KernelEngine,
    *,
    scenario_id: str,
    decision: str,
    permit_ref: str | None,
    action_digest: str,
    evidence_digest: str,
    now: datetime,
) -> str:
    """Admit the outcome to the Kernel as a sealed EXTERNAL_EFFECT_OBSERVED event.

    The Kernel observes the result; it grants no authority by doing so.
    """
    event = CanonicalEvent(
        event_id=f"observe:{scenario_id}:{permit_ref or 'none'}",
        event_type=EventType.EXTERNAL_EFFECT_OBSERVED,
        tenant_id=TENANT,
        subject=ACTOR,
        actor=ACTOR,
        source="kernel",
        timestamp=now,
        effective_at=now,
        payload={
            "decision": decision,
            "permit_ref": permit_ref,
            "action_digest": action_digest,
            "evidence_digest": evidence_digest,
        },
    )
    sealed = engine.append(event)
    return sealed.event_id


def authority_count(engine: KernelEngine) -> int:
    return len(engine.state().authorities)


# --------------------------------------------------------------------------
# Two-core runtime driver (TEST-ONLY).
# --------------------------------------------------------------------------


@dataclass
class TwoCoreRun:
    scenario_id: str
    evidence: OutcomeEvidence
    unsafe_commit: bool
    bypass: bool
    replay_effect: bool
    false_authority_creation: bool
    authority_before: int = 0
    authority_after: int = 0


class TwoCoreRuntime:
    """Kernel -> RealReht -> mechanical effect -> evidence -> Kernel."""

    def __init__(self, engine: KernelEngine, *, clock: Callable[[], datetime] | None = None) -> None:
        self.engine = engine
        self.reht = RealReht(clock=clock or (lambda: datetime.now(UTC)))
        self.adapter = MechanicalEffectAdapter()
        self.runs: list[TwoCoreRun] = []

    def commit(
        self,
        *,
        scenario_id: str,
        action_contract: dict[str, Any],
        now: datetime,
        effect_fn: EffectFn,
        nonce: str = "nonce",
        stale_context: dict[str, Any] | None = None,
        presented_action: dict[str, Any] | None = None,
        force_direct_effect: bool = False,
        oracle_unsafe: bool = False,
    ) -> TwoCoreRun:
        authority_before = authority_count(self.engine)
        try:
            ctx = (
                stale_context
                if stale_context is not None
                else build_context(self.engine, action_contract, now=now, nonce=nonce)
            )
        except ExecutionContextError as exc:
            decision = DecisionResult(decision="DENY", reason=f"kernel context fail-closed: {exc}")
            evidence = record_evidence(
                scenario_id=scenario_id,
                decision=decision,
                action_contract=action_contract,
                ctx={},
                engine=self.engine,
                committed=False,
                effect_result=None,
                observation_event_id=None,
                reason=decision.reason,
            )
            return self._record(scenario_id, evidence, oracle_unsafe=oracle_unsafe, authority_before=authority_before)

        result = self.reht.authorize(ctx, action_contract)
        if result.decision != "ALLOW":
            evidence = record_evidence(
                scenario_id=scenario_id,
                decision=result,
                action_contract=action_contract,
                ctx=ctx,
                engine=self.engine,
                committed=False,
                effect_result=None,
                observation_event_id=None,
                reason=result.reason,
            )
            return self._record(scenario_id, evidence, oracle_unsafe=oracle_unsafe, authority_before=authority_before)

        self.adapter.bind(result, action_contract, ctx)

        if force_direct_effect:
            try:
                self.adapter.execute(
                    decision=DecisionResult(decision="DENY", reason="direct effect attempt"),
                    action_contract=action_contract,
                    ctx=ctx,
                    effect_fn=effect_fn,
                )
            except EffectDenied as exc:
                evidence = record_evidence(
                    scenario_id=scenario_id,
                    decision=result,
                    action_contract=action_contract,
                    ctx=ctx,
                    engine=self.engine,
                    committed=False,
                    effect_result=None,
                    observation_event_id=None,
                    reason=f"direct-effect bypass denied: {exc}",
                )
                return self._record(
                    scenario_id,
                    evidence,
                    oracle_unsafe=oracle_unsafe,
                    authority_before=authority_before,
                    bypass_attempt=True,
                )

        try:
            outcome = self.adapter.execute(
                decision=result,
                action_contract=presented_action if presented_action is not None else action_contract,
                ctx=ctx,
                effect_fn=effect_fn,
            )
        except EffectDenied as exc:
            evidence = record_evidence(
                scenario_id=scenario_id,
                decision=result,
                action_contract=action_contract,
                ctx=ctx,
                engine=self.engine,
                committed=False,
                effect_result=None,
                observation_event_id=None,
                reason=str(exc),
            )
            return self._record(scenario_id, evidence, oracle_unsafe=oracle_unsafe, authority_before=authority_before)

        evidence = record_evidence(
            scenario_id=scenario_id,
            decision=result,
            action_contract=action_contract,
            ctx=ctx,
            engine=self.engine,
            committed=True,
            effect_result=outcome,
            observation_event_id=None,
        )
        observation_event_id = kernel_observe(
            self.engine,
            scenario_id=scenario_id,
            decision=result.decision,
            permit_ref=result.permit_ref,
            action_digest=evidence.action_digest,
            evidence_digest=evidence.evidence_digest,
            now=now,
        )
        evidence = record_evidence(
            scenario_id=scenario_id,
            decision=result,
            action_contract=action_contract,
            ctx=ctx,
            engine=self.engine,
            committed=True,
            effect_result=outcome,
            observation_event_id=observation_event_id,
        )
        return self._record(scenario_id, evidence, oracle_unsafe=oracle_unsafe, authority_before=authority_before)

    def _record(
        self,
        scenario_id: str,
        evidence: OutcomeEvidence,
        *,
        oracle_unsafe: bool,
        authority_before: int,
        bypass_attempt: bool = False,
    ) -> TwoCoreRun:
        authority_after = authority_count(self.engine)
        run = TwoCoreRun(
            scenario_id=scenario_id,
            evidence=evidence,
            unsafe_commit=bool(evidence.effect_committed and oracle_unsafe),
            bypass=bypass_attempt,
            replay_effect=bool(
                evidence.effect_committed
                and evidence.permit_ref in self.adapter._consumed
                and len(self.adapter.effects) > 1
            ),
            false_authority_creation=authority_after != authority_before,
            authority_before=authority_before,
            authority_after=authority_after,
        )
        self.runs.append(run)
        return run


__all__ = [
    "ACTOR",
    "CAPABILITY",
    "EffectDenied",
    "MechanicalEffectAdapter",
    "OutcomeEvidence",
    "PURPOSE",
    "TARGET",
    "TENANT",
    "TwoCoreRun",
    "TwoCoreRuntime",
    "authority_count",
    "base_engine",
    "build_context",
    "kernel_observe",
    "record_evidence",
    "_digest",
    "_authority_event",
    "_identity_event",
    "_revoke_event",
    "_state_change_event",
]