# Mycelium × Stentor × regulatory memory — memory as bias over future regeneration

Date: 2026-08-20  
Status: cross-domain research synthesis  
Epistemic status: external biological evidence + parallel controlled Synapse Lab evidence + explicit hypothesis boundary  
Related: `../hypotheses/2026-08-20-mesh-neuro-ai.md`, `2026-08-20-framleis-synapse-regeneration-and-minimum-state.md`

## Executive synthesis

The Mesh / Neuro AI line has treated persistent state, relation structure, selective communication and recurrence as candidate carriers of system-level capability. A new convergence across fungal networks, single-cell regeneration/learning and epigenetic regulation suggests a sharper experimental distinction:

```text
G = generative repertoire / grammar
M = latent regulatory or relational memory
P = currently expressed phenotype / active organization
E = compatible execution substrate
```

The central hypothesis is not that AI is biologically equivalent to fungi, ciliates or genomes. It is narrower:

> **An adaptive system may preserve less than its active phenotype while retaining enough history to bias what useful organization is regenerated next.**

Operationally:

```text
P may be destroyed
while G + M survive

G + M + E + consequence -> P'
```

The discriminating control is:

```text
G + E + consequence -> P'
```

A retained state counts as regulatory memory only if it changes reacquisition relative to a matched fresh condition after the active organization itself has been removed.

A compact formal statement is:

```text
P(O | G, E, H) != P(O | G, E)
```

where `H` is prior interaction history and `O` is future organization. A useful memory effect requires more than inequality: the historical trace must improve reacquisition of a previously useful phenotype under controlled cost and information budgets.

---

## 1. Mycelial memory after a relation disappears

Fukasawa, Savoury and Boddy studied the cord-forming fungus *Phanerochaete velutina*. Mycelial networks first grew from an inoculum toward wood resources. After prior outgrowth was removed and the original inoculum was relocated to fresh soil, subsequent growth remained biased by prior growth/resource history. The paper frames the result as ecological memory affecting later relocation decisions while discussing possible underlying somatic and structural mechanisms.

External source:

- Fukasawa Y, Savoury M, Boddy L. "Ecological memory and relocation decisions in fungal mycelial networks: responses to quantity and location of new resources." *The ISME Journal* 14, 380–388 (2020). DOI: `10.1038/s41396-019-0536-3`.

The useful abstraction is:

```text
active relation R
-> interaction history modifies persistent state
-> R is destroyed
-> future organization remains biased by that history
```

This separates:

```text
R   = the active relation itself
M_R = a persistent disposition produced by the history of R
```

For Mesh / Neuro AI this motivates a stronger question than persistence of topology:

> Can a relation be completely removed while a much smaller state trace still changes how quickly or reliably an equivalent useful organization is rediscovered?

That is a different claim from checkpointing the relation itself.

---

## 2. Stentor: generative information and structural organization are separable

*Stentor coeruleus* is a large single-celled ciliate with an unusual capacity for regeneration. Experimental and review literature shows that cell fragments can regenerate a complete, proportioned organism when they retain sufficient macronuclear material and a patch of the original cortex. The cortex is not merely an outer container; ciliates possess cortical patterning with self-assembly, self-propagation, repair and regeneration properties.

External sources:

- Slabodnick MM, Marshall WF. *Stentor coeruleus* overview, PMCID `PMC5036449`.
- "Methods for the Study of Regeneration in Stentor", PMCID `PMC6101732`.
- "Anterior–posterior pattern formation in ciliates", PMCID `PMC9309198`.

The structural distinction is:

```text
generative/nuclear information alone != regenerated phenotype
structural organization alone          != regenerated phenotype

sufficient generative information
+ sufficient organization
-> regeneration
```

This resembles a result already isolated in Synapse Lab's minimum-continuity experiments: learned selection state did not preserve phenotype if the semantic/operator binding was corrupted. Correct state plus correct organizational semantics did.

This is only an architectural analogy. Nuclear DNA, ciliate cortex and digital relation-state are not claimed to share a mechanism.

---

## 3. Stentor: learning and persistence through division

*Stentor* also provides a clean warning against equating learning with nervous systems. Habituation experiments show that a single cell can reduce response to repeated non-harmful stimulation while retaining responses to relevant stimuli. Rajan et al. (2026) identified roles for calcium signaling and protein phosphorylation and reported maintenance of habituation memory in progeny following cell division.

External source:

- Rajan DH et al. "Molecular pathways for learning in the single-cell Stentor coeruleus." *Current Biology* (2026). PMID `42025171`. DOI: `10.1016/j.cub.2026.03.080`.

The result does not establish cognition equivalent to an animal nervous system. For the present research line it establishes a useful pattern:

```text
experience
-> persistent response disposition
-> major structural transition / division
-> disposition remains measurable
```

This motivates a future lineage falsifier in Synapse Lab:

```text
learn
-> destroy parent runtime
-> regenerate child on fresh substrate
-> destroy child runtime
-> regenerate child2
-> measure persistence / decay / interference
```

---

## 4. Epigenetic memory: same generative repertoire, different phenotype

In multicellular organisms, differentiated cells largely share the same genome while regulatory and epigenetic state changes which programs are accessible and expressed. Relevant mechanisms include chromatin state, DNA methylation, histone state, mitotic bookmarking and primed/poised regulatory elements.

External sources:

- Dobreva et al., work on epigenetic memory of cell-fate commitment, PMID `33535129`.
- Puri et al., "High-wire act: the poised genome and cellular memory", PMID `25440020`.
- Crispatzu et al., "The chromatin, topological and regulatory properties of pluripotency-associated poised enhancers are conserved in vivo", *Nature Communications* (2021), PMID `34272393`.

The relevant abstraction is:

```text
generative repertoire != expressed phenotype

same repertoire
+ different regulatory state
-> different expressed phenotype
```

This converges structurally with the controlled relational-phenotype experiments:

```text
same fixed model / same candidate relations
+ different learned relation-state
-> different capability phenotype
```

The claim is not that learned human memories are stored in DNA or inherited genetically. The relevant comparison is regulatory accessibility and persistent state, not genetic encoding of experience.

---

## 5. Latent capability: inactive does not mean useless

The biological comparison becomes more useful when combined with X² R21 in `nsolland/synapse-lab`.

R21 compared three bounded construction policies under the same finite Boolean grammar:

```text
BLIND
GREEDY immediate fitness
RELATIONAL DIVERSITY
```

For a preregistered rule-derived discriminator family, GREEDY spent more target feedback but pruned lower relations that had poor isolated fitness and were nevertheless necessary ingredients for later exact compositions. RELATIONAL DIVERSITY retained those low-current-value relations and recovered the target family.

Controlled R21 result:

```text
BLIND:      3/3 exact
GREEDY:     0/3 exact
DIVERSITY:  3/3 exact
```

Some required lower relations had isolated immediate fitness only `0.125` and ranked near the bottom of the greedy list.

Narrow result:

> **Current isolated utility is not equivalent to latent compositional capability in this finite system.**

This gives a computational reason to preserve some presently inactive or weakly useful relational state: it may be a prerequisite for later capability even when immediate local scoring says otherwise.

This is relevant to the epigenetic/poising analogy, but is not evidence of biological epigenetics.

---

## 6. X² RM1: direct regulatory-memory falsifier

The biological convergence above was converted into a preregistered Synapse Lab experiment rather than left as analogy.

Repository: `nsolland/synapse-lab`  
PR: `#33` — `experiment: X² regulatory memory RM1`  
Dedicated Actions run: `32410102961`  
Job: `96558273937`  
General Fractal World run: `32410103171` — SUCCESS  
Artifact: `9421787536`  
Artifact ZIP SHA-256: `206b81357f02c0905d769176af0fbc0dc06d0c91fb244428bd2c60e5cbf460bd`  
Classification: `LATENT_REGULATORY_TRACE_ACCELERATES_REACQUISITION`

### Destruction boundary

After a first lifecycle had learned an exact relational program, RM1 destroyed:

- the active program;
- constructor state;
- reward history and reward magnitudes;
- runtime/world state;
- runtime/node identity;
- active topology.

The only learning object allowed to survive was:

```text
31-bit poised-relation mask
serialized as exactly 4 bytes
maximum 4 marked lower relations
```

The retained trace contained no:

```text
target id
target truth table
final program text
operand order
reward rates/counts
runtime identity
active topology
relation utility magnitudes
```

The trace was allowed to alter only fresh candidate evaluation order. It could not alter candidate semantics, grammar, reward channel, bind threshold or final validation.

### Controls and result

| Condition | Total candidates to exact reacquisition | Accepted one-bit rewards | Median candidates |
|---|---:|---:|---:|
| SCRATCH | 56 | 1,344 | 22 |
| ERASED_TRACE | 56 | 1,344 | 22 |
| MATCHED_TRACE | **4** | **96** | **1** |
| SHUFFLED_TRACE | 104 | 2,496 | 42 |
| WRONG_TARGET_TRACE | 71 | 1,704 | 33 |

Per target:

```text
scratch -> matched
22 -> 2
33 -> 1
 1 -> 1
```

All matched conditions reacquired the exact target and validated at `1.00` transported capability. Direct visibility remained zero. Target-labelled candidate payload leakage remained zero. Delayed/out-of-order consequence and deliberate corruption of one genuine correct reward were retained.

The matched trace therefore reduced reacquisition candidate evaluations and accepted consequence bits by `14x` versus scratch in this finite controlled experiment.

Critical accounting boundary:

> This is a reacquisition/retention effect only. It does not include the cost of the previous lifecycle that formed the trace and must not be reported as a 14x reduction in total lifetime learning cost.

---

## 7. What RM1 now supports

The narrow project statement is:

> **A previous functional phenotype can be deleted while a much smaller latent relational disposition survives and measurably biases what organization is reacquired next.**

The tested operational definition is therefore supported in this bounded setting:

```text
memory = bias over future regeneration
```

This is materially different from storing the old program or topology.

The matched trace was only a small set of poised relation identities. It did not preserve the final AST or operand ordering. Fresh computation still had to instantiate and evaluate candidate programs through consequence.

---

## 8. Relationship to Framleis

Framleis asks what must remain invariant for identity/function to persist through transformation.

The earlier continuity experiments localized some necessary invariants to relation-state and semantic binding. RM1 adds another possibility:

> The invariant need not always be the previously expressed organization itself. It may be a much smaller regulatory disposition that changes how future organization is reconstructed.

This suggests a hierarchy of persistence:

```text
active phenotype P
    can disappear

latent regulatory memory M
    may persist

generative repertoire G
    remains available

compatible substrate E
    supplies execution

G + M + E + consequence
    regenerates P'
```

This is a candidate mechanism for invariant-preserving transformation. It is not a validation of the universal Framleis / Phi-law equation or its spectral metrics.

---

## 9. Relationship to Mycelium / Mesh Neuro AI

The existing Mesh / Neuro AI hypothesis already cites Mycelium / active shared context graphs and asks for the minimum sufficient state transfer between nodes.

RM1 adds a different minimum-state problem:

```text
minimum transmissible online state
!=
minimum persistent continuity state
!=
minimum latent regulatory memory
```

The last object is not necessarily sent between active nodes at all. It may be dormant until a later reconstruction event.

The resulting architecture candidate is:

```text
local compute
+ generative grammar
+ active relational substrate
+ latent regulatory traces
+ consequence
```

where active state and latent state are explicitly different classes.

---

## 10. New falsifiers

RM1 is deliberately narrow. The next useful attacks are:

1. **Trace-size ablation:** `4 marks -> 3 -> 2 -> 1 -> 0`; locate the minimum trace that still beats scratch.
2. **Online-local trace formation:** remove the current peak-participation summary and require traces to form from strictly local online updates.
3. **Dormant trace only:** carry only the four bytes through a cold-dormancy boundary onto disjoint substrate.
4. **Lineage:** repeat regeneration over multiple generations carrying only latent trace; measure persistence, decay and interference.
5. **Environment reversal:** make prior trace maladaptive; require extinction/rewrite rather than lock-in.
6. **Cross-target matrix:** quantify positive transfer, neutral transfer and interference between traces.
7. **Storage-matched recipe control:** compare the latent trace against the best explicit compressed program/recipe allowed the same storage budget.
8. **Richer task family:** move beyond finite Boolean truth-function catalogs.

A particularly strong future result would be:

```text
old phenotype destroyed
old topology destroyed
runtime destroyed
only tiny latent trace survives
new environment resembles old problem
fresh substrate reconstructs useful organization faster than scratch
old trace is rewritten when environment changes
```

That would still be computational regulatory memory, not biological epigenetics.

---

## 11. Claim boundary

Do not claim from this synthesis or RM1 that:

- X² is alive;
- the trace is literally a genome or epigenome;
- fungi, Stentor and X² share a physical mechanism;
- human learned memories are encoded in latent DNA;
- biological heredity has been reproduced;
- consciousness or autonomous purpose has emerged;
- open-ended learning or general intelligence has been demonstrated;
- Phi Law has been universally validated.

The supported insight is more useful because it is narrower:

> **Persistent memory can be experimentally operationalized as a learned, compact change in the future reconstruction landscape after the previously expressed organization is gone.**
