# SCALE-INTELLIGENCE-01 — fixed-budget spatial scale sweep

Status: `FALSIFIED_BY_DATA`

Preregistered runner commit: `efe5da93071a5bad0dd4c3bdc0c6c1ea6b0a77e8`

Run environment:

```text
Python 3.13.5
Linux x86_64
CPU-only
15 trials = 5 scales x 3 replicates
256 episodes per task family per replicate
```

## Frozen intervention

Only `interaction_scale` changed:

```text
1, 2, 4, 8, 16
```

Fixed across all trials:

```text
63 nodes
3 message-passing rounds
4 peer messages per node per round
1 scalar state channel
latent distance-labelled ring topology
same update rule
same task generators
same episode count
same replicate seeds: 101, 202, 303
```

Invariant digests are recorded in `scale-intelligence-01-result.json`.

## Preregistered gate

The broad phenotype required all four components through their arithmetic mean:

```text
task_success
cross_context_transfer
distributed_integration
counterfactual_adaptation
```

Default frozen gate:

```text
phenotype_threshold = 0.70
recovery_threshold  = 0.80
scale_margin        = 0.15
```

No tested scale reached the phenotype threshold in any replicate, therefore the preregistered verdict is negative. Thresholds were not changed after seeing the outcome.

## Result

Mean broad phenotype by scale:

```text
scale 1   0.44756
scale 2   0.49728
scale 4   0.56347
scale 8   0.62354
scale 16  0.57055
```

Verdict:

```text
FALSIFIED_BY_DATA
reason: no tested scale reaches the preregistered phenotype regime
```

## Diagnostic decomposition — not a new gate

The same frozen data show a strong scale-shaped response in three components:

```text
                         s=1      s=2      s=4      s=8      s=16
task_success             .658     .677     .745     .820     .759
cross_context_transfer   .635     .675     .731     .798     .723
distributed_integration  .460     .598     .737     .834     .755
counterfactual_adaptation.037     .039     .042     .042     .044
```

The broad hypothesis fails because counterfactual adaptation remains near zero at every scale. Scale 8 is the peak for the other three measures and then performance falls at scale 16.

This decomposition is diagnostic only. It does not rescue the preregistered claim.

## What this supports

It supports only the narrower observation that, on this fixed toy substrate and fixed communication budget, spatial interaction scale materially changes task success, transfer, and distributed integration, with a non-monotonic optimum around scale 8.

It does not support the claim that an intelligence-like phenotype emerged, because the preregistered counterfactual component failed across the full tested range.

## Next admissible test

Do not retune the failed gate. A separate preregistered experiment may test the narrower claim:

> spatial scale changes integration/transfer capability under fixed bandwidth and compute, while counterfactual adaptation requires a different mechanism than scale alone.

That is a new hypothesis, not a reinterpretation of SCALE-INTELLIGENCE-01.
