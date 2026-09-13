# VALO Value Weighting

Date: 2026-06-24
Status: v0.1 reference implementation

## Purpose

VALO should not reward large claims.

VALO should reward hard evidence, repeatability, clear attribution, and strategic value.

## Formula

Weighted Value = raw value
× evidence weight
× duration weight
× attribution weight
× strategic weight
− risk cost
− extra cost

## Evidence weight

- claimed: 0.10
- estimated: 0.30
- observed: 0.60
- verified: 1.00
- audited: 1.20

## Duration weight

- one-time: 0.30
- weekly: 0.70
- daily: 1.00
- cross-team reuse: 1.50
- platform effect: 2.00

## Attribution weight

- unclear: 0.30
- team: 0.60
- direct: 1.00
- split: 0.80

## Strategic weight

- low priority: 0.50
- normal: 1.00
- critical process: 1.50
- regulatory risk reduction: 2.00
- new revenue: 2.00

## Example

100,000 USD estimated value
× 0.30 estimated evidence
× 0.70 weekly use
× 0.60 team attribution
× 1.00 normal priority
= 12,600 USD weighted value

The same 100,000 USD with verified evidence, daily use, direct attribution, and normal priority:

100,000 × 1.00 × 1.00 × 1.00 × 1.00
= 100,000 USD weighted value

## Decisions

`ACCEPT`

Weighted value is positive, baseline exists, and evidence is strong enough.

`OBSERVE`

Value is promising, but evidence is only claimed or estimated.

`DEFER`

Baseline is missing.

`DENY`

Weighted value is not positive or below threshold.

`HALT`

Invalid negative inputs.

## Files

- `vacs/src/value_weighting.py`
- `vacs/tests/test_value_weighting.py`

## Product position

The economy should not reward activity.

It should reward verified change in the world.
