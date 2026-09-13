# Muse Code runtime patterns in VALO Factory

Status: adopted pattern, optional harness identity fail-closed
Source: Meta AI Research, "Introducing Muse Code and Muse Spark 1.2", 2026-08-05

## What is adopted

Meta describes Muse Code as a coding harness with persistent background specialists, an append-only local event log, restart-safe exact replay, goal-directed execution, context compaction, and long-horizon repository work.

VALO adopts those runtime patterns provider-neutrally:

1. Persistent specialists are stable identities within one bounded Factory run. Re-requesting the same role reuses the same identity instead of silently spawning a fresh context.
2. Runtime events are append-only and hash chained. Model calls, tool runs, approvals and edits can be replayed from the same durable source of truth.
3. Goal binding is immutable inside a run. A materially different objective requires an explicit new run rather than silent goal drift.
4. Context compaction preserves a source event-chain hash and compaction digest. A compacted summary is guidance, not evidence and not authority.
5. Recovery reopens the durable store, verifies the event chain, restores the goal and persistent specialists, and replays exact events after the latest compaction point.

Implementation: `lib/muse_code_runtime.py`.

## What is not imported

Muse Code is not an authority layer and Muse runtime state is not authorization evidence.

The canonical Factory boundary remains:

VAIG evaluates -> REHT authorizes -> RACS expresses -> external execution boundary enforces -> Veritas records evidence.

A model call, agent message, plan, approval event, compacted context, harness success result or specialist state cannot substitute for fresh authorization bound to the exact consequence-bearing action.

## Harness status

`muse_code` is registered as a replaceable harness identity in `config/harness-providers.json` and `lib/harness_provider_adapters.py` so workflow invocations can bind the intended harness separately from model/provider identity.

Execution remains fail-closed. The public Meta announcement documents the product and runtime architecture, but this adoption does not assume an undocumented bounded non-interactive CLI contract or execution-mode controls. `plan_harness_execution("muse_code", ...)` therefore rejects execution until those surfaces are documented and conformance-tested.

This keeps the useful architecture while avoiding accidental authority leakage or invented wrapper guarantees.
