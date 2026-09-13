# SCALE-COMPRESSION-07 — Task-sufficient compression test

Status before execution: PREREGISTERED.

## Question

Does the previously replicated scale-8 capability peak correspond to a regime that suppresses task-irrelevant local arrangement while retaining enough information for the correct global decision?

This is a new explanation test. SCALE-ORDER-05 and SCALE-RELEVANCE-06 remain negative results and are not reinterpreted as support.

## Frozen substrate

Reuse `scale_sweep.py` unchanged:

- 63-node distance-labelled ring;
- scales `1, 2, 4, 8, 16`;
- 3 synchronous rounds;
- fanout 4;
- one scalar state channel;
- same update rule and segmented task generator;
- 256 probe episodes per scale/replicate;
- same invariant digests for node set, topology, initial-state encoding, taskset, compute budget and update rule.

Fresh seeds: `17017, 18018, 19019, 20020, 21021`.

The candidate scale is frozen at `8` from prior independent evidence. It is not selected after this run.

## New nuisance intervention

For every segmented input, construct a paired nuisance twin by randomly permuting the complete vector of node values.

The permutation preserves exactly:

- the multiset of local evidence values;
- the global sum;
- the correct majority target;
- the number of positive and negative values;
- node count, topology, update rule and compute budget.

It changes only where local evidence is located on the ring. For this global-majority task, that spatial arrangement is nuisance information.

Both members of the pair are evolved independently under the same interaction scale.

## Frozen measurements

### Target decodability

Mean node-level majority accuracy across the original input and its nuisance twin.

This asks whether individual final node states still carry the correct global decision.

### Nuisance compression

Let `D0` be the mean absolute node-wise distance between the original and nuisance-twin inputs. Let `D1` be the same distance after evolution.

`nuisance_compression = clip(1 - D1 / D0, 0, 1)`.

Higher values mean that local rearrangement differences are removed by the relational dynamics.

### Sufficient compression

Harmonic mean of target decodability and nuisance compression.

This score is deliberately high only when the system both preserves the decision and suppresses task-irrelevant arrangement.

## Preregistered gates

SCALE-COMPRESSION-07 survives only if all gates hold:

1. scale-8 sufficient-compression mean exceeds scale 1 by at least `0.05`;
2. scale-8 sufficient-compression mean exceeds scale 16 by at least `0.03`;
3. scale-8 target decodability exceeds scale 1 by at least `0.05`;
4. scale-8 target decodability exceeds scale 16 by at least `0.03`;
5. scale-8 nuisance compression exceeds scale 1 by at least `0.10`;
6. scale 8 beats both scales 1 and 16 on sufficient compression in at least `4/5` paired fresh replicates;
7. five valid replicates exist at every scale and all non-scale invariant digests are identical.

Any invariant failure or insufficient replication yields `INSUFFICIENT_EVIDENCE`.

No metric or threshold may be changed after execution.

## Interpretation boundary

`NOT_FALSIFIED_BY_DATA` would support only the bounded statement that, on this fixed toy global-majority task, the known scale-8 regime achieves a better joint tradeoff between decision retention and removal of spatial nuisance information than the tested low- and high-scale extremes.

It would not establish a universal compression principle, intelligence, understanding, consciousness, or an information-bottleneck theorem.

`FALSIFIED_BY_DATA` means this task-sufficient-compression explanation fails under the frozen intervention, metrics and gates.
