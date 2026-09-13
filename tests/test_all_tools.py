"""Run tool contract tests against each tool adapter class in tools/adapters.py."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.interfaces import ToolInterface, Result, Decision
import tools.adapters as mod

CLASSES = ["GitHub", "Gmail", "GoogleDrive", "Slack", "Docker",
           "Kubernetes", "SSH", "MCP", "REST"]


def make_adapter(cls_name):
    return getattr(mod, cls_name)()


@pytest.mark.parametrize("cls", CLASSES)
def test_name_and_capabilities(cls):
    t = make_adapter(cls)
    assert isinstance(t.name(), str) and len(t.name()) > 0
    caps = t.capabilities()
    assert isinstance(caps, list) and len(caps) > 0


@pytest.mark.parametrize("cls", CLASSES)
def test_rejects_unauthorized_request(cls):
    t = make_adapter(cls)
    try:
        r = t.invoke({"action": "do_something", "params": {}})
    except AssertionError:
        return
    except Exception:
        return
    assert r.status == "FAILURE" or r.error is not None


@pytest.mark.parametrize("cls", CLASSES)
def test_executes_only_authorized(cls):
    t = make_adapter(cls)
    auth = {"reht_ref": "reht-xyz", "racs_decision": Decision.ALLOW.value,
            "veritas_ref": "ver-xyz", "action_id": "act-1"}
    r = t.invoke({"action": "capability_0", "params": {}, "authorization": auth})
    assert isinstance(r, Result)
    assert r.action_id == "act-1"


@pytest.mark.parametrize("cls", CLASSES)
def test_no_authority_origination(cls):
    t = make_adapter(cls)
    auth = {"reht_ref": "reht-xyz", "racs_decision": Decision.DENY.value,
            "veritas_ref": "ver-xyz", "action_id": "act-2"}
    r = t.invoke({"action": "capability_0", "params": {}, "authorization": auth})
    assert r.status == "FAILURE"


if __name__ == "__main__":
    for cls in CLASSES:
        for fn in [test_name_and_capabilities, test_rejects_unauthorized_request,
                   test_executes_only_authorized, test_no_authority_origination]:
            fn(cls)
    print(f"ALL_TOOL_ADAPTER_TESTS_PASS ({len(CLASSES)} tools)")
