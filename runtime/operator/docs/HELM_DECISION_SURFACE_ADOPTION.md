# HELM decision-surface adoption

Status: adopted operator/UI pattern.

This note adopts two useful methodological principles from HELM-style decision instrumentation without changing VALO's authority or effect architecture.

## 1. One named action question per governance surface

Every Operator/UI governance surface MUST be organized around one explicit action question rather than a generic dashboard or collection of metrics.

Canonical form:

> Can this actor perform this action, now, under what authority, and what actually happened?

A surface MAY expose supporting state, evidence, constraints, confidence, provenance, and history, but those remain subordinate to the named action question.

A surface MUST NOT imply that observed state, model output, recommendation, or presentation grants authority. Authority is resolved by the existing VALO chain at consequence time.

The surface SHOULD make the following directly inspectable when relevant:

- current observable state;
- actor and identity context;
- requested action / registered Function;
- applicable authority, delegation, rights, purpose, constraints and expiry;
- RACS/REHT decision and reason;
- permit / denial / escalation status;
- intended effect and postconditions;
- Veritas/BARO effect verification;
- evidence and replay references;
- UNKNOWN or divergence when reality cannot be established.

The UI is therefore a decision instrument over governed execution, not an authorization layer and not a substitute for consequence verification.

## 2. Producer and verifier must be separable

A component that produces a proposal, classification, recommendation, summary, candidate action, or effect claim MUST NOT be treated as sufficient evidence for validating its own output.

Where independent validation is material, evaluation SHOULD run in an independent context and, when practical, through a different evaluator/provider or verification path.

This is especially important for:

- candidate actions before execution;
- high-impact judgments;
- factual/evidence synthesis;
- claims that an external effect occurred;
- quality/admissibility checks that could otherwise inherit the producer's assumptions.

Independent evaluation does not create authority. It supplies evidence to the governed chain.

For external effects, the stronger rule remains canonical: the sender cannot prove delivery merely by reporting transport success. Veritas must observe the external state independently, and BARO must record divergence or UNKNOWN when the desired state is not established.

## 3. Evidence presentation

Operator/UI surfaces SHOULD distinguish evidence strength and provenance explicitly where the underlying data supports it. Synthetic, inferred, simulated, stale, or incomplete evidence MUST NOT be presented as observed ground truth.

Evidence labels are presentation metadata only. They do not override Kernel truth, REHT/RACS authorization, domain admissibility, or effect verification.

## 4. Architectural boundary

Adopted pattern:

```text
observable state
  -> evidence / candidate interpretation
  -> named action question surface
  -> registered Function / typed request
  -> fresh authority + admissibility
  -> RACS / REHT decision
  -> governed effect path
  -> Veritas / BARO verification
  -> evidence + replay
```

The key distinction is deliberate: HELM-like decision instrumentation can improve the cockpit, but VALO remains responsible for whether an action is actually allowed, whether it can reach consequence, and whether the claimed consequence occurred.

## Invariant

A locally useful dashboard is insufficient if it obscures the actual governed question.

Every governance surface must preserve the chain from question -> authority -> decision -> effect -> verified consequence.
