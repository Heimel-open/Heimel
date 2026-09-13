# Needle 2 integration v1

Status: candidate runtime adapter for VALO Edge.

## Role

Needle 2 is an inference component, not an authority component. It converts local text/state into one structured candidate function call.

Canonical path:

`input/sensor -> Needle 2 -> TinyLLMInferenceClaimV1 -> VAIG -> micro-reht -> device gateway -> physical world -> Veritas`

Needle must never bypass VAIG, micro-reht, the gateway, or receipt generation.

## Hard invariants

1. The adapter calls `Needle.complete()` only. It never calls `Needle.run()`.
2. Tools are supplied as plain JSON schemas, not executable Python callables.
3. A Needle response is only a candidate intent. Confidence is evidence for VAIG; it is never ALLOW authority.
4. Exactly one candidate call is admitted per edge inference. Empty, malformed, unknown, or multiple calls fail closed.
5. The declared toolset is hashed into the inference claim. The raw Needle response is hashed into the claim. Optional reasoning is stored as a digest only.
6. Runtime provenance is propagated into `EdgeActionProposal` so downstream authorization/evidence can bind execution to the model output that proposed it.
7. reht remains the sole authorization boundary immediately before execution.

## Function Fabric bridge

Needle accepts JSON tool schemas directly. Function Fabric should therefore remain the canonical source for function identity and typed inputs, with a deterministic export step:

`FunctionDefinition + admitted input schema -> Needle tool schema -> toolset_hash`

The Needle schema narrows what the model can emit. It does not grant capability, authority, purpose, rights, evidence standing, jurisdiction, or execution permission. Those remain governance inputs downstream.

For large catalogues, Needle may retrieve a small candidate subset before decoding. That subset is a model-context reduction only; it is not an authorization filter.

## Model Factory loop

A safe learning loop is:

`shadow inputs -> Needle candidate -> VAIG signals -> reht decision -> gateway outcome -> Veritas receipt -> curated training set -> LoRA/tuned .cact -> new model manifest`

Rejected, deferred, step-up, insufficient-evidence, and no-call outcomes are valid training labels. Training may improve candidate selection and argument extraction but must never distill reht authorization policy into the model as a replacement for runtime authorization.

## Compute Mesh placement

Needle is suitable as a low-cost local inference tier before escalation to larger models:

`deterministic code -> Needle local -> larger local model -> enterprise GPU -> external frontier model`

Escalation policy belongs to VAIG/orchestration. Model size or Needle confidence alone cannot authorize an action.

## Install

Needle is optional:

```bash
pip install -e '.[needle]'
```

The production adapter imports the runtime lazily. Unit tests inject a non-executing fake client so the core test suite does not download model weights or depend on network access.
