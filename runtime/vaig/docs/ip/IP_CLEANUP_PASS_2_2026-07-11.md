# IP Cleanup Pass 2 — 2026-07-11

Status: completed

## Scope

This pass reviewed active-facing architecture and repository-navigation files that still mixed current VALO components with collaboration-era or archived terminology.

## Changes

### `docs/eu_submission/index.md`

Classification: `historical_joint_work`

Action:

- replaced the active-facing submission framing with an explicit historical collaboration notice
- preserved original authorship and subject matter in Git history
- stated that MECHA and EFA are not active VALO runtime dependencies
- recorded the Zenodo contribution split for DOI `10.5281/zenodo.20668225`
- pointed readers to the current VALO system map and IP classification records

Reason:

The file listed multiple authors and collaboration-specific components as if they were part of the current normative architecture. It is now retained as historical evidence rather than an active source of truth.

Commit: `9c6e34ae34525ebb701d5ebe63b00d7b7e69d683`

### `docs/architecture/EXECUTION_BOUNDARY_ARCHITECTURE.md`

Classification: `valo_owned_active_architecture`

Action:

- removed ACS/VACS as the active protocol path
- removed MECHA and IGL as required runtime dependencies
- replaced Phi Runtime terminology with the current REHT and VALO Core boundary
- added VALO Harness as the orchestration layer
- defined RACS as the clean-room contract standard
- documented Speider and BARO as upstream observation layers
- added continuous-integrity, formal-claim and AI-echo boundaries

Reason:

The file is VALO-owned architecture but contained obsolete collaboration and standard terminology. The underlying execution-boundary concept remains active; only the dependency map and terminology were corrected.

Commit: `133a4b662009d3f0bc40183df8df8def1537eaf5`

### `valo-platform/docs/repository-map.md`

Classification: `valo_owned_active_navigation`

Action:

- replaced archived `ACS` with active `Racs`
- added `reht` and `Speider`
- clarified VAIG, BARO, Core and Platform boundaries
- marked the old ACS repository as third-party/imported historical material
- recorded the MECHA paper contribution split
- added IP, provenance and claim-maturity rules
- defined the current repository dependency direction

Reason:

The previous repository map directed active development toward an archived and imported ACS repository and omitted newly separated source-of-truth repositories.

Commit: `04c3f5231b8cf17e5fda363be7cb54d071c58de7`

## Current active path

```text
Speider -> BARO -> VALO Harness -> VAIG -> REHT -> VALO Core -> Execution
                         \________________ RACS contracts ________________/
```

## Preservation

No Git history was rewritten.

Original states remain available in repository history and backup branches:

- `VAIG: backup/pre-charles-ip-cleanup-2026-07-11`
- `valo-platform: backup/pre-ip-cleanup-2026-07-11`
- `valo-v5-core: backup/ip-cleanup-2026-07-11`

## Remaining priorities

- `SUBMISSION_PACKAGE.md`
- `docs/eu_submission/00_submission_package.md`
- `docs/eu_submission/01_executive_summary.md`
- `docs/eu_submission/06_local_node_normative_anchor.md`
- `docs/architecture/vaig-execution-boundary.md`
- Core comments and scripts that use collaboration-era naming
- Platform governability and phase-summary documents
- final consolidated update to `nsolland/Index`
