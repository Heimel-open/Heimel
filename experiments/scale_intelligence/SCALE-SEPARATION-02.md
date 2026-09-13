# SCALE-SEPARATION-02

Status: preregistered replication before outcome.

## Primary question

Does interaction scale materially modulate integration/transfer capability while counterfactual adaptation remains insensitive and low on the same fixed substrate?

This is narrower than SCALE-INTELLIGENCE-01. The earlier broad intelligence-like phenotype was falsified because counterfactual adaptation stayed near zero. The present test does not rescue that claim. It tests whether the observed separation replicates under fresh seeds.

## Frozen substrate

Reuse the SCALE-INTELLIGENCE-01 ring substrate unchanged:

- 63 nodes;
- distance-labelled ring latent topology;
- 3 message-passing rounds;
- fixed fanout 4;
- one scalar state channel;
- same segmented, transfer and counterfactual task generators;
- 256 episodes per family;
- same noise and block parameters;
- same scales: 1, 2, 4, 8, 16.

Only the interaction scale varies within a replicate.

## Fresh replication seeds

```text
404, 505, 606
```

These seeds were frozen before the replication outcome was generated.

## Metrics

Integration/transfer family:

```text
task_success
cross_context_transfer
distributed_integration
```

Adaptation:

```text
counterfactual_adaptation
```

## Frozen gates

The narrower separation hypothesis survives only if all are true:

1. each of the three integration/transfer metrics has a scale-wise mean spread >= 0.08;
2. at least two of the three metrics share the same best-performing scale;
3. counterfactual adaptation scale-wise mean spread <= 0.03;
4. counterfactual adaptation mean across scales <= 0.10;
5. all non-scale invariant digests remain identical;
6. all five scales have at least three replicates.

Outcomes:

```text
NOT_FALSIFIED_BY_DATA
FALSIFIED_BY_DATA
INSUFFICIENT_EVIDENCE
```

Thresholds are replication gates informed by SCALE-INTELLIGENCE-01 discovery. They are not universal constants.

## Claim boundary

A positive result would support only this bounded statement on the toy substrate:

> Integration/transfer capability is materially scale-sensitive, while the tested counterfactual adaptation mechanism is not rescued by scale alone.

It would not establish that intelligence is universally scale-dependent, nor prove that adaptation requires a specific missing mechanism.

The next causal test, only if this replication survives, should intervene on a candidate adaptation-enabling mechanism while preserving the scale sweep.
