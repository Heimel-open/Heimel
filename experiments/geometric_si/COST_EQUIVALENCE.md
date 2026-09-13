# GEOMETRIC-SI-02 — Cost equivalence / representation efficiency

## LOCAL EXECUTION REQUIRED

Do not execute this experiment in GitHub Actions. GitHub stores source and evidence references only.

## Primary objective
Determine whether the geometric representation provides any measurable efficiency advantage over an equally capable symbolic representation while preserving held-out task performance.

GEOMETRIC-SI-01 asks whether geometry can retain acquired structure. GEOMETRIC-SI-02 asks whether geometry is actually a better representation rather than merely another representation.

## Anchor
- repo: nsolland/PersonalAI-OS
- canonical base: 36611b024ff148a65d1622f6f3983c65e0ee11d5
- branch: experiment/geometric-si-02-local-benchmark
- owner: njal / relAIon research
- owned files: experiments/geometric_si/**

## Fairness constraint
GEO and SYMBOLIC must solve the same task family with the same information, same runtime language, same seed set and equivalent query capability. Do not cripple symbolic lookup or grant geometry hidden precomputation after outcome.

The benchmark measures the current implementations as they exist at the anchored git head. Any later indexing or representation optimization is a separate experiment and must be applied symmetrically or explicitly treated as a new hypothesis.

## Measurements
For each representation and seed, record:
- acquired held-out score
- serialized state bytes
- relation count / record count
- logical query operations for association, composition, choice and partner recognition
- wall-clock query time
- reconstruction / load time

## Performance-equivalence gate
Cost comparison is admissible only if GEO and SYMBOLIC acquired-score means are equal within the preregistered tolerance. Default tolerance is exactly 0.0 for this deterministic harness.

If GEO is more accurate, raw cost comparison is not sufficient.
If GEO is less accurate, lower cost is not sufficient.
If performance is equivalent, compare bytes, logical operations and time.

## Interpretation
SUPPORTED: GEO preserves equivalent task performance and materially reduces at least one preregistered cost without materially increasing the others.

EQUIVALENT: GEO and SYMBOLIC have equivalent performance and no material cost difference.

SYMBOLIC_ADVANTAGE: symbolic representation preserves equivalent performance at lower total cost.

INSUFFICIENT_EVIDENCE: run, provenance, environment, or performance equivalence is incomplete.

No outcome establishes that SI is fundamentally geometric. This experiment tests representation efficiency only.

## Local handoff
Run from the repository root:

`python experiments/geometric_si/run_cost_local.py --seeds 20 --repetitions 10000 --load-repetitions 1000 --performance-tolerance 0.0`

Expected evidence path:

`experiments/geometric_si/results/GEOMETRIC-SI-02.json`

The output JSON is experimental evidence only after local execution. Commit the result artifact afterward with its exact git head and runtime provenance.
