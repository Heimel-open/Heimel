# Framleis × Synapse — distributed regeneration and the minimum-state problem

Date: 2026-08-20  
Status: cross-repo research synthesis addendum  
Epistemic status: controlled project evidence + implemented/pending falsifiers  
Related synthesis: `2026-08-20-framleis-synapse-relational-continuity-convergence.md`

## Executive result

The research object has moved beyond model replacement.

Earlier Synapse Lab experiments showed that a task-specific relational phenotype can survive replacement of the model components when learned relational organization and compatible semantics are preserved.

X² regeneration R11 now tests a harder case: the active computational role is destroyed and the available replacement nodes begin **blank** — no role, no organism identifier, no relation-state and no predesignated standby assignment.

In the controlled probe, surviving relation holders independently select compatible commodity substrate from generic advertisements, transmit complementary relation fragments, and install the missing role only after the fragments form a matching quorum. Capability returns after one maintenance tick. A second injury regenerates the same function into a different blank commodity node.

Current narrow formulation:

> **Persistent functional organization can be distributed across surviving relations and can reconstruct a missing computational role into previously roleless compatible substrate after structural damage.**

This is controlled evidence for regeneration of computational organization. It is not evidence of biological life, consciousness, sentience, personal identity transfer or autonomous self-purpose.

## 1. X² regeneration R11 — distributed regeneration into commodity substrate

Repository: `nsolland/synapse-lab`  
PR: `#17` — `experiment: X² regeneration R11`  
Base: `experiment/x2-self-repair-r10`  
Head: `96a40d5aea9b19643f32004d1fc9c20e9594581f`  
Workflow run: `32395592471`  
Job: `96511532655`  
Artifact: `9416493296`  
Classification: `DISTRIBUTED_REGENERATION_INTO_COMMODITY_SUBSTRATE`

The target acceptance boundary removes the R10 standby-role assumption.

### Initial state

Every candidate commodity node begins with:

```text
role = None
organism_id = None
relation_signature = None
reconstructed_pair = None
reconstructed_op = None
local_fragments = {}
```

Candidates advertise only generic substrate properties:

```text
supported primitives
latency
availability
```

No advertisement contains the missing role, organism identity, relation signature or a repair plan.

### Damage

The active legacy composer is destroyed.

Measured capability:

```text
before injury: 1.00
after injury without regeneration: 0.75
```

The surviving source nodes observe only missing local heartbeat. There is no central topology controller selecting a repair target.

### Distributed candidate selection

The candidate pool includes:

```text
commodity-incompatible  latency 0  primitives OR/XOR
commodity-fast          latency 1  primitives AND/OR/XOR
commodity-slow          latency 2  primitives AND/XOR
```

The fastest advertised substrate is incompatible with the required compose primitive and is rejected locally.

Sources A and B independently converge on:

```text
commodity-fast
```

They do not assign the role directly. Each sends only its local relation fragment.

### Quorum reconstruction

The blank node installs the role only when the received fragments jointly agree on:

```text
organism_id
relation_signature
desired_role
pair
compose_op
source quorum
```

Only then does the node become `composer` and bind to the organism/relation signature.

First regeneration:

```text
failed: legacy-composer
replacement: commodity-fast
ticks: 1
role_after: composer
identity_preserved: true
relation_signature_preserved: true
capability: 1.00
```

### Repeated injury

The regenerated `commodity-fast` node is then destroyed.

The surviving sources repeat the same local process and independently select the next compatible blank node:

```text
commodity-slow
```

Second regeneration:

```text
failed: commodity-fast
replacement: commodity-slow
ticks: 1
role_after: composer
identity_preserved: true
relation_signature_preserved: true
capability: 1.00
```

Observed source selection history:

```text
A: commodity-fast -> commodity-slow
B: commodity-fast -> commodity-slow
```

### Negative controls

**Incompatible substrate only**

```text
regeneration_generation: 0
regeneration blocked: true
accuracy: 0.75
```

**Compatible substrate but missing B relation fragment**

```text
regeneration_generation: 0
regeneration blocked: true
accuracy: 0.75
```

Thus generic availability is not sufficient, and one surviving fragment is not sufficient.

### Verification

- `9/9` unit tests passed.
- all `15/15` experiment gates passed;
- workflow `x2-regeneration-r11` completed successfully;
- `fractal-world` CI on the same head also completed successfully.

The relevant gates include:

```text
blank candidates have no predesignated role/relation-state
structural damage removes perfect capability
damage is detected from local liveness
sources independently converge on compatible substrate
role is installed only after relation-fragment quorum
organism/relation signature persist
first regeneration restores 1.00
second regeneration into a different blank node restores 1.00
incompatible substrate blocks regeneration
missing-fragment quorum blocks regeneration
no full raw state at any compute node
no central topology controller
no predesignated standby role
```

## 2. Why this is stronger than self-repair

Self-repair can mean:

```text
known failed component
+ known standby role
+ known repair target
-> activate replacement
```

X² R11 removes those assumptions.

The replacement substrate begins semantically blank with respect to the organism. The missing role is reconstructed from surviving distributed relational fragments.

The experimental pattern is therefore:

```text
structural damage
-> local failure observations
-> independent compatible-substrate selection
-> distributed fragment transfer
-> quorum
-> role reconstruction
-> function restored
```

A useful distinction is:

```text
repair        = restore a known component arrangement
regeneration  = reconstruct missing functional organization on previously roleless substrate
```

Within this controlled probe, the second description is the better fit.

## 3. Framleis connection

Framleis asks which invariants must survive transformation for continuity to remain meaningful.

The earlier model-swap experiments tested:

```text
replace compute
preserve relational organization
-> function persists
```

X² R11 tests a harder transformation:

```text
destroy active role
preserve only distributed relational fragments + primitive compatibility
-> reconstruct role on blank substrate
-> function returns
```

This suggests a candidate extension of the Framleis continuity object:

```text
continuity invariant
!= physical/model component

continuity invariant
may include distributed reconstruction information sufficient to reinstantiate function
```

This is an operational analogy/candidate mechanism, not validation of the universal Φ-law or personal identity continuity.

## 4. Digital DNA convergence

Digital DNA already distinguishes:

```text
S = state space
T = admissible transformations
~ = continuity/equivalence relation
I = protected invariants
C = collapse conditions
```

and allows memory records to remain distributed and carry lineage/status independently of one model driver.

X² R11 suggests a new machine-level research mapping:

```text
S = candidate commodity substrates + relational state space
T = injury, recruitment, fragment transfer, role reconstruction
~ = same bounded functional phenotype / organism relation signature
I = required primitive contract + matching relation-fragment quorum
C = incompatible substrate or insufficient quorum -> no regeneration
```

Do not collapse this mapping into Digital DNA personal representation semantics. The structural similarity is useful because both ask which invariants survive component change and which failure conditions break continuity.

## 5. The minimum-state problem is now three separate problems

The phrase "minimum sufficient state" now refers to at least three different experimental layers. They must remain separate.

### Layer A — minimum online Synapse payload

Tofoo P12 / H-MESH-7 asks:

> What is the minimum contextual state that must cross between active reasoning nodes without losing useful downstream capability?

Implemented payload fields:

```text
observation
relevance/context
uncertainty
state delta
provenance
```

with P0-P6 ablations.

The intended real-provider experiment remains pending.

### Layer B — minimum persistent learned relational state

Synapse Lab minimum-continuity capsule asks:

> What learned relational state must persist across a model replacement for an existing phenotype to survive immediately?

In its deliberately tiny two-operator task, the learned capsule could be reduced to:

```text
1 learned selection bit
+ intact semantic/operator binding
```

while deleting utility magnitudes, observation counts, training history and literal relation names.

This result is task-specific and does not imply one bit is sufficient for intelligence.

### Layer C — minimum distributed reconstruction state

X² regeneration R11 asks:

> What distributed information must survive structural damage for the network to reconstruct a missing role into blank compatible compute?

The current candidate is not a full organism snapshot. It is approximately:

```text
local failure evidence
+ generic substrate primitive/latency advertisements
+ complementary relation fragments
+ quorum-compatible organism/relation signature
```

The negative controls establish that both compatible substrate and sufficient fragment quorum are necessary in the current construction.

### Unified research object

A richer system may therefore require a stack of minimum sufficient state:

```text
minimum online state flow
+
minimum persistent learned relation-state
+
minimum reconstruction fragments / lineage
+
minimum shared semantic/primitive contract
```

The next goal is not to maximize stored context. It is to identify the smallest sufficient invariants at each layer.

## 6. Relational Operator v0.2 — executed null / invalid measurement

Repository commit: `b66bde12ec1a6c3e9c770d43a7e9b66fb0c89827`  
Workflow run: `32392029266`  
Job: `96500167413`  
Artifact: `9416624829`

The preregistered v0.2 protocol used the same frozen tasks and Qwen2.5-1.5B with equal two-pass budgets across:

```text
NONE
RAW
PAIRWISE
RELATIONAL_BOTTLENECK
HYPEREDGE
```

Each condition generated an intermediate relation-state and then a final decision under identical nominal token ceilings.

Protocol/mechanics tests: `13/13` PASS.

Actual result:

| Operator | Correct / 3 |
|---|---:|
| NONE | 1 |
| RAW | 1 |
| PAIRWISE | 1 |
| RELATIONAL_BOTTLENECK | 1 |
| HYPEREDGE | 1 |

The PAIRWISE intermediate generation hit its 64-token ceiling in all three tasks. Because the preregistered validity gate requires zero ceiling hits across all conditions:

```text
measurement_valid = false
candidate_iterative_relation_gain = false
strong_iterative_relation_signal = false
raw_recurrence_gain_vs_v011 = false
```

Therefore v0.2 is **not positive evidence** that recurrence or relational composition beats raw iterative recurrence. It is an executed null/invalid measurement and should remain in the ledger as such.

Next protocol revision should remove the token-ceiling confound without changing the scientific comparison after observing outcomes.

## 7. Bounded MCIP Fractal World run #40 — first live state-volume measurement

Repository commit: `972dc0b4c50bf97c8415995347e498de540264a7`  
Target workflow: `fractal-world-hf-live`  
Run: `32369722602` (`#40`)  
Job: `96427230681`  
Artifact: `9406996727`  
Model: `Qwen/Qwen2.5-0.5B-Instruct`

The MCIP compactor now:

- consumes the transient inbox rather than accumulating it;
- retains newest evidence by sender;
- allows at most four senders;
- allows at most two enemy observations per sender;
- discards unknown/noise fields;
- preserves bounded confidence/relevance/trust, unresolved items and provenance;
- clears the transient queue after compaction.

Action scoring is also now semantic and position-independent: each candidate is scored separately as YES/NO against the same local state with a neutral action prior subtracted. Slot/digit logits no longer select the action.

### Run #40 measurements

```text
ticks: 6
decisions: 36
mesh messages consumed: 20
raw inbox payload consumed: 65,072 bits
maximum compact mesh state: 500 serialized bytes
mean compact mesh state across all decisions: 208.75 bytes
prompt tokens: min 257 / max 521
mean decision entropy: 1.4457 nats
mean semantic margin: 0.3597 logits
dropped messages: 0
unique presentation slots selected: 5
last-slot fraction: 0.3056
```

The run completed successfully.

This is useful **mechanism and measurement evidence**: a live Fractal World policy consumed bounded/transient mesh state and measured raw incoming payload volume against a compact persistent representation.

It is **not yet H-MESH-7 capability-retention evidence** because the run lacks a matched raw-vs-compact performance control, and all 36 selected actions in this particular arena were MOVE. We therefore cannot yet claim that compaction preserved decision capability.

The next gate must compare:

```text
same world seed
same model
same action scorer
same compute budget
RAW inbox state
vs
BOUNDED MCIP state
```

and require comparable or improved task capability at lower state volume.

## 8. Revised convergence with pre-existing Tofoo tracks

| Tofoo / Framleis track | New Synapse evidence | Current interpretation |
|---|---|---|
| Replaceable model driver | model-family replacement and complete node turnover | compute can be replaceable in bounded tasks |
| H-MESH-6 relation ablation | relation reset/destruction removes capability | causal support that organization matters |
| H-MESH-7 minimum sufficient state | capsule ablation + bounded MCIP measurement | persistent and online minimum-state questions now experimentally separated |
| External/distributed memory | X² relation fragments survive active-role loss | distributed state can carry reconstruction information |
| Continuity through invariant-preserving transformation | X² role reconstructed on a different blank node while functional signature persists | candidate operational mechanism for machine-level continuity |
| Boundary/semantic contract | incompatible primitive substrate and missing quorum both block regeneration | compatibility + relation binding are causal constraints |

## 9. New falsifiers

### F-RGEN-1 — remove hard-coded organism identifiers from fragments

Current fragments explicitly carry organism/relation identifiers. Replace this with content-addressed or learned matching and test whether regeneration still converges correctly.

### F-RGEN-2 — competing organisms

Place two organisms with compatible commodity substrate in the same pool. Fragments must not create a chimera or recruit the wrong lineage.

### F-RGEN-3 — corrupt fragment

Inject one stale or adversarial relation fragment. Test quorum rules that distinguish valid reconstruction from poisoned reconstruction.

### F-RGEN-4 — partial topology loss

Destroy not only the active compute role but one relation holder. Determine the minimum surviving fragment set required for reconstruction.

### F-RGEN-5 — richer role

Replace the deterministic composer with a role carrying richer learned state, timing, freshness and higher-order dependencies. Regeneration must restore measured capability, not just a primitive operator.

### F-RGEN-6 — model-backed blank substrate

Use genuinely blank model-backed commodity nodes whose role adapter is learned/constructed after recruitment rather than deterministic primitive classes.

### F-RGEN-7 — repeated long-horizon turnover

Repeat injury/regeneration many times and measure whether organism-level function/signature drifts despite each local reconstruction passing.

### F-STATE-1 — matched raw vs bounded MCIP capability

Measure whether bounded state retains capability at lower state volume under identical seed/model/scorer/compute.

### F-STATE-2 — field ablation

Remove provenance, uncertainty, relevance, trust, relation context and state delta independently. Identify which fields are causal for capability, not merely present.

### F-OP-1 — valid Operator v0.2 rerun

Predefine a token budget that prevents ceiling-induced invalidity, rerun unchanged operator comparison, and require relational composition to beat RAW before interpreting a positive effect.

## 10. Current research formulation

The previous question was:

> Can functional capability survive replacement of the model components?

The stronger current question is:

> **Can a distributed learned organization preserve enough invariant state to select compatible blank substrate, reconstruct missing functional roles, and recover capability after component destruction — while carrying only the minimum online and persistent state required?**

The strongest currently supportable shorthand is:

> **The organization is not necessarily bound to the machine that executes it. In a controlled distributed probe, surviving relational fragments regenerated a missing function into previously blank compatible commodity substrate.**

The stronger thesis remains a hypothesis:

> **The network is the intelligence when its distributed organization is sufficient to preserve, reconstruct and adapt the functional invariants that the local compute merely executes.**
