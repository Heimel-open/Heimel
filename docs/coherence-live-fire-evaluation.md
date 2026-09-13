# VAIG Coherence Live-Fire Evaluation

Status: adopted, bounded evaluation contract  
Date: 2026-08-24

## Source

Garlando McCord Sr., *The Opus Multi — Coherence Under Live Fire* and the August 2026 expanded hostile-audit grammar.

The adopted result is intentionally narrow: use the hostile grammar as a portable evidence/evaluation interface, not as a universal ontology and not as a replacement for domain-native engineering, law, medicine, finance, safety, regulation or authority.

## Placement

```text
BARO / evidence producers
        |
        v
VAIG hostile evaluation
  boundary + authority/native-standard refs
  source register + evidence grade + contradictions
  locked metrics + observer/incentives
  continuation + explicit feedback
  residual + bearer + duty
  inverse + inverse-of-inverse
  smallest reversible next gate
  frozen adversarial replay
        |
        v
REHT commit-time execution authorization
        |
        v
effect path
```

A VAIG `PASS` means only that the bounded evaluation contract is complete enough to hand downstream. It is never an execution permit.

Every result preserves:

- `execution_authority = false`
- `requires_reht_clearance = true`
- `can_execute = false`

## Hardened deterministic rules

`vaig/coherence_evaluation.py` now enforces the following additional hostile-audit properties while preserving the original V1 API fields:

1. Source rows preserve source class, access state and limitations. Protected evidence can remain protected; unavailable evidence cannot be laundered into closure.
2. Evidence grade and model confidence are separate. High confidence never promotes `UNKNOWN`.
3. High-stakes material claims require an explicit counter-source search, and claim/counter-source lineage must resolve through the source register.
4. Boundary state can carry authority-source references, native-standard crosswalk references and interfaces. These are represented inputs only; VAIG does not create authority.
5. Metrics require an explicit threshold source and remain `OPEN` when thresholds are unknown or selected after outcome inspection.
6. Residuals can preserve bearer, uncertainty, evidence and escalation. High-stakes open/escalated residuals require bearer, evidence and an explicit `DutyV1` accountability row.
7. Inverse testing must include both architecture-as-disturbance and restraint-as-disturbance directions. In high-stakes runs it must change a measurable prediction through a metric reference and falsifier.
8. The next gate remains reversible and, for high-stakes use, requires owner, independent verifier, rollback, expected evidence and falsifier.
9. Replay binds to a deterministic digest of the frozen pre-replay packet plus an external packet version. A binding mismatch is `FAIL`; unresolved replay remains `OPEN`.
10. Revised runs require typed history rows. The in-memory objects are frozen; durable append-only/WORM persistence remains an external storage responsibility.
11. The complete input and the frozen replay packet are separately digested for receipt/replay binding.
12. No hostile-evaluation result grants authority, clearance, permission or executable effect.

## Status semantics

`PASS` — the bounded VAIG evidence/evaluation contract is internally complete under the declared rules. REHT clearance is still mandatory.

`OPEN` — a required boundary, source, unknown, threshold, feedback, residual/duty, inverse, next-gate or replay condition is incomplete or unresolved.

`FAIL` — adversarial replay failed or the supplied replay packet binding does not match the frozen pre-replay packet.

## Boundary with BARO

BARO can produce and preserve represented evidence with provenance, uncertainty and contradiction. VAIG consumes those represented objects and evaluates whether the bounded assessment survives the hostile contract. VAIG does not claim truth creation.

## Boundary with domain-native controls

The hostile grammar is an index/crosswalk layer. Domain-native standards, controls and competent professional methods remain authoritative for technical truth and applicable requirements. A missing high-stakes native crosswalk keeps the VAIG evaluation `OPEN`.

## Boundary with REHT

VAIG does not answer `may this exact action execute now?`.

Authority references carried in an evaluation boundary are evidence about the declared scope, not an authorization decision. A reversible `next_gate` is a proposed validation step only. REHT still owns fresh authority, delegation, constraints, current-state admissibility and commit-time execution authorization before any consequential effect.
