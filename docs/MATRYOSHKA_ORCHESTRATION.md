# Matryoshka orchestration adoption

Status: canonical factory pattern
Source: https://arxiv.org/abs/2607.25090
Owner: `nsolland/valo-factory`

VALO adopts the Matryoshka Agent pattern as a provider-neutral orchestration pattern inside Agent Factory / Dispatcher.

It is not a new OS, not a new LA layer, and not an authorization mechanism.

## Canonical model

The orchestrator keeps only compact strategic state across long-running work: goal, constraints, current state, decisions, dependency state, work status and evidence references.

Concrete work is unfolded into short-lived, replaceable workers. Each worker receives only the context required for its bounded mission and owned files. Full worker transcripts are disposable context and are not promoted into canonical state.

Workers return structured deltas rather than narrative history:

- state delta
- artifact references
- evidence references
- tests/checks performed
- unresolved items

`WORK_CONTRACT.json` remains the canonical worker handoff surface. `valo-orchestrator` remains the canonical factory control process.

## Separation of duties

The orchestrator coordinates but does not authorize.

Workers implement but do not self-attest.

Independent QC verifies returned work against executable evidence.

For consequence-bearing execution, current VALO separation remains unchanged:

`worker/orchestrator -> VAIG evaluation -> REHT authorization -> RACS decision contract -> external enforcement -> Veritas/receipts`

Orchestration state, model confidence, worker claims and prior transcripts never constitute an execution permit.

## Required behavior

A worker can fail, restart or be replaced without changing authority state. Provider/model swaps must not change governance semantics. Context compaction must preserve evidence references and unresolved dependencies, while dropping redundant transcript history.

The orchestrator may select, retry or replace workers, but it may not expand their authority, certify their output as correct, revive expired authority or bypass independent verification.

## Existing VALO role mapping

- Kristina / coordinator role: compact strategic orchestrator
- Codex, Antigravity, Hermes and conformant workers: bounded disposable workers
- Work Contract: explicit handoff and scope
- Independent QC: verification
- REHT: sole final execution authorization boundary
- Veritas / receipts: observed execution evidence

This pattern extends the existing dispatcher architecture. It does not create another agent hierarchy with independent authority.
