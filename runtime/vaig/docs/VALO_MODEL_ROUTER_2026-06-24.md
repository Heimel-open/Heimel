# VALO Model Router

Date: 2026-06-24
Status: v0.1 reference implementation

## Purpose

VALO Model Router selects the cheapest approved model that is good enough for a task.

Core rule:

Do not ask the best model. Ask the cheapest approved model that is good enough.

## Local-first assumption

The default future state is not that every task goes to a frontier cloud model.

The default future state is that every user, team and company has a small local model close to its context.

Examples:

- Ollama
- llama.cpp
- LM Studio
- embedded models
- private endpoints
- local enterprise runtimes

That local layer should do most low-risk context work before expensive remote tokens are spent.

## Flow

Intent
→ Authority Gate
→ ROI Gate
→ Model Router
→ Model call
→ Receipt

## Routing logic

The router evaluates:

- task type
- token estimate
- expected output size
- quality requirement
- reasoning requirement
- latency limit
- max cost
- data class
- jurisdiction
- tool requirement
- remote knowledge requirement
- risk level

Then it selects the cheapest eligible model.

If a local model is good enough, local wins.

If the task needs stronger reasoning, tool support, remote knowledge or compliance guarantees, it may route to private or remote models.

If no model is eligible, it denies or defers.

If the task is high risk, it routes to human approval after model selection.

## Files

- `vacs/src/model_router.py`
- `vacs/tests/test_model_router.py`

## Product position

Most companies do not have an AI problem.
They have an AI spend control problem.

VALO fixes that before the token is spent.
