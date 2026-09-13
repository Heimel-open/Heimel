# Long-horizon harness

VALO Factory adopts the architecture pattern from Google ADK Long Horizon without adopting Google ADK or Vertex as an authority dependency.

Reference observed: `google/adk-samples` `core/python/long-horizon-harness`, main at `f9f7e2124b37426a104e54ec0ac93e83cdf3d9f5` on 2026-08-08.

## Adopted pattern

The harness provides:

- durable run checkpoints and explicit resume cursors;
- isolated child contexts with their own sandbox and owned-file scope;
- a non-blocking judge fork whose output is evidence only;
- deterministic context compaction that preserves source digests and evidence references;
- durable sandbox lifecycle: `CREATED -> ACTIVE -> SEALED -> RELEASED`;
- an action journal that prevents automatic replay of completed side effects and blocks ambiguous `PREPARED` actions for reconciliation;
- a fail-closed right-before-action gate.

## Authority boundary

Harness state has no authority effect.

For every consequence-bearing action, the gate computes the exact action digest and invokes an external authorization callback immediately before execution. The callback must return three separately bound artifacts:

`VAIG evaluation -> REHT clearance -> RACS decision`

All three artifacts must bind to the same action digest. REHT remains the final authorization boundary; RACS expresses the decision. Only `RACS=ALLOW` executes in this harness version. `MODIFY`, `DEFER`, `DENY`, `STEP_UP`, and `HALT` do not execute.

The harness never treats memory, a judge result, a provider response, a sandbox state, a checkpoint, or resumability as authority.

## Crash and replay semantics

A side effect is journaled as `PREPARED` immediately before the executor is invoked and `COMPLETED` only after it returns.

- `COMPLETED`: resume returns the stored result digest and never replays the action.
- `PREPARED`: the process may have crossed the external boundary. Automatic replay is denied; reconciliation is required.
- no journal row: a fresh VAIG -> REHT -> RACS authorization is required before execution.

This chooses duplicate-side-effect prevention over optimistic retry.

## Sandbox durability

Sandbox lifecycle state is persisted independently of process memory. A restarted harness can recover the lifecycle state and verify it against the checkpoint before resuming. A mismatch fails closed.

`SEALED` records a deterministic manifest digest. `RELEASED` removes the working directory but retains lifecycle metadata and the sealed digest.

## Judge separation

The judge fork runs separately from the worker path and cannot self-attest. Provider independence is recorded explicitly so stricter QC policy can require a different provider. Judge findings remain `authority_effect=none`.

## Dependency policy

This is a provider-neutral pattern adoption. There is no required dependency on Google ADK, Vertex AI, Gemini, Memory Bank, or Vertex sandboxes. Those remain possible capability providers behind VALO-owned contracts.
