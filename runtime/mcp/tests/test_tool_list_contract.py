from __future__ import annotations

import ast
from pathlib import Path


SERVER = Path(__file__).parents[1] / "server" / "server.py"


def _tool_names_from_list() -> set[str]:
    tree = ast.parse(SERVER.read_text(encoding="utf-8"))
    names: set[str] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        try:
            value = ast.literal_eval(node)
        except (ValueError, TypeError):
            continue
        if isinstance(value, dict) and isinstance(value.get("name"), str) and "inputSchema" in value:
            names.add(value["name"])

    return names


def _tool_names_from_map() -> set[str]:
    tree = ast.parse(SERVER.read_text(encoding="utf-8"))

    for node in ast.walk(tree):
        if not isinstance(node, ast.AnnAssign):
            continue
        if not isinstance(node.target, ast.Name) or node.target.id != "tool_map":
            continue
        assert isinstance(node.value, ast.Dict)
        names: set[str] = set()
        for key in node.value.keys:
            assert isinstance(key, ast.Constant) and isinstance(key.value, str)
            names.add(key.value)
        return names

    raise AssertionError("tool_map not found")


def test_tools_list_matches_callable_tool_map_exactly() -> None:
    assert _tool_names_from_list() == _tool_names_from_map()
