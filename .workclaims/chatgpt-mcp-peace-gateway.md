# Work claim: ChatGPT MCP -> PEACE gateway

Owner: ChatGPT on behalf of Njål / VALO
Canonical base: b07c5554bf4d34d62c269e0f5cd3f1977f628374
Branch: feat/chatgpt-mcp-peace-gateway

Active delivery: add a ChatGPT custom-MCP adapter that treats ChatGPT app/tool availability, workspace approval and user confirmation as capability/context signals only. Every consequence-bearing MCP call must still pass fresh PEACE/VALO consequence-time authorization before the remote MCP tool is invoked, and must return a deterministic receipt.

Owned files:
- src/valo_kernel/integrations/chatgpt_mcp.py
- tests/test_chatgpt_mcp_peace_gateway.py
- docs/chatgpt_mcp_peace_gateway_v1.md
- .workclaims/chatgpt-mcp-peace-gateway.md

Dependencies:
- existing mcp_capability_bridge
- existing windows_capability_adapter consequence-time gate
- OpenAI ChatGPT custom MCP app surface as external transport/capability layer

Invariants:
- ChatGPT app availability != authority
- workspace action approval != current authority
- user confirmation != current authority
- exact server + tool + arguments + ChatGPT context are digest-bound
- fresh authorization is resolved at consequence time
- DENY / ESCALATE / stale / mismatched authorization produces zero MCP effect
- provider result is evidence only and is receipt-bound
- no direct effect path bypasses the PEACE gate
