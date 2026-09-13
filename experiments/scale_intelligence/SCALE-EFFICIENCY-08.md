# SCALE-EFFICIENCY-08 — Continuous information-efficiency optimum

Status before execution: PREREGISTERED.

## Question

Does the fixed ring substrate exhibit a continuous interior optimum in information efficiency, and does that optimum align with the independent task-capability optimum?

This follows SCALE-COMPRESSION-07, which produced its highest observed target-decoding, nuisance-compression and joint score at scale 8 but missed one preregistered pairwise margin by 0.0013666. This protocol does not change that result or its gates. Instead it tests the whole response curve with a new, frozen model.

## Frozen substrate

Reuse the existing scale-sweep substrate unchanged:

- 63 nodes on the same distance-labelled ring;
- interaction scales `1, 2, 4, 8, 16`;
- 3 synchronous rounds;
- fanout 4;
- one scalar state channel;
- same update rule;
- same segmented/transfer/counterfactual task generators;
- 256 episodes per family;
- same invariant digests.

Fresh replicate seeds: `22022, 23023, 24024, 25025, 26026`.

Only `interaction_scale` varies within a replicate.

## Frozen measurements

### Information efficiency

Reuse the SCALE-COMPRESSION-07 nuisance probe unchanged.

For each segmented episode, create a nuisance twin by randomly permuting the complete node-value multiset. This preserves global sum, majority target and evidence counts while changing spatial arrangement.

- `target_decodability`: mean node-level majority-target accuracy across original and nuisance twin.
- `nuisance_compression`: `1 - final paired L1 distance / initial paired L1 distance`, clipped to `[0,1]`.
- `information_efficiency`: harmonic mean of target decodability and nuisance compression.

### Independent capability

`capability = 0.5 * (task_success + cross_context_transfer)` from the frozen scale-sweep runner using the same scale and seed.

The information-efficiency terms are not included in capability.

## Continuous response model

Let `x = log2(interaction_scale)`, giving `x = 0,1,2,3,4`.

Fit ordinary least-squares quadratics to the five scale-wise aggregate means:

`E(x) = a_E x^2 + b_E x + c_E`

`C(x) = a_C x^2 + b_C x + c_C`

When `a < 0`, define the continuous vertex `x* = -b/(2a)` and corresponding scale `2^x*`.

No polynomial degree, score definition or fitting rule may change after execution.

## Preregistered gates

SCALE-EFFICIENCY-08 is `NOT_FALSIFIED_BY_DATA` only if all hold:

1. the information-efficiency quadratic is concave: `a_E < 0`;
2. the capability quadratic is concave: `a_C < 0`;
3. both fitted vertices lie strictly inside the tested interval: `0 < x*_E < 4` and `0 < x*_C < 4`;
4. the two continuous vertices differ by at most `0.75` log2-scale units;
5. Spearman rank correlation between the five aggregate information-efficiency means and five aggregate capability means is at least `0.80`;
6. the observed information-efficiency winner is an interior scale (`2`, `4`, or `8`) in at least `4/5` fresh replicates;
7. all five scales have exactly five valid fresh replicates and all non-scale invariants are identical.

No pairwise fixed performance margin against scale 16 is used in this protocol.

Invalid/missing data or invariant drift yields `INSUFFICIENT_EVIDENCE`. Any other gate failure yields `FALSIFIED_BY_DATA`.

## Interpretation boundary

A surviving result would support only this bounded claim:

> On this fixed toy substrate and tested scale range, information efficiency and independent task capability are both consistent with nearby interior optima rather than monotonic improvement with interaction scale.

It would not prove an information bottleneck law, a universal optimum for intelligence, or that the quadratic model is mechanistically correct. The quadratic is a preregistered continuous surrogate over five tested scales.

Record the complete result without retuning.