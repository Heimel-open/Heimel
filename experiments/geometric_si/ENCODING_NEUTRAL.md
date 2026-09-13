# GEOMETRIC-SI-04 — Encoding-neutral representation control

## LOCAL EXECUTION REQUIRED

Do not execute this experiment in GitHub Actions. GitHub stores source, review and evidence references only. Scientific execution is local and the run must be registered in `nsolland/Index/ops/RUN_LEDGER.json` before execution.

## Objective

Test whether the GEOMETRIC-SI-03 advantage survives after removing serialization-layout differences.

SI-03 gave GEO and SYMBOLIC the same semantic normalization and the same adjacency-indexing opportunity, but the two conditions still used different serialized layouts. SI-04 therefore feeds both conditions the exact same packed binary source representation and compares the cost of constructing, querying and mutating two different in-memory organizations.

## Experimental conditions

Both conditions ingest byte-identical canonical packed facts:

`(source_id, kind_id, target_id, weight, provenance_count)`

The shared symbol table and fact payload are encoded once and passed unchanged to both conditions. `source_encoding_bytes` must therefore be identical by construction and is an invariant, not an outcome metric.

Two in-memory organizations are compared:

1. `PACKED_GEO`
   - key-addressed edge map keyed by `(source, kind, target)`;
   - adjacency keyed by `(source, kind)`;
   - weighted updates mutate the edge relation directly.

2. `PACKED_SYMBOLIC`
   - normalized columnar fact table;
   - primary-key index keyed by `(source, kind, target)`;
   - adjacency index keyed by `(source, kind)` and row identity;
   - weighted updates mutate the corresponding row through the primary-key index.

Both receive the same indexing opportunity. No post-outcome optimization is allowed.

## Scaling

Preregistered normalized relation counts:

- 32
- 128
- 512
- 2048

Default: 20 deterministic seeds per scale.

For each seed/scale, generate the same task-bearing relations as SI-03 plus deterministic distractors. Normalize once, map symbols to integer IDs once, encode once, then construct both representations from the same bytes.

## Mutation stream

After the initial performance check, apply the same deterministic mutation stream to cloned instances of both representations.

Each mutation either:

- increments an existing relation weight; or
- inserts a new relation using IDs already present in the shared symbol table.

Default mutation count per seed/scale: `max(32, scale // 4)`.

The post-mutation semantic digest must match between conditions. Any digest mismatch makes that run invalid.

## Performance-equivalence gate

Before cost interpretation:

- pre-mutation acquired score must be equal within tolerance;
- post-mutation semantic digest must be identical;
- source packed bytes must be identical.

Default performance tolerance: `0.0`.

## Measurements

Per representation and scale:

- acquired score;
- source encoding bytes (equality invariant);
- build/index time from the same packed bytes;
- logical query operations;
- wall-clock query time for the fixed four-task bundle;
- mutation time per operation;
- traced Python allocation peak during build (`tracemalloc`), treated as runtime-specific evidence only;
- post-mutation semantic digest equality.

## Interpretation

`ORGANIZATION_ADVANTAGE_GEO` requires equal task performance, identical packed source bytes and identical post-mutation semantics, with a reproducible material advantage for GEO in build, mutation and/or runtime memory that is not offset by a material query disadvantage.

`ORGANIZATION_ADVANTAGE_SYMBOLIC` is the symmetric outcome.

`EQUIVALENT` means no material organization-specific difference survives the encoding-neutral control.

`MIXED` means dimensions disagree without a defensible overall winner.

`INSUFFICIENT_EVIDENCE` applies if packed-byte equality, performance equivalence, semantic digest equality, runtime provenance or scale coverage is incomplete.

No outcome establishes that SI is fundamentally geometric. SI-04 only tests whether the observed efficiency survives a shared physical encoding.

## Local handoff

From repository root:

```bash
python experiments/geometric_si/run_encoding_neutral_local.py \
  --seeds 20 \
  --scales 32 128 512 2048 \
  --repetitions 5000 \
  --build-repetitions 250 \
  --performance-tolerance 0.0
```

Expected evidence artifact:

`experiments/geometric_si/results/GEOMETRIC-SI-04.json`

The artifact is evidence only. Canonical run state is owned by `nsolland/Index/ops/RUN_LEDGER.json`.
