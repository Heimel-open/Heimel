# SCALE-ADAPTATION-04 — carryover × delta ablation

Status: preregistered before outcome.

Canonical base: `e7b7581539f5ce93362173c89569113dec48c8e1`

Primary question:

> In the SCALE-ADAPTATION-03 gain, is temporal carryover alone sufficient, is exact input delta alone sufficient, or does the gain require their conjunction?

## Frozen substrate

Reuse the exact SCALE-ADAPTATION-03 toy substrate and counterfactual generator:

- 63-node distance-labelled ring;
- scales `1, 2, 4, 8, 16`;
- 3 message-passing rounds;
- fanout 4;
- 256 paired counterfactual episodes per scale/replicate;
- same adaptation score;
- all SCALE-ADAPTATION-03 non-enabler invariants unchanged.

Fresh confirmatory replicate seeds:

```text
4004, 5005, 6006
```

## Four frozen conditions

For each identical `(before, after)` pair, first compute:

```text
before_final = evolve(before, scale)
delta        = after - before
```

Then evaluate exactly four conditions:

```text
baseline       = evolve(after, scale)
carryover_only = evolve(before_final, scale)
delta_only     = evolve(delta, scale)
joint          = evolve(before_final + delta, scale)
```

Interpretation:

- `baseline`: frozen independent recomputation control;
- `carryover_only`: retained processed state without receiving the observed change;
- `delta_only`: observed change signal without retained prior processed state;
- `joint`: SCALE-ADAPTATION-03 enabler.

No condition may add channels, nodes, edges, fanout, rounds, model calls, task hints, global summaries, or altered scoring.

## Frozen gates

Harness status is `NOT_FALSIFIED_BY_DATA` for the conjunction-specific hypothesis only if all are true:

```text
baseline_mean <= 0.10
joint_gain_vs_baseline >= 0.02
carryover_only_gain_vs_baseline <= 0.01
delta_only_gain_vs_baseline <= 0.01
joint_excess_over_best_single >= 0.02
joint_positive_gain_scales >= 4 of 5
paired_replicates_per_scale >= 3
all non-enabler invariants identical
```

Where gain is the paired mean adaptation-score difference against baseline.

If either single-component condition gains more than `0.01`, the conjunction-specific claim is falsified and the component is reported as independently sufficient at the preregistered effect floor.

If the joint condition fails to gain at least `0.02`, SCALE-ADAPTATION-03 does not replicate under fresh seeds and the claim is falsified.

Confounded or under-replicated data return `INSUFFICIENT_EVIDENCE`.

## Claim boundary

This experiment identifies which part of one toy adaptation mechanism carries the measured effect. It does not establish a general theory of adaptation, intelligence, memory, temporal cognition, or consciousness.
