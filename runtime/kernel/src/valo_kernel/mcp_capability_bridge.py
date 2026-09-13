from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

from .windows_capability_adapter import (
    AuthorizationDisposition,
    CommitAuthorization,
    EffectRequest,
    InvocationReceipt,
    WindowsCapabilitySurface,
    invoke_governed_windows_capability,
)


@dataclass(frozen=True)
class McpTool:
    server_id: str
    tool_name: str
    description: str | None = None

    @property
    def capability_id(self) -> str:
        return f"mcp:{self.server_id}:{self.tool_name}"


McpInvoke = Callable[[str, str, dict[str, Any]], Any]
Authorize = Callable[[EffectRequest, datetime], CommitAuthorization]


def discover_mcp_tools(raw_tools: Iterable[dict[str, Any]], *, server_id: str) -> tuple[McpTool, ...]:
    tools: list[McpTool] = []
    for raw in raw_tools:
        name = str(raw.get("name", "")).strip()
        if not name:
            continue
        tools.append(McpTool(server_id=server_id, tool_name=name, description=raw.get("description")))
    return tuple(sorted(tools, key=lambda t: t.capability_id))


def normalize_mcp_tool_call(
    *,
    request_id: str,
    actor_id: str,
    principal_id: str,
    server_id: str,
    tool_name: str,
    arguments: dict[str, Any],
    purpose: str,
    mandate_ref: str,
    requested_at: datetime | None = None,
) -> EffectRequest:
    return EffectRequest(
        request_id=request_id,
        actor_id=actor_id,
        principal_id=principal_id,
        surface=WindowsCapabilitySurface.MCP,
        capability_id=f"mcp:{server_id}:{tool_name}",
        provider_id=server_id,
        target=tool_name,
        purpose=purpose,
        mandate_ref=mandate_ref,
        parameters=arguments,
        requested_at=requested_at or datetime.now(timezone.utc),
    )


def invoke_governed_mcp_tool(
    *,
    request: EffectRequest,
    authorize: Authorize,
    invoke: McpInvoke,
    commit_time: datetime,
) -> InvocationReceipt:
    if request.surface != WindowsCapabilitySurface.MCP:
        raise ValueError("request surface must be MCP")

    def provider(effect: EffectRequest) -> Any:
        return invoke(effect.provider_id, effect.target, effect.parameters)

    return invoke_governed_windows_capability(
        request=request,
        authorize=authorize,
        provider_invoke=provider,
        commit_time=commit_time,
    )


def deny_all_authorizer(request: EffectRequest, at: datetime) -> CommitAuthorization:
    return CommitAuthorization(
        decision_id=f"deny:{request.request_id}",
        disposition=AuthorizationDisposition.DENY,
        effect_digest=request.effect_digest,
        evaluated_at=at,
        valid_until=at,
        reasons=("MCP_DENY_BY_DEFAULT",),
        authority_ref="policy:deny-all",
    )
