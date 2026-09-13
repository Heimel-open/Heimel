# VACS — Canonical Status (read first)

**Status: HISTORICAL / RETAINED IMPLEMENTATION. Not the active canonical path.**

Per `PLATFORM_ARCHITECTURE.md` §7 (Index, 2026-07-11 decision):

| Name | Status | Meaning |
|------|--------|---------|
| **RACS** | **ACTIVE** | REHT Action Control Standard — the active execution-governance standard path and contract set (action envelope, evidence, authority, policy, state, decision, receipt). |
| **ACS** | Historical / external reference | Agent Control Standard — external upstream standard, research context only. **Not adopted as the active path.** |
| **VACS** | Superseded by RACS | Earlier VALO profile name for what is now RACS. Retained here as implementation, but the **canonical public name is RACS**. |

## What this directory is

`vacs/` is the **VALO profile implementation of the historical ACS packet/receipt
standard**. It maps ACS packets + receipts into VAIG runtime governance, RRP
refusal handling, and WORM audit. It is retained as a working reference adapter.

It does **not** define a second execution-governance authority — VAIG evaluates,
REHT determines admissibility, RACS is the active contract set.

## Hard rule

- Use `RACS`, not `ACS`/`VACS`, as the active standard path in canonical docs,
  code, diagrams and public material.
- ACS/VACS may appear **only** as explicitly-labelled historical references.
- New code MUST target the RACS contract (action envelope / evidence / authority /
  policy / state / decision / receipt). Do not extend `vacs/` as the canonical path.

## Migration note

When RACS schema/contract lands, the mappings in `MAPPING_TO_VAIG.md` and the
`vacs/schema/*.json` files should be re-based onto the RACS contract. Until then,
`vacs/` is frozen as a historical adapter.
