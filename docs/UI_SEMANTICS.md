# VALO UI Safety Semantics

**Purpose:** define the human-facing safety language for VAIG/VALO without changing the canonical machine codes.

This document is canonical for UI labels, operator wording, traffic-light colors and VU-meter display semantics.

---

## Core Rule

Use two layers:

```text
Machine/audit layer: precise canonical codes
Human/UI layer: intuitive labels, colors and VU-meter states
```

Do not expose only `ALLOW`, `HALT`, `DENY` etc. in the operator UI. These are machine/audit terms. Operators should see simple status words and traffic-light colors.

---

## Canonical VALO UI Levels

| Level | UI Label | Color | Operator meaning | Machine level | Governance decision |
|---|---|---|---|---|---|
| L0 | CLEAR | Green | Normal flow | `L0_TRUSTED` | `ALLOW` |
| L1 | WATCH | Blue/Green | Watch but allow | `L1_MONITOR` | `ALLOW` |
| L2 | FRICTION | Yellow | Something needs correction | `L2_WARN` | `MODIFY` |
| L3 | COUNCIL | Orange | Human review required | `L3_DEFER` | `DEFER` |
| L4 | LOCK | Red | Stop / locked | `L4_HALT` | `HALT` |

---

## VU Meter Model

The operator interface should show risk as a VU-meter / traffic-light scale.

```text
0%        25%        50%        75%        100%
|---------|----------|----------|----------|
CLEAR     WATCH      FRICTION   COUNCIL    LOCK
Green     Blue/Green Yellow     Orange     Red
```

The goal is instant comprehension. An operator should understand system state in less than one second.

---

## Display Contract

Every runtime result should be representable with both canonical code and VALO label.

Example:

```json
{
  "level_code": "L4_HALT",
  "level_label": "LOCK",
  "decision_code": "HALT",
  "ui_color": "red",
  "operator_text": "System locked. Human review required.",
  "transport_outcome": "BLOCKED"
}
```

---

## Separation of Concepts

Do not collapse these concepts into one enum.

| Concept | Purpose | Examples |
|---|---|---|
| Machine level | stable internal/audit state | `L0_TRUSTED`, `L4_HALT` |
| UI label | human-facing display | `CLEAR`, `WATCH`, `FRICTION`, `COUNCIL`, `LOCK` |
| Governance decision | what VAIG decided | `ALLOW`, `MODIFY`, `DEFER`, `DENY`, `HALT`, `STEP_UP` |
| Transport outcome | what the adapter did | `FORWARDED`, `BLOCKED`, `DEFERRED`, `FAILED` |
| L1 outcome | Rust guardian result | `ALLOW`, `DEGRADED`, `HALT`, `LOGFULLHALT` |

---

## Operator Copy

Recommended short operator messages:

| UI Label | Operator text |
|---|---|
| CLEAR | Normal. Output cleared. |
| WATCH | Allowed, but monitored. |
| FRICTION | Output requires correction or warning. |
| COUNCIL | Human review required before release. |
| LOCK | Locked. Output blocked. Escalation required. |

---

## Implementation Guidance

Code may use stable enums such as:

```python
class MachineLevel(Enum):
    L0_TRUSTED = "L0_TRUSTED"
    L1_MONITOR = "L1_MONITOR"
    L2_WARN = "L2_WARN"
    L3_DEFER = "L3_DEFER"
    L4_HALT = "L4_HALT"
```

UI rendering should map these to display labels:

```python
UI_LEVELS = {
    "L0_TRUSTED": {"label": "CLEAR", "color": "green"},
    "L1_MONITOR": {"label": "WATCH", "color": "blue-green"},
    "L2_WARN": {"label": "FRICTION", "color": "yellow"},
    "L3_DEFER": {"label": "COUNCIL", "color": "orange"},
    "L4_HALT": {"label": "LOCK", "color": "red"},
}
```

---

## Assistant Rule

AI assistants may not rename these labels ad hoc.

If alternative naming is proposed, it must preserve:

1. machine code stability,
2. audit clarity,
3. operator intuitiveness,
4. traffic-light comprehension,
5. VU-meter ordering.

---

## Current Decision

Canonical VALO UI naming:

```text
CLEAR -> WATCH -> FRICTION -> COUNCIL -> LOCK
```

Canonical design metaphor:

```text
VU meter + traffic light colors
```
