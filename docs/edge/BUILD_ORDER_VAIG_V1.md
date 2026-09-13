# Build Order: Local VAIG Edge Profile V1

Status: READY FOR REVIEW
Repository: `nsolland/valo-edge`
Canonical base: `7764f9b20d289b4c5846ee81ae7c665e9c5d7248`
Branch: `feat/edge-vaig-v1`
PR: `#10`

## Boundary

Local VAIG evaluates and packages evidence. It has no execution authority and cannot emit ALLOW, DENY, DEFER, STEP_UP or HALT.

micro-REHT consumes the resulting evidence in the next delivery.

## Delivered

- deterministic `LocalVaigEdge` evaluator
- canonical `EdgeEvidenceV1` output bound to the proposal digest
- device and hardware attestation checks
- firmware, runtime and model hash comparison
- sensor-source provenance and deterministic aggregate commitment
- evidence freshness and future-clock detection
- physical-state commitment, required-key and expected-state checks
- model confidence and uncertainty capture
- explicit model-free path
- explicit missing, stale, contradictory and untrusted evidence gaps
- deterministic evidence IDs and digests independent of sensor input order

## Acceptance gates

- a model-backed proposal requires matching model evidence
- a model-free proposal can be complete without model evidence
- required device, sensor and physical evidence cannot disappear silently
- conflicting device, model, firmware, runtime, sensor or physical-state claims remain visible
- stale or future-dated evidence is surfaced
- VAIG output has no decision field
- sensor ordering does not change the evidence digest
- focused tests pass before CI
