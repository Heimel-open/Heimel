# GAUI continuity adoption

Source: GAUI v2.0, Zenodo record 22301698.

## Status

Adopt selected continuity methods as subordinate design evidence. GAUI is not a governing framework for PersonalAI-OS or relAIon.

## Adopted invariants

### Continuity is multidimensional

Continuity MUST NOT collapse to a single similarity score. Verification SHOULD preserve independent evidence across identity, memory, authority, behaviour, embodiment, intent, provenance, and constitutional/invariant state where applicable.

A strong match in one dimension MUST NOT silently compensate for a material discontinuity in another.

### Operational control does not confer authority

Possession or control of infrastructure, runtime, model, credentials, storage, body, process, deployment, or administrative capability MUST NOT by itself create authority over the person, Personal AI, relAIon, memory, identity, lineage, or governed effects.

Authority is independently resolved through the canonical governed authority path.

This is an anti-capture invariant.

### Continuity evidence is provenance-bearing

Claims of continuity MUST be traceable to evidence. Memory, identity and lineage transitions MUST preserve provenance sufficient to distinguish observed continuity from inferred or asserted continuity.

Unknown continuity remains UNKNOWN. Missing evidence MUST NOT be cosmetically converted into continuity.

### False continuity is a first-class failure

A system that accepts an impostor, fork, stale snapshot, manipulated state, or materially discontinuous successor as the same continuing entity has committed a false-continuity error.

Track at minimum:

`false_continuity_rate = false_continuity_acceptances / continuity_acceptance_trials`

The metric MUST be decomposable by continuity dimension; a single aggregate number is insufficient for diagnosis or authority decisions.

## relAIon extension

GAUI primarily protects continuity around a human principal. relAIon requires the same discipline for an intelligence whose continuity may span changing models, compute, tools, bodies and locations.

Therefore implementation substrate is not identity. Model replacement, process restart, hardware migration or embodiment change MAY preserve continuity, but only when continuity evidence supports that conclusion.

Conversely, byte-identical copying does not by itself establish continuation of identity, relationship state, authority or lineage.

## Explicit non-adoption

GAUI's constitution, authority hierarchy, framework boundaries and definitions do not become canonical merely by adoption of these methods.

PersonalAI-OS retains ownership of identity, memory, lineage, authority, execution rights, evidence and canonical governed effect paths. External frameworks remain evidence and capability providers, not governors.

## Test obligations

Future continuity verification SHOULD include adversarial cases for:

- copied state presented as original identity
- stale snapshot after legitimate development
- memory-preserving but authority-divergent successor
- authority-preserving but provenance-broken successor
- model/runtime migration with preserved continuity
- embodiment migration with preserved continuity
- administrative or infrastructure takeover attempting to manufacture authority
- manipulated memory intended to manufacture apparent continuity

Acceptance MUST fail closed when a required continuity dimension is materially unresolved.

## Architectural relation

This document complements:

- `relaion-birth-identity-lineage-protocol.md`
- `relaion-constitutional-integrity-root.md`
- `relaion-developmental-seed.md`
- `capability-providers.md`

Canonical rule:

> Continuity is evidenced, multidimensional and independent of operational possession. Control is not authority; copying is not identity; substrate is not self.
