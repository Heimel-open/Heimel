# ADR: Provenance-preserving token-free edge memory

Status: ADOPTED FOR VALO EDGE DESIGN
Date: 2026-08-04
Repository: `nsolland/valo-edge`
Canonical base: `2664c07d38315d0ed36a06f2ccadab49ba2b61c5`
Source: Zero-Mem, arXiv:2607.29377v1

## Decision

VALO Edge adopts the following memory doctrine for LastSeen and later local agents:

1. Original local observations and Veritas receipts are the source of record.
2. Summaries, embeddings, entity graphs, aliases and temporal structures are derived indexes only. They never replace or rewrite source evidence.
3. Memory construction, organization, routing, retrieval and deterministic calibration should run locally without LLM calls where practical.
4. A local model may interpret retrieved evidence or propose an answer, but it has no authority to store, expose, combine or delete memory.
5. micro-REHT clears the concrete memory consequence. The gateway performs it. Veritas records what actually happened.

Canonical rule:

> Generative models may interpret memory, but they do not rewrite history. Original traces are authoritative; derived structures are indexes. micro-REHT decides whether retrieved memory may be used for the concrete consequence.

## Why this fits Edge AI

This architecture reduces recurring model calls, network dependency and token cost. It also preserves provenance and supports offline operation, bounded latency and local privacy.

The paper's reported latency is not an edge-device benchmark. Its experiments used four concurrent threads and RTX 4090 GPUs. NER, embeddings, lexical indexes, graph traversal and storage still consume compute, memory and energy. VALO Edge must therefore benchmark every adopted component on target hardware and retain a simpler fallback path.

## LastSeen adoption

The current MVP remains intentionally simple: governed SQLite observations, newest-observation lookup, aliases and explicit deletion.

The Camera Alpha should extend this foundation in this order:

1. Preserve immutable source identifiers, observation time, ingestion time, camera and zone scope, actor or device identity, policy version and receipt digest.
2. Add a deterministic temporal hierarchy over observation, local window, episode and session boundaries.
3. Add lexical lookup for exact names, aliases, dates, locations and identifiers.
4. Add local dense retrieval only when measurements show that lexical and temporal retrieval are insufficient.
5. Add an entity-context graph only for demonstrated cross-session or relational queries. It must not enter the critical path without edge benchmarks.

Every derived index entry must resolve to one or more source observation identifiers. Indexes must be rebuildable from retained source records.

## Governance boundary

Existing governed actions remain authoritative:

- `STORE_OBSERVATION`
- `READ_LAST_SEEN`
- `DELETE_OBJECT_HISTORY`

Future index maintenance may introduce `REBUILD_MEMORY_INDEX`, but only as an explicit governed mutation with a bounded scope and receipt.

The retrieval boundary must include the authorized object or alias, location scope, camera scope, time range, requester or device identity and policy version when available. Retrieval outside that boundary fails closed.

## Deletion and evidence

Deleting an object's history removes the source observation content and every derived index entry that resolves to it.

A Veritas deletion receipt may retain a non-reversible digest, policy version, timestamp and deletion result. It must not retain the deleted image, location text or other recoverable personal content.

## Acceptance gates

- No LLM call is required to ingest, index, retrieve, calibrate or delete LastSeen memory.
- No model, detector or indexer writes directly to persistence.
- Every retrieved item resolves to retained source evidence.
- Query scope is enforced before evidence reaches a reader or UI.
- Deletion removes source content and all derived references.
- Index rebuilds are deterministic for the same retained source set and configuration.
- The full path works without network access.
- Latency, memory and energy are measured on each supported edge profile.
- A simple SQLite temporal lookup remains available if dense or graph components exceed the device budget.

## Non-claims

This adoption does not claim that Zero-Mem proves truth, production security or execution governance. Its evaluation is based on question-answering benchmarks, not physical agents, adversarial memory poisoning, deletion guarantees, concurrent writers or authority enforcement. VALO supplies those boundaries through micro-REHT, the gateway and Veritas.