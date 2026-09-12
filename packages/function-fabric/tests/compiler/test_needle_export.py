from __future__ import annotations

import pytest

from valo_function_fabric.compiler.needle import (
    export_needle_tool_bundle,
    function_to_needle_tool,
)
from valo_function_fabric.contracts import (
    AutonomyLevel,
    AutonomyProfile,
    FunctionDefinition,
    FunctionStatus,
    TypeRef,
)


def _function(
    *,
    function_id: str = "valo.ops.set_pump_speed",
    version: str = "1.0.0",
    status: FunctionStatus = FunctionStatus.ACTIVE,
    deprecated: bool = False,
) -> FunctionDefinition:
    return FunctionDefinition(
        function_id=function_id,
        name="Set pump speed",
        version=version,
        input_type=TypeRef(name="input", type="PumpSpeedCommand"),
        output_type=TypeRef(name="output", type="PumpSpeedResult"),
        workflow_ref="wf.set-pump-speed@1.0.0",
        autonomy_profile=AutonomyProfile(
            allowed_autonomy_levels=[AutonomyLevel.RECOMMEND, AutonomyLevel.STEP_UP],
            default_autonomy_level=AutonomyLevel.RECOMMEND,
        ),
        status=status,
        deprecated=deprecated,
    )


def _schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "pump_id": {"type": "string"},
            "rpm": {"type": "integer", "minimum": 0, "maximum": 3000},
        },
        "required": ["pump_id", "rpm"],
    }


def test_active_function_exports_as_plain_needle_schema() -> None:
    function = _function()
    tool = function_to_needle_tool(function, _schema())

    assert tool["name"] == "valo.ops.set_pump_speed"
    assert tool["parameters"] == _schema()
    assert "authorization is external" in tool["description"]
    assert "authority_requirements" not in tool


def test_export_is_stable_independent_of_input_function_order() -> None:
    a = _function(function_id="valo.ops.a")
    b = _function(function_id="valo.ops.b")
    schemas = {a.identity: _schema(), b.identity: _schema()}

    first = export_needle_tool_bundle([b, a], schemas)
    second = export_needle_tool_bundle([a, b], schemas)

    assert first.tools == second.tools
    assert first.toolset_hash == second.toolset_hash
    assert first.toolset_hash.startswith("sha256:")
    assert [tool["name"] for tool in first.tools] == ["valo.ops.a", "valo.ops.b"]


def test_export_deep_copies_input_schema() -> None:
    function = _function()
    schema = _schema()
    bundle = export_needle_tool_bundle([function], {function.identity: schema})

    schema["properties"]["rpm"]["maximum"] = 9999

    assert bundle.tools[0]["parameters"]["properties"]["rpm"]["maximum"] == 3000


def test_non_active_function_fails_closed() -> None:
    draft = _function(status=FunctionStatus.DRAFT)

    with pytest.raises(ValueError, match="only ACTIVE"):
        export_needle_tool_bundle([draft], {draft.identity: _schema()})


def test_missing_version_specific_input_schema_fails_closed() -> None:
    function = _function()

    with pytest.raises(ValueError, match="missing input schema"):
        export_needle_tool_bundle([function], {})


def test_duplicate_active_function_id_across_versions_fails_closed() -> None:
    v1 = _function(version="1.0.0")
    v2 = _function(version="2.0.0")
    schemas = {v1.identity: _schema(), v2.identity: _schema()}

    with pytest.raises(ValueError, match="duplicate active Needle tool name"):
        export_needle_tool_bundle([v1, v2], schemas)


def test_non_object_input_schema_fails_closed() -> None:
    function = _function()

    with pytest.raises(ValueError, match="type='object'"):
        function_to_needle_tool(function, {"type": "array", "items": {"type": "string"}})

