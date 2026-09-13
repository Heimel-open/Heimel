# Windows Capability Adapter v0 — Work Anchor

Issue: #68
Owner: ChatGPT for Njål
Canonical base: `0a8205f8a3c169eede7b7d8e50c4d66a950d5c32`
Branch: `feat/windows-capability-adapter-v0`

## Active delivery

Add a provider-neutral adapter boundary for Windows capability invocation surfaces such as MCP and App Actions. The adapter MUST resolve fresh authority immediately before effect execution, fail closed when authorization is missing/stale/denied, and return an evidence receipt.

## Owned files

- `docs/work-anchors/windows-capability-adapter-v0.md`
- `src/valo_kernel/windows_capability_adapter.py`
- `tests/test_windows_capability_adapter.py`

## Dependencies

- Existing VALO deterministic authorization semantics.
- No Windows SDK dependency in v0; Windows-specific bindings sit outside the kernel and feed normalized requests into this adapter.

## Invariants

1. Discovery is not authority.
2. No provider invocation before commit-time authorization returns ALLOW.
3. Authorization is evaluated against the exact normalized effect request.
4. DENY and ESCALATE never invoke the provider.
5. Missing or stale authority fails closed.
6. Every decision returns deterministic evidence material suitable for replay.
