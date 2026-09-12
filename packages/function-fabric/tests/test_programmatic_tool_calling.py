from __future__ import annotations

import pytest
from pydantic import ValidationError

from valo_function_fabric.tool_catalog import (
    PROGRAMMATIC_DISPATCH_PATH,
    RACS_BINDING_CONTRACT,
    ProgrammaticToolCall,
    ToolCatalog,
    ToolDescriptor,
    ToolProtocol,
)


def _catalog() -> ToolCatalog:
    catalog = ToolCatalog()
    catalog.register(
        ToolDescriptor(
            tool_id="payments.send",
            protocol=ToolProtocol.MCP,
            endpoint_ref="mcp://payments",
            operation="send",
            mutates_external_state=True,
            consequence_bearing=True,
            required_authority_scope="payments.send",
        )
    )
    return catalog


def test_programmatic_surface_is_composition_not_execution() -> None:
    projected = _catalog().project("payments.send", "programmatic")

    assert projected["programmatic_composition"] is True
    assert projected["direct_execution"] is False
    assert projected["state_recheck_required"] is True
    assert projected["dispatch_path"] == PROGRAMMATIC_DISPATCH_PATH
    assert projected["authority_effect"] == "none"
    assert projected["final_authorization_boundary"] == "REHT"
    assert projected["binding_contract"] == RACS_BINDING_CONTRACT
    assert "RACS" not in projected["dispatch_path"]
    assert "allow" not in projected
    assert "approved" not in projected


def test_programmatic_stub_only_builds_governed_call_envelope() -> None:
    catalog = _catalog()
    stub = catalog.programmatic_stub("payments.send")

    call = stub(amount=100, currency="EUR")

    assert call.tool_id == "payments.send"
    assert call.arguments == {"amount": 100, "currency": "EUR"}
    assert call.direct_execution is False
    assert call.state_recheck_required is True
    assert call.dispatch_path == PROGRAMMATIC_DISPATCH_PATH
    assert call.required_authority_scope == "payments.send"
    assert call.final_authorization_boundary == "REHT"


def test_programmatic_call_cannot_enable_direct_execution() -> None:
    with pytest.raises(ValidationError, match="cannot execute tools directly"):
        ProgrammaticToolCall(
            tool_id="payments.send",
            protocol=ToolProtocol.MCP,
            endpoint_ref="mcp://payments",
            operation="send",
            mutates_external_state=True,
            consequence_bearing=True,
            required_authority_scope="payments.send",
            direct_execution=True,
        )


def test_programmatic_call_cannot_bypass_canonical_dispatch_path() -> None:
    with pytest.raises(ValidationError, match="canonical dispatch path"):
        ProgrammaticToolCall(
            tool_id="payments.send",
            protocol=ToolProtocol.MCP,
            endpoint_ref="mcp://payments",
            operation="send",
            mutates_external_state=True,
            consequence_bearing=True,
            required_authority_scope="payments.send",
            dispatch_path=("Python", "API"),
        )


def test_effectful_programmatic_call_requires_execution_time_state_recheck() -> None:
    with pytest.raises(ValidationError, match="state re-check"):
        ProgrammaticToolCall(
            tool_id="payments.send",
            protocol=ToolProtocol.MCP,
            endpoint_ref="mcp://payments",
            operation="send",
            mutates_external_state=True,
            consequence_bearing=True,
            required_authority_scope="payments.send",
            state_recheck_required=False,
        )


def test_programmatic_stub_rejects_unknown_tools() -> None:
    with pytest.raises(KeyError, match="unknown tool"):
        ToolCatalog().programmatic_stub("missing.tool")
