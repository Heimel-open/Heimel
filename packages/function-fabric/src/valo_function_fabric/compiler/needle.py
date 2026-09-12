from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from ..contracts import FunctionDefinition, FunctionStatus, canonical_digest


@dataclass(frozen=True)
class NeedleToolBundleV1:
    """Deterministic export artifact for a Needle tool catalogue."""

    tools: tuple[dict[str, Any], ...]
    toolset_hash: str


def _validate_input_schema(function: FunctionDefinition, schema: Mapping[str, Any]) -> dict[str, Any]:
    copied = deepcopy(dict(schema))
    if copied.get("type") != "object":
        raise ValueError(f"{function.identity}: Needle input schema must have type='object'")
    properties = copied.get("properties")
    if properties is not None and not isinstance(properties, dict):
        raise ValueError(f"{function.identity}: properties must be an object")
    required = copied.get("required")
    if required is not None and not isinstance(required, list):
        raise ValueError(f"{function.identity}: required must be a list")
    return copied


def function_to_needle_tool(
    function: FunctionDefinition,
    input_schema: Mapping[str, Any],
) -> dict[str, Any]:
    """Export one ACTIVE FunctionDefinition as a plain Needle JSON tool schema.

    This is a representation transform only. Governance requirements remain on the
    FunctionDefinition and must still be enforced downstream. Export does not grant
    capability, authority, purpose, rights, evidence standing, jurisdiction, or
    execution permission.
    """

    if function.status != FunctionStatus.ACTIVE or function.deprecated:
        raise ValueError(f"{function.identity}: only ACTIVE non-deprecated functions may be exported")

    parameters = _validate_input_schema(function, input_schema)
    return {
        "name": function.function_id,
        "description": f"{function.name} ({function.identity}). Candidate function only; authorization is external.",
        "parameters": parameters,
    }


def export_needle_tool_bundle(
    functions: Sequence[FunctionDefinition],
    input_schemas: Mapping[str, Mapping[str, Any]],
) -> NeedleToolBundleV1:
    """Export a stable, hash-bound Needle catalogue from Function Fabric definitions.

    ``input_schemas`` is keyed by ``FunctionDefinition.identity`` so versions cannot
    accidentally share a schema. The bundle is sorted by identity before hashing.
    Multiple active versions with the same function_id fail closed because Needle
    tool names must resolve unambiguously back to one Function Fabric function.
    """

    by_identity = sorted(functions, key=lambda function: function.identity)
    seen_names: set[str] = set()
    tools: list[dict[str, Any]] = []

    for function in by_identity:
        if function.identity not in input_schemas:
            raise ValueError(f"{function.identity}: missing input schema")
        if function.function_id in seen_names:
            raise ValueError(f"{function.function_id}: duplicate active Needle tool name")
        seen_names.add(function.function_id)
        tools.append(function_to_needle_tool(function, input_schemas[function.identity]))

    if not tools:
        raise ValueError("Needle tool bundle requires at least one function")

    toolset_hash = f"sha256:{canonical_digest(tools)}"
    return NeedleToolBundleV1(tools=tuple(tools), toolset_hash=toolset_hash)

