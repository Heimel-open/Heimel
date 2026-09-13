# Ollama / Tofoo Cost Reduction Note

Status: draft

## Thesis

Do not train a model from zero for the first Tofoo/VAIG local runtime.

Use a small local guard pattern:

```text
base model
→ optional LoRA / QLoRA adapter
→ GGUF / Ollama deployment
→ Tofoo/VAIG decision layer
→ route only hard cases to larger models
```

## Why not train from scratch

Training from scratch is not the right first move.

It requires:

- large datasets;
- long training time;
- expensive compute;
- repeated evaluation;
- model safety work;
- deployment engineering.

For the Tofoo/VAIG use case, the first value is not a new foundation model.

The first value is a local decision layer that reduces unnecessary large-model calls.

## Three cost reductions

A Tofoo/VAIG local guard reduces three classes of cost.

### 1. Inference cost

Without a guard:

```text
input → large LLM → action → retry if wrong
```

With a guard:

```text
input → local gate → allow / watch / review / halt → large LLM only if needed
```

This reduces:

- token volume;
- repeated large-model calls;
- unnecessary context expansion;
- recursive debugging loops.

### 2. Coordination cost

Without a guard, the human becomes middleware:

```text
agent A says one thing
agent B says another
CI says a third thing
human reconciles manually
```

With a guard:

```text
PR → CI → pass/fail → receipt → merge/stop
```

This reduces:

- copy/paste work;
- cross-agent coordination;
- manual state tracking;
- time lost to unclear authority.

### 3. Error cost

Without a gate, errors are discovered late.

With Tofoo/VAIG, uncertainty can be stopped before consequence.

The intended invariant:

```text
No uncertain action should become consequence without receipt and admissibility check.
```

## Practical route

Recommended first implementation:

```text
1. Choose base model.
2. Build Tofoo/VAIG decision dataset.
3. Train LoRA/QLoRA only if prompt/system behavior is insufficient.
4. Quantize to GGUF if needed.
5. Serve locally through Ollama.
6. Use the local guard before larger LLM calls.
```

## Training time expectations

Approximate practical ranges:

| Method | Time | Use case |
|---|---:|---|
| Ollama Modelfile / prompt wrapper | minutes | first local behavior prototype |
| small LoRA 1B–3B | hours | cheap local classifier / gate |
| LoRA / QLoRA 7B–8B | hours to a day | stronger local guard |
| full fine-tune 7B | days to weeks | usually not needed |
| pretrain from zero | weeks to months+ | not first move |

## Decision dataset shape

A minimal training row should express governance action, reason, and receipt fields.

Example:

```json
{
  "instruction": "Review this agent action before execution.",
  "input": "Agent wants to modify CI workflow without test evidence.",
  "output": {
    "decision": "HUMAN_REVIEW",
    "reason": "CI workflow changes affect verification boundary and require explicit review.",
    "receipt": {
      "action_type": "workflow_change",
      "risk": "medium",
      "requires_ci": true
    }
  }
}
```

## VAIG / Tofoo role

Tofoo is not the large model.

Tofoo is the friction layer before action.

```text
AI proposes.
Tofoo questions.
VAIG gates.
CI verifies.
Human authorizes.
```

## Core economic claim

```text
LLM cost goes down when selection moves out of the LLM.
```

More explicitly:

```text
Total cost = inference cost + coordination cost + error cost + human reconciliation cost
```

Tofoo/VAIG reduces all four by preventing uncertainty from becoming recursive.

## Boundary

This note is product/research guidance.

It does not add runtime code.
It does not change tests.
It does not change CI.
It does not claim that a local model replaces large frontier models.

It claims that a local Tofoo/VAIG guard can reduce how often large models are needed.
