from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from ..mcp_capability_bridge import Authorize, McpInvoke, invoke_governed_mcp_tool, normalize_mcp_tool_call
from ..windows_capability_adapter import EffectRequest, InvocationReceipt


@dataclass(frozen=True)
class ChatGPTMcpContext:
    app_id: str
    workspace_id: str | None = None
    frozen_tool_snapshot: str | None = None
    action_enabled: bool | None = None
    user_confirmed: bool | None = None
    conversation_ref: str | None = None

    def as_parameters(self) -> dict[str, Any]:
        return {
            "app_id": self.app_id,
            "workspace_id": self.workspace_id,
            "frozen_tool_snapshot": self.frozen_tool_snapshot,
            "action_enabled": self.action_enabled,
            "user_confirmed": self.user_confirmed,
            "conversation_ref": self.conversation_ref,
        }


def normalize_chatgpt_mcp_action(
    *,
    request_id: str,
    actor_id: str,
    principal_id: str,
    server_id: str,
    tool_name: str,
    arguments: dict[str, Any],
    purpose: str,
    mandate_ref: str,
    chatgpt: ChatGPTMcpContext,
    requested_at: datetime | None = None,
) -> EffectRequest:
    """Normalize a ChatGPT custom-MCP action into the canonical PEACE effect request.

    ChatGPT-side app approval, action enablement and user confirmation are bound into
    the request as context. They are deliberately not converted into authority.
    """

    parameters = {
        "tool_arguments": arguments,
        "chatgpt_context": chatgpt.as_parameters(),
    }
    return normalize_mcp_tool_call(
        request_id=request_id,
        actor_id=actor_id,
        principal_id=principal_id,
        server_id=server_id,
        tool_name=tool_name,
        arguments=parameters,
        purpose=purpose,
        mandate_ref=mandate_ref,
        requested_at=requested_at or datetime.now(timezone.utc),
    )


def invoke_governed_chatgpt_mcp_action(
    *,
    request: EffectRequest,
    authorize: Authorize,
    invoke: McpInvoke,
    commit_time: datetime,
) -> InvocationReceipt:
    """Resolve fresh authority at the effect boundary, then invoke the MCP tool once.

    The remote MCP provider receives only the original tool arguments. The bound
    ChatGPT context remains part of the governed request/receipt evidence.
    """

    def invoke_original(server_id: str, tool_name: str, parameters: dict[str, Any]) -> Any:
        arguments = parameters.get("tool_arguments")
        if not isinstance(arguments, dict):
            raise ValueError("governed ChatGPT MCP request missing tool_arguments")
        return invoke(server_id, tool_name, arguments)

    return invoke_governed_mcp_tool(
        request=request,
        authorize=authorize,
        invoke=invoke_original,
        commit_time=commit_time,
    )
