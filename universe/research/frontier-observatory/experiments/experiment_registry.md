# Φ-law experiment registry

Canonical source for Φ-law / LIM validation experiments and prediction protocols.

Purpose: prevent drift between README, manifesto, context and notebooks.

---

## Status labels

| Status | Meaning |
|---|---|
| PLANNED | protocol proposed but not yet run |
| DONE | completed in project workstream |
| DOCUMENTED | completed and documented in repo / notes / notebook |
| ACTIVE | current work in progress |
| REPLICATED | independently reproduced |
| DEPRECATED | replaced by newer protocol |

Important:

```text
DONE does not mean independently replicated.
```

---

## Claim maturity labels

| Label | Meaning |
|---|---|
| M0 Symbolic | mythic, narrative or cultural claim |
| M1 Conceptual | philosophical or architectural claim |
| M2 Formal | mathematically or formally specified |
| M3 Simulated | tested in simulation or toy model |
| M4 Empirical | tested on real data or working system |
| M5 Replicated | independently reproduced |
| M6 Standardized | adopted into protocol, standard or practice |

---

## Registry

| Protocol | System | Status | Maturity | Artifact / note | Current result summary |
|---|---|---|---|---|---|
| P1 | LLM coherence / GPT-2 | DONE / DOCUMENTED | M3/M4 | `P1_LLM_LIM_Test/` | tau stabilizes with LIM; unfiltered run drifts |
| P2 | REM / sleep / navigation | DONE | M1/M3 | project notes / pending artifact registry | REM/filter hypothesis evaluated in workstream |
| P3 | Human feedback / WCST | DONE | M1/M3 | project notes / pending artifact registry | feedback/perseveration hypothesis evaluated in workstream |
| P4 | Economic / flash-crash simulation | DONE | M3 | project notes / pending artifact registry | regulation/filter hypothesis evaluated in simulation workstream |
| P5 | Swarm coherence | DONE / DOCUMENTED | M3 | `P5_Swarm_Coherence/` | 100-agent coherence stabilized with Φ-law; no-filter collapse observed |
| P6 | MECHA / governance verification | DONE / DOCUMENTED | M2/M3 | MECHA / TLA+ notes | v1.1 holds; v1.0 bug exposed missing veto check |
| P7 | K-measurement GPT-2 / Neo | DONE | M3/M4 | context + notebooks / pending artifact registry | K_spectral measured for GPT-2 and Neo variants |
| P8 | Lambda + Neo-2.7B | DONE | M3 | context + notebooks / pending artifact registry | Lambda/C0_outer relationship evaluated |
| P9 | Two-level Colab | DONE | M3 | context + Colab / pending artifact registry | two-level structure evaluated; C0_outer Neo result recorded |
| P10 | Transformer workspace dynamics / tau / J-space | ACTIVE / DOCUMENTED protocol | M2 implemented protocol; empirical sweep pending | `P10_Transformer_Workspace_Dynamics/` + `../docs/theories/2026-08-10-jspace-framleis-adaptive-cognitive-sweep.md` | J-space corrected to sparse workspace/readout rather than transition mechanism; deterministic adaptive-sweep falsifier and synthetic mechanics tests added; empirical J-lens + tau run pending |
| P11 | Discrete–continuous closed-loop coupling | PLANNED / DOCUMENTED | M1/M2 protocol | `research/2026-07-26-discrete-continuous-closed-loop-hypothesis.md` | Test whether bidirectional micro/macro coupling with LIM preserves identity better than disconnected controls |
| P12 | Synapse / relational understanding + minimum state transfer | PLANNED / DOCUMENTED | M2 implemented protocol | `P12_Synapse_Test/` + `P12_Synapse_Test/p12_payload_ablation.py` + `../notebooks/P12_Synapse_Colab.ipynb` | Runnable relational-understanding protocol plus P0-P6 causal payload-ablation mechanics; intended real-provider empirical run remains pending |

---

## Parallel Synapse Lab evidence — not a P12 result

The following controlled project evidence lives in `nsolland/synapse-lab`. It is relevant to P12 / Mesh / Framleis hypotheses but **must not be counted as an empirical P12 provider result or as independent replication of Φ-law claims**.

Canonical synthesis:

- `../docs/theories/2026-08-20-framleis-synapse-relational-continuity-convergence.md`
- `../docs/theories/2026-08-20-framleis-synapse-regeneration-and-minimum-state.md`

Current cross-repo evidence includes:

```text
minimum learned continuity capsule:
  in a bounded two-operator task, cross-model phenotype continuity survived
  with one learned selection bit + intact semantic/operator binding;

complete gradual model replacement:
  a constructed higher-order organism retained 1.00 function while all model
  nodes were replaced one at a time with frozen relation-state;

X² regeneration R11:
  after structural loss of the active compute role, surviving distributed
  relation fragments reconstructed the role into previously blank compatible
  commodity substrate; capability returned from 0.75 to 1.00 in one tick;
  repeated injury regenerated into a different blank node; incompatible
  substrate and missing-fragment controls blocked regeneration;

Relational Operator v0.2:
  executed successfully but measurement_valid=false because the PAIRWISE
  relation-state hit the preregistered token ceiling; no relational > RAW gain
  may be claimed from this run;

bounded MCIP Fractal World #40:
  live measurement consumed 65,072 raw inbox bits with bounded compact mesh
  state <= 500 serialized bytes per decision, but no matched RAW-vs-compact
  capability control exists yet, so H-MESH-7 capability retention is unproven.
```

The cross-repo evidence sharpens three distinct minimum-state questions:

```text
A. minimum online payload between active nodes (P12 / H-MESH-7)
B. minimum persistent learned relation-state across component replacement
C. minimum distributed reconstruction state after structural damage
```

Do not merge these into a single metric without an experiment that manipulates all three.

---

## Current canonical statement

Use:

```text
P1-P9 are completed in the project workstream. P10 is active with an implemented J-space/tau falsification protocol. P11 is planned. P12 is implemented, including its payload-ablation mechanics, and is awaiting the intended empirical provider execution. Related Synapse Lab continuity/regeneration experiments are tracked separately as cross-repo project evidence.
```

Do not use:

```text
Only five predictions exist.
```

Do not use:

```text
P1-P9 are independently replicated.
```

Do not use:

```text
Synapse Lab R11/R12/X² R11 means P12 has empirically passed.
```

unless the intended P12 provider experiment itself is executed and registered.

---

## Falsification field to add per protocol

Each protocol should eventually include:

```text
Hypothesis:
Measurement:
Control:
Expected LIM result:
Expected no-filter result:
Falsification condition:
Artifact path:
Replication status:
```

P10's J-space extension uses a protocol-specific structure because it tests workspace-selection dynamics rather than LIM/no-filter alone. Its required distinctions are:

```text
BROAD_SCAN
vs TARGET_LOCK
vs DISCONFIRMING_SWEEP
vs UNCERTAINTY_MAP
vs repeated CANDIDATE_SET
```

with matched lexical/task controls, non-J-space controls where available, raw J-space coordinates, and independent tau measurement.

P12 uses a protocol-specific control structure because the tested variable is relational architecture rather than LIM/no-filter alone. Its required comparison is:

```text
single node
vs isolated ensemble
vs sequential chain
vs structured Synapse
vs relational ablations/randomization
```

with equal model, source and controlled API generation budgets. Actual token usage is retained per call.

Its minimum-state extension additionally requires:

```text
P0 full/raw transferable context
P1 contextualized state delta
P2 compressed contextualized state delta
P3 without provenance
P4 without uncertainty
P5 without relevance/relation context
P6 randomized/irrelevant transfer control
```

with shared upstream node calls so the causal variable is the transferred payload.

---

## Related interpretive notes

- `notes/2026-06-30-quantization-fim-and-half-automata.md` — connects arXiv:2606.28432, quantization/FIM perturbation and the half-automata hypothesis as a possible explanatory frame for P1-P9. Status: interpretive hypothesis, not proof.
- `../docs/theories/2026-08-20-framleis-synapse-relational-continuity-convergence.md` — cross-repo mapping from pre-existing Framleis/P12 hypotheses to controlled relational-continuity evidence.
- `../docs/theories/2026-08-20-framleis-synapse-regeneration-and-minimum-state.md` — distributed regeneration, three-layer minimum-state decomposition, Operator v0.2 null result and bounded-MCIP measurement.

---

## Known drift to patch

README currently says five falsifiable predictions.
Manifesto currently says P1-P6.
Context says P1-P9 done and P10 next.

Canonical update should be:

```text
P1-P9 completed; P10 active with implemented workspace falsification protocol; P11 planned; P12 implemented including minimum-state payload ablation, empirical provider run pending; parallel Synapse Lab continuity/regeneration evidence tracked separately.
```

Patch README and manifesto after artifacts/paths for P2-P4 and P7-P9 are mapped.
