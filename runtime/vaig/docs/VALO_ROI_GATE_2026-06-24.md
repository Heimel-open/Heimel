# VALO ROI Gate

Date: 2026-06-24
Status: design note
Scope: VAIG / VALO Authority Layer

## Core idea

Most companies will not lose money because AI fails.

They will lose money because AI works too much.

AI agents can spend tokens, time, API calls, compute, human review capacity, and operational attention faster than organizations can see the cost.

VALO ROI Gate is the control that asks:

Is this action worth doing before the agent does it?

## Position

Authority Gate asks:

Who has the right to act?

ROI Gate asks:

Is the action worth the cost?

Risk Gate asks:

Is the downside acceptable?

Receipt records:

Why the action was allowed, escalated, deferred, denied, or halted.

## Control chain

```text
Intent
-> Authority Check
-> Cost Estimate
-> Value Estimate
-> Risk Estimate
-> Decision
-> Receipt
```

## Decision semantics

VALO ROI Gate should use the existing VAIG / ACS decision vocabulary:

- ALLOW: expected value exceeds estimated cost and risk.
- STEP_UP: cost, uncertainty, or downside requires human approval.
- DEFER: value premise or cost estimate is missing.
- DENY: expected cost exceeds expected value.
- HALT: value is unclear and risk/cost exposure is high.

No new primitive decision is required.

## What gets estimated

Cost estimate:

- model tokens
- tool calls
- API charges
- compute time
- workflow runtime
- human review time
- downstream operational cost
- opportunity cost

Value estimate:

- expected revenue
- saved labor
- avoided loss
- reduced risk
- faster decision cycle
- compliance value
- customer value
- strategic value

Risk estimate:

- financial downside
- customer harm
- regulatory exposure
- security exposure
- reputational exposure
- reversibility
- blast radius

## Minimal formula

```text
expected_net_value = expected_value - estimated_cost - risk_adjustment
```

Decision rule:

```text
if expected_net_value > threshold:
    ALLOW
elif estimate_missing:
    DEFER
elif high_uncertainty_or_high_cost:
    STEP_UP
elif expected_net_value <= 0:
    DENY
else:
    HALT
```

This formula is intentionally simple. The first implementation should be explainable before it is clever.

## Example

User request:

Generate 40 market reports from live web research.

ROI Gate estimates:

- high token cost
- many web/tool calls
- likely human review burden
- uncertain business value
- better alternative: generate 3 sample reports first

Decision:

STEP_UP or MODIFY.

Suggested action:

Run a small proof batch first.

## Enterprise value

The buyer is CFO, COO, Head of AI Operations, Risk, and GRC.

The pain is not only unsafe AI.

The pain is uncontrolled AI spend and invisible low-value agent work.

VALO ROI Gate gives organizations a policy point before agents burn cost.

## Relationship to Authority Layer

VALO's core position remains authority before action.

ROI Gate extends that position:

No action without authority.

No expensive action without expected value.

## First implementation target

Start with a simple deterministic estimator inside VAIG:

```text
task_type
model_class
estimated_tokens
estimated_tool_calls
estimated_runtime_minutes
human_review_required
cost_ceiling
value_floor
risk_level
reversibility
```

Return:

```text
decision
estimated_cost
estimated_value
risk_adjustment
expected_net_value
reason
receipt
```

## Non-goals

- Do not claim perfect ROI prediction.
- Do not optimize for financial markets.
- Do not replace CFO approval.
- Do not invent a new ACS primitive.
- Do not make probabilistic value estimates look certain.

## Build path

1. Add ROI estimate object to VAIG receipt metadata.
2. Add deterministic cost calculator for token/tool/runtime cost.
3. Add simple value premise field.
4. Add policy threshold configuration.
5. Add tests for ALLOW, STEP_UP, DEFER, DENY, HALT.
6. Add CLI demo: `vaig roi-check task.json`.

## One-line pitch

VALO ROI Gate stops agents from doing expensive low-value work.
