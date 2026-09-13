# NVIDIA AVO × Tofoo — long-horizon capability, lineage and challengeable wisdom

Date: 2026-08-22  
Status: `ADOPTED_RESEARCH_CONVERGENCE`  
Production adoption: **not authorized**

## External evidence

Primary sources:

- NVIDIA Technical Blog, “NVIDIA AVO Reaches 100% on ARC-AGI-3, Demonstrating a Frontier-Level General-Purpose Architecture for Long-Horizon Autonomous Agents” (2026-08-21): https://developer.nvidia.com/blog/nvidia-avo-reaches-100-on-arc-agi-3-demonstrating-a-frontier-level-general-purpose-architecture-for-long-horizon-autonomous-agents/
- Chen et al., “AVO: Agentic Variation Operators for Autonomous Evolutionary Search” (2026-03-25): https://arxiv.org/abs/2603.24517

NVIDIA reports that the same AVO agent architecture was applied across GPU-kernel optimization and ARC-AGI-3 with persistent memory, tool use, execution feedback, recovery, supervision and lineage. On the ARC-AGI-3 public set it completed all 183 levels across 25 environments with a 100.00 RHAE score. NVIDIA explicitly cautions that comparisons against model-only or other harness results are not controlled ablations.

The paper describes AVO as an agentic variation operator that can consult current lineage, domain knowledge and execution feedback to propose, repair, critique and verify candidate changes.

## What Tofoo adopts

### 1. Long-horizon capability is a system property

Adopt as external convergence:

> **The model is not the whole agent. Long-horizon capability emerges from the interaction of model, persistent state, tools, feedback, recovery, supervision and context management.**

This is compatible with the existing Tofoo/Synapse distinction between local model capability and persistent relational/harness state.

### 2. Lineage is computational state

Adopt:

```text
candidate
→ branch / variation
→ execute
→ evidence
→ retain / reject
→ lineage update
→ next candidate
```

Lineage is not merely audit metadata. In long-horizon systems it can become part of the computational substrate because prior variants, outcomes and failed directions change what the system explores next.

This is directly relevant to Tofoo’s provenance, clone/fork/merge, protected/latent state and identity-continuity work.

### 3. Agentic variation is a reusable research mechanism

Adopt AVO-style variation as a reference pattern for research search:

- candidate generation may be agentic rather than fixed;
- variants should be evaluated through grounded execution feedback;
- failed candidates should remain available as negative evidence;
- the committed state should remain distinct from exploratory candidate state;
- lineage should preserve how capability changed, not only the winning artifact.

This complements the existing guarded-plasticity rule:

> **Form the invariant. Protect it. Explore around it. Commit only what survives retention. Forget only what is safe to forget.**

### 4. Generality may come from machinery that compounds reasoning and feedback over time

NVIDIA’s broader interpretation is adopted as external convergence, with an explicit Tofoo correction:

> **Capability compounds through experience. Wisdom requires that what compounds remains challengeable.**

The first sentence captures AVO’s long-horizon accumulation mechanism. The second is the Tofoo constraint introduced by the Experience → Learning → Wisdom lifecycle.

Accumulation alone is not wisdom.

## Tofoo correction: persistent memory is not wisdom

AVO provides strong evidence for the value of persistent memory and carried-forward understanding, but Tofoo must not collapse:

```text
persistent memory
=
learning
=
wisdom
```

The canonical Tofoo distinctions remain:

```text
experience != memory
memory != learning
learning != wisdom
```

A persistent strategy can remain:

- overfit;
- stale;
- outside its original scope;
- reinforced by biased feedback;
- protected only because it previously succeeded;
- increasingly influential without current legitimacy.

Therefore any AVO-like accumulated state that is allowed to influence future decisions should remain inspectable through at least:

- provenance;
- supporting evidence;
- counterevidence;
- scope and exclusions;
- credibility history;
- last challenge / renewal state;
- amendment history;
- revocation or challenge triggers.

Compact rule:

> **Memory preserves progress. Challenge preserves truthfulness.**

## Connection to the Tofoo wisdom lifecycle

The AVO loop can be interpreted as:

```text
hypothesis
→ action
→ consequence
→ preserved state
→ model revision
→ recovery
→ continue
```

Tofoo adds the epistemic lifecycle:

```text
experience
→ memory
→ learning
→ generalization
→ contradiction
→ refinement
→ transfer
→ boundary awareness
→ renewal
→ wisdom candidate
```

The combined architecture is therefore not merely “remember more.” It is:

```text
preserve useful state
+ preserve negative evidence
+ allow challenge
+ detect changed scope
+ renew or revoke
```

This yields the adopted candidate principle:

> **Long-horizon intelligence requires persistence. Long-horizon wisdom requires persistence that can still be revised.**

## Connection to Governed Relational Self-Authorship

AVO’s accumulated lineage changes the future search policy of the agent. Tofoo’s self-authorship work adds an important distinction:

```text
what influenced me
!=
what I endorse
!=
what I am authorized to do
```

A learned or lineage-derived policy may become part of an agent’s history without automatically becoming a protected commitment or legitimate authority source.

This supports the sequence:

```text
inherited / accumulated state
→ provenance
→ reflection / challenge
→ retention or rejection
→ ratified commitment
→ enacted continuity
```

## Boundary to handlingsrett

AVO-style learning and optimization decide what the agent should try or retain.

They do **not** by themselves answer whether a real-world consequence-bearing action is authorized at execution time.

Keep the boundaries separate:

```text
learning / capability evolution:
experience
→ candidate adaptive state
→ evaluation
→ state commit

execution governance:
committed state
→ proposed consequence-bearing action
→ current state / authority / admissibility
→ governed consequence cut-set
→ effect
```

Therefore:

> **Capability is not authority. Learned competence is not handlingsrett.**

## Connection to Governed Consequence Cut-Set

AVO demonstrates a strong long-horizon autonomous loop inside a task environment. For deployment into open, multi-authority or consequential environments, Tofoo/VALO requires an additional question:

> **Which consequence-bearing paths can the accumulated capability actually commit, and where do those paths intersect current legitimate governance?**

The adopted topology remains:

- a single gateway is only the `|cut-set| = 1` case;
- distributed systems may require multiple governed local boundaries;
- no consequence-bearing path inside the governed domain may bypass the applicable governed cut-set.

AVO strengthens the need for this boundary because persistent memory and long-horizon autonomy increase the system’s ability to sustain intent across many actions.

## Candidate research implications

### A. Capability Accumulation State

Candidate question:

> Should long-horizon agents explicitly distinguish accumulated capability state from ordinary memory state?

Possible decomposition:

```text
EPISODIC EVIDENCE
LEARNED HEURISTIC
DEMONSTRATED CAPABILITY
PROTECTED COMMITMENT
WISDOM CANDIDATE
REVOKED / STALE
```

Do not adopt this schema as an implementation contract yet.

### B. Lineage Credibility

A lineage that only preserves winners can become survivorship-biased.

Candidate requirement:

> **Useful lineage should preserve rejected variants, failure reasons and counterevidence sufficiently to prevent successful descendants from laundering away the path by which they were reached.**

### C. Adversarial challenge of accumulated state

Future falsification should test:

1. whether persistent memory can lock an agent into a stale but locally successful model;
2. whether adversarial false feedback can poison lineage over long horizons;
3. whether supervisor interventions create hidden policy authority;
4. whether preserving failed branches improves or degrades search;
5. whether a challenge/renewal layer improves transfer without destroying useful continuity;
6. whether capability accumulation produces increasing consequence reach faster than governance placement adapts.

## Adoption decision

Adopt NVIDIA AVO as:

- **external convergence** on long-horizon capability as a full-system property;
- **reference architecture** for persistent memory, grounded feedback, recovery, supervision and lineage;
- **reference search pattern** for agentic variation and candidate evaluation;
- **evidence that capability can compound over time outside a single model invocation.**

Do **not** adopt AVO as:

- a substitute for execution-time authority/admissibility;
- evidence that persistent memory equals wisdom;
- evidence that a winning variant is generally valid;
- evidence that supervisor control is legitimate authority;
- a proof of Tofoo/VALO/Synapse hypotheses that AVO did not test.

## Canonical compact synthesis

> **Capability compounds through experience. Wisdom requires that what compounds remains challengeable.**

And:

> **The model is not the whole agent. The memory is not the wisdom. The capability is not the authority.**
