# Framleis × Synapse Lab — relational functional continuity convergence

Date: 2026-08-20  
Status: cross-repo research synthesis  
Research level: L1/L2 synthesis over existing implemented hypotheses plus controlled project evidence  
Epistemic boundary: this note does **not** validate the universal Φ-law, consciousness, personal identity, AGI or unrestricted model independence.

## Why this note exists

On 2026-08-20, two research paths that had been developed separately inside the project converged on the same technical object:

1. **Tofoo / Framleis / P12** had already formalized questions about representation continuity under replaceable model drivers, relation-dependent capability, and the minimum sufficient state that must cross a Synapse boundary.
2. **Synapse Lab** independently produced controlled R11/R12 experiments in which learned relational organization preserved a task-specific functional phenotype across model replacement, including gradual replacement of every functional model node.

The important point is not rhetorical similarity. The variables manipulated in the two paths are structurally aligned: **what state must persist, what may be replaced, which invariants carry function, and what happens when the relational/semantic binding is destroyed.**

## Chronology: the convergence was not written after the result

The relevant Tofoo work existed before the Synapse Lab R11/R12 implementation landed:

- `8881742d56e9a9f11210daeb12344fd6027d6893` — Mesh / Neuro AI synthesis: effective cognitive unit may be `node + synapse + persistent state + time`; H-MESH-6 specifies relation ablation as a causal test.
- `5332d279b9f2998146c685280f3d001d9f4474ef` — 2026-08-20 09:04 +02:00: adds biomimetic process/context/interdependence evidence and **H-MESH-7 — minimum sufficient state transfer**.
- `2dec250fd58f832754b7bdbd5733b985e4e4d1b5` — 2026-08-20 12:21 +02:00: implements the P12 `P0..P6` payload-ablation axis with shared upstream calls, causal payload isolation and minimum-sufficient-state reporting.

Later the same day in Synapse Lab:

- `c4f296111377fd0214b00b9e743cb7407b2309bb` — 2026-08-20 16:38Z: versions the minimum-continuity-capsule probe (R11).
- `b01d49886d29dd03da221c8185f08fa29e27e29d` — 2026-08-20 16:44Z: adds gradual node replacement / Ship-of-Theseus continuity (R12).

This chronology matters because H-MESH-7 and the P12 payload ablation were not retrofitted after seeing R11/R12.

## Parallel path A — Framleis representation continuity

Earlier Tofoo work separated representation continuity from personal identity and established the canonical boundary:

```text
Model predicts.
Twin represents.
Framleis preserves continuity and integrity of the representation.
Authority governs intervention.
```

The Framleis long-horizon twin-driver challenge v2 then made model replacement explicit:

```text
model-a -> model-b
```

must not require changing:

```text
canonical twin identity/state
```

This is not the same object as Synapse relation-state. The twin is a maintained representation; the Synapse substrate is learned relational organization. But the experimental pattern is the same:

> **replace the compute while preserving the state/invariants whose continuity is under test.**

Digital DNA also already operationalized continuity as an executable `S/T/~/I/C` grammar:

- `S`: state space;
- `T`: admissible transformation classes;
- `~`: continuity/equivalence relation;
- `I`: protected invariants;
- `C`: collapse conditions.

This supplies an existing formal vocabulary for the new relational continuity work, without implying that relational phenotype equals personal identity.

## Parallel path B — Mesh / Neuro AI before R11/R12

The Mesh / Neuro AI hypothesis already defined:

```text
Edge node  = local specialized compute
Synapse    = selective relation layer
Mesh       = effective distributed cognitive unit
KWorld     = persistent external world state
```

The working thesis was:

> The node computes. The synapse shapes interaction. The mesh may become the cognitive unit.

H-MESH-6 then made the causal requirement explicit:

> If a capability is genuinely mesh-level, ablating or randomizing specific relation classes should remove that capability even while every node remains individually unchanged.

This is substantially stronger than "many agents beat one agent." It asks where the capability is causally localized.

## Parallel path C — H-MESH-7 / P12 minimum sufficient state

Before R11 was run, Tofoo sharpened a second question:

> What is the minimum sufficient state transfer between nodes that preserves or increases mesh-level capability?

The candidate state packet was:

```text
observation
+ relevance/context
+ uncertainty
+ state delta
+ provenance
```

P12 #114 then implemented a causal payload ablation:

```text
P0  full/raw transferable context
P1  contextualized state delta
P2  compressed contextualized state delta
P3  delta without provenance
P4  delta without uncertainty
P5  delta without relevance/relation context
P6  randomized/irrelevant transfer control
```

Critically, all variants share the same upstream node calls. The manipulated variable is therefore the payload that crosses the Synapse boundary, not a different upstream reasoning trajectory.

P12 remains an implemented protocol awaiting the intended empirical provider run. The mock/smoke path validates experiment mechanics, not H-MESH-7 itself.

## Synapse Lab R11 — minimum learned continuity capsule

Synapse Lab R11 asked a narrower but strikingly aligned question:

> After replacing the model, how much **learned relational organization** must cross the boundary for an already learned phenotype to survive?

Source model:

```text
Qwen/Qwen2.5-0.5B-Instruct
```

Replacement model:

```text
HuggingFaceTB/SmolLM2-360M-Instruct
```

Five conditions were tested under the replacement model:

| Condition | Result |
|---|---|
| Full learned relation state | preserved |
| Winner-only state; utility magnitude/history erased | preserved |
| Renamed winner token + correct semantic adapter | preserved |
| No learned selection state | lost |
| Same selection bit + corrupted operator binding | lost |

All preserved conditions retained the crossed temporal phenotype over four unseen streams with minimum own-task accuracy `1.00`.

For this deliberately tiny two-operator task, the learned state can be compressed to:

```text
1 selection bit + intact semantic operator binding
```

This does **not** mean one bit is sufficient for intelligence. It means that the tested learned history contained much more information than was required to preserve this particular phenotype.

Classification:

```text
MINIMUM_CAPSULE_ISOLATED
```

### R11 versus H-MESH-7

These are **parallel ablations of different state layers**:

- P12/H-MESH-7 asks what **communicated contextual payload** must cross between reasoning nodes.
- R11 asks what **learned relational selection/binding state** must persist across model replacement.

They should not be collapsed into one variable.

Together they suggest a layered minimum-state problem:

```text
minimum online payload
+
minimum persistent relational state
+
minimum shared semantic/operator contract
```

The next research target should measure all three jointly.

## Synapse Lab R12 — complete component replacement with function continuous

R12 constructed a three-node organism:

```text
sensor_a
sensor_b
coordinator
+ one learned higher-order joint relation
```

The joint relation was learned under Qwen and then frozen. No relational relearning was allowed during replacement.

Replacement sequence:

| Stage | Node composition | Accuracy |
|---|---|---:|
| stage0 | Qwen A + Qwen B + Qwen coordinator | 1.00 |
| stage1 | Smol A + Qwen B + Qwen coordinator | 1.00 |
| stage2 | Smol A + Smol B + Qwen coordinator | 1.00 |
| stage3 | Smol A + Smol B + Smol coordinator | 1.00 |

The SHA-256 digest of the learned joint relation state remained identical across all stages.

Controls:

- best `sensor_a` singleton: `0.50`;
- best `sensor_b` singleton: `0.50`;
- destroy only learned joint relation binding: `0.50`;
- restore exact relation binding: `1.00`;
- preserve state but corrupt semantic adapter: `0.00`.

Classification:

```text
GRADUAL_MODEL_REPLACEMENT_CONTINUITY
```

Narrow result:

> In this constructed XOR organism, every functional model component could be replaced one at a time by another model family while the measured system function remained continuous, provided the learned higher-order relational organization and compatible semantic contract were preserved.

## Direct mapping across the parallel tracks

| Earlier Tofoo variable / claim | Synapse Lab observation | Current status |
|---|---|---|
| Model driver may be replaceable while maintained state persists | R10/R12 replace Qwen with SmolLM2 while relational function persists | controlled project evidence for relational state, not validation of the digital-twin claim |
| H-MESH-6: true mesh-level capability should disappear under relation ablation while nodes remain competent | R7/R12: relation reset/destruction removes phenotype/capability; restoration restores it | narrow causal support in constructed tasks |
| H-MESH-7: find minimum sufficient transferred state | R11: minimum **persistent learned** capsule collapses to one selection bit + semantic binding in the two-operator task | adjacent result; different state layer from P12 payload |
| Synapse is more than transport; relation semantics matter | R11 wrong operator binding loses phenotype; R12 corrupted semantic adapter gives `0.00` | direct narrow support |
| External/persistent state may carry adaptation outside one node | R10/R12 function survives model replacement while relational state persists | direct narrow support |
| Framleis: continuity depends on preserved invariants through transformation | R12 explicitly preserves a byte-identical relational invariant while components transform | candidate operational instantiation, **not** proof of universal Framleis |
| A4-style boundary memory / geometry matters | state with incorrect semantic binding fails despite state value being present | mechanistic analogy/candidate, not validation of A4 |

## The stronger synthesis

Before the new experiments, the Mesh / Neuro AI program could be summarized as:

```text
capability = f(nodes, topology, state, time)
```

R11/R12 justify a sharper research decomposition for bounded systems:

```text
functional phenotype = F(local compute, semantic contract, relational organization, online state flow)
```

with the observed intervention pattern:

```text
replace local compute
preserve relational organization + semantic contract
=> phenotype can persist
```

while:

```text
destroy relational organization
preserve competent local compute
=> phenotype can collapse
```

This makes the relational substrate a first-class candidate carrier of functional continuity.

A concise research statement is now:

> **Compatible models can act as replaceable local compute while persistent learned relational organization carries a task-specific functional phenotype.**

A stronger hypothesis, still unproven, is:

> **The network is the intelligence when the organization of state, selection, semantics, timing and higher-order relations is sufficient to carry the system's functional invariants.**

The word **sufficient** is the research problem. It must be earned by progressively harder falsifiers.

## Framleis connection — what is supported and what is not

The Framleis core statement is:

```text
stable continuity requires invariant-preserving transformation over time
```

R12 is a concrete experiment of this form:

```text
component transformation: Qwen -> SmolLM2
preserved invariant: learned joint relation state + compatible semantic contract
observed system function: continuous
```

Destroying the relational invariant destroys the function in the tested system.

This is a useful operationalization of the **shape** of the Framleis continuity question.

It does not establish:

- personal identity continuity;
- the universal Φ-law;
- the specific tau metric or Goldilocks bounds;
- consciousness or phenomenal continuity;
- unrestricted transfer across arbitrary model families/tasks;
- that the observed invariant is unique or minimal in richer systems.

## New unified falsification program

The parallel tracks should now be connected rather than duplicated.

### F1 — joint minimum-state decomposition

Independently ablate:

```text
A. persistent learned relation state
B. semantic/operator contract
C. online Synapse payload fields
D. topology/higher-order grouping
```

Measure which combination is minimally sufficient for function.

### F2 — learned adapter rather than supplied adapter

R11/R12 currently require compatible semantic bindings. Replace the supplied adapter with a learned boundary mapping.

Falsifier: continuity depends on a hand-specified shared code rather than transferable organization.

### F3 — richer Fractal World continuity

Move R12 from constructed XOR into real bounded transport with:

- partial observability;
- latency;
- freshness;
- finite link capacity;
- persistent entity/world state;
- contradictory and stale evidence.

### F4 — repeated turnover

Do not stop after one Qwen -> SmolLM2 sequence. Replace nodes repeatedly over long horizons while preserving/perturbing relational state.

Question:

> Does functional continuity survive turnover, or does hidden model-specific drift accumulate?

### F5 — reverse and third-family replacement

Run:

```text
SmolLM2 -> Qwen
Qwen/SmolLM2 -> third independent model family
```

### F6 — P12 empirical payload run

Run the implemented P0..P6 provider protocol. Determine whether a compact contextual state packet preserves operational understanding relative to raw transfer.

This is complementary to R11, not redundant with it.

### F7 — non-constructed capability

Require:

- every isolated node insufficient;
- relational organization succeeds;
- organization destruction removes capability;
- competent replacement nodes do not rescue it without the relational state.

### F8 — dormant reconstitution savings

R10 showed reacquisition but not faster reacquisition versus a fresh prior. Test whether retained relational traces reduce samples/time to recover function after disruption.

## Canonical boundaries

Use:

> Synapse Lab R11/R12 provide controlled project evidence that a learned relational phenotype can survive model replacement and, in the constructed R12 organism, complete gradual replacement of all model nodes while frozen higher-order relation state is preserved.

Use:

> This converges with pre-existing Tofoo H-MESH-6/H-MESH-7 and Framleis replaceable-driver continuity hypotheses.

Do not use:

> R12 proves the Φ-law.

Do not use:

> The network is universally the intelligence.

Do not use:

> R12 proves personal identity can transfer between models.

Do not use:

> P12 payload ablation has empirically passed; the provider experiment is still pending.

## Canonical cross-repo anchors

Tofoo:

- `docs/hypotheses/2026-08-20-mesh-neuro-ai.md`
- `experiments/P12_Synapse_Test/p12_payload_ablation.py`
- `experiments/P12_Synapse_Test/README.md`
- `docs/theories/2026-08-17-prediction-representation-continuity-authority.md`
- `docs/theories/2026-08-17-representation-is-not-person.md`
- `experiments/framleis_twin_driver_v2.md`
- `digital_dna/`

Synapse Lab:

- `docs/relational-continuity-r11-r12-2026-08-20.md`
- `experiments/fractal_world/relational_minimum_capsule_probe.py`
- research commit `b01d49886d29dd03da221c8185f08fa29e27e29d`
- R11 run `32393120589`, artifact `9415709582`
- R12 run `32393689340`, artifact `9415963322`

## Current research object

The central question is no longer merely whether networking improves model performance.

It is:

> **What is the smallest persistent organization of state, semantic bindings, selection, timing and higher-order relations that can carry a functional capability through replacement of the components executing it?**

That is the direct bridge between Framleis continuity, P12 minimum state, and the Synapse Lab relational substrate program.
