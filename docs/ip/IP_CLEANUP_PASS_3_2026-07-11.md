# IP Cleanup Pass 3 — 2026-07-11

## Scope

This pass continued the separation of active VALO architecture from historical collaboration frameworks while preserving attribution, source history and coauthored material.

## Changes completed

### VAIG submission material

The following files were reclassified as historical collaboration drafts rather than active VALO architecture:

- `SUBMISSION_PACKAGE.md`
- `docs/eu_submission/00_submission_package.md`
- `docs/eu_submission/01_executive_summary.md`

The documents remain available for historical and submission-context purposes. Their collaboration-specific architecture must not be interpreted as a current runtime dependency.

### VAIG execution boundary

`docs/architecture/vaig-execution-boundary.md` was updated so that human and organizational authority are represented as external accountable inputs rather than being owned by a named collaboration framework.

### VALO Core TLC runner

`nsolland/valo-v5-core/scripts/run_tlc.sh` now uses the VALO-owned active state machine as its default target:

`formal-verification/ValoStateMachine.tla`

Historical collaboration models under `mecha/` remain available only when explicitly selected.

Classification:

- active default: `valo_owned`
- explicitly selected historical model: `historical_joint_work` or `external_reference`, depending on the artifact

### VALO Core pre-intent architecture

`nsolland/valo-v5-core/docs/architecture/PRE_INTENT_GOVERNANCE_ALIGNMENT.md` was updated to:

- remove MECHA/BOA as active architectural dependencies
- represent human and organizational authority as external accountable inputs
- separate VAIG evaluation, REHT admissibility, Core enforcement and RACS receipts
- preserve the boundary between pre-intent evidence checks and the bounded TLA execution state machine

### VALO Platform governability position

`nsolland/valo-platform/docs/governability-architecture-position.md` was rewritten around the current active architecture:

Reality -> Speider -> BARO -> VALO Harness -> VAIG -> REHT -> VALO Core -> Execution -> RACS Receipt

The file now states explicitly that:

- historical collaboration frameworks are research context, not runtime dependencies
- VALO does not manufacture human standing or organizational authority
- RACS defines contracts and receipts but does not decide
- orchestration, evaluation, admissibility and enforcement remain separate responsibilities

## Preservation rules applied

- Git history was not rewritten.
- Historical and coauthored artifacts were not deleted.
- Attribution was preserved where applicable.
- Generic governance ideas were not claimed as exclusive IP.
- VALO-owned formal models, implementation, verification results and current architecture were separated from collaboration-specific semantics.

## Remaining priority work

### VAIG

- classify and annotate `docs/eu_submission/06_local_node_normative_anchor.md`
- review remaining GEA and historical research documents
- review VACS/ACS-era profiles and mark them historical or migrate them to RACS where appropriate

### VALO Core

- review `mcp_server.py` for ACS-era terminology and unsupported standards claims
- classify `mecha/` formal artifacts individually
- review `validation.md`, `whitepaper.md` and historical analysis files
- update Core trace register after file-level classification

### VALO Platform

- review source comments and enums that still imply MECHA ownership
- review configuration-manager and historical phase summaries
- classify legacy ACS service paths
- update Platform trace register after file-level classification

## Index rule

`nsolland/Index` must not be updated until the multi-repository cleanup and final verification pass are complete.
