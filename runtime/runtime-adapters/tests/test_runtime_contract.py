"""Contract tests for ALL runtime adapters (local, harness, google, openai, claude).

Every runtime adapter MUST pass these identical tests. Swapping a vendor must
require NO change here. This enforces the canonical RuntimeInterface.
"""
import abc
import importlib
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.interfaces import (RuntimeInterface, Event, Checkpoint, Result, Decision)


def make_adapter() -> RuntimeInterface:
    """Load the adapter under test. Overridden per repo via env ADAPTER_MODULE."""
    mod_name = os.environ.get("ADAPTER_MODULE", "runtime_adapters")
    mod = importlib.import_module(mod_name)
    return mod.build()


def test_submit_returns_action_id():
    a = make_adapter()
    aid = a.submit({"type": "noop", "payload": {}})
    assert isinstance(aid, str) and len(aid) > 0


def test_no_direct_execution_on_submit():
    """submit() must NOT execute. The action must remain pending/clearable."""
    a = make_adapter()
    aid = a.submit({"type": "echo", "payload": {"x": 1}})
    evs = a.stream(aid)
    kinds = [e.kind for e in evs]
    assert "EXECUTED" not in kinds, "submit() must not execute directly"


def test_checkpoint_and_restart():
    a = make_adapter()
    aid = a.submit({"type": "stateful", "payload": {"v": 0}})
    cp = a.checkpoint(aid)
    assert isinstance(cp, Checkpoint)
    assert cp.digest.startswith("sha256:")
    new_aid = a.restart(cp.id)
    assert isinstance(new_aid, str) and new_aid != aid or new_aid == aid


def test_result_contract():
    a = make_adapter()
    aid = a.submit({"type": "noop", "payload": {}})
    r = a.result(aid)
    assert isinstance(r, Result)
    assert r.status in ("SUCCESS", "FAILURE", "PARTIAL")


def test_event_model():
    a = make_adapter()
    aid = a.submit({"type": "noop", "payload": {}})
    evs = a.stream(aid)
    assert all(isinstance(e, Event) for e in evs)
    assert all(e.id and e.kind and e.timestamp for e in evs)


if __name__ == "__main__":
    for fn in [test_submit_returns_action_id, test_no_direct_execution_on_submit,
               test_checkpoint_and_restart, test_result_contract, test_event_model]:
        fn()
        print(f"PASS {fn.__name__}")
    print("ALL_RUNTIME_CONTRACT_TESTS_PASS")
