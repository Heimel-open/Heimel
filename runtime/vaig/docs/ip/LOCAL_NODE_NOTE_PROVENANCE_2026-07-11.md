# Provenance Classification — Local-Node Authority Preservation Note

Date: 2026-07-11
Target: `docs/eu_submission/06_local_node_normative_anchor.md`

## Classification

`historical_collaboration_draft`

The target document is a composite EU-submission support note created during a collaboration period. It contains a mixture of:

- VALO/VAIG execution-boundary concepts
- local-node and shadow-IT risk analysis
- Authority Visibility and Governability Architecture language
- explicit MECHA, EFA, WHY Gate and RRP references
- later implementation candidates

It must not be treated as the current normative architecture for VAIG, REHT, RACS or VALO Core.

## Active architecture boundary

The current VALO architecture is:

```text
Reality
→ Speider
→ BARO
→ VALO Harness
→ VAIG
→ REHT
→ VALO Core
→ Execution
→ RACS Receipt
```

Human and organizational authority are external governed inputs. MECHA, EFA, WHY Gate and RRP are not active runtime dependencies.

## Preserved value

The document contains potentially reusable VALO-owned or independently developed ideas, including:

- governance following the point of consequence
- local-node and invisible-node risk
- shadow IT as authority leakage
- topology-aware execution controls
- evidence that human presence is not equivalent to retained authority
- node-level receipt and state evidence

These ideas may be restated in clean-room active documentation without importing collaboration-specific terminology or ownership claims.

## Required handling

1. Preserve the original file and Git history.
2. Do not index it as active architecture.
3. Do not present its architectural split as current VALO design.
4. Extract reusable concepts into a new VALO-owned active note using current terminology.
5. Keep authorship and contribution questions separate from technical usefulness.
6. Mark factual legal and market claims for independent source verification before external use.

## Recommended replacement

Create a clean active document titled:

`docs/architecture/LOCAL_EXECUTION_BOUNDARY_AND_NODE_INTEGRITY.md`

It should use only current components and define:

- managed-node state
- authority evidence at consequence commit
- stop-right and escalation evidence
- connector/tool provenance
- node integrity and receipt capability
- shadow-IT detection as BARO evidence
- VAIG evaluation
- REHT admissibility
- Core enforcement
- RACS receipt linkage
