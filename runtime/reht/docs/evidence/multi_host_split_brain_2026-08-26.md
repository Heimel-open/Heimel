# Multi-host split-brain falsification — 2026-08-26

## Question

Can the current same-host SQLite permit store and execution journal safely be
used as if they provide one multi-host consequence truth?

## Result

No.

A two-host split-brain probe used independent SQLite databases on each simulated
host. Across 1,000 permit references, both hosts successfully consumed the same
permit 1,000/1,000 times. Across 1,000 execution intents, both hosts successfully
opened the same logical intent 1,000/1,000 times.

This is expected behavior for independent SQLite databases. It confirms that
`production_safe=True` was too coarse to express deployment topology.

## Repair

The consequence boundary now distinguishes:

- `PROCESS_LOCAL`
- `SAME_HOST_SHARED`
- `DISTRIBUTED_CONSENSUS`

and deployment topology:

- `SINGLE_HOST`
- `MULTI_HOST`

`SQLitePermitStore` and `SQLiteExecutionJournal` explicitly declare
`SAME_HOST_SHARED`. `EffectBoundary(..., deployment_topology="MULTI_HOST")`
fails during construction unless both permit truth and execution-journal truth
explicitly declare `DISTRIBUTED_CONSENSUS`.

The gate executes before REHT authorization, permit consumption, journal intent,
or external effect invocation.

## What this proves

- independent same-host stores are not cross-host single-use truth;
- accidental use of SQLite as declared multi-host production is fail-closed at
  boundary construction;
- undeclared consistency scope is rejected for multi-host topology;
- single-host production behavior remains available.

## What this does not prove

No distributed-consensus persistence backend is implemented or verified by this
change. A backend that declares `DISTRIBUTED_CONSENSUS` remains responsible for
actually satisfying that contract under partitions, failover, leader changes,
concurrent writers, stale replicas, and crash recovery.

The declaration is a deployment contract, not cryptographic or mathematical
proof of the backend implementation.

## Provenance

CPU-only, no model/GPU/external API cost.

The split-brain probe was executed locally with the same SQLite primary-key,
transaction, WAL and FULL-sync semantics used by the reference stores. The exact
consistency-gate function committed on the branch was executed locally against
same-host, undeclared, distributed and invalid-topology cases.

Native branch checkout/full pytest was not available because the local runtime
could not resolve `github.com`; hosted Actions has also been failing before job
startup. Therefore no native-checkout full-suite PASS is claimed here.

Machine-readable evidence:
`validation/results/multi_host_split_brain_20260826_local.json`.
