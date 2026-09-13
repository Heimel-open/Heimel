# AI Economy Optimizer

Status: concept draft
Scope: VAIG extension

## Purpose

The AI Economy Optimizer governs cost, context and attention before an agent spends tokens.

It does not decide truth.

It does not replace VAIG admissibility.

It decides whether the next model call is economically justified, context-efficient and routed to the right level of compute.

## Core claim

AI cost is not only model price.

AI cost is also:

- language token inflation
- repeated conversation history
- cache misses
- oversized context
- unnecessary tool calls
- wrong model routing
- agent loops that continue after value has collapsed

The relevant metric is not cost per token.

The relevant metric is cost per useful decision.

## Context economics

A naive chat loop resends the conversation state on every turn.

If each turn adds `n` tokens and the whole history is resent each time, billed input grows as:

```text
n * (1 + 2 + ... + t)
```

At 20 turns:

```text
1 + 2 + ... + 20 = 210
```

If each turn adds 300 tokens:

```text
300 * 210 = 63,000 billed tokens
```

But unique content is only:

```text
300 * 20 = 6,000 tokens
```

Effective rebilling multiplier:

```text
63,000 / 6,000 = 10.5x
```

This is before language inflation.

If Danish, Norwegian or another smaller language produces 54 percent more tokens than English for the same semantic content, then the cost multiplier compounds.

## Governance position

This is a governance problem because expensive context changes system behavior.

Operators will shorten prompts, remove evidence, skip review, use weaker models or disable controls when cost becomes invisible and unmanaged.

Therefore cost must be governed explicitly.

## Boundary

AI Economy Optimizer governs:

- context budget
- language token inflation
- cache strategy
- retrieval strategy
- model routing
- compression / summarization timing
- stop / continue decisions for agent loops
- cost-value threshold before execution

It does not govern:

- truth
- human authority
- legal accountability
- moral legitimacy
- final action authorization

Those remain separate VAIG / MECHA / organizational governance concerns.

## State model

Each agent call should carry a small economy state:

```json
{
  "task_id": "...",
  "intent": "...",
  "decision_needed": "...",
  "context_budget_tokens": 4000,
  "estimated_input_tokens": 1800,
  "estimated_output_tokens": 600,
  "language": "da",
  "language_token_multiplier": 1.54,
  "history_rebilling_multiplier": 10.5,
  "cache_expected": true,
  "cache_hit_risk": "medium",
  "retrieval_required": true,
  "summary_required": false,
  "model_tier": "small | standard | frontier",
  "estimated_cost": 0.0,
  "expected_value": "low | medium | high | critical",
  "decision": "allow | compress | retrieve | downgrade_model | require_human | stop"
}
```

## Decisions

The optimizer may return:

- `allow` — call is economically acceptable
- `compress` — summarize or reduce history before calling
- `retrieve` — search evidence instead of sending broad context
- `downgrade_model` — route to cheaper model
- `upgrade_model` — use stronger model because consequence/value justifies it
- `cache_reorder` — move stable prefix earlier to improve cache hit
- `require_human` — ask human whether the cost is justified
- `stop` — cost exceeds value or loop has no justified next decision

## Rules v0.1

### 1. No full-history default

Do not send full chat history unless it is required for the next decision.

Send:

- active task state
- relevant evidence
- current constraints
- last decision
- open question

### 2. Compress after threshold

If accumulated context exceeds budget or rebilling multiplier exceeds threshold, compress to state.

Compression target:

- what is decided
- what is open
- what is blocked
- what evidence matters
- next decision needed

### 3. Search before loading

Use retrieval before adding long documents.

Load only relevant excerpts.

### 4. Route by consequence

Small model:

- formatting
- classification
- extraction
- low-risk summaries

Standard model:

- normal reasoning
- code review
- planning

Frontier model:

- high consequence
- ambiguous governance boundary
- legal / medical / financial / infrastructure relevance
- decisions where error cost exceeds model cost

### 5. Track language multiplier

For each language, maintain observed token multiplier against English for similar semantic content.

This is not cultural preference.

It is cost accounting.

### 6. Account for cache

Stable instructions and static documents should be placed before volatile content where provider caching benefits from stable prefixes.

Changing the prefix too often destroys cache value.

### 7. Stop loops with declining value

If repeated calls do not reduce uncertainty or advance the decision, stop or escalate.

## Metrics

Track:

- input tokens
- output tokens
- cached input tokens
- unique semantic tokens
- rebilled history multiplier
- language token multiplier
- cost per turn
- cumulative cost per task
- cost per useful decision
- retrieval hit rate
- compression ratio
- model routing accuracy
- stop decisions avoided

## Relation to VAIG

VAIG asks:

```text
May this intent/action proceed?
```

AI Economy Optimizer asks:

```text
Is this model call worth making in this form?
```

Cost-value gating should happen before expensive model calls and before agent-loop continuation.

## Relation to issue #35

This document extends the cost-value gate idea.

Issue #35 should become the implementation tracker for:

- context budget enforcement
- token multiplier measurement
- history rebilling calculation
- model routing rules
- cost-value receipts

## Minimal implementation

Create:

```text
src/vaig/economy/
  __init__.py
  context_budget.py
  token_meter.py
  router.py
  decision.py
  receipt.py

tests/
  test_context_rebilling.py
  test_language_multiplier.py
  test_model_routing.py
  test_cost_value_gate.py
```

## First acceptance tests

1. A 20-turn conversation with 300 tokens per turn reports a 10.5x rebilling multiplier.
2. A Danish/Norwegian language multiplier can be applied on top of the rebilling multiplier.
3. A low-risk formatting task is routed to a small model.
4. A high-consequence governance task is not downgraded solely to save cost.
5. A context over budget returns `compress` or `retrieve`, not `allow`.
6. A loop with rising cost and no uncertainty reduction returns `stop`.

## Core principle

Do not optimize for cheap tokens.

Optimize for justified attention.
