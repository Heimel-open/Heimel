# Historical MECHA Formal-Model Directory

Status: historical research and joint-publication support material
Date classified: 2026-07-11

This directory is preserved for provenance, reproducibility and historical research context.

It is not the active formal-verification entry point for VALO Core.

The active core model is:

`formal-verification/ValoStateMachine.tla`

## Ownership and attribution boundary

The deposited MECHA paper is a jointly authored publication by Charles R. Rupp and Njål Gaute Solland.

The publication record separates contributions:

- Charles R. Rupp: EFA semantics, MECHA tuple, HSRS, Empty Cockpit and related definitions.
- Njål Gaute Solland: TLA+ specification, model-checking implementation, verification results and VALO infrastructure descriptions.

Files in this directory must therefore be assessed at file level. Their location under `mecha/` does not by itself imply joint ownership, Charles Rupp ownership or an active runtime dependency.

## Runtime boundary

Active architecture:

```text
VAIG evaluates runtime conditions.
REHT determines admissibility semantics.
VALO Core enforces bounded state transitions.
RACS carries action and receipt contracts.
```

No active VALO Core runtime component may import MECHA, EFA, HSRS or Empty Cockpit semantics unless that dependency is explicitly documented, licensed and tested.

## Use rules

- Historical models may be executed only through explicit paths.
- CI and default scripts must target the active `formal-verification/` model.
- Historical research artifacts must not be cited as current production architecture.
- Git history and attribution must be preserved.
- Any reuse in active code requires a separate provenance and dependency review.
