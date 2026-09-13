# Tid × rom × relasjon — korrigert Tofoo-syntese

Date: 2026-08-22  
Status: cross-project research synthesis  
Epistemic status: M1 hypothesis over mathematical definitions + bounded project evidence + external convergence  
Scope: Tofoo / Framleis / Synapse research only

## Executive result

The strongest current Tofoo formulation is not:

> time and space have been proven emergent.

It is the narrower, testable construction:

```text
relational distinction / filtering
-> boundary and relation state
-> repeated state transition
-> persistent history
```

from which two different operational coordinates can be defined:

```text
time  = order / measure of relational state change
space = geometry of admissible relations and reachable transformations
```

This joins the older axioms

```text
A3: Time is filter recurrence.
A4: Space is boundary memory.
```

with the newer Synapse evidence that functional state can reside in persistent relations, survive replacement of local compute, regenerate missing roles, and bias future reconstruction after the active phenotype is gone.

The resulting candidate is:

> **Time and space may be two projections of one deeper versioned relational process: time describes how the relation/boundary state changes; space describes what the current relation/boundary state makes adjacent, reachable or excluded.**

That statement is still a research hypothesis. It is not a claim about fundamental physical spacetime.

---

## 1. Canonical Tofoo roots

`experiments/axioms.md` already contains the two required primitives.

### A3 — time

```text
Time is the filter's breath.
Time is filter recurrence.
```

Operational meaning: identity or continuity is not maintained once. It is maintained through repeated transformation against drift.

A3 therefore gives an intrinsic ordering primitive:

```text
state before filter/update
-> event
-> state after filter/update
```

No wall clock is required to define the before/after relation.

### A4 — space

```text
Space is the filter's memory of where the boundary goes.
Space is boundary memory.
```

Operational meaning: previous distinctions constrain the region of states, relations or actions that remain reachable/admissible now.

A4 therefore gives a geometry primitive:

```text
what is connected?
what is separated?
what is reachable?
through which boundary?
at what relational cost?
```

The key update on 2026-08-22 is to stop treating these as separate metaphors and test whether they can be generated from one explicit relational state model.

---

## 2. Mathematical correction: Test 7 no longer carries the inverse-time law

The original 2026-07-02 Test 7 incorrectly claimed that constant Banach contraction implied

$$
T\propto \frac{1}{|\tau_0-\tau^*|}.
$$

For

$$
\tau_{n+1}=(1-\alpha)\tau_n+\alpha\tau^*,
$$

with $q=|1-\alpha|\in(0,1)$,

$$
d_n=q^n d_0,
$$

and the threshold hitting time is

$$
T_\epsilon=
\left\lceil
\frac{\ln(\epsilon/d_0)}{\ln q}
\right\rceil
$$

for $d_0>\epsilon$.

So fixed contraction gives logarithmic hitting time. Starting closer to the fixed point takes fewer transitions, not infinitely many.

Critical slowing requires an additional mechanism such as

$$
q(state)\to1
$$

near a critical regime. It does not follow from constant $\alpha$.

The corrected Test 7 is now:

`docs/theories/2026-07-02-test7-emergence-of-time.md`

This matters for the synthesis because the deeper candidate does not need the invalid inverse law. The useful primitive is transition order itself.

---

## 3. Candidate common substrate

Let the system at transition $k$ have:

```text
R_k = relational state
B_k = boundary / admissibility state
I_k = currently protected or required invariants
```

Let an event $e_k$ produce a governed or experimentally defined update

$$
(R_k,B_k,I_k)
\xrightarrow{U(e_k)}
(R_{k+1},B_{k+1},I_{k+1}).
$$

Nothing here requires physical spacetime. It is a state-transition object.

The synthesis asks whether useful notions of time and space can both be derived from this object rather than supplied independently.

---

## 4. Operational time from transition order

The minimal relational clock is simply

$$
t_{rel}(k)=k.
$$

It says only that one causally registered transition happened after another.

A richer clock may weight transitions by a preregistered measure of structural change:

$$
t_{rel}(k)=\sum_{i=0}^{k-1}c(e_i),
$$

where $c(e_i)$ may measure, for example:

- causal state change;
- relation-state mutation;
- information incorporated;
- invariant-preserving transformation cost.

The weight must be fixed before evaluation. Otherwise the clock can be fitted post hoc to any trajectory.

A genuine relational-clock signal requires schedule invariance:

```text
same causal transition sequence
+ different wall-clock delays
-> same trajectory under t_rel
```

Wall-clock duration may still matter physically or operationally. The claim is only that the system has an additional intrinsic transition coordinate.

---

## 5. Operational space from relational reachability

At a fixed state $k$, define a graph or higher-order relation structure

$$
G_k=(V,E_k,w_k),
$$

where an edge/hyperedge exists only when the corresponding relation or transformation is currently available under $R_k$ and $B_k$.

A candidate relational distance is

$$
d_k(x,y)
=
\min_{p:x\leadsto y}
\sum_{e\in p}w_k(e),
$$

where the minimum is over admissible relational paths.

This makes two objects "near" when a low-cost admissible relation path joins them and "far" when only costly paths exist. If no admissible path exists, they are disconnected in the current operational geometry.

This is a concrete version of A4:

> space is the remembered shape of what the boundary currently permits to connect.

It is not Euclidean distance and is not asserted to be physical spatial distance.

The geometry can also be higher-order rather than pairwise. Recent Synapse work already motivates this because some functions depend on joint relation structure that is lost under pairwise or node-isolated views.

---

## 6. Time and space become coupled when geometry itself changes

Because $G_k$ depends on relational and boundary state,

$$
G_{k+1}=F_G(G_k,e_k),
$$

the operational geometry changes through ordered transitions.

Then:

```text
space_k = current reachability geometry

time     = ordered change space_k -> space_{k+1}
```

or more compactly:

> **Space is the current relational possibility structure. Time is the ordered transformation of that structure.**

This is the central candidate produced by the synthesis.

It is stronger and cleaner than the old formulation where one exponential equation was merely observed to work over both $r$ and $t$.

---

## 7. Earlier spatial note: what survives and what does not

`docs/theories/2026-06-26-harmonisk-geometri-resonansprosess.md` observed that

$$
T(r)=T_0e^{-r/r_0}
$$

has the same contraction form as an iterative Framleis update.

What survives:

```text
same operator family can act over different ordered parameters
```

What does not follow:

```text
same mathematical form
!= same physical mechanism
!= proof that physical space is Framleis time
```

The 2026-08-22 synthesis therefore replaces form analogy with an intervention-ready relational construction.

---

## 8. New own evidence: relation state is not decorative

The last two days of Synapse / Tofoo work materially strengthen the relational side of the hypothesis.

### 8.1 R11/R12 — functional continuity across model replacement

The relational-continuity work showed in bounded constructed tasks that:

```text
replace local model compute
preserve learned relational organization + semantic binding
-> task-specific phenotype persists
```

while:

```text
keep competent compute
break the relation binding
-> phenotype collapses
```

In R12 every functional model node could be replaced one at a time while the frozen higher-order relation state remained unchanged and measured function stayed intact.

This does not prove that "the network is intelligence" in general. It does show causally that a tested functional invariant can be carried by relational organization rather than by one persistent node.

Internal anchor:

`docs/theories/2026-08-20-framleis-synapse-relational-continuity-convergence.md`

### 8.2 X² regeneration — geometry can reconstruct missing compute

The regeneration experiment removed the active computational role. Surviving distributed relation fragments independently selected compatible blank substrate and reconstructed the missing role only after a matching quorum formed.

The relevant pattern is:

```text
relation geometry survives
-> local component disappears
-> surviving relations constrain compatible reconstruction
-> function returns on different substrate
```

That is directly relevant to A4. The effective possibility structure was carried by surviving relations and boundaries, not by the destroyed node.

Internal anchor:

`docs/theories/2026-08-20-framleis-synapse-regeneration-and-minimum-state.md`

### 8.3 RM1 — memory changes future reachable organization

RM1 destroyed the active program, topology, runtime and reward history while preserving only a tiny latent relation trace. That trace measurably changed later reacquisition relative to scratch, shuffled and wrong-target controls.

The narrow result was:

```text
past interaction
-> small persistent relational disposition
-> old phenotype gone
-> future reconstruction landscape changed
```

This gives A4 a sharper computational interpretation:

> **memory can be represented as a persistent deformation of future reachability.**

That is stronger than memory as stored historical content.

Internal anchor:

`docs/theories/2026-08-20-mycelium-stentor-regulatory-memory.md`

### 8.4 R29/R31 — continuity is invariant plus plastic geometry

R28 first failed to discover a privileged "natural" identity core from target-blind structural centrality.

R29 instead selected a demonstrated capability phenotype and found its minimum joint relational support. Protecting that support preserved the selected phenotype across unseen turnover.

R31 later showed, in the bounded frozen task family, that persistent plastic retention could acquire the previously missed expansion capabilities while preserving the formed invariant throughout.

This suggests:

```text
protected invariant != frozen whole system
continuity = invariant survives while surrounding relational geometry changes
```

That is exactly the kind of system in which an intrinsic transition coordinate is useful: the system changes materially without losing the selected continuity object.

Internal anchors:

- `docs/theories/2026-08-21-harness-continual-learning-stability-plasticity.md`
- `frontier_garden/research_synthesis_2026-08-21.md`

---

## 9. Mesh / Neuro AI: the effective unit already contains time and relation

The current Mesh / Neuro AI hypothesis defines the effective unit as more than a node:

```text
node
+ synapse / relation
+ persistent state
+ environment
+ recurrence over time
```

Recent additions sharpened two relevant variables:

1. topology/relation structure can change system capability while local nodes remain fixed;
2. temporal residue can change later behavior even when current input is the same.

This produces an immediate test of the new synthesis:

```text
fix nodes and current input
change only R_k / B_k history
measure:
- current relational geometry
- reachable capabilities
- future transition path
```

If prior relational history changes neither geometry nor later behavior after proper controls, the proposed memory-space-time coupling weakens.

Internal anchors:

- `docs/hypotheses/2026-08-20-mesh-neuro-ai.md`
- `docs/hypotheses/2026-08-20-encounter-ontology-mesh-extension.md`

---

## 10. A compact unified candidate

The current candidate can be written as four related quantities over the same state-transition process.

### Relation / boundary state

$$
X_k=(R_k,B_k).
$$

### Space

$$
\mathcal{S}_k=\mathrm{Geometry}(X_k),
$$

where geometry means admissible/reachable relational structure.

### Time

$$
\mathcal{T}(0\to k)=\mathrm{OrderedMeasure}(X_0\to X_1\to\dots\to X_k).
$$

### Memory

A history $H$ is memory when, after controlling current exogenous input,

$$
P(X_{k+1}\mid X_k,H)\neq P(X_{k+1}\mid X_k).
$$

Operationally, memory is present when prior interaction changes future transition probabilities, costs or reachable states.

### Continuity

For declared invariant set $I$ and transformation sequence $U_{0:k}$,

$$
I(X_0)=I(X_k)
$$

under the relevant equivalence criterion, while non-invariant state may change.

Compactly:

```text
space      = current relational possibility structure
time       = ordered transformation of that structure
memory     = history-dependent deformation of future possibility
continuity = selected invariant surviving those transformations
```

This is the cleanest current bridge between A1/A3/A4, Framleis continuity and Synapse relational evidence.

---

## 11. External convergence: Group Field Theory

Current Group Field Theory work provides a useful independent physics precedent for relational construction, but not for the Tofoo mechanism.

### Calcinari & Gielen — relational dynamics

Group Field Theory is formulated without a background notion of space or time and can use matter degrees of freedom as relational clocks.

- arXiv:2407.03432
- published as *Quantum* 9, 1610 (2025)

### Relational observables in GFT

The 2025 work on relational observables constructs localization relative to dynamical quantum reference frames rather than external coordinate labels.

- DOI: 10.1088/1361-6382/adedf4

### Dekhil et al. 2026 — emergent local spacetime description

The 2026-08-12 paper begins from fundamental GFT quantum-gravity dynamics in a fully relational framework. Collective dynamics reconstruct an effective cosmological spacetime and local matter field description, with localization in space and time defined relationally relative to a material reference frame.

- arXiv:2608.12003

### What this contributes

The valid external convergence is methodological:

```text
fundamental description need not begin with background spacetime coordinates
relational observables/reference structures can define localization and evolution
effective spacetime structure can arise collectively in a different formal system
```

The invalid transfer would be:

```text
GFT has emergent spacetime
therefore Φ / Framleis generates physical spacetime
```

That inference is not allowed.

The LinkedIn item that prompted this comparison is retained as discovery provenance only:

- https://lnkd.in/p/eTc8qCrD

---

## 12. MELLOMROM discipline: prevent a beautiful analogy from becoming a false reference

The new MELLOMROM correction corpus is directly relevant to this synthesis.

Its current error classes include:

```text
E02_REFERENCE_MISALIGNMENT
E07_LOCAL_GLOBAL_MISMATCH
E08_ANALOGY_OVERREACH
E09_FALSE_REFERENCE_STABILIZATION
E11_UNCERTAINTY_ERASURE
```

Those are exactly the risks here.

Therefore the transfer discipline is explicit:

```text
shared mathematical form -> analogy only
shared relational method -> convergence signal
controlled intervention in our system -> project evidence
independent physical derivation -> required for physical claim
```

No amount of conceptual convergence upgrades one level into the next.

Internal anchor:

`experiments/mellomrom/`

---

## 13. Direct falsification program

Do not create a broad new cosmology program. Test the common-substrate hypothesis inside systems already under control.

### TS-1 — relational clock under schedule perturbation

Use the same causal state-transition trace under multiple wall-clock schedules.

Pass candidate:

```text
state trajectories align under preregistered t_rel
and do not align under wall-clock time
```

This establishes only an intrinsic system clock.

### TS-2 — relational distance predicts functional reach

Construct $G_k$ from currently available relations using a target-blind preregistered edge-cost rule.

Ask whether $d_k(x,y)$ predicts:

- reconstruction cost;
- capability transfer cost;
- time-to-reacquire;
- vulnerability to relation ablation.

Falsifier: the metric adds no predictive value beyond trivial node count, raw topology hops or current utility.

### TS-3 — history deforms geometry

Start from matched current input and compute state, but vary only validated prior relational history.

Measure whether the resulting $G_k$, reachable capability set or reconstruction cost differs.

Then erase/randomize the retained history object.

Positive evidence requires the effect to disappear or change in the predicted direction.

### TS-4 — one substrate, two projections

This is the strongest test.

Derive both:

```text
t_rel from ordered X_k updates
space_k from geometry(X_k)
```

from the same measured relational/boundary state $X_k$.

Then intervene on $X_k$ while holding local compute fixed.

The common-substrate hypothesis predicts coordinated changes in:

```text
transition dynamics
and
reachability geometry
```

according to preregistered rules.

If separate hidden variables are repeatedly required to explain the two quantities, the claim that time and space are projections of one relational substrate weakens.

### TS-5 — state-dependent slowing only where q changes

Estimate local $q(state)$ independently.

Call a regime "critical slowing" only when

```text
q(state) -> 1
AND measured relaxation time diverges consistently with q(state)
```

This prevents the original Test 7 error from returning under a different label.

---

## 14. What would be genuinely interesting if the tests work

The important result would not be a claim about quantum gravity.

It would be this computational result:

> A system with replaceable local compute possesses a persistent relational state from which both an intrinsic transition coordinate and a predictive reachability geometry can be derived; history changes that geometry, and selected invariants can survive while the geometry evolves.

That would connect four previously separate Tofoo/Synapse tracks with one measurable object:

```text
Framleis continuity
Synapse relational capability
latent regulatory memory
Mesh temporal/topological dynamics
```

At that point the question "the network is the intelligence" becomes sharper:

> **How much capability, continuity and future possibility is carried by the evolving relational geometry rather than by the nodes?**

---

## 15. Claim boundary

Do not claim from this synthesis that:

- physical spacetime has been derived from Φ;
- Group Field Theory validates Tofoo or Synapse;
- computational relational distance is physical distance;
- transition count is physical time;
- the universe follows the Framleis contraction operator;
- relational persistence establishes consciousness, life or personal identity;
- later positive Synapse results erase the original negative P12 result;
- analogy can substitute for an intervention or independent derivation.

Current bounded statement:

> **Tofoo already had compatible primitives for time as recurrence and space as boundary memory. Correcting Test 7 removes the invalid inverse-distance law. Recent Synapse results now make the relational substrate experimentally concrete enough to test a stronger common-substrate hypothesis: operational time as ordered change of relational state, operational space as the reachability geometry induced by that same state, memory as its history-dependent deformation, and continuity as the invariant that survives its transformation.**

---

## Internal evidence anchors

- `experiments/axioms.md`
- `docs/theories/2026-07-02-test7-emergence-of-time.md`
- `docs/theories/2026-06-26-harmonisk-geometri-resonansprosess.md`
- `docs/hypotheses/2026-08-20-mesh-neuro-ai.md`
- `docs/hypotheses/2026-08-20-encounter-ontology-mesh-extension.md`
- `docs/theories/2026-08-20-framleis-synapse-relational-continuity-convergence.md`
- `docs/theories/2026-08-20-framleis-synapse-regeneration-and-minimum-state.md`
- `docs/theories/2026-08-20-mycelium-stentor-regulatory-memory.md`
- `docs/theories/2026-08-21-harness-continual-learning-stability-plasticity.md`
- `frontier_garden/research_synthesis_2026-08-21.md`
- `experiments/mellomrom/`

## External evidence anchors

- https://arxiv.org/abs/2407.03432
- https://doi.org/10.1088/1361-6382/adedf4
- https://arxiv.org/abs/2008.02774
- https://arxiv.org/abs/2608.12003
