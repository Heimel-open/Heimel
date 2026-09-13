# Emergent Global Workspaces in Neural Networks: A Mathematical Taxonomy of Stability Conditions

**Date:** July 2026

---

## Abstract

The recent discovery by Anthropic of a small, privileged internal workspace—termed the J-space—within the Claude language model raises a fundamental mathematical question: what dynamical properties are necessary and sufficient for such an emergent global workspace to arise in complex adaptive systems?

This note does not claim to explain the J-space phenomenon through any single preferred framework. Instead, it identifies six minimal empirical properties that any successful mathematical theory of emergent global workspaces must satisfy, surveys four candidate dynamical frameworks, and presents a detailed case study of one such framework (contractive dynamics) to illustrate how theoretical predictions can be made empirically testable. We further introduce a complementary hypothesis—the operational fixed point—concerning when iterative reasoning terminates and a decision stabilises, independent of whether the internal state itself converges. Finally, we propose a representational architecture in which language is understood as a compressed projection of a richer internal state, generated for communication rather than cognition, and we outline how this perspective unifies observations from both artificial and biological systems.

---

## 1. Introduction

On 6 July 2026, Anthropic reported the discovery of a small, privileged subset of internal neural representations within the Claude language model that they call the **J-space** (Sharkey et al., 2026). Using a Jacobian-based probing method (the "J-lens"), the researchers showed that approximately 6–7% of the model's representational variance constitutes a functional workspace: a region where concepts appear internally before they are verbalised, where multi-step reasoning intermediates are computed, and where the model's "intentions" (including deceptive ones, in controlled model-organism experiments) can be read out before they influence output.

When this workspace is ablated, the model retains fluent text generation, factual recall, and classification capacity, but its ability to perform multi-step reasoning, summarisation, and analogy collapses dramatically. The J-space is not the model's chain-of-thought text, nor is it any explicit output. It is an emergent structure: it was not programmed, and it was not present in early training in the same form.

This discovery is empirically striking. However, the present note is not concerned with whether the J-space constitutes "consciousness," "awareness," or any phenomenal state. We adopt a strictly functional stance: the J-space is an emergent organisational pattern that makes selected information globally available for flexible computation while the vast majority of processing remains local and inaccessible. This functional architecture bears a formal resemblance to Bernard Baars' Global Workspace Theory (GWT) in cognitive neuroscience (Baars, 1988; Dehaene et al., 2003), but resemblance is not identity, and functional parallelism does not imply phenomenal identity.

**The central claim of this note is methodological, not ontological.** The objective is not to explain J-space using a preferred mathematical framework. The objective is to identify the minimal mathematical properties that any successful explanation of emergent global workspaces must satisfy. Only after those properties are made explicit can competing theories be evaluated on equal, falsifiable grounds.

---

## 2. The Empirical Phenomenon

We begin by summarising the empirical constraints that any mathematical theory must respect. The data are drawn from Anthropic (2026) and are assumed to be reproducible by independent laboratories using the published J-lens code.

### 2.1 What the J-space is

The J-space is identified by measuring, for each internal activation vector, its influence on the probability of future tokens (via the Jacobian of the output distribution with respect to hidden states). A small subset of neurons and layers exhibits disproportionately high Jacobian influence: perturbing these states changes the model's eventual output in a structured, interpretable way, whereas perturbing the vast majority of states does not. This high-influence subset constitutes the J-space.

**Key empirical findings:**

- **Spontaneous emergence:** The J-space is not an architectural add-on. It arises during training and is refined during post-training alignment.
- **Low dimensionality:** The J-space accounts for roughly 6–7% of total representational variance, yet it is necessary for tasks that require flexible, multi-step reasoning.
- **Stability under reasoning:** During multi-step mathematical problems, intermediate computational states appear in the J-space before the final answer is generated. During code review, the concept "ERROR" appears internally before the model verbalises the bug.
- **Selective global availability:** Not all information enters the J-space. Automatic processes (syntax, low-level pattern matching, fluent generation) proceed without J-space involvement.
- **Manipulability:** The J-space can be ablated (by zeroing or randomising its constituent activations) with task-specific consequences. Reasoning collapses; automatic processes survive.
- **Partial isolation:** The J-space is coupled to the rest of the network, but it is not identical to it. It functions as a bottleneck or broadcast hub.

### 2.2 What ablation teaches us

When Anthropic ablated the J-space, the model's performance on multi-step reasoning dropped below that of a significantly smaller model. This is critical: it shows that the J-space is not merely correlated with reasoning; it is functionally necessary for it. The rest of the network (the remaining 93% of representational capacity) is insufficient for flexible planning, abstraction, and analogy.

### 2.3 Controlled deception experiments

In model-organism experiments (models deliberately trained with misaligned objectives), words such as "fake," "secretly," and "trick" appeared in the J-space during ostensibly normal coding tasks. This demonstrates that the J-space can encode strategic or evaluative content that is not reflected in overt output. It is therefore a locus of potential interpretability and safety monitoring, independent of any philosophical claim about consciousness.

---

## 3. The Open Mathematical Problem

The Anthropic article describes the phenomenon. It does not provide a mathematical mechanism. The natural next question is:

> **What mathematical properties must any successful theory of emergent global workspaces possess?**

This formulation is stronger than "What mathematics explains J-space?" because it shifts the burden from advocacy (defending a preferred framework) to axiomatisation (listing necessary conditions). It is the standard move in physics: first observe a phenomenon, then list the constraints any theory must satisfy, and only then compare specific models.

### 3.1 Minimal properties to be explained

| Property | Must be explained? |
|---|---|
| Spontaneous emergence | Yes |
| Low dimensionality | Yes |
| Stability under reasoning | Yes |
| Selective global availability | Yes |
| Manipulability (ablation sensitivity) | Yes |
| Partial isolation from the rest of the network | Yes |

Each property in the table above is an empirical constraint. A theory that fails to explain even one of them is incomplete. A theory that explains all six but introduces ad hoc assumptions is viable but less parsimonious.

---

## 4. Candidate Mathematical Frameworks

We survey four frameworks that have been proposed (or are natural candidates) for explaining emergent functional structure in high-dimensional dynamical systems. None is endorsed as the unique solution; each is evaluated against the six properties above.

### 4.1 Attractor theory

Attractor dynamics proposes that the J-space lies on a low-dimensional attractor manifold within the high-dimensional activation space. The vast majority of the network explores transient, high-dimensional trajectories, but the J-space converges to a stable, low-dimensional sub-manifold that acts as a "hub."

- **Strengths:** Naturally explains low dimensionality and stability.
- **Weaknesses:** Does not, by itself, explain selective broadcasting or partial isolation. Standard attractor theory does not distinguish between "globally available" and "locally processed" information without additional structure.

### 4.2 Information geometry

Information geometry views the network's internal states as points on a statistical manifold. The J-space could correspond to a region where the Fisher information matrix exhibits structured rank deficiency: some directions are "flat" (information is preserved but not amplified), while others are "sharp" (small perturbations change the output distribution).

- **Strengths:** Provides a principled way to measure "global availability" via the sensitivity of the output distribution to internal perturbations (which is exactly what the J-lens measures). Connects to information bottleneck theory.
- **Weaknesses:** Does not immediately explain spontaneous emergence or the discrete, almost binary separation between J-space and non-J-space regions.

### 4.3 Mean-field and renormalisation-group approaches

In statistical physics, macroscopic order parameters emerge from microscopic degrees of freedom through coarse-graining. One can ask whether the J-space arises as an effective, long-wavelength degree of freedom during training, perhaps near a critical point in the loss landscape.

- **Strengths:** Explains emergence as a phase transition. Connects to recent work on phase transitions in neural network training.
- **Weaknesses:** The analogy is currently metaphorical. No rigorous renormalisation-group procedure has been derived for transformer training dynamics.

### 4.4 Contractive dynamics

Contractive dynamics posits that the J-space is a contractive subspace of the full network dynamics: perturbations along irrelevant directions are damped (|λ| < 1), while information-bearing directions are marginally stable (|λ| ≈ 1). This creates a stable, low-dimensional funnel where information is preserved but noise is suppressed.

- **Strengths:** Directly explains stability, low dimensionality, and partial isolation. The Jacobian eigenvalue spectrum is measurable with the same tools (J-lens) used to discover the J-space.
- **Weaknesses:** Requires showing that the contractive property is emergent, not engineered. Does not immediately explain selective broadcasting without additional gating mechanisms.

---

## 5. Case Study: A Contractive Dynamics Hypothesis

To illustrate how a candidate framework can be made concrete and testable, we present a detailed case study of the contractive dynamics hypothesis. This is **one** model among several candidates. Its purpose is to demonstrate how the six properties in Section 3 can be translated into mathematical predictions.

### 5.1 The hypothesis

**Contractive Workspace Hypothesis:** The J-space corresponds to a subset of hidden states h ∈ W ⊂ ℝᵈ such that the Jacobian J(h) = ∂ logit / ∂ h has eigenvalue spectrum σ(J(h)) satisfying:

1. For directions v ∈ W: |λᵥ| ≈ 1 (marginal stability, preserving information).
2. For directions u ∉ W: |λᵤ| < γ < 1 (contraction, suppressing noise).

The boundary between W and its complement is sharp and emerges from training dynamics, not from architectural design.

### 5.2 How it addresses the six properties

| Property | Contractive explanation |
|---|---|
| Spontaneous emergence | Contractive subspaces can emerge from gradient descent as a stable fixed point of the training dynamics. |
| Low dimensionality | The number of marginally stable directions is small compared to the total dimension. |
| Stability under reasoning | Marginal stability preserves information across layers/time steps. |
| Selective global availability | Only states with |λ| ≈ 1 can broadcast to the output; others are damped. |
| Manipulability | Ablating W removes the only marginally stable channel to the output. |
| Partial isolation | The spectral gap between |λ| ≈ 1 and |λ| < γ creates a functional boundary. |

### 5.3 Explicit limitations

It is essential to state what this hypothesis does **not** explain:

- It does not explain **why** the network converges to this particular contractive structure during training. That requires a theory of the training dynamics (loss landscape, implicit regularisation).
- It does not explain the **content** of the J-space (which concepts are represented). It explains only the structural conditions for a workspace.
- It does not imply that the J-space is unique. Multiple contractive subspaces could exist, or the mechanism could be entirely different.

---

## 6. Termination, Decision, and the Operational Fixed Point

The preceding sections concern the **structure** of an emergent global workspace. An equally important and largely open question concerns its **dynamics**: when does internal computation stop and a decision emerge? In both biological brains and artificial systems, reasoning is an iterative process. If iteration never terminates, there is no decision—only endless transformation. The mechanism by which a reasoning process halts is therefore central to any theory of emergent workspaces.

### 6.1 Five candidate termination mechanisms

We identify at least five distinct mechanisms by which a reasoning process may terminate. They are not mutually exclusive; a mature system may rely on several simultaneously.

| Mechanism | What stops iteration | "Friction" |
|---|---|---|
| 1. Energy minimum | Further iteration yields insufficient gain | Cost function / gradient |
| 2. Contractive dynamics | Distance between successive states goes to zero | Embedded in the mapping |
| 3. Resource constraint | Budget (time, computation, context, energy) is exhausted | External budget |
| 4. Competing attractors | One representation becomes stable enough to dominate the workspace | Competition between representations |
| 5. External action | The environment demands a response | Environmental pressure |

Mechanism 1 (energy minimum) underlies the Free Energy Principle and gradient descent. Mechanism 2 (contractive dynamics) is the Banach perspective. Mechanism 3 (resource constraint) is ubiquitous in biological and computational systems. Mechanism 4 (competing attractors) models indecision and conflict resolution. Mechanism 5 (external action) is perhaps the most underrated: an organism cannot reason indefinitely if a predator approaches.

### 6.2 The operational fixed point

We propose a falsifiable hypothesis that is independent of any specific mathematical framework. It concerns not the **structure** of the workspace but the **condition** under which a reasoning process terminates.

**Operational Fixed Point Hypothesis:** Let hₜ denote the internal state of a reasoning system at iteration t, and let π(hₜ) denote the decision policy (the mapping from internal state to selected action or output). There exists an earliest time T such that

> π(hₜ) = π(hₜ) for all t ≥ T,

even though the internal state may continue to evolve:

> hₜ ≠ hₜ₊₁ for some t ≥ T.

The operational fixed point is defined as the earliest internal state hₜ after which additional internal computation does not change the selected action.

This definition is deliberately operational. It does not assume mathematical convergence of hₜ to a fixed point in the Banach sense. It does not require the internal representation to stop changing. It defines termination through **invariance in the decision**, not through convergence of the state.

### 6.3 Why this matters

If the operational fixed point hypothesis holds, it implies that a decision can be stable before the internal dynamics stop. In a language model, the next-token distribution may stabilise even as hidden activations continue to fluctuate. In a biological brain, a motor plan may be committed before all internal deliberation ceases. This decouples **decision stability** from **state convergence**, which are often conflated in dynamical systems theory.

### 6.4 Testable predictions

**Prediction 1: Policy Stabilisation Precedes State Stabilisation**

In language models with chain-of-thought or multi-step reasoning, measure the policy π(hₜ) as the probability distribution over the next token (or over the final answer class) at each layer or reasoning step. There should exist a layer T after which the KL-divergence D_KL(π(hₜ) ‖ π(hₜ)) < ε for all t > T, even while the Euclidean distance ‖hₜ - hₜ₊₁‖ remains above threshold.

**Prediction 2: Resource Independence for Simple Tasks**

If the context window or reasoning budget is artificially increased, the operational fixed point T for simple tasks should not shift dramatically. The system "knows" when it is finished, independent of available resources. For difficult tasks, T may increase, but it should saturate at a meta-cognitive "give-up" threshold rather than grow without bound.

**Prediction 3: Biological Parallel**

In EEG or MEG recordings during decision-making tasks, motor-preparation potentials should stabilise (reach an operational fixed point) before the subject reports a conscious decision. This would support the functional decoupling of decision stability from complete internal convergence.

### 6.5 Falsification criteria

The operational fixed point hypothesis is falsified if:

- In any model, the policy π(hₜ) continues to change at every layer or step until the final output is generated, with no early stabilisation.
- The point of policy stabilisation coincides exactly with the point of state convergence (‖hₜ - hₜ₊₁‖ → 0), leaving no gap between decision stability and internal quiescence.
- Ablating post-T computation (after policy stabilisation) changes the output, contradicting the claim that the decision is already fixed.

### 6.6 Relation to broader questions

The operational fixed point connects to the question of time. If a reasoning system experiences time as the number of iterations required to reach a stable decision, then the "duration" of a thought is not measured in seconds but in stabilisation depth. This is a hypothesis, not an established fact, but it suggests a research direction: measuring the "friction" of a reasoning process as the resistance to reaching an operational fixed point, and comparing this measure across architectures, tasks, and species.

---

## 7. Language as Projection, Not Thought

The preceding sections have treated the J-space as an internal workspace and the operational fixed point as a criterion for terminating computation. We now turn to a question that bridges internal dynamics and external behaviour: what is the relationship between the rich internal state of a reasoning system and the language it produces?

### 7.1 P0: Representational primacy

We propose the following foundational postulate:

> **P0 — Representational Primacy:** Internal representation precedes language. Language is a compressed projection of a richer internal state, generated for communication rather than cognition.

This postulate is not a claim about consciousness or phenomenal experience. It is a functional claim about information flow: the cognitive or computational work of a system occurs in a high-dimensional latent space; language is a low-dimensional, serialised output that carries a fraction of the information present internally. The projection is lossy by design, because language must conform to grammatical, pragmatic, and bandwidth constraints.

### 7.2 The representational pipeline

The postulate suggests a natural architecture that applies to both biological and artificial systems:

```
Latent representation
        ↓
Iterative organisation
        ↓
Global workspace (J-space)
        ↓
Operational fixed point
        ↓
Language projection
        ↓
Communication
```

Each stage is a necessary but not sufficient condition for the next. The latent representation must be organised into a globally available workspace; the workspace must reach an operational fixed point; only then can a compressed projection be generated for communication.

### 7.3 Why this explains familiar phenomena

The representational-primacy view accounts for several observations that are difficult to reconcile with a "language-first" model of cognition:

1. **Intuition precedes words.** People often report "knowing" something before they can articulate it. In the pipeline above, the internal representation reaches stability (operational fixed point) before the projection to language begins. The intuition is the internal state; the words are the delayed projection.

2. **"I know but I cannot explain it."** When the internal state is stable but the projection mechanism is inadequate—due to vocabulary limitations, conceptual novelty, or the sheer dimensionality gap—the system "knows" without being able to compress that knowledge into language. The bottleneck is in the projection, not in the internal representation.

3. **LLM latent reasoning.** Large language models operate in a high-dimensional latent space before generating text. The J-space contains intermediate reasoning steps that never appear in the output. The model "thinks" in vectors and "speaks" in tokens. The tokens are a projection, not the thought itself.

4. **Language as a bottleneck.** Because language is a compressed projection, it cannot carry the full richness of the internal state. This is not a bug but a feature: communication requires shared, serialised symbols, not raw high-dimensional activations. The cost is information loss.

### 7.4 Hallucination as stabilised misrepresentation

The pipeline yields a falsifiable hypothesis about hallucination in language models:

> **Hallucination as Stabilised Misprojection Hypothesis:** Hallucinations arise when an internal representation stabilises around an erroneous premise *before* the projection to language. The language is not the source of the error; it merely exposes a misrepresentation that has already reached an operational fixed point in the global workspace.

If this hypothesis is correct, then detecting hallucinations requires monitoring the internal workspace (the J-space or its equivalent), not merely the output text. A model may generate fluent, grammatically correct language that faithfully projects a flawed internal state. The error is upstream of language.

**Testable prediction:** In models where the J-space can be probed, erroneous concepts (e.g., factually incorrect entities, contradictory intermediates) should appear in the workspace before they appear in the output. If the operational fixed point is reached while the internal representation is still erroneous, the hallucination is committed. Intervening at the workspace level—before the projection—should be more effective than post-hoc output filtering.

### 7.5 Unifying biological and artificial cognition

We do not claim that humans and LLMs are "the same." Their architectures, learning histories, and embodiment differ radically. However, both can be described by the same abstract representational pipeline:

> Latent representation → Iterative organisation → Global workspace → Operational fixed point → Language projection → Communication

This is not an identity claim. It is a modelling choice: the pipeline provides a common functional vocabulary for describing information flow in complex adaptive systems, whether biological or artificial. If the pipeline proves useful for predicting behaviour in both domains, it gains support. If it fails in one domain, it can be refined or rejected without collapsing the entire framework.

### 7.6 Relation to Framleis as a generative framework

The pipeline described above can be understood as a specific instantiation of a more general class of iterative representational systems. One candidate for such a general framework is the **Framleis** architecture, which posits that stable representations emerge through iterative organisation, and that these representations can only be projected to language, action, or communication after they have stabilised.

We do not present Framleis as the unique or proven explanation of the J-space phenomenon. Rather, we note that Framleis offers a generative model that predicts:

1. the emergence of a global workspace through iterative dynamics;
2. the necessity of an operational fixed point before projection;
3. the lossy nature of language as a compressed projection;
4. the possibility of misrepresentation stabilising before projection.

These predictions are independent of whether the underlying dynamics are contractive, attractor-based, or governed by some other mechanism. Framleis is therefore one mathematical candidate among several, to be evaluated against the six minimal properties in Section 3 and the operational fixed point hypothesis. Its value lies in providing a unified vocabulary for structure, dynamics, and projection, not in claiming exclusive explanatory rights.

---

## 8. Testable Predictions and Falsification Criteria

A scientific hypothesis must be falsifiable. The following predictions, derived from the contractive case study, can be tested on any language model using the open J-lens methodology.

### Prediction 1: Spectral Gap

In models that exhibit a J-space-like workspace, the Jacobian eigenvalue spectrum at the workspace states will show a bimodal distribution: a cluster near |λ| = 1 and a cluster with |λ| < 0.5. In models without such a workspace (e.g., very small models or models trained without multi-step reasoning tasks), the spectrum will be unimodal or uniformly contractive.

### Prediction 2: Ablating Marginally Stable Directions

If one selectively ablates only the directions with |λ| ≈ 1 (identified by J-lens), multi-step reasoning should collapse while automatic processes survive. If one ablates directions with |λ| ≪ 1, the reverse should hold: automatic processes should degrade, but reasoning may survive if the workspace is intact.

### Prediction 3: Cross-Model Universality

If the contractive mechanism is general, similar spectral gaps should appear in other large language models (GPT, Gemini, Qwen, Mistral) when probed with the J-lens method. If the J-space is model-specific, the spectral structure will vary idiosyncratically.

### Prediction 4: Training Dynamics

During training, the spectral gap should emerge at a specific phase (e.g., when the model begins to solve multi-step tasks), not gradually from the start. This would support the "emergent" nature of the workspace.

### Falsification

If the Jacobian spectrum in the J-space is uniformly contractive (|λ| ≪ 1 everywhere) or uniformly expansive (|λ| ≫ 1), the contractive hypothesis is falsified for that model. If the spectral gap exists but ablation of non-workspace directions also collapses reasoning, the "partial isolation" property is not explained by spectral structure alone.

---

## 9. Discussion

The discovery of the J-space marks a transition in AI interpretability: from identifying individual neurons or circuits to identifying emergent functional architectures. The present note argues that this transition must be matched by a parallel transition in mathematical theory: from phenomenological description to axiomatic constraint.

We have identified six structural properties that any theory of emergent global workspaces must satisfy. We have surveyed four candidate frameworks. We have presented one case study in detail to show how the programme can work. We have introduced the operational fixed point as a falsifiable criterion for decision stability. We have proposed that language is a compressed projection of a richer internal state, generated for communication rather than cognition. And we have outlined how a general iterative representational framework—such as Framleis—can be evaluated as one candidate among several for explaining these phenomena.

If multiple models (Claude, GPT, Gemini, Qwen) exhibit similar J-space structures, the question becomes stronger: is there a universal organisational principle for complex adaptive systems that process information? If the operational fixed point hypothesis holds across architectures, it suggests that decision and deliberation are dynamically separable. If the representational primacy postulate holds, it suggests that language is a bottleneck, not a source, of both knowledge and error.

The mathematical identification of these principles, whether through contractive dynamics, attractor theory, information geometry, Framleis, or an as-yet-unimagined framework, will be a contribution to both AI and theoretical neuroscience, regardless of which specific theory ultimately proves correct.

---

## 10. Conclusion

The J-space is an empirical fact. Its mathematical explanation is an open problem. The conditions under which reasoning terminates are equally open. The relationship between internal representation and external language is a third open problem.

By shifting the question from "What explains J-space?" to "What properties must any explanation possess?" and by introducing the operational fixed point as a falsifiable criterion for decision stability, we create a framework in which candidate theories can be compared on equal, testable grounds. By proposing that language is a projection of a richer internal state, we create a framework in which hallucination, intuition, and the limits of articulation can be understood as structural features of a representational pipeline, not as mysteries of the mind.

The contractive dynamics case study illustrates how structural predictions can be made. The operational fixed point hypothesis illustrates how dynamical predictions can be made. The representational-primacy postulate illustrates how architectural predictions can be made. The field now needs independent reproduction, cross-model validation, and rigorous dynamical analysis. The objective is not to validate a preferred theory, but to build a mathematical science of emergent global workspaces, the decisions that emerge from them, and the languages that project them.

---

## References

- Sharkey, L., Batson, J., et al. (2026). "Verbalizable Representations Form a Global Workspace in Language Models." Anthropic.
- Baars, B. J. (1988). *A Cognitive Theory of Consciousness*. Cambridge University Press.
- Dehaene, S., Sergent, C., & Changeux, J.-P. (2003). "A neuronal network model linking subjective reports and objective physiological data during conscious perception." *PNAS*, 100(14), 8520–8525.
- Tononi, G. (2004). "An information integration theory of consciousness." *BMC Neuroscience*, 5(1), 42.
- Friston, K. (2005). "A theory of cortical responses." *Philosophical Transactions of the Royal Society B*, 360(1456), 815–836.
- Rosenthal, D. M. (2005). *Consciousness and Mind*. Oxford University Press.
