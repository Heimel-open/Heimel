from __future__ import annotations

import ast
from pathlib import Path


SERVER = Path(__file__).parents[1] / "server" / "server.py"
REQUIRED_HINTS = {
    "readOnlyHint",
    "destructiveHint",
    "idempotentHint",
    "openWorldHint",
}


def _declared_tools() -> list[dict[str, object]]:
    tree = ast.parse(SERVER.read_text(encoding="utf-8"))
    tools: list[dict[str, object]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        try:
            value = ast.literal_eval(node)
        except (ValueError, TypeError):
            continue
        if isinstance(value, dict) and isinstance(value.get("name"), str) and "inputSchema" in value:
            tools.append(value)

    return tools


def test_every_declared_tool_has_explicit_boolean_safety_hints() -> None:
    tools = _declared_tools()
    assert tools

    for tool in tools:
        annotations = tool.get("annotations")
        assert isinstance(annotations, dict), tool["name"]
        assert REQUIRED_HINTS <= annotations.keys(), tool["name"]
        assert all(isinstance(annotations[hint], bool) for hint in REQUIRED_HINTS), tool["name"]


def test_read_only_tools_are_not_destructive() -> None:
    for tool in _declared_tools():
        annotations = tool["annotations"]
        if annotations["readOnlyHint"]:
            assert annotations["destructiveHint"] is False, tool["name"]
