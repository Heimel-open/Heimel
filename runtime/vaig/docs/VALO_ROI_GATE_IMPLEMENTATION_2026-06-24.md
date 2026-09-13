# VALO ROI Gate Implementation

Date: 2026-06-24
Status: v0.1 reference implementation

## Purpose

VALO ROI Gate is a deterministic pre-action value gate for AI agents.

Authority Gate asks:

> Does the agent have the right to act?

ROI Gate asks:

> Is the action worth the expected cost and risk?

Core rule:

> No expensive action without expected value.

## Flow

Intent
→ Authority check
→ ROI estimate
→ ROI policy
→ Decision
→ Receipt

## Inputs

`ROIEstimate`:

- `action_id`
- `expected_value_usd`
- `estimated_cost_usd`
- `risk_cost_usd`
- `review_cost_usd`
- `confidence`
- `reversible`
- `value_basis`
- `cost_basis`

`ROIPolicy`:

- `min_net_value_usd`
- `min_roi_ratio`
- `max_cost_without_step_up_usd`
- `min_confidence`
- `halt_on_irreversible_negative_value`

## Decisions

`ALLOW`

The action has acceptable expected value, cost, risk and confidence.

`STEP_UP`

The action may be worth doing, but the expected cost exceeds automatic approval limits.

`DEFER`

The value estimate is too uncertain. The agent should not spend more until the premise improves.

`DENY`

The action costs more than it is expected to return.

`HALT`

The estimate is invalid, or an irreversible action has negative expected value.

## Files

- `vacs/src/roi_gate.py`
- `vacs/tests/test_roi_gate.py`
- `examples/roi_gate_demo.py`

## Example

```bash
python examples/roi_gate_demo.py
```

## Positioning

Most companies will not lose money because AI fails.
They will lose money because AI works too much.

VALO ROI Gate stops agents from doing expensive low-value work.
