# Relational substrate correction — temporal residue is part of state

Date: 2026-08-22
Issue: #124
Epistemic status: bounded empirical correction to M1 synthesis
Supersedes: snapshot-only readings of `docs/theories/2026-08-22-time-space-relational-synthesis.md`

## Correction

The earlier 2026-08-22 synthesis defined a useful common-substrate candidate using current relation and boundary state and treated memory as history-dependent deformation of future possibility.

A frozen Synapse Lab R31 secondary analysis now makes one ambiguity explicit and falsifies the stronger snapshot-only reading:

```text
X_k != terminal/current relation graph alone
```

Five R31 cumulative regimes end with exactly the same final target-to-capsule relation geometry while stable capability and process cost differ.

Frozen source:

```text
synapse-lab R31 Actions run: 32473619742
artifact: 9443539316
artifact ZIP sha256: 793b292b96f5d8039bc66f42fa219e7ca2330a63e050d4a20caacde5bc99e70a
secondary analysis merged: bdcab207541e7dc9fda0d33b7a5c32206e55a478
classification: FINAL_RELATION_SNAPSHOT_INSUFFICIENT_FOR_R31_OUTCOME_AND_PROCESS
```

Identical final capsule-geometry fingerprint across five cumulative regimes:

```text
fc418c51b9506bf64f3381001b31e7409df048bc8a614b5cf6360bc2c9948d7c
```

Stable recovered capability across those same-geometry regimes:

```text
persistent-overload       4/6
persistent-steady         4/6
persistent-progressive    5/6
persistent-retention      6/6
progressive-retention     6/6
```

Evaluated candidates:

```text
persistent-overload       1012
persistent-steady         1000
persistent-progressive    1004
persistent-retention       747
progressive-retention      880
```

The strongest matched pair is `persistent-retention` versus `progressive-retention`: same terminal geometry and same 6/6 stable capability, but 747 versus 880 evaluations and 912 versus 1296 median breakthrough bits.

Therefore terminal geometry does not contain enough information to reconstruct either stable capability outcome across all five regimes or transition/search cost even when endpoint capability is matched.

## Corrected common substrate

Use a history-bearing state:

$$
X_k=(R_k,B_k,H_k,I_k),
$$

where:

```text
R_k = current relational organization
B_k = current boundary/admissibility structure
H_k = temporal residue: a sufficient retained/compressed statistic of prior process
I_k = declared protected/required invariants
```

`H_k` is not defined as the full transcript or full historical trajectory. The research problem is to find the smallest state that preserves the future-relevant effect of history.

The corrected projections are therefore:

$$
\mathcal{S}_k=\mathrm{Geometry}(R_k,B_k,H_k; I_k),
$$

and

$$
\mathcal{T}(0\to k)=\mathrm{OrderedMeasure}(X_0\to X_1\to\dots\to X_k).
$$

This means "space" in the computational synthesis is not merely graph adjacency. It is current reachable possibility under a history-bearing relational state.

Likewise, operational time cannot generally be reconstructed from the terminal graph. Two trajectories may terminate in the same graph and capability while having different transition cost.

## What R31 changes

Before R31 secondary analysis, the synthesis could be read as:

```text
current graph -> space
ordered graph changes -> time
```

The corrected form is:

```text
current relation/boundary state + temporal residue -> current possibility geometry
ordered changes of that history-bearing state       -> operational time
```

Memory is therefore not an optional fifth variable beside the substrate. In systems where history continues to affect future transition, the future-relevant residue of history is part of the state required to define the substrate itself.

This sharpens A4:

> Space is boundary memory.

In the bounded computational interpretation, the "memory" term is literal: two systems can have the same visible terminal relation graph and still occupy different effective possibility states because their retained process state differs.

It also sharpens A3:

> Time is filter recurrence.

The residue carried forward by recurrence can affect subsequent possibility even when the visible relation graph converges to the same endpoint.

## Minimal-state falsifier

The next experiment must identify the smallest history-bearing augmentation that distinguishes the R31 same-geometry regimes without target leakage.

Candidate nesting:

```text
G0  terminal capsule geometry only
G1  G0 + persistent/reset state
G2  G1 + retained partial-consequence / relation-score state
G3  G2 + compact failure/search-memory summary
G4  G3 + pressure/turnover trajectory summary
G5  full ordered stage trace
```

R31 already falsifies `G0` as sufficient.

A positive next result requires one preregistered `G_i` to recover the observed capability/process distinctions on held-out comparisons while smaller representations fail. If no compact augmentation succeeds and only the full trace works, the claim that a compact state substrate exists is weakened.

## Claim boundary

This correction supports only the following bounded statement:

> In the frozen R31 deterministic NOR system, terminal relation geometry is not a sufficient state representation for stable capability and developmental process cost. A candidate relational substrate must retain some future-relevant temporal residue.

It does not show that:

- physical spacetime contains temporal residue in this sense;
- the R31 variables are universal state variables;
- topology is unimportant;
- full history is required;
- the Tofoo common-substrate hypothesis is validated;
- memory, time and space are physically identical.

The correction strengthens falsifiability by removing a representation that existing project evidence already disproves.