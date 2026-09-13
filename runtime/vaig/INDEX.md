# VAIG Index

Status: internal navigation index  
Date: 2026-08-02

## Start here

- `README.md` — current VAIG runtime-governance boundary
- `SYSTEM_MAP.md` — authoritative current VALO architecture and terminology
- `docs/architecture/rich-state-evaluation-contract.md` — canonical rich-state input, tail-risk evaluation and REHT handoff mapping
- `docs/GEA_CURRENT_ARCHITECTURE_2026-07-11.md` — active VALO-owned Governance Execution Architecture
- `TEST_EVIDENCE.md` — evidence and claim-maturity map
- `PILOT_PACKAGE.md` — bounded pilot package
- `CLEANUP_PLAN.md` — cleanup and freeze checklist

## IP and provenance

- `docs/ip/CHARLES_RUPP_TRACE_REGISTER.md` — collaboration-reference audit and cleanup record
- `docs/ip/MECHA_FORMAL_MODEL_OWNERSHIP.md` — formal-model ownership boundary from Zenodo DOI `10.5281/zenodo.20668225`
- `docs/ip/OWNERSHIP_CLARIFICATION_LOG_2026-07-11.md` — owner clarifications for GEA, Ambient Overlay and formal-model contributions
- `docs/ip/AI_ASSISTED_AUTHORSHIP_AND_ECHO_RISK.md` — rule against treating AI repetition as independent validation
- `docs/ip/IP_CLASSIFICATION_MATRIX.md` — component and artifact ownership classification

## Current architecture

```text
Reality
→ Speider
→ BARO
→ MAL admits model/runtime/output contract
→ VALO Harness invokes and preserves provenance
→ model produces proposed action + optional RichStateEnvelope
→ VAIG evaluates evidence, state, uncertainty, boundaries and tail risk
→ REHT determines present admissibility and clears or refuses the exact action
→ RACS binds the decision and constraints
→ VALO Core enforces fail-closed
→ Execution
→ Receipt / Veritas custody and outcome linkage
```

## Rich-state rule

For history-dependent or consequence-sensitive workflows, VAIG must not rely only on a direct final answer when policy requires a richer contract.

The governed object may include:

- relevant history scope and digest;
- represented state and digest;
- representation and granularity level;
- source evidence and transformation lineage;
- proposed action and action digest;
- uncertainty, alternatives and omissions;
- boundary conditions and tail-risk summary;
- authoritative-correction reference.

A state digest proves identity and integrity of the representation. It does not prove truth, completeness or sufficiency.

VAIG evaluates the actual produced state. MAL only admits the model, runtime and required output profile. REHT alone clears the exact action.

## Historical material

Older documents may contain ACS, VACS, MECHA, EFA or temporary collaboration-stack language. They remain as provenance but are not normative unless explicitly linked from the current system map.

The MECHA paper is a joint publication. Its formal TLA+ model, model checking, verification results and VALO infrastructure descriptions are recorded as Njål Gaute Solland's contribution under the paper's explicit copyright and author-contribution sections.

## Current principle

```text
Models propose.
MAL admits the model and output contract.
The Harness orchestrates.
VAIG evaluates.
REHT clears.
RACS binds.
Core enforces.
Receipts attest.
Veritas preserves custody and links outcomes.
```
