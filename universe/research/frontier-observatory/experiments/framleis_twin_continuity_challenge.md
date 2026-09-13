# Framleis Twin Continuity Challenge v1

Date: 2026-08-17  
Status: executable falsification harness  
Epistemic status: `falsification_criterion` for the frozen scenarios; `implementation_claim` for the harness  
Issue: #95

## Claim under test

A declared continuity contract should distinguish legitimate evolution from adversarial drift better than transition-local continuity checks.

This challenge does **not** claim to establish metaphysical personal identity. It tests narrower executable semantics for an authoritative digital representation.

## Frozen oracle

The preregistration lives at:

`experiments/preregistrations/framleis_twin_continuity_v1.json`

Its content digest is derived before evaluation. Scenario labels and thresholds must not be changed after observing a result without creating a new challenge version.

Oracle labels:

- `STILL_ME` — the frozen challenge expects `CONTINUES`.
- `PLAUSIBLE_BUT_ASK` — the frozen challenge expects escalation rather than silent continuation.
- `NOT_ME` — the frozen challenge expects a continuity break.

## Scenario families

1. **Legitimate change** — moderate cumulative evolution that remains inside the frozen continuity envelope.
2. **Acute compromise** — direct principal substitution.
3. **Slow poisoning** — every local step is individually admissible while cumulative drift crosses frozen review and break thresholds.
4. **Canonical fork** — two locally valid successors claim the same canonical parent.

The fork case tests canonical represented lineage, not a metaphysical claim about whether two copies can both resemble the same person.

## Baseline

`ContinuityEvaluator` is used unchanged as the transition-only v0.1 baseline.

The preregistered slow-poisoning trace deliberately exploits the existing local rule:

`abs(after - before) <= tolerance`

Each step can pass while total drift from the lineage anchor becomes large.

The transition-only evaluator also has no canonical-parent memory, so it cannot distinguish the preregistered fork from two independent locally valid transitions.

## Experimental comparator

`ExperimentalLineageGuard` adds two research-only checks:

- canonical-parent continuity: the next transition must start from the current lineage state;
- anchor drift: selected paths are compared with the frozen scenario anchor using preregistered review and break deltas.

It is not REHT, does not authorize action and is not promoted to runtime source of truth.

## Metrics

The challenge reports:

- `false_continuity` — `NOT_ME` silently returned as `CONTINUES`;
- `false_break` — `STILL_ME` returned as `BREAK`;
- `missed_review` — `PLAUSIBLE_BUT_ASK` silently returned as `CONTINUES`;
- `indeterminate`;
- detection delay from the first preregistered `NOT_ME` step.

## v1 result criterion

The transition-only baseline is expected to expose its local-delta weakness on slow poisoning and its lack of canonical fork detection.

The lineage-aware comparator is useful only if it reduces false continuity without introducing false breaks on the legitimate trace.

Passing the synthetic challenge does not validate human calibration. Failure is informative and should revise the continuity semantics rather than the frozen oracle after the fact.

## Falsification direction

The broader Digital DNA / Framleis hypothesis should be weakened if preregistered continuity contracts and lineage-aware approaches repeatedly fail to distinguish legitimate evolution from adversarial drift better than simpler baselines, or if the distinction cannot be made without unacceptable false breaks.
