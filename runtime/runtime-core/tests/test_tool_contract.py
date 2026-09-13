"""Contract tests for ALL tool adapters (GitHub, Gmail, Drive, Slack, Docker,
Kubernetes, SSH, MCP, REST).

Every tool adapter MUST pass these identical tests. No tool adapter may perform
an action directly — it only executes a REHT-authorized request carrying RACS
contract data. Swapping a vendor must require NO change here.
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.interfaces import ToolInterface, Result, Decision


def make_adapter() -> ToolInterface:
    mod_name = os.environ.get("ADAPTER_MODULE", "tools.adapters")
    mod = importlib.import_module(mod_name)
    res = mod.build()
    if isinstance(res, list):
        return res[0]
    return res


def test_name_and_capabilities():
    t = make_adapter()
    assert isinstance(t.name(), str) and len(t.name()) > 0
    caps = t.capabilities()
    assert isinstance(caps, list) and len(caps) > 0


def test_rejects_unauthorized_request():
    """Tool adapter must refuse to act without an authorization envelope."""
    t = make_adapter()
    try:
        r = t.invoke({"action": "do_something", "params": {}})
    except AssertionError:
        return  # explicit refusal is acceptable
    except Exception:
        return
    # If it returns instead of raising, the result must mark UNAUTHORIZED
    assert r.status == "FAILURE" or r.error is not None, \
        "tool adapter executed without authorization envelope"


def test_executes_only_authorized():
    """With a valid REHT clearance envelope, the adapter executes and returns Result."""
    t = make_adapter()
    auth = {
        "reht_ref": "reht-xyz",
        "decision": Decision.ALLOW.value,
        "veritas_ref": "ver-xyz",
        "action_id": "act-1",
    }
    r = t.invoke({"action": "capability_0", "params": {}, "authorization": auth})
    assert isinstance(r, Result)
    assert r.action_id == "act-1"


def test_no_authority_origination():
    """Tool adapter must not grant authority — on REHT DENY it must refuse execution."""
    t = make_adapter()
    auth = {
        "reht_ref": "reht-xyz",
        "decision": Decision.DENY.value,
        "veritas_ref": "ver-xyz",
        "action_id": "act-2",
    }
    r = t.invoke({"action": "capability_0", "params": {}, "authorization": auth})
    assert r.status == "FAILURE", "adapter executed despite DENY"


if __name__ == "__main__":
    for fn in [test_name_and_capabilities, test_rejects_unauthorized_request,
               test_executes_only_authorized, test_no_authority_origination]:
        fn()
        print(f"PASS {fn.__name__}")
    print("ALL_TOOL_CONTRACT_TESTS_PASS")
