# VALO Efficiency Engine

Date: 2026-06-24
Status: v0.1 reference implementation

## Purpose

VALO Efficiency Engine measures real value creation.

The unit is not cost per token.

The unit is verified value per dollar.

## Core formula

TCW = Total Cost of Work

TCW includes:

- model cost
- compute cost
- tool/API cost
- storage cost
- human time
- review
- correction
- compliance
- latency
- maintenance
- risk
- opportunity cost

VVC = Verified Value Created

VVC includes:

- time saved
- cost avoided
- risk reduced
- quality improved
- revenue enabled
- reuse value
- audit value
- learning value

VES = Verified Efficiency Score

VES = VVC / TCW

## Flow

Claim
→ Evidence
→ Observation
→ Verification
→ Credit

Never:

Claim
→ Credit

## Verification levels

`claimed`

A person or agent says value exists.
Heavy discount. No automatic credit.

`estimated`

There is a baseline or model, but limited usage.
Still weak.

`observed`

The workflow has been used more than once.
Value is partially discounted.

`verified`

There is usage, evidence receipt, and enough repetition.
Value can become credit if it beats total cost of work.

## Decisions

`CREDIT`

Verified value exceeds total cost of work.

`OBSERVE`

Promising, but not verified enough yet.

`DEFER`

Missing evidence.

`DENY`

No real value, worse error rate, or poor efficiency.

`HALT`

Invalid data.

## Why this matters

A cheap model can be expensive if it creates bad work.

An expensive model can be cheap if it prevents review, errors, rework, or risk.

Most systems optimize token cost.

VALO optimizes real value.

## Files

- `vacs/src/efficiency_engine.py`
- `vacs/tests/test_efficiency_engine.py`

## Product position

Cost per token is infrastructure accounting.

Verified value per dollar is business accounting.

VALO should own the second one.
