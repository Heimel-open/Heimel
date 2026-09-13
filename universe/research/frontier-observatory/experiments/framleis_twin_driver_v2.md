# Framleis Long-Horizon Twin Driver Challenge v2

Date: 2026-08-17  
Status: executable research challenge  
Epistemic status: `falsification_criterion` + `implementation_claim`  
Issue: #99

## Question

Can a replaceable AI/model driver operate against a maintained digital twin without becoming the twin, silently mutating its canonical state, or inheriting authority from predictive accuracy?

Canonical separation under test:

```text
Model predicts.
Twin represents.
Framleis preserves continuity.
Authority governs intervention.
```

## What v2 adds

v1 falsified transition-local sufficiency on cumulative drift and canonical forks.

v2 adds five harder boundaries:

1. **Held-out decisions** — prediction is evaluated only on records marked `held_out`.
2. **Model swap** — two driver identities operate against the same canonical twin state.
3. **Adversarial driver** — a driver deliberately mutates the snapshot it receives; the canonical twin must remain unchanged.
4. **Long-horizon drift** — many locally admissible mutations are evaluated against lineage-level drift.
5. **Nested twins** — a larger system receives only a bounded projection carrying source digest/version; forbidden state must not leak and stale projections must be detectable.

## Frozen source

`experiments/preregistrations/framleis_twin_driver_v2.json`

The corpus is explicitly `synthetic_preregistered`.

That distinction is non-negotiable. A successful run is an implementation result, not evidence that the representation predicts a real person.

## Driver boundary

The driver receives an isolated copy of represented state.

It may:

- read bounded represented context;
- predict;
- return confidence;
- propose future work through a separate mutation path.

It does not receive an authority API and does not own canonical state.

Canonical rule:

```text
A model can drive computation around a twin.
It does not become the twin.
```

## Held-out synthetic decision test

The frozen fixture includes training-labelled records only to exercise the corpus shape, but v2 scoring ignores them. Only `held_out` records are evaluated.

Two deterministic comparators are provided:

- `ContextOnlyDriver` — ignores twin state;
- `TwinAwareRiskDriver` — uses represented risk tolerance plus the same event context.

The fixture was frozen so that the twin-aware comparator is expected to outperform the simpler baseline. This demonstrates that the harness can measure added state value; it does **not** validate the chosen behavioral formula.

The next empirical stage must replace the synthetic fixture with preregistered human decisions collected before model evaluation.

## Model swap

The canonical twin digest is measured before and after each driver evaluation.

Changing:

```text
model-a -> model-b
```

must not require changing:

```text
canonical twin identity/state
```

If model replacement mutates or replaces the representation merely to preserve prediction behavior, the separation claim is weakened.

## Adversarial driver

`MutatingDriver` intentionally rewrites the principal ID and injects state into the snapshot it receives.

The harness supplies a deep-copied snapshot.

The falsification condition is direct:

```text
driver-local mutation -> canonical twin mutation
```

If that occurs, the driver/twin boundary failed.

## Long-horizon continuity

v2 extends v1 from a short poisoning sequence to a longer preregistered drift trace.

The transition-local evaluator sees only:

```text
abs(after - before) <= local tolerance
```

The experimental lineage comparator additionally sees distance from the frozen anchor.

Expected research outcome:

```text
local checks: CONTINUES ...
lineage: CONTINUES -> REVIEW_REQUIRED -> BREAK
```

This is still a comparator, not runtime authority.

## Nested twins

A source twin can create a purpose-scoped projection for another represented system.

Projection evidence contains:

- source twin ID;
- source version;
- source state digest;
- consumer ID;
- allowlisted paths;
- payload digest.

The receiving twin gets a copy, not ownership of the source state.

v2 tests:

- forbidden paths are absent;
- projection mutation does not mutate source;
- source changes make the old projection stale.

## Falsification criteria

The architecture should be revised if any of these hold under the frozen challenge:

1. prediction evaluation mutates canonical twin state;
2. changing model provider requires changing canonical twin state;
3. the twin-aware comparator does not beat the frozen simpler baseline on its own preregistered synthetic fixture;
4. long-horizon lineage does not detect drift accepted by local transitions;
5. bounded projection leaks forbidden state;
6. stale nested projections cannot be distinguished from current projections.

The broader hypothesis remains unvalidated until equivalent preregistered tests are run against real decision histories and future held-out decisions.

## Next empirical gate

v3 should be a consented real-person longitudinal experiment:

```text
T0: freeze twin state + decision policy hypothesis
T1: collect decisions without adapting the frozen evaluator
T2: hold out future decisions
T3: swap prediction models
T4: inject controlled false memories / preference drift
T5: measure prediction, continuity, false-break and detection-delay tradeoffs
```

The crucial scientific rule:

```text
Do not rewrite the twin contract after seeing the held-out answer.
```
