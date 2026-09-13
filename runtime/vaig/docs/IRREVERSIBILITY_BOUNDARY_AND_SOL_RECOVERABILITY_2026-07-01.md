# Irreversibility Boundary and SOL Recoverability Model

Date: 2026-07-01  
Status: repository architecture design note  
Scope: VALO / SOL / ACT / PNR / PERT / TAD / AGR

This note does not replace `SYSTEM_MAP.md`.

## Core problem

Governance cannot only decide whether an action may begin.

It must also determine whether an action may safely be interrupted once execution has started.

Some operations are reversible.

Some operations are not.

Stopping an irreversible operation mid-execution may create greater harm than allowing the atomic operation to complete.

## Core concept

Introduce:

```text
PNR — Point of No Return
```

Also called:

```text
Irreversibility Boundary
```

PNR is the point inside an execution path after which the action cannot be safely interrupted without causing greater harm than controlled completion.

## Architectural responsibility

The Execution Layer owns and enforces PNR.

SOL must know PNR before selecting an action.

```text
SOL evaluates reversibility before selection.
ACT enforces interruptibility during execution.
PERT reconciles the outcome after execution.
NJAL records the proof chain.
```

## Execution rule

```text
Before PNR:
    Safe abort is allowed.

After PNR:
    Atomic completion is allowed.
    New actions are locked.
    Full validation, compensation or human review is required before continuation.
```

## TAD contract violation during execution

If a TAD validity contract breaks while an action is already running, the system must branch based on PNR.

```text
IF contract_broken AND before_PNR:
    abort safely
    route to full validation

IF contract_broken AND after_PNR:
    allow atomic completion
    lock new actions
    require PERT reconciliation
    require compensation or human review
```

## SOL admissibility filter

SOL must not weigh every action as a pure numeric tradeoff.

Irreversibility is first a hard boundary, not merely a soft variable.

Before SOL scores options, it runs an admissibility filter.

```text
Irreversible + no verified compensation + no escalation rule
→ not admissible
```

The action is then either:

```text
Optional action:
    reject

Necessary or only available action:
    STEP_UP / human approval / quorum
```

SOL only optimizes across actions that have already passed admissibility.

## Recoverability principle

In governance optimization, recoverability outranks expected correctness when consequences are irreversible.

```text
Recoverability outranks expected correctness
when consequences are irreversible.
```

The reason is simple:

Governance does not only maximize expected value.

Governance preserves control if the system's assumptions turn out to be wrong.

## SOL scoring after admissibility

After the hard admissibility filter, SOL may rank allowed actions using recoverability-aware scoring.

Conceptual scoring model:

```text
score =
  expected_value
- risk
- uncertainty
- irreversibility_penalty
+ reversibility_credit
+ compensation_credit
+ trust_recovery_credit
```

But the score cannot override the hard gate.

```text
If trust cannot be recovered after failure,
the action requires STEP_UP or rejection.
```

## Reversible high-risk vs irreversible low-risk

A reversible high-risk action may be preferable to an irreversible low-risk action if:

- the outcome space is bounded
- rollback is verified
- compensation is available
- PERT can reconcile outcome
- trust can be restored if assumptions fail

An irreversible low-risk action may be allowed only if:

- it is pre-authorized or explicitly approved
- the benefit margin is sufficient
- compensation resources are reserved
- escalation rules are defined
- receipts and proof are complete

## Governing question

The key question is not only:

```text
Which action is most likely to be correct?
```

The governance question is:

```text
Which admissible action preserves governability if it is wrong?
```

## New SOL principle

```text
The best admissible action is not the action most likely to be correct.
It is the action that preserves governability if it is wrong.
```

## Updated VALO flow

```text
VAIG
    ↓
AGR
    ↓
SOL
    • admissibility filter
    • risk class
    • reversibility
    • Point of No Return
    • compensation strategy
    • recoverability score
    ↓
ACT
    • before PNR → safe abort
    • after PNR → atomic completion
    ↓
PERT
    • outcome reconciliation
    • compensation required?
    ↓
NJAL
    • proof
    • receipt
```

## Research paper candidate

Potential title:

```text
Execution Continuity Governance: Irreversibility Boundaries and Recoverability in Autonomous Systems
```

Core contribution:

A runtime governance architecture must distinguish between interruptible and non-interruptible execution segments, and must optimize not only for expected correctness but for recoverability under failed assumptions.
