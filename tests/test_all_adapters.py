"""Run runtime contract tests against each adapter class in runtime_adapters."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.interfaces import RuntimeInterface, Event, Checkpoint, Result, Decision
import runtime_adapters as mod

CLASSES = ["HarnessRouter", "GoogleAgentPlatform", "OpenAIAgents", "ClaudeCode"]


def make_adapter(cls_name):
    return getattr(mod, cls_name)()


@pytest.mark.parametrize("cls", CLASSES)
def test_submit_returns_action_id(cls):
    a = make_adapter(cls)
    aid = a.submit({"type": "noop", "payload": {}})
    assert isinstance(aid, str) and len(aid) > 0


@pytest.mark.parametrize("cls", CLASSES)
def test_no_direct_execution_on_submit(cls):
    a = make_adapter(cls)
    aid = a.submit({"type": "echo", "payload": {"x": 1}})
    kinds = [e.kind for e in a.stream(aid)]
    assert "EXECUTED" not in kinds


@pytest.mark.parametrize("cls", CLASSES)
def test_checkpoint_and_restart(cls):
    a = make_adapter(cls)
    aid = a.submit({"type": "stateful", "payload": {"v": 0}})
    cp = a.checkpoint(aid)
    assert isinstance(cp, Checkpoint)
    assert cp.digest.startswith("sha256:")
    new_aid = a.restart(cp.id)
    assert isinstance(new_aid, str)


@pytest.mark.parametrize("cls", CLASSES)
def test_result_contract(cls):
    a = make_adapter(cls)
    aid = a.submit({"type": "noop", "payload": {}})
    r = a.result(aid)
    assert isinstance(r, Result)
    assert r.status in ("SUCCESS", "FAILURE", "PARTIAL")


@pytest.mark.parametrize("cls", CLASSES)
def test_event_model(cls):
    a = make_adapter(cls)
    aid = a.submit({"type": "noop", "payload": {}})
    evs = a.stream(aid)
    assert all(isinstance(e, Event) for e in evs)
    assert all(e.id and e.kind and e.timestamp for e in evs)


if __name__ == "__main__":
    run_all()
    print(f"ALL_RUNTIME_ADAPTER_TESTS_PASS ({len(CLASSES)} adapters)")
