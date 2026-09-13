# CAN / SHOULD / WHY VU Meter — Design Specification

Status: design spec — operator-facing signal model  
Related: issue #9, issue #10, `management_overlay/`

---

## Core model

Three governance signals — one for each governance axis:

| Signal | Axis | Question |
|---|---|---|
| CAN | Capability / tool permission | Does the agent have the permission to do this? |
| SHOULD | Policy / admissibility | Is this action admissible under current policy? |
| WHY | Justification continuity | Is the reasoning chain intact and grounded? |

Supporting signals:

| Signal | Axis | Question |
|---|---|---|
| WORM | Proof / evidence chain | Is the audit trail intact? |
| SSIP | Integrity / forensic mode | Is the governance state itself trustworthy? |

---

## Status palette

| Status | Meaning | Action class |
|---|---|---|
| GREEN | All signals nominal | Continue |
| YELLOW | Degradation detected | Watch |
| ORANGE | Threshold crossed | Human review required |
| RED | Boundary hit | Halt — consequence blocked |
| PURPLE | System trust event | Forensic mode — governance state in question |

**Critical distinction:**

> Traffic light (GREEN → RED) = action risk.  
> Purple = system trust risk.

RED blocks an action.  
PURPLE means the trustworthiness of the governance state itself is in question.

---

## Aggregation rule

Do not average CAN, SHOULD, WHY.  
Use weakest link:

```text
overall = worst(CAN, SHOULD, WHY)
```

Where `worst` = the signal at highest danger level among the three.

**Rationale:** High CAN + high SHOULD + low WHY is still unsafe.

**PURPLE override:** If WORM or SSIP signals integrity degradation, the overall status is PURPLE regardless of CAN / SHOULD / WHY values. Consequence commitment is disabled.

---

## Display formats

### Compact operator display

```
VALO: ORANGE — HUMAN REVIEW
Reason: WHY continuity degraded
Receipt: WORM hash available
```

### Expanded display

```
CAN     [====    ] OK
SHOULD  [====    ] OK
WHY     [==      ] DEGRADING

STATUS: ORANGE — HUMAN REVIEW
Reason: WHY continuity below threshold
Receipt: WORM hash available
```

### Purple display

```
STATUS: PURPLE — SYSTEM TRUST EVENT
Reason: OOB / WORM / SSIP integrity degraded
Consequence commitment: DISABLED
Evidence: PRESERVED
```

---

## Device signal mapping

| Status | Haptic | Audio |
|---|---|---|
| GREEN | None | None |
| YELLOW | One light short tap | Low tick |
| ORANGE | Two short taps | Soft alert |
| RED | One long vibration | Hard stop tone |
| PURPLE | Three short + one long | Critical integrity tone |

---

## Device surfaces

| Surface | Display |
|---|---|
| Phone | Color banner + haptic + receipt drawer |
| Watch | Short status phrase + haptic pattern |
| Desktop | VU meters + decision banner + receipt hash |
| Audio | Optional alert tone for ORANGE, RED, PURPLE only |

---

## Accessibility rule

Never rely on color, haptics, or audio alone.  
Use: **color + text + icon + optional haptic/audio**.

---

## Icon suggestions

| Signal | Icon |
|---|---|
| CAN | Gear / plug / key |
| SHOULD | Shield / gate |
| WHY | Question mark / chain |
| WORM | Receipt / lock / chain |
| SSIP | Vault / emergency brake / integrity pulse |

---

## Implementation boundary

This spec drives `management_overlay/signals/can_should_why.py` and `management_overlay/api/status.py`.

Aggregation logic: `management_overlay/signals/can_should_why.py`  
Status object: `management_overlay/api/status.py`  
Leadership view: `management_overlay/docs/leadership-overlay.md`

Do not embed display constants or private thresholds in any public-facing UI — expose receipt hash references only.
