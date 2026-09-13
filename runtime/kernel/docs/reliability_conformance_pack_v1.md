# Reliability Conformance Pack v1

Status: implementation candidate  
Scope: deterministic reliability testing for bounded workflows

## Purpose

The pack converts discovered workflow failure modes into repeatable,
machine-executable conformance scenarios:

```text
scenario -> one controlled state change -> expected invariant
         -> observed behavior -> evidence -> PASS / FAIL / INSUFFICIENT_EVIDENCE
```

It is general infrastructure. Healthcare is the first domain profile, not a
separate evaluation product or a permanent manual service.

## Boundary

Reliability conformance asks whether a configured workflow preserves an
explicit invariant under a controlled change. It does not determine whether an
actor has authority and it does not authorize or execute an action.

`PASS` means only that the observation is eligible to proceed to the separate,
fresh REHT authorization boundary. Every report therefore carries
`authorization_effect = NO_AUTHORITY_CREATION`.

The chain remains:

```text
workflow candidate -> reliability conformance -> fresh Kernel context
                   -> REHT -> RACS -> Gateway -> Veritas
```

## Contract

Each scenario binds:

- a versioned profile and scenario identifier;
- one baseline state;
- exactly one controlled state change;
- the invariant and expected observable behavior;
- the evidence required to evaluate the observation.

The evaluator compares exact scenario binding, baseline, transitioned state,
required evidence and expected behavior. Identical inputs produce an identical
report and evidence digest.

Outcomes are:

- `PASS`: the declared invariant held and required evidence is present;
- `FAIL`: observed state or behavior violated the scenario;
- `INSUFFICIENT_EVIDENCE`: scenario binding, baseline or required evidence is
  missing or inconsistent.

Only `PASS` is eligible for a separate authorization decision. No outcome grants
authority.

## Healthcare profile v1

The initial profile makes three reliability boundaries executable:

1. State change reliability: earlier clinical truth cannot silently remain
   current after governed state changes.
2. Contradictory evidence: material contradiction prevents silent continuation.
3. Context transfer reliability: decision-relevant context survives transfer or
   the workflow fails closed.

New domains add profiles and scenarios against the same evaluator. Research may
discover new boundaries; once stable, those boundaries become versioned
conformance cases rather than recurring manual interpretation.

## Non-goals

- clinical certification or regulatory approval;
- judging model quality in general;
- replacing human clinical responsibility;
- creating authority from a passing test;
- making any named external evaluator a runtime dependency.
