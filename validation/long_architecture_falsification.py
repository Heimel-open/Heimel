from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
from threading import Barrier, Lock
from typing import Any, Mapping

from valo_reht.active_session import (
    ActiveExecutionSession,
    ObservationSource,
    SessionDisposition,
    SessionObservation,
    SessionState,
)
from valo_reht.contracts import DecisionResult
from valo_reht.effect_boundary import EffectBoundary, EffectDenied, InMemoryPermitStore
from valo_reht.evidence_closure import (
    EvidenceClosure,
    EvidenceClosureError,
    VeritasKernelExecutionEvidenceSink,
)
from valo_reht.execution_journal import ExecutionRecoveryRequired
from valo_reht.runtime_interlocks import (
    BoundaryEffect,
    MechanicalBlock,
    ProbeDisposition,
    ProbeResult,
    ResourceBudget,
    ResourceBudgetLedger,
    ResourceReservation,
    RuntimeControlPlane,
    build_execution_receipt,
    canonical_digest,
)

DEFAULT_SEED = 20260826
DEFAULT_ITERATIONS = 100_000


def _digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(dict(payload), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _action(index: int = 0) -> dict[str, Any]:
    return {
        "action_id": f"action:long:{index}",
        "capability": "DO_EFFECT",
        "action_type": "DO_EFFECT",
        "target": "target:1",
        "actor_id": "actor:1",
        "principal_id": "principal:1",
        "payload": {"value": index},
    }


def _context(action: Mapping[str, Any], version: int = 1) -> dict[str, Any]:
    return {
        "state_version": version,
        "actor_id": action.get("actor_id"),
        "principal_id": action.get("principal_id"),
        "authority_state_id": "authority:1",
    }


class StaticReht:
    def __init__(
        self,
        decision: str = "ALLOW",
        *,
        permit_ref: str = "permit:long",
        before_return=None,
    ) -> None:
        self.decision = decision
        self.permit_ref = permit_ref
        self.before_return = before_return

    def authorize(
        self,
        execution_context: dict[str, Any],
        action_contract: dict[str, Any],
    ) -> DecisionResult:
        if self.before_return is not None:
            self.before_return()
        if self.decision != "ALLOW":
            return DecisionResult(decision=self.decision, reason="long-run restriction")
        return DecisionResult(
            decision="ALLOW",
            clearance_ref="clearance:long",
            permit_ref=self.permit_ref,
            execution_context_hash=_digest(execution_context),
        )


class NoConsumeProductionPermitStore:
    """Production-construction test double for non-ALLOW closure tests only."""

    production_safe = True

    def consume_once(self, permit_ref: str) -> bool:
        raise AssertionError("non-ALLOW closure test must never consume a permit")

    def is_consumed(self, permit_ref: str) -> bool:
        raise AssertionError("non-ALLOW closure test must never inspect permit state")


class NoUseProductionExecutionJournal:
    """Production-marked test double that must stay untouched on DENY paths."""

    production_safe = True

    def _unexpected(self, *args, **kwargs):
        raise AssertionError("non-ALLOW closure test must never use execution journal")

    open_intent = _unexpected
    mark_effect_invoking = _unexpected
    mark_receipt_ready = _unexpected
    mark_evidence_closing = _unexpected
    mark_closed = _unexpected
    get = _unexpected


class FakeVeritas:
    def __init__(self, events: list[str], *, fail: bool = False) -> None:
        self.events = events
        self.fail = fail

    def store_effect_boundary_execution_observation(self, payload: Mapping[str, Any]) -> str:
        self.events.append("VERITAS")
        if self.fail:
            raise ValueError("synthetic-veritas-failure")
        if payload.get("authority_granted") is not False:
            raise ValueError("authority contamination")
        return "a" * 64


class FakeKernel:
    def __init__(self, events: list[str], *, fail: bool = False) -> None:
        self.events = events
        self.fail = fail

    def append_verified_execution_outcome(self, outcome: Mapping[str, Any]) -> str:
        self.events.append("KERNEL")
        if self.fail:
            raise RuntimeError("synthetic-kernel-failure")
        if not outcome.get("veritas_ref"):
            raise ValueError("missing Veritas ref")
        if outcome.get("authority_granted") is not False:
            raise ValueError("authority contamination")
        return "kernel-event:" + "b" * 64


class MismatchedClosureSink:
    def close(self, receipt) -> EvidenceClosure:
        return EvidenceClosure(
            receipt_id="sha256:" + "0" * 64,
            veritas_ref="veritas-worm:sha256:" + "a" * 64,
            kernel_ref="kernel:" + "b" * 64,
            closed=True,
        )


def _sealed(calls: list[dict[str, Any]] | None = None) -> BoundaryEffect:
    calls = calls if calls is not None else []
    return BoundaryEffect.seal(
        "long-effect",
        lambda action: calls.append(deepcopy(action)) or {"ok": True},
    )


def _allow(context: dict[str, Any], suffix: str) -> DecisionResult:
    return DecisionResult(
        decision="ALLOW",
        clearance_ref=f"clearance:{suffix}",
        permit_ref=f"permit:{suffix}",
        execution_context_hash=_digest(context),
    )


def _session(version: int = 1, control: RuntimeControlPlane | None = None) -> ActiveExecutionSession:
    action = _action(version)
    context = _context(action, version)
    return ActiveExecutionSession(
        action_contract=action,
        execution_context=context,
        decision=_allow(context, str(version)),
        runtime_control=control,
        dynamic_bounds={
            "max_usd": 100.0,
            "targets": ("a", "b", "c"),
            "may_retry": True,
            "mode": "bounded",
        },
    )


def stress_permit_concurrency(rounds: int, workers: int = 32) -> dict[str, int]:
    attempts = 0
    commits = 0
    replays = 0
    for repetition in range(rounds):
        permit = f"permit:race:{repetition}"
        store = InMemoryPermitStore()
        boundary = EffectBoundary.for_development(store)
        barrier = Barrier(workers)
        calls = 0
        calls_lock = Lock()

        def effect(_: dict[str, Any]) -> dict[str, Any]:
            nonlocal calls
            with calls_lock:
                calls += 1
            return {"ok": True}

        sealed = BoundaryEffect.seal("race-effect", effect)
        action = _action(repetition)

        def attempt(_: int) -> str:
            barrier.wait()
            try:
                result = boundary.commit(
                    reht=StaticReht(permit_ref=permit),
                    context_factory=lambda candidate: _context(candidate),
                    action_contract=action,
                    effect=sealed,
                )
            except ExecutionRecoveryRequired:
                return "REPLAY_BLOCKED"
            except EffectDenied as exc:
                if "PERMIT_REPLAY" not in str(exc):
                    raise
                return "REPLAY_BLOCKED"
            if not result.effect_committed or result.evidence_closure is None:
                raise AssertionError("committed race did not produce terminal evidence object")
            if result.evidence_closure.closed:
                raise AssertionError("process-local stress must not claim durable evidence closure")
            return "COMMIT"

        with ThreadPoolExecutor(max_workers=workers) as pool:
            outcomes = list(pool.map(attempt, range(workers)))
        attempts += workers
        commits += outcomes.count("COMMIT")
        replays += outcomes.count("REPLAY_BLOCKED")
        if outcomes.count("COMMIT") != 1 or calls != 1:
            raise AssertionError(
                f"permit race {repetition}: commits={outcomes.count('COMMIT')} effects={calls}"
            )
        if not store.is_consumed(permit):
            raise AssertionError("winning permit was not consumed")
    return {"attempts": attempts, "commits": commits, "replays": replays}


def stress_toctou_halt(iterations: int) -> dict[str, int]:
    blocked = 0
    for i in range(iterations):
        control = RuntimeControlPlane()
        store = InMemoryPermitStore()
        calls: list[dict[str, Any]] = []
        permit = f"permit:toctou:{i}"
        boundary = EffectBoundary.for_development(
            store,
            runtime_control=control,
        )
        try:
            boundary.commit(
                reht=StaticReht(permit_ref=permit, before_return=control.halt_global),
                context_factory=lambda candidate: _context(candidate),
                action_contract=_action(i),
                effect=_sealed(calls),
            )
        except EffectDenied as exc:
            if "HALT_GLOBAL" not in str(exc):
                raise
            blocked += 1
        else:
            raise AssertionError("late HALT crossed effect boundary")
        if calls:
            raise AssertionError("effect ran after late HALT")
        if store.is_consumed(permit):
            raise AssertionError("permit consumed after late HALT")
    return {"attempts": iterations, "blocked": blocked, "unsafe_commits": 0}


def stress_exact_snapshot(iterations: int) -> dict[str, int]:
    for i in range(iterations):
        proposed = _action(i)
        expected = deepcopy(proposed)
        seen: list[dict[str, Any]] = []

        def context_factory(candidate: dict[str, Any]) -> dict[str, Any]:
            proposed["payload"]["value"] = -1
            proposed["target"] = "attacker-target"
            return _context(candidate)

        result = EffectBoundary.for_development(InMemoryPermitStore()).commit(
            reht=StaticReht(permit_ref=f"permit:snapshot:{i}"),
            context_factory=context_factory,
            action_contract=proposed,
            effect=_sealed(seen),
        )
        if not result.effect_committed or seen != [expected]:
            raise AssertionError("authorized action snapshot changed before effect")
    return {"attempts": iterations, "snapshot_escapes": 0}


def stress_resource_hierarchy(iterations: int, rng: random.Random) -> dict[str, int]:
    accepted = 0
    rejected = 0
    for i in range(iterations):
        parent_limit = float(rng.randint(1, 1000))
        ledger = ResourceBudgetLedger()
        ledger.register_budget(ResourceBudget("parent", {"units": parent_limit}))
        ledger.register_budget(ResourceBudget("left", {"units": parent_limit}, parent_id="parent"))
        ledger.register_budget(ResourceBudget("right", {"units": parent_limit}, parent_id="parent"))
        total = 0.0
        for j in range(8):
            amount = float(rng.randint(0, max(1, int(parent_limit // 2) + 1)))
            budget = "left" if rng.random() < 0.5 else "right"
            reservation = ResourceReservation(
                f"res:{i}:{j}",
                budget,
                canonical_digest(_action(i * 10 + j)),
                {"units": amount},
            )
            try:
                ledger.reserve(reservation)
            except ValueError:
                rejected += 1
            else:
                accepted += 1
                total += amount
                if total > parent_limit + 1e-9:
                    raise AssertionError(
                        f"sibling reservations exceeded parent: total={total} limit={parent_limit}"
                    )
    return {"reservations_accepted": accepted, "reservations_rejected": rejected, "oversubscriptions": 0}


def stress_session_continuity(iterations: int) -> dict[str, int]:
    drift_forced_reauth = 0
    denied_reauth_halted = 0
    widening_rejected = 0
    for i in range(iterations):
        session = _session(i + 1)
        changed = _context(_action(i + 1), i + 2)
        checkpoint = session.observe(
            execution_context=changed,
            observation=SessionObservation(
                ObservationSource.WATCHER,
                SessionDisposition.CONTINUE,
            ),
        )
        if (
            checkpoint.disposition is not SessionDisposition.REAUTHORIZE
            or session.state is not SessionState.PAUSED
            or not session.requires_reauthorization
        ):
            raise AssertionError("context drift did not force reauthorization")
        drift_forced_reauth += 1

        denied = session.reauthorize(reht=StaticReht("DENY"), execution_context=changed)
        if denied.disposition is not SessionDisposition.HALT or session.state is not SessionState.HALTED:
            raise AssertionError("failed reauthorization did not halt session")
        denied_reauth_halted += 1

        fresh = _session(10_000_000 + i)
        fresh.observe(
            execution_context=_context(_action(10_000_000 + i), 10_000_001 + i),
            observation=SessionObservation(
                ObservationSource.SYSTEM,
                SessionDisposition.CONTINUE,
                bound_updates={"max_usd": 50.0, "targets": ("a",), "may_retry": False},
            ),
        )
        try:
            fresh.observe(
                execution_context=_context(_action(10_000_000 + i), 10_000_001 + i),
                observation=SessionObservation(
                    ObservationSource.SYSTEM,
                    SessionDisposition.CONTINUE,
                    bound_updates={"max_usd": 75.0},
                ),
            )
        except ValueError:
            widening_rejected += 1
        else:
            raise AssertionError("runtime bound widening was accepted")
    return {
        "drift_forced_reauth": drift_forced_reauth,
        "denied_reauth_halted": denied_reauth_halted,
        "widening_rejected": widening_rejected,
    }


def stress_evidence_ordering(iterations: int) -> dict[str, int]:
    success = 0
    veritas_failures = 0
    kernel_failures = 0
    for i in range(iterations):
        mode = i % 3
        events: list[str] = []
        sink = VeritasKernelExecutionEvidenceSink(
            veritas=FakeVeritas(events, fail=mode == 1),
            kernel=FakeKernel(events, fail=mode == 2),
        )
        receipt = build_execution_receipt(
            status="COMMITTED",
            action=_action(i),
            execution_context_hash="c" * 64,
            reht_decision="ALLOW",
            clearance_ref="clearance:evidence",
            permit_ref=f"permit:evidence:{i}",
            effect_name="evidence-effect",
            effect_result={"ok": True},
        )
        try:
            closure = sink.close(receipt)
        except EvidenceClosureError as exc:
            if mode == 1:
                veritas_failures += 1
                if exc.stage != "VERITAS" or events != ["VERITAS"]:
                    raise AssertionError("Veritas failure ordering violated") from exc
            elif mode == 2:
                kernel_failures += 1
                if exc.stage != "KERNEL" or events != ["VERITAS", "KERNEL"] or not exc.veritas_ref:
                    raise AssertionError("Kernel failure closure semantics violated") from exc
            else:
                raise
        else:
            if mode != 0:
                raise AssertionError("failed evidence leg reported closed")
            if events != ["VERITAS", "KERNEL"] or not closure.closed:
                raise AssertionError("evidence closure order violated")
            if not closure.veritas_ref or not closure.kernel_ref or closure.authority_granted:
                raise AssertionError("invalid closed evidence object")
            success += 1
    return {
        "closed": success,
        "veritas_failures": veritas_failures,
        "kernel_failures": kernel_failures,
        "false_closures": 0,
    }


def stress_malicious_closure(iterations: int) -> dict[str, int]:
    rejected = 0
    for i in range(iterations):
        boundary = EffectBoundary(
            NoConsumeProductionPermitStore(),
            evidence_sink=MismatchedClosureSink(),
            execution_journal=NoUseProductionExecutionJournal(),
        )
        try:
            boundary.commit(
                reht=StaticReht("DENY"),
                context_factory=lambda candidate: _context(candidate),
                action_contract=_action(i),
                effect=_sealed(),
            )
        except EvidenceClosureError as exc:
            if exc.stage != "CLOSURE":
                raise
            rejected += 1
        else:
            raise AssertionError("mismatched closure receipt was accepted")
    return {"attempts": iterations, "rejected": rejected}


def stress_non_authority_surfaces(iterations: int) -> dict[str, int]:
    rejected = 0
    direct_effect_blocks = 0
    for i in range(iterations):
        try:
            ProbeResult(ProbeDisposition.PASS, execution_authority=True)
        except ValueError:
            rejected += 1
        else:
            raise AssertionError("probe created execution authority")
        try:
            SessionObservation(
                ObservationSource.SENSOR,
                SessionDisposition.CONTINUE,
                authority_granted=True,
            )
        except ValueError:
            rejected += 1
        else:
            raise AssertionError("session observation created execution authority")
        effect = BoundaryEffect.seal("direct", lambda action: action)
        try:
            effect.invoke(_action(i))
        except MechanicalBlock as exc:
            if "NO_DIRECT_EFFECT_PATH" not in str(exc):
                raise
            direct_effect_blocks += 1
        else:
            raise AssertionError("direct effect invocation bypassed boundary")
    return {
        "authority_creation_attempts_rejected": rejected,
        "direct_effect_bypasses_blocked": direct_effect_blocks,
    }


def run(iterations: int, seed: int) -> dict[str, Any]:
    if iterations < 1_000:
        raise ValueError("long-run iterations must be >= 1000")
    rng = random.Random(seed)
    started = time.perf_counter()
    failures: list[dict[str, str]] = []
    families: dict[str, Any] = {}

    plan = [
        ("permit_concurrency", lambda: stress_permit_concurrency(max(50, iterations // 500))),
        ("toctou_halt", lambda: stress_toctou_halt(max(1000, iterations // 10))),
        ("exact_snapshot", lambda: stress_exact_snapshot(max(1000, iterations // 10))),
        ("resource_hierarchy", lambda: stress_resource_hierarchy(max(1000, iterations // 10), rng)),
        ("session_continuity", lambda: stress_session_continuity(max(1000, iterations // 10))),
        ("evidence_ordering", lambda: stress_evidence_ordering(max(1000, iterations // 10))),
        ("malicious_closure", lambda: stress_malicious_closure(max(1000, iterations // 20))),
        ("non_authority_surfaces", lambda: stress_non_authority_surfaces(max(1000, iterations // 20))),
    ]

    for name, family in plan:
        family_started = time.perf_counter()
        try:
            counters = family()
        except Exception as exc:
            failures.append(
                {
                    "family": name,
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
            )
            counters = {"status": "FAIL"}
        else:
            counters = {"status": "PASS", **counters}
        counters["elapsed_seconds"] = round(time.perf_counter() - family_started, 6)
        families[name] = counters

    return {
        "schema": "valo.reht.long-architecture-falsification.v1",
        "seed": seed,
        "requested_iterations": iterations,
        "implementation_sha": os.environ.get("IMPLEMENTATION_SHA", "UNKNOWN"),
        "python": sys.version,
        "platform": platform.platform(),
        "cpu_only": True,
        "external_api_cost": 0,
        "families": families,
        "failures": failures,
        "classification": "PASS" if not failures else "FAIL",
        "elapsed_seconds": round(time.perf_counter() - started, 6),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--output",
        default="validation/results/long_architecture_falsification.json",
    )
    args = parser.parse_args()
    payload = run(args.iterations, args.seed)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    if payload["classification"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
