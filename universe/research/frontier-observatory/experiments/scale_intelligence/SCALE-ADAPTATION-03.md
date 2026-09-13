# SCALE-ADAPTATION-03 — single-enabler counterfactual adaptation test

Status: preregistered confirmatory toy-substrate test.

Canonical base: `e8279cb046ddcac4d39949e3401b9940279f3103`.

Primary question:

> Holding the SCALE-INTELLIGENCE-01/02 substrate and scale sweep fixed, does one temporal adaptation enabler causally increase counterfactual adaptation relative to the frozen independent-recompute baseline?

This does not reopen the broad intelligence-like phenotype falsified by SCALE-INTELLIGENCE-01.

## One manipulated enabler

Baseline second phase:

```text
after_final = evolve(after_raw, scale)
```

Enabled second phase:

```text
carryover_initial[i] = before_final[i] + (after_raw[i] - before_raw[i])
after_final = evolve(carryover_initial, scale)
```

Interpretation: retain the prior evolved scalar state and inject only the exact observed local input delta.

No additional state channel, node, edge, fanout, round, model, task hint, global summary or task-specific rule is added. The same `evolve()` rule and same number of rounds are used.

## Frozen sweep

```text
scales = 1, 2, 4, 8, 16
confirmatory seeds = 1001, 2002, 3003
episodes per scale/replicate = 256
```

The non-enabler invariants remain the canonical hashes imported from `scale_sweep.py`:

```text
node_set
topology
initial_state
taskset
compute_budget
update_rule
```

The enabler is represented as the experimental condition, not silently folded into those invariant hashes.

## Frozen gates

The result is `NOT_FALSIFIED_BY_DATA` only if all of the following hold:

```text
baseline mean counterfactual adaptation <= 0.10
mean paired carryover gain >= 0.02
positive gain at >= 4 of 5 tested scales
>= 3 paired replicates per condition and scale
all non-enabler invariants identical
```

Otherwise the result is `FALSIFIED_BY_DATA`, except incomplete/confounded data which is `INSUFFICIENT_EVIDENCE`.

The 0.02 gain gate is intentionally modest: the test asks whether temporal carryover is a causal enabler at all, not whether it solves adaptation. Absolute enabled performance and any scale interaction are reported but are not rescue gates.

## Claim boundary

A positive result supports only this bounded claim on this toy substrate:

```text
temporal state carryover + exact observed input delta
causally improves the tested counterfactual adaptation metric
relative to independent recomputation
```

It does not establish general intelligence, consciousness, biological equivalence, or a universal theory of adaptation.

A positive result also does not imply that interaction scale causes adaptation. Scale sensitivity of the enabled condition is diagnostic and must be tested separately if material.

## Run

```bash
cd experiments/scale_intelligence
pytest -q test_scale_adaptation_falsifier.py
python scale_adaptation_run.py --output evidence/scale-adaptation-03-result.json
```
