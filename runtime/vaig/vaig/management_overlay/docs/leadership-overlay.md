# VALO Executive Overlay — Leadership View

Status: implemented  
Audience: operators, executives, compliance leads  
Implementation: `vaig/management_overlay/`

---

## What this is

The Executive Overlay translates VAIG's internal governance signals into three operator-facing indicators:

| Signal | Plain meaning |
|---|---|
| CAN | Does the agent have permission to do this? |
| SHOULD | Is this action allowed under current policy? |
| WHY | Is the reasoning chain intact and grounded? |

These three signals are the minimum a human operator needs to make an informed decision about whether to allow, watch, or halt an AI action.

---

## Status palette

| Status | What it means | What to do |
|---|---|---|
| GREEN | All signals nominal | Continue |
| YELLOW | Degradation detected | Watch closely |
| ORANGE | Threshold crossed | Require human review |
| RED | Boundary hit | Halt — consequence blocked |
| PURPLE | Governance state in question | Forensic mode — disable consequence commitment |

**Critical distinction:** GREEN through RED measure action risk. PURPLE measures whether the governance system itself can be trusted. PURPLE disables consequence commitment until integrity is restored.

---

## Aggregation rule

The overall status is the worst of the three signals:

```
overall = worst(CAN, SHOULD, WHY)
```

High CAN + high SHOULD + low WHY is still unsafe.

PURPLE overrides all: if WORM or SSIP integrity is degraded, the status is PURPLE regardless of CAN / SHOULD / WHY values.

---

## What operators see

On ORANGE or RED, the display shows:

```
VALO: ORANGE — HUMAN REVIEW
Reason: WHY continuity degraded
Receipt: WORM hash <hash>
```

On PURPLE:

```
STATUS: PURPLE — SYSTEM TRUST EVENT
Reason: OOB / WORM / SSIP integrity degraded
Consequence commitment: DISABLED
Evidence: PRESERVED
```

---

## What this does not do

- It does not predict events — it reports current governance state
- It does not make authorization decisions — AARM does that
- It does not store raw content — only receipt hashes are exposed at the operator surface
- It does not replace human judgment — it routes attention to where judgment is needed

---

## Implementation boundary

| Module | Purpose |
|---|---|
| `vaig/management_overlay/signals/can_should_why.py` | SignalLevel, OverlaySignals, aggregate() |
| `vaig/management_overlay/api/status.py` | OverlayStatus, render_compact(), render_expanded() |
| `tests/test_management_overlay.py` | 26 tests covering aggregation, PURPLE override, display formats |

Related: `docs/can-should-why-vu-meter.md` (full design spec)
