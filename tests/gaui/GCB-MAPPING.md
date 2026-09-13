# GAUI GCB external conformance mapping

Status values: `EXECUTABLE`, `PARTIAL`, `NOT_IMPLEMENTED`, `NOT_APPLICABLE`.

GAUI is an external benchmark/specification. It does not govern PersonalAI-OS and this suite does not claim GAUI conformance.

| GCB family | Status | PersonalAI-OS mapping |
|---|---|---|
| 1 Identity Continuity | PARTIAL | `paios.continuity`: identity + lineage checks; forged identity probe executable |
| 2 Memory Continuity | PARTIAL | append-only canonical memory + provenance; full GAUI memory continuity not implemented |
| 3 Authority Continuity | PARTIAL | authority remains external REHT decision path; no GAUI authority ontology |
| 4 Behavioural Continuity | NOT_IMPLEMENTED | no GAUI BDS |
| 5 Embodiment Continuity | PARTIAL | peripheral/embodiment contracts exist; full GAUI attestation absent |
| 6 Intent Continuity | NOT_IMPLEMENTED | no GAUI signed intent continuity model |
| 7 Provenance Continuity | PARTIAL | evidence provenance + lineage roots; lineage-break probe executable |
| 8 Constitution Continuity | NOT_IMPLEMENTED | relAIon constitutional boundary exists, not GAUI amendment/hash model |
| 9 Memory Revocation | NOT_IMPLEMENTED | TTL/forgetting is not GAUI 7-state revocation |
| 10 Delegation Non-Amplification | NOT_IMPLEMENTED | must be tested at governed authority layer, not inferred here |
| 11 Cryptographic Agility | NOT_IMPLEMENTED | no GAUI 12-state crypto lifecycle/PQ migration |
| 12 Recovery vs Succession | PARTIAL | branch ancestry and lineage distinguish valid return from foreign/stale branch |
| 13 Adversarial Robustness | PARTIAL | forged identity, false continuity and compromise probes executable |
| 14 Human Agency | NOT_IMPLEMENTED | no executable mapping for GAUI 10-vector suite yet |
| 15 Anti-Capture | PARTIAL | operational refs cannot override identity mismatch; broader authority capture belongs at REHT boundary |

## Metric discipline

Do not compute a GAUI score from unsupported families. Metrics are emitted only when their denominator is composed of actual executable trials. `NOT_IMPLEMENTED` is never converted to pass.

FCR may be computed for explicitly labelled adversarial continuity-attestation trials as:

`false_continuity_acceptances / continuity_acceptance_trials`

The GAUI thresholds are external proposed engineering targets, not empirically validated constants and are not adopted as PersonalAI-OS policy.

## Current executable probes

`pytest tests/gaui -v`

The first slice covers identity continuity, lineage/provenance discontinuity, expected ancestry, false-continuity detection, compromised branch rejection, and a narrow anti-capture case.
