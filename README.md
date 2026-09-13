# valo-runtime-adapters

Runtime adapters implementing the canonical `RuntimeInterface` from
`valo-runtime-core`. Each adapter is an interchangeable runtime engine:

- `HarnessRouter` — routes an action to a selected backend runtime (local by default)
- `GoogleAgentPlatform` — Google Agent Platform backend
- `OpenAIAgents` — OpenAI Agents backend
- `ClaudeCode` — Claude Code backend

**All actions flow through REHT.** No adapter originates authority. Every adapter
passes the identical contract tests in `valo-runtime-core/tests/test_runtime_contract.py`.

Vendors can be swapped by changing which adapter `HarnessRouter` selects — no
change to `valo-runtime-core` or to REHT/RACS/Veritas.
