# WHY Gate + SSIP architecture

## Core formulation

```text
CAN asks capability.
SHOULD asks policy.
WHY asks continuity.
```

WHY Gate is the runtime mechanism that continuously verifies that the justification for execution remains valid until consequence commitment.

```text
No consequence commitment without a valid answer to WHY.
```

## Stack placement

```text
TOFOO
  Identity / meaning

LIM
  Coherence

VAIG
  Admissibility

WHY Gate
  Justification continuity

SSIP
  Integrity preservation, rollback and forensic recovery

WORM / OOB Reservoir
  Evidence

COMMIT / HALT / REVERT
  Consequence control
```

## WHY Gate responsibility

WHY Gate answers one question:

```text
Is the reason for this action still valid at the point of consequence commitment?
```

Minimum continuity checks:

```text
Authority
Is the authority still valid?

Policy
Is the governing rule still valid?

Reality
Is the model of the world still valid?

Consequence
Is the consequence still acceptable?
```

WHY Gate does not replace VAIG. VAIG decides admissibility. WHY Gate checks whether the reason remains valid until consequence commitment.

## Thresholds

Initial policy mapping:

| WHY score | Decision | Meaning |
|---:|---|---|
| `>= 0.85` | `CONTINUE` | Legitimacy continuity remains strong |
| `>= 0.65 and < 0.85` | `WATCH` | Continue with increased monitoring |
| `>= 0.45 and < 0.65` | `HUMAN_REVIEW` | Justification degraded; require review |
| `< 0.45` | `HALT` | Continuity failed; block consequence commit |

Use minimum aggregation in the first implementation:

```text
why_score = min(authority, policy, reality, consequence)
```

One broken reason is enough to block or escalate the action.

## WHY Proof

Each WHY decision should produce a hash-linked state object:

```json
{
  "why_id": "why_...",
  "action_id": "act_...",
  "timestamp": "...",
  "authority_score": 0.93,
  "policy_score": 0.91,
  "reality_score": 0.88,
  "consequence_score": 0.86,
  "why_score": 0.86,
  "decision": "CONTINUE",
  "previous_hash": "...",
  "state_hash": "..."
}
```

A sequence of WHY states forms a WHY Proof:

```text
WHY-1 -> WHY-2 -> WHY-3 -> COMMIT
```

This is the VALO/VAIG counterpart to a continuity proof object.

## SSIP boundary

SSIP is not the same thing as WHY Gate.

WHY Gate answers:

```text
Does the justification still hold?
```

SSIP answers:

```text
What must the system do when governance integrity, logging integrity or legitimacy continuity degrades?
```

The Self-Scaling Integrity Protocol contributes:

- out-of-band WORM reservoir;
- temporal anchoring;
- rollback interlock;
- operational deferment;
- hysteresis recovery logic;
- reversion module;
- governance immutable snapshots;
- post-incident forensic review.

## Implementation modules

Recommended module map:

```text
vaig/why_gate.py
vaig/ssip/__init__.py
vaig/ssip/deferment.py
vaig/ssip/evidence_pack.py
vaig/ssip/oob_reservoir.py
vaig/ssip/pifr.py
vaig/ssip/reversion.py
```

## Implementation rule

Build minimal, testable runtime first:

```text
WHY State
WHY Score
WHY Chain
Consequence Commit Gate
WORM Receipt extension
```

Do not start with a full governance platform, blockchain system or complex mathematical L(t). The first version should prove the runtime principle.
