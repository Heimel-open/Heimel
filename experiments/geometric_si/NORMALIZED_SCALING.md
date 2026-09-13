# GEOMETRIC-SI-03 — Normalized/indexed scaling control

## LOCAL EXECUTION REQUIRED

Do not execute this experiment in GitHub Actions. GitHub stores source, review and evidence references only. Scientific execution is local.

## Objective

Test whether the GEOMETRIC-SI-02 cost differences survive when geometric and symbolic representations are given the same semantic normalization and the same query indexing opportunity, then scale relation-set size under equal task performance.

This experiment is specifically designed to separate a representational effect from an implementation/data-structure effect.

## Prior-result boundary

GEOMETRIC-SI-02 established equal task performance in the tested harness while GEO used fewer serialized bytes and loaded faster, but SYMBOLIC used fewer logical query operations and queried faster. GEO also aggregated repeated relations while SYMBOLIC retained duplicate records. Therefore SI-02 cannot attribute the byte/load difference to geometry itself.

GEOMETRIC-SI-03 must not interpret duplicate-record compression or one-sided indexing as evidence for geometry.

## Experimental conditions

Two representations are compared:

1. `NORMALIZED_GEO`
2. `NORMALIZED_SYMBOLIC`

Both conditions receive the same generated relation events and must:

- aggregate duplicate `(source, kind, target)` relations by summed weight;
- retain equivalent provenance information at the semantic level used by the experiment;
- build an adjacency index from the normalized relation set before timed queries;
- expose equivalent `strongest_target` and bounded `reachable` operations;
- serialize the same normalized semantic facts, differing only in representation layout;
- use the same Python runtime, task generator, seed set and timing harness.

No representation may receive a post-outcome optimization unavailable to the other.

## Scaling

Preregistered normalized relation counts:

- 32
- 128
- 512
- 2048

Default seed set: 20 deterministic seeds per scale.

For each scale, the generator creates:

- a deterministic path chain used for held-out reachability;
- deterministic association relations;
- weighted choice relations with repeated observations that are normalized before comparison;
- partner-pattern relations;
- deterministic distractor relations sufficient to reach the target normalized relation count.

The task answers are generated before representation construction and are identical across conditions.

## Performance-equivalence gate

Cost comparison at a scale is admissible only if both representations obtain identical acquired score within tolerance.

Default tolerance: `0.0`.

If performance equivalence fails at a scale, cost results from that scale are reported but scientifically marked inadmissible.

## Measurements

Per representation and scale:

- acquired task score;
- normalized relation count;
- serialized state bytes;
- index-build/load time;
- logical query operations under the indexed implementation;
- wall-clock query time for the fixed task bundle.

Report means across seeds plus GEO/SYMBOLIC ratios.

## Interpretation

`GEOMETRIC_ADVANTAGE` requires equivalent performance and a reproducible material cost reduction that persists after normalization and symmetric indexing, especially as scale increases.

`SYMBOLIC_ADVANTAGE` requires equivalent performance and lower total cost for the symbolic condition across the relevant scaled comparisons.

`EQUIVALENT` means no material representation-specific cost difference survives the controls.

`MIXED` means different cost dimensions favor different representations without a defensible total-cost winner.

`INSUFFICIENT_EVIDENCE` applies if provenance, execution environment, performance equivalence, normalization, symmetric indexing or scale coverage is incomplete.

No result establishes that SI is fundamentally geometric. This experiment tests representational efficiency only.

## Local handoff

From repository root:

```bash
python experiments/geometric_si/run_normalized_scaling_local.py \
  --seeds 20 \
  --scales 32 128 512 2048 \
  --repetitions 5000 \
  --load-repetitions 500 \
  --performance-tolerance 0.0
```

Expected evidence artifact:

`experiments/geometric_si/results/GEOMETRIC-SI-03.json`

The artifact is evidence only. The canonical run state is owned by `nsolland/Index/ops/RUN_LEDGER.json`.
