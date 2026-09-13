# Governing Contract Drift v1

## Normative rule

The governing contract cannot drift during a governed continuation.

A contract that determines whether a work unit is legitimate, in scope or executable must be declared in `WorkspaceSpec.governing_contract_ids`. Declaration is explicit; Kernel never guesses which contract governs a work unit.

Each declared governing contract must:

- exist in current Kernel state;
- be operative (`SIGNED` or current `AMENDED` state);
- be active when the workspace is compiled;
- remain active for at least the lifetime of the workspace.

The contract itself does not need to be shown to the worker. Kernel adds it as a hidden `StateDependency`, binding its exact canonical digest into the workspace dependency digest.

## Drift behavior

If a governing contract is amended, terminated, replaced or otherwise changes while a worker is operating on an existing workspace, conformance returns `DEFER` with `GOVERNING_CONTRACT_DRIFT`.

The old candidate cannot be rebound under the changed contract. The required continuation is:

```text
contract change
  -> old workspace invalid
  -> DEFER
  -> compile fresh workspace under current contract
  -> rerun/re-evaluate candidate as required
  -> fresh VAIG evaluation
  -> fresh REHT authorization
```

A contract expiry cannot occur inside an otherwise valid workspace because compilation rejects any workspace whose expiry exceeds a governing contract's `valid_until`.

## Program/workflow distinction

Compiled program/workflow identity was already protected before this change: `program_ref` and `program_digest` are atomically bound into the sealed workspace and carried into `WorkspaceExecutionBinding`. Changing the compiled program therefore changes the workspace digest.

This change closes the separate gap for mutable institutional/business `Contract` state. Governing contract IDs and their exact dependency digests are now carried into the execution binding delivered downstream.

## Boundary

Contract freshness creates no authority and issues no clearance. It only proves that the candidate was evaluated under the same governing contract state that the workspace was compiled against. Fresh execution authorization remains REHT's responsibility.
