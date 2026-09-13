# Work claim: OpenAI Agents consequence gate

Owner: ChatGPT on behalf of Njål / VALO
Canonical base: 0a8205f8a3c169eede7b7d8e50c4d66a950d5c32
Branch: feat/openai-agents-consequence-gate

Active delivery: add a reference OpenAI Agents SDK integration that maps a function-tool input guardrail to VALO consequence-time admissibility. The integration must fail closed before tool execution and must not create, widen or reinterpret authority.

Owned files:
- src/valo_kernel/integrations/openai_agents.py
- src/valo_kernel/integrations/__init__.py
- tests/test_openai_agents_consequence_gate.py
- examples/openai_agents_consequence_gate_demo.py
- docs/openai_agents_consequence_gate_v1.md
- .workclaims/openai-agents-consequence-gate.md

Dependencies:
- existing WorkspaceExecutionBinding / ProposedAction contracts
- existing canonical_digest helper
- OpenAI Agents SDK tool-input guardrail contract as an external integration surface only

Invariants:
- every consequence-bearing function tool call is checked immediately before execution
- exact tool name + parsed arguments are digest-bound to the authorized action
- stale or missing clearance fails closed
- DENY / ESCALATE / DEFER / malformed inputs produce zero tool effect
- OpenAI guardrails transport/enforce the decision; they do not mint VALO authority
- no mandatory openai-agents runtime dependency is introduced into valo-kernel
