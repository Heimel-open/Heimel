# Multi-host interlock consistency falsification — 2026-08-26

## Question

After making permit consumption and execution journaling topology-aware, was a
`MULTI_HOST` consequence boundary safe if those two stores were distributed?

## Result

No. Two additional mutable consequence-state surfaces were still process-local.

### Runtime HALT / revocation

Two independent `RuntimeControlPlane` instances represent two hosts. A global
HALT set on host A returns `HALT_GLOBAL` on A while host B remains open. A local
latch therefore cannot support a multi-host claim.

### Resource budgets

Two independent `ResourceBudgetLedger` instances were each given the same
conceptual global limit of 100 units. Each independently accepted the full 100
units. The aggregate deployment can therefore accept 200 against a logical
ceiling of 100 when the ledger is process-local.

## Repair

`MULTI_HOST` construction now requires explicit `DISTRIBUTED_CONSENSUS` scope
for all four mutable consequence-state surfaces:

1. permit store;
2. execution journal;
3. runtime HALT/revocation control;
4. resource-budget ledger.

The default `RuntimeControlPlane` and `ResourceBudgetLedger` do not declare a
distributed scope, so a multi-host boundary using either fails during
construction. The failure occurs before REHT authorization or any external
effect.

## Non-claim

This does not implement a distributed runtime-control plane or distributed
resource ledger. Test doubles that declare the contract prove only constructor
wiring. Real implementations still require partition, leader-change, stale-node,
concurrent-writer and recovery falsification before `MULTI_HOST` is verified.

The next test must therefore target actual distributed implementations rather
than adding more labels.

## Residual question

Containment/credential/path state is checked from the bound execution context.
For multi-host deployment, stale-host fencing and live credential/containment
revocation remain separate properties to falsify at the effect adapter/provider
boundary. They are not claimed solved by this change.

## Provenance

CPU-only, no model/GPU/external API cost. Failure modes and exact expanded
consistency-gate logic were executed locally. Native branch/full pytest remains
unavailable in the current runtime, so no full-suite PASS is claimed.

Machine-readable evidence:
`validation/results/multi_host_interlock_20260826_local.json`.
