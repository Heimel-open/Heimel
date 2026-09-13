# SCALE-ADAPTATION-04 result

Canonical base: `e7b7581539f5ce93362173c89569113dec48c8e1`

Preregistration commit: `25924b2c35df3f1ccbef5024f47c0b96d7d982a8`

Outcome: `FALSIFIED_BY_DATA` for the conjunction-specific hypothesis.

Fresh seeds: `4004, 5005, 6006`.

Same five scales, same substrate, same 256 paired counterfactual episodes per scale/replicate, same update rule and frozen adaptation score.

Mean adaptation by condition:

```text
baseline       0.0395751
carryover_only 0.0352059
delta_only     0.3187252
joint          0.0757358
```

Paired gain versus baseline:

```text
carryover_only -0.0043692
delta_only     +0.2791501
joint          +0.0361607
```

The joint SCALE-ADAPTATION-03 effect replicated at all 5 scales, but the preregistered conjunction claim failed because `delta_only` exceeded the frozen single-component effect ceiling by a very large margin. Carryover alone did not help.

This means the previous statement "temporal continuity carries the adaptation effect" is not supported by this ablation.

## Critical diagnostic

The primary verdict remains frozen and is not retuned. However, causal attribution to delta alone is not yet safe.

`delta_only = evolve(after - before)` creates an extremely sparse state. Across the run, 79.365% of its evolved node values are exactly zero. The inherited scorer defines `sign(0) = +1`, while baseline, carryover-only and joint have no exact-zero mass.

Therefore the very large delta-only score may be materially inflated by a tie-handling artifact that is specific to this ablation condition.

Correct evidence boundary:

- conjunction-specific claim: falsified;
- carryover-only sufficiency: falsified;
- exact-delta signal is the only remaining candidate carrier;
- strong claim that delta alone causes the observed adaptation gain: not established until the score is repeated with preregistered tie-neutral handling.

Validation: 7/7 logical falsifier cases pass in local execution. CPU-only run; 5 scales × 3 paired replicates × 256 episodes × 4 conditions.
