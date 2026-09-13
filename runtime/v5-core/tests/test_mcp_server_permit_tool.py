"""Tests for the MCP permit tool that routes into the golden execution path."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MCP_SERVER_PATH = ROOT / "mcp_server.py"


def _load_mcp_server():
    spec = importlib.util.spec_from_file_location("mcp_server_test_module", MCP_SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakePermitRuntime:
    def __init__(self):
        self.calls = []

    def process_permit(self, permit, trusted_issuer, now_epoch_ms=None, revocation_registry_path=None):
        call = {
            "permit": permit,
            "trusted_issuer": trusted_issuer,
            "now_epoch_ms": now_epoch_ms,
            "revocation_registry_path": revocation_registry_path,
        }
        self.calls.append(call)
        return {
            "ok": True,
            "outcome": "Executed",
            "execution_allowed": True,
            "receipt": {
                "receipt_id": "rcpt-001",
                "effector_id": "connector.erp",
            },
        }


def test_process_permit_tool_routes_to_golden_path_runtime():
    mcp_server = _load_mcp_server()
    runtime = FakePermitRuntime()
    mcp_server._permit_runtime = runtime

    result = mcp_server._dispatch_tool(
        "process_permit",
        {
            "permit": {"artifact_id": "permit-1"},
            "trusted_issuer": {"issuer_id": "platform:test"},
            "now_epoch_ms": 1234567890,
            "revocation_registry_path": "/tmp/revocations.jsonl",
        },
    )

    assert result["ok"] is True
    assert result["tool"] == "process_permit"
    assert runtime.calls == [
        {
            "permit": {"artifact_id": "permit-1"},
            "trusted_issuer": {"issuer_id": "platform:test"},
            "now_epoch_ms": 1234567890,
            "revocation_registry_path": "/tmp/revocations.jsonl",
        }
    ]


def test_process_permit_tool_is_exposed_in_schema():
    mcp_server = _load_mcp_server()
    tool = next(item for item in mcp_server._TOOLS if item["name"] == "process_permit")

    assert tool["inputSchema"]["required"] == ["permit", "trusted_issuer"]
    assert "revocation_registry_path" in tool["inputSchema"]["properties"]
    assert tool["description"].startswith("Golden path tool.")


def test_legacy_mcp_tools_remain_explicitly_marked_as_telemetry():
    mcp_server = _load_mcp_server()
    legacy_tools = [item for item in mcp_server._TOOLS if item["name"] != "process_permit"]

    assert legacy_tools, "expected legacy telemetry tools to remain present"
    assert all(item["description"].startswith("Legacy telemetry tool.") for item in legacy_tools)
    assert len([item for item in mcp_server._TOOLS if item["name"] == "process_permit"]) == 1


def test_dispatch_tool_rejects_unknown_names():
    mcp_server = _load_mcp_server()

    result = mcp_server._dispatch_tool("not_a_real_tool", {})

    assert result == {"error": "Unknown tool: not_a_real_tool"}
