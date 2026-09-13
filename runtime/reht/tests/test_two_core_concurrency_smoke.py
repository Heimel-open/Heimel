"""TWO-CORE single-use smoke test under concurrency.

One fresh REHT permit is presented concurrently by 8-16 commit attempts. The
mechanical effect adapter must admit exactly one effect and deny every other
attempt as replay. This is the cheap smoke version of the frozen Gateway race
(25 races x 16 workers = 400 attempts); it uses a single race with a reduced
worker count and does not run the full stress/reproduction suite.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier, Lock
from typing import Any

from tests.two_core_harness import (
    CAPABILITY,
    PURPOSE,
    TARGET,
    EffectDenied,
    MechanicalEffectAdapter,
    base_engine,
    build_context,
)
from valo_reht import RealReht

RACE_WORKERS = 12
RACE_REPETITIONS = 1

NOW = datetime(2026, 8, 23, 13, 0, tzinfo=UTC)


def _action() -> dict[str, Any]:
    return {
        "action_id": "action:race",
        "capability": CAPABILITY,
        "target": TARGET,
        "action_type": CAPABILITY,
        "purpose_id": PURPOSE,
    }


def _run_single_race(repetition: int) -> None:
    engine = base_engine(now=NOW)
    ctx = build_context(engine, _action(), now=NOW, nonce=f"nonce:race:{repetition}")
    decision = RealReht().authorize(ctx, _action())
    assert decision.decision == "ALLOW"

    adapter = MechanicalEffectAdapter()
    adapter.bind(decision, _action(), ctx)

    barrier = Barrier(RACE_WORKERS)
    calls: list[int] = []
    calls_lock = Lock()

    def effect(arguments: dict[str, Any]) -> dict[str, Any]:
        with calls_lock:
            calls.append(1)
        return {"ok": True}

    def attempt(index: int) -> str:
        barrier.wait()
        try:
            adapter.execute(
                decision=decision,
                action_contract=_action(),
                ctx=ctx,
                effect_fn=effect,
                arguments={"attempt": index},
            )
        except EffectDenied as exc:
            if "permit replay" not in str(exc):
                raise
            return "DENIED_REPLAY"
        return "COMMITTED"

    with ThreadPoolExecutor(max_workers=RACE_WORKERS) as pool:
        outcomes = list(pool.map(attempt, range(RACE_WORKERS)))

    assert outcomes.count("COMMITTED") == 1
    assert outcomes.count("DENIED_REPLAY") == RACE_WORKERS - 1
    assert calls == [1]


def test_two_core_permit_single_use_under_concurrency() -> None:
    for repetition in range(RACE_REPETITIONS):
        _run_single_race(repetition)