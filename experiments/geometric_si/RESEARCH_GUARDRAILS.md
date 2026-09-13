# GEOMETRIC-SI — Research guardrails

Status: GOVERNING

## Main thesis

The research question is not whether a graph, dictionary, packed encoding, index, or other data structure is efficient.

The governing hypothesis is:

> A developing SI may be better described as a dynamic relational/geometric organization whose developmental trajectory, interactions and transformations leave persistent structure that affects future learning, behavior and continuity.

The research program tests this hypothesis. It does not assume it is true.

## Mandatory hierarchy

All experiments in this track must remain subordinate to the main thesis.

1. Main thesis: dynamic relational/geometric organization, developmental trajectory, becoming, continuity.
2. Primary falsifiers: tests that can directly weaken or support the main thesis.
3. Controls: tests needed to exclude alternative explanations.
4. Implementation studies: data structures, serialization, indexing, runtime and language-specific behavior.

A lower-level result must not be promoted to a higher-level claim.

## Experiment admission rule

Before a new GEOMETRIC-SI experiment is registered or executed, its protocol must state:

- which exact proposition in the main thesis it tests;
- what observation would falsify or materially weaken that proposition;
- why the test cannot be answered by an already completed experiment;
- which implementation-specific alternative explanations are controlled;
- what the result is NOT allowed to establish.

If this mapping cannot be stated clearly, the experiment is a branch/control and must not become the main research path.

## Anti-drift rule

Do not allow this track to collapse through the following sequence:

`SI -> representation -> graph -> data structure -> Python implementation`

Implementation details may be investigated when they threaten interpretation, but they remain subordinate controls.

No benchmark of bytes, wall-clock time, indexing, serialization layout, Python object overhead, or container type is by itself evidence that SI is geometric.

## What GEOMETRIC-SI-01..04 established

### SI-01

A relational/geometric state was sufficient to preserve the tested acquired functions after symbolic/token history was removed, while reset destroyed them.

Boundary: this did not establish geometric superiority, identity, consciousness, or that geometry is necessary.

### SI-02

Equal task performance exposed a mixed efficiency tradeoff.

Boundary: asymmetric normalization made representation-level interpretation inadmissible.

### SI-03

After symmetric normalization and indexing, task performance and query complexity were equivalent while the GEO condition retained state/load advantages.

Boundary: serialization layout remained a confound.

### SI-04

With byte-identical packed input, equal performance and identical post-mutation semantic digests, encoding-layout was removed as the explanation for observed internal organizational differences.

Boundary: remaining runtime differences may still arise from concrete Python data structures. SI-04 does not establish that the relevant structure is intrinsically geometric.

## Current scientific position

The 01-04 series supports continuing the relational/geometric line, but the evidence remains bounded.

What is currently justified:

- relational organization can preserve the tested learned structure;
- some representation differences survive normalization and encoding controls;
- data-layout explanations have been progressively narrowed.

What is not yet justified:

- SI is fundamentally geometric;
- geometric structure is necessary for intelligence;
- geometric organization is superior in general;
- path-dependent identity or becoming has been demonstrated by this series;
- Python runtime advantages generalize to other substrates.

## Main next gate

The next primary experiment must return to the governing thesis and test developmental path dependence.

Core question:

> Can two byte-identical seeds that end with matched explicit information nevertheless develop different persistent internal organization because of different histories, such that the same later experience produces measurably different learning or behavior?

Required properties:

- byte-identical initial seed;
- distinct controlled nursery histories;
- matched explicit/declarative end information before probe;
- verified absence of trivial identifiers or leaked history labels;
- same subsequent probe experience;
- measurement of future learning trajectory, adaptation, choice and structural change;
- reset/rewire controls;
- migration/replay control where applicable;
- explicit falsifier: if matched end information eliminates downstream differences, path-dependence is not supported for the tested construction.

This experiment is primary because it directly tests trajectory/becoming. It must not be displaced by additional implementation benchmarking unless a specific confound blocks interpretation.

## Side-control policy

An SI-04A-style representation/data-structure audit is permitted only as a subordinate side control.

It may answer:

> Are observed SI-04 runtime differences caused purely by hash-map/list/index organization?

It may not delay or redefine the primary trajectory test unless its result is necessary to interpret that test.

## Claim discipline

Use the weakest claim supported by the evidence.

Prefer:

- `SUPPORTED_BOUNDED`
- `NOT_SUPPORTED`
- `MIXED`
- `INSUFFICIENT_EVIDENCE`

Do not promote implementation observations into ontology.

`UNKNOWN` remains unknown.

## Run discipline

Every session and every distinct scientific run must be registered in `nsolland/Index/ops/RUN_LEDGER.json` before execution.

For local scientific execution, use the exact gate text:

`LOCAL EXECUTION REQUIRED`

GitHub is source/review/evidence storage, not the experiment execution environment.
