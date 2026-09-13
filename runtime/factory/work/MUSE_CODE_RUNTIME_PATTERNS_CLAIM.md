# Muse Code runtime patterns claim

Status: active
Owner: execution worker
Repository: nsolland/valo-factory
Canonical base SHA: 1296f2f22a757f180a3134b17dbae1e5795945c7
Branch: feat/muse-code-runtime-patterns
Draft PR: #84

Owned files:
- work/MUSE_CODE_RUNTIME_PATTERNS_CLAIM.md
- lib/muse_code_runtime.py
- lib/harness_provider_adapters.py
- config/harness-providers.json
- tests/test_muse_code_runtime.py
- tests/test_jcode_harness_adapter.py
- docs/architecture/muse-code-runtime-patterns.md

Dependencies:
- existing provider-neutral long-horizon harness
- existing replaceable harness provider contract
- existing VAIG -> REHT -> RACS execution authorization invariant
- existing Veritas receipt boundary for external effects
- Meta AI Research, "Introducing Muse Code and Muse Spark 1.2", 2026-08-05

Scope:
Adopt the useful Muse Code runtime patterns without importing Muse Code as an authority source: persistent specialist subagents, append-only replay-exact event history, restart-safe run recovery, explicit goal binding, provenance-preserving context compaction, and optional Muse Code harness identity. Harness/runtime state remains non-authoritative. Consequence-bearing actions still require fresh VAIG -> REHT -> RACS authorization and Veritas evidence. Muse Code execution stays fail-closed until a bounded CLI contract is documented and conformance-tested.
