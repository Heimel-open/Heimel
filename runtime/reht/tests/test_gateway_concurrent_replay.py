from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock

RACE_REPETITIONS = 25
RACE_WORKERS = 16


def _run_same_permit_race(repetition: int) -> None:
    from valo_gateway import ValoGateway
    from valo_gateway.tool_adapters import FunctionTool

    from tests.test_security_non_bypass_stage1 import _authorized_chain

    chain = _authorized_chain()
    gateway = ValoGateway()
    barrier = Barrier(RACE_WORKERS)
    calls: list[int] = []
    calls_lock = Lock()

    def effect(**_: object) -> str:
        with calls_lock:
            calls.append(1)
        return "ok"

    tool = FunctionTool("payment", effect)

    def attempt(index: int) -> str:
        barrier.wait()
        try:
            gateway.execute(
                authority=chain.authority,
                clearance=chain.clearance,
                permit=chain.permit,
                action=chain.action,
                executor_id=f"executor:race:{repetition}:{index}",
                tool=tool,
                now=chain.now,
            )
        except ValueError as exc:
            if "already consumed" not in str(exc):
                raise
            return "DENIED_REPLAY"
        return "COMMITTED"

    with ThreadPoolExecutor(max_workers=RACE_WORKERS) as pool:
        outcomes = list(pool.map(attempt, range(RACE_WORKERS)))

    assert outcomes.count("COMMITTED") == 1
    assert outcomes.count("DENIED_REPLAY") == RACE_WORKERS - 1
    assert calls == [1]


def test_same_permit_concurrent_replay_commits_exactly_once() -> None:
    for repetition in range(RACE_REPETITIONS):
        _run_same_permit_race(repetition)
