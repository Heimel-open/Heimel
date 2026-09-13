"""Fail-closed normalization for MCP JSON responses.

The helpers unwrap transport envelopes only. They never invent domain values,
fill missing records or treat a successful transport response as verified fact.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Sequence


class MCPResponseShapeError(ValueError):
    """Raised when a tool response cannot be mapped without fabrication."""


def unwrap_mcp_payload(raw: Any) -> Any:
    """Remove common MCP transport envelopes while preserving domain payloads."""

    if raw is None:
        raise MCPResponseShapeError("MCP response is null")

    payload = raw
    if isinstance(payload, dict):
        if payload.get("isError") is True or payload.get("error"):
            raise MCPResponseShapeError(f"MCP tool returned an error: {payload.get('error')}")

        result = payload.get("result")
        if isinstance(result, (dict, list)):
            payload = result

    if isinstance(payload, dict):
        content = payload.get("content")
        if isinstance(content, list):
            text_items = [
                item.get("text")
                for item in content
                if isinstance(item, dict)
                and item.get("type") == "text"
                and isinstance(item.get("text"), str)
            ]
            if len(text_items) == 1:
                try:
                    payload = json.loads(text_items[0])
                except json.JSONDecodeError:
                    payload = {"text": text_items[0]}

    if isinstance(payload, dict):
        envelope_keys = {
            "data",
            "status",
            "meta",
            "metadata",
            "request_id",
            "trace_id",
        }
        if "data" in payload and set(payload).issubset(envelope_keys):
            data = payload["data"]
            if isinstance(data, (dict, list)):
                payload = data

    return payload


def require_object(raw: Any, *, keys: Sequence[str] = ()) -> Dict[str, Any]:
    """Return an exact object payload or fail closed."""

    payload = unwrap_mcp_payload(raw)
    if isinstance(payload, dict):
        for key in keys:
            candidate = payload.get(key)
            if isinstance(candidate, dict):
                payload = candidate
                break
    if not isinstance(payload, dict):
        raise MCPResponseShapeError(
            f"Expected object response, received {type(payload).__name__}"
        )
    return dict(payload)


def require_list(raw: Any, *, keys: Sequence[str] = ()) -> List[Dict[str, Any]]:
    """Return an exact list of objects or fail closed."""

    payload = unwrap_mcp_payload(raw)
    if isinstance(payload, dict):
        for key in keys:
            candidate = payload.get(key)
            if isinstance(candidate, list):
                payload = candidate
                break
    if not isinstance(payload, list):
        raise MCPResponseShapeError(
            f"Expected list response, received {type(payload).__name__}"
        )
    if not all(isinstance(item, dict) for item in payload):
        raise MCPResponseShapeError("Expected every list item to be an object")
    return [dict(item) for item in payload]


__all__ = [
    "MCPResponseShapeError",
    "require_list",
    "require_object",
    "unwrap_mcp_payload",
]
