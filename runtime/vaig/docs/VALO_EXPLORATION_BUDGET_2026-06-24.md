# VALO Exploration Budget

Date: 2026-06-24
Status: v0.1 reference implementation

## Purpose

VALO must control cost without killing creativity.

Hard ROI is right for production work.
Hard ROI is wrong for early exploration.

Exploration Budget gives every employee, team, or project a bounded AI wallet for safe experimentation.

Core rule:

VALO does not stop experimentation.
VALO stops uncontrolled spend.

## Why this exists

Many useful ideas look uneconomic before they mature.

If every prompt needs a business case, people stop exploring.
If every agent can spend freely, the company burns tokens and leaks context.

The answer is not no.
The answer is bounded yes.

## Spend classes

- `production`
- `experiment`
- `learning`
- `play`
- `incident`
- `regulated_action`

Exploration Budget applies to:

- `experiment`
- `learning`
- `play`

Production work routes to ROI Gate.
Regulated or high-risk work routes to human approval.

## Wallet dimensions

A wallet can limit:

- money
- local tokens
- remote tokens
- frontier calls
- period
- owner

This supports a future where most context work starts locally through Ollama, llama.cpp, LM Studio, embedded models, or private enterprise runtimes.

## Default behavior

Low-risk exploration inside budget:

ALLOW

Production work:

DEFER to ROI Gate

Secret or restricted data:

DENY

Personal data:

STEP_UP

Frontier model use:

STEP_UP

External action:

STEP_UP

Irreversible action:

STEP_UP

Missing learning objective:

DEFER

## Flow

Intent
→ Spend class
→ Exploration Budget or ROI Gate
→ Model Router
→ Receipt

## Files

- `vacs/src/exploration_budget.py`
- `vacs/tests/test_exploration_budget.py`

## Product position

No action without authority.
No expensive action without expected value.
No remote token before local context is exhausted.
No creativity killed by premature ROI.

## Key sentence

Bounded exploration is not waste.
Unbounded execution is waste.
