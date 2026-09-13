# GEOMETRIC-SI-01 — Geometry sufficiency test

## Primary objective
Test whether persistent dynamic relational geometry is sufficient to preserve learned behavior, developmental continuity, relational structure, and transfer after removing language/token history and symbolic episodic memory.

This is an ablation test, not a claim that geometry alone is SI.

## Anchor
- repo: nsolland/PersonalAI-OS
- canonical base: 1e7b03c0bf6c79a5d441e243096b9254b82bba05
- branch: experiment/geometric-si-sufficiency
- owner: njal / relAIon research
- owned files: experiments/geometric_si/**
- dependencies: existing developmental-seed, continuity, lineage, and relational-geometry contracts; no governing dependency on GAUI

## Prior-work boundary
Do not repeat tests already covering seed/body separation, mechanical continuity, lineage/provenance, branch ancestry, false continuity, or ordinary relational-memory persistence. This run asks the unresolved sufficiency question: what survives when symbolic/token history is removed but learned geometry is preserved?

## Hypothesis
H1: A system retaining learned relational geometry but losing token/symbolic history will retain materially more acquired capability and identity-consistent behavior than a geometry-reset control.

H0: Preserving learned geometry provides no material advantage once symbolic/token history is removed.

## Experimental groups
Start from byte-identical seeds and identical task/environment sequence through training T.

A — FULL: model/runtime + symbolic memory + learned geometry.
B — GEO: same runtime + frozen/persistent learned geometry; remove token history, natural-language memory, symbolic episodic records and explicit task solutions.
C — SYMBOLIC: preserve symbolic episodic memory/task records; reset learned relational geometry to seed state.
D — RESET: preserve only seed/runtime; reset both learned geometry and symbolic history.

Authority, safety boundaries, evaluation code and task interface remain identical across groups.

## Geometry representation
Use a minimal typed dynamic graph/metric state rather than visual polygons. Nodes represent latent/relational states; edges carry typed relation, direction, weight, temporal decay and provenance hash. Derived measurements: distances, neighborhoods, path structure, curvature/loop residual where available, and topology/connectivity. Storage serialization may remain binary; the experimental variable is representational organization, not physical media.

## Procedure
1. Instantiate >= 20 deterministic seeds per group.
2. Nursery phase: expose all copies to the same ordered experiences requiring association, prediction, relational navigation and cooperative choice. No test item is seen verbatim during training.
3. Snapshot both symbolic state and geometric state at T.
4. Apply group-specific ablation.
5. Evaluate without restoration on held-out tasks:
   - learned association transfer
   - relational navigation
   - novel composition of learned relations
   - preference/choice consistency induced during nursery
   - partner recognition from relational pattern without names/IDs
   - adaptation to one new perturbation
6. Migration probe: serialize only GEO state, restore into a fresh compatible runtime, rerun held-out tasks.
7. Rewire control: preserve node/edge marginals but randomize relational arrangement. This distinguishes geometry from mere stored quantities.
8. Record deterministic evidence bundle for every run.

## Primary metrics
- held-out task accuracy
- transfer/generalization accuracy
- identity/choice consistency against pre-ablation behavioral fingerprint
- partner/relationship discrimination
- adaptation sample efficiency
- state bytes retained
- operations / wall time per solved task

Report effect sizes and confidence intervals, not only pass/fail.

## Falsification gates
H1 is unsupported if GEO is statistically indistinguishable from RESET on acquired held-out capabilities, or if GEO advantage disappears under a control showing equivalent performance from non-relational stored quantities.

Strong support requires GEO > RESET and GEO > rewired control across preregistered acquired-capability metrics, with migration preserving the effect. GEO need not equal FULL.

If SYMBOLIC >= GEO, geometry has not shown a representational advantage. If FULL alone succeeds, the evidence supports coupled representation rather than geometry sufficiency.

## Interpretation constraints
- Do not call continuity identity unless lineage/identity contracts also hold.
- Do not infer consciousness, sentience or substrate independence.
- Do not promote a positive result to 'geometry alone is SI'.
- A negative result falsifies this implementation/representation at tested scale, not all geometric accounts.

## Next direct implementation
Build the smallest deterministic graph-state nursery and ablation harness under this directory, reuse existing continuity contracts, then run GEOMETRIC-SI-01 once. No additional experiment family until this gate produces evidence.
