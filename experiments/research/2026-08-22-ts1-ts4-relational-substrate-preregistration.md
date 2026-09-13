# TS-1 / TS-4 relational substrate — protocol lock v0.1

Date: 2026-08-22
Issue: #122
Epistemic status: falsification_criterion + mathematical_definition + implementation_claim
Maturity: synthetic harness qualification only

## Scope

This protocol tests whether the proposed measurements are internally coherent and falsifiable in a deterministic system under full experimental control.

It does not test physical spacetime. It does not validate A3/A4 as natural law. Passing this harness means only that the TS-1/TS-4 instrumentation behaves as specified and is ready to be applied to measured Synapse/mesh traces.

## Common substrate X_k

The synthetic substrate is a directed relational/boundary state:

```text
X_k = (nodes, directed weighted relations, informed set, version)
```

Local node compute is fixed for every condition:

```text
synchronous-frontier-propagation-v1
```

Only the relation geometry or wall-clock embedding may be changed.

Baseline geometry:

```text
A -> B -> C -> D -> E
     \--------> D
```

All edge costs are 1.0. Source is A. Target is E.

Two independently computed projections are used:

```text
t_rel(X_k)  = number of ordered causal X updates required for E to become reachable/informed
space(X_k)  = weighted directed shortest-path distance A -> E
```

The two functions consume the same measured relation state but are implemented separately.

## TS-1 — relational clock under schedule perturbation

Use exactly the same causal state trace under two wall-clock schedules.

Locked schedules:

```text
regular:    [0, 1, 2, 3]
perturbed:  [0, 3, 4, 8]
```

Primary measures:

```text
relational_alignment = mean Jaccard(state_k^A, state_k^B) at matched ordered updates
wall_clock_alignment = mean Jaccard(state^A(t), state^B(t)) at union of event times
```

Pass criterion:

```text
same causal trace fingerprints
AND relational_alignment == 1.0
AND wall_clock_alignment < 0.8
```

Falsifier: schedule perturbation changes the causal trace, relational indexing fails to align it exactly, or wall-clock indexing aligns equally well under this locked perturbation.

Interpretation boundary: a pass establishes only that an intrinsic transition coordinate can be operationalized independently of elapsed wall-clock duration in this controlled system.

## TS-4 — one substrate, two projections

### Primary intervention

Remove relation:

```text
B -> D
```

Hold node set and local compute rule fixed.

Locked prediction:

```text
delta t_rel > 0
AND delta space > 0
AND both deltas have the same sign
```

### Negative control

Add an irrelevant reverse relation:

```text
E -> A
```

Locked prediction:

```text
delta t_rel == 0
AND delta space == 0
```

Pass criterion requires both the primary intervention and negative control.

Falsifier: the bridge intervention does not move both projections in the predicted direction, or the irrelevant control changes either projection.

## Why the negative control matters

TS-4 must not reduce to "any change in X changes two numbers". The E -> A control changes the substrate but should not alter A -> E propagation or A -> E reachability geometry. A failure here invalidates the harness logic.

## Validation status

Before repository commit, the producing session executed the new module in an isolated temporary Python environment:

```text
8 tests passed
TS-1 relational_alignment = 1.0
TS-1 wall_clock_alignment = 0.6583333333333333
TS-4 baseline: t_rel=3, space=3
TS-4 remove B->D: t_rel=4, space=4
TS-4 add E->A control: delta_t_rel=0, delta_space=0
```

Per repository verification governance, this is INTERNAL_REVIEW only. It is not independent attestation and not a scientific result.

## Next evidence gate

After this synthetic harness is qualified, TS-4 must be repeated on measured relational states from an existing Synapse/mesh experiment while:

- freezing node/model compute;
- deriving X_k from recorded relations rather than hand-constructing it;
- preregistering edge-cost and transition rules target-blind;
- including null/irrelevant interventions;
- preserving negative results;
- checking whether separate hidden variables are required to explain t_rel and reachability.

Only that next gate can begin to provide project evidence for the common-substrate hypothesis.

## Post-lock empirical correction — R31 snapshot insufficiency

The next evidence gate was partially exercised on 2026-08-22 as a secondary analysis of the already frozen Synapse Lab X² R31 artifact. This does not alter the synthetic protocol or retroactively change its pass result.

Frozen source:

```text
synapse-lab Actions run 32473619742
artifact 9443539316
artifact ZIP sha256 793b292b96f5d8039bc66f42fa219e7ca2330a63e050d4a20caacde5bc99e70a
secondary-analysis merge bdcab207541e7dc9fda0d33b7a5c32206e55a478
```

R31 supplies a direct counterexample to the stronger snapshot-only interpretation of `X_k`.

Five cumulative regimes end with exactly the same final target-to-capsule relation geometry, fingerprint:

```text
fc418c51b9506bf64f3381001b31e7409df048bc8a614b5cf6360bc2c9948d7c
```

but their stable capability differs:

```text
4/6, 4/6, 5/6, 6/6, 6/6
```

and their process cost differs:

```text
1012, 1000, 1004, 747, 880 evaluated candidates
```

The strongest matched pair, `persistent-retention` versus `progressive-retention`, has the same final geometry and the same 6/6 stable capabilities but requires respectively 747 versus 880 evaluations and 912 versus 1296 median breakthrough bits.

Therefore the following generalization is falsified in this bounded system:

```text
X_k = terminal relation geometry alone
```

A state representation used for the empirical TS-4 program must instead be history-bearing:

```text
X_k = (current relation/boundary state, temporal residue H_k)
```

where `H_k` is not assumed to be the full trace. It is the smallest sufficient retained/compressed process state needed to distinguish future possibility and transition cost after controlling current exogenous input.

Candidate components, to be tested smallest-first:

```text
G0  terminal relation geometry only                         [falsified as sufficient by R31]
G1  G0 + persistent/reset state
G2  G1 + retained partial-consequence / relation-score state
G3  G2 + compact failure/search-memory summary
G4  G3 + pressure/turnover trajectory summary
G5  full ordered stage trace
```

The next falsifier is no longer "does topology matter?". It is:

> What is the minimum temporal residue that, together with current relation geometry, recovers the observed differences in stable capability and transition cost without target leakage?

This is bounded computational evidence only. It does not establish that physical space or time contains an analogous hidden history state.