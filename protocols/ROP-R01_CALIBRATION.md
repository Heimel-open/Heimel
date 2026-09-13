# ROP-R01 — Calibration Run v0.1

Registration status: PREREGISTERED
Execution status: NOT STARTED / READY TO RUN
Evidence status: NO OUTCOME EVIDENCE
Execution gate: execution must be performed by an executor separate from the blind scorer(s). The same agent or operator must not both execute and score the run.
Execution architecture: automated two-process pipeline with isolated contexts, executor without answer key, scorer without condition labels, immutable raw event logs, and distinct role/session IDs.
Only active blocker: NONE (execution gate resolved by two-process architecture).

Parent protocol: drafts/reduction-operator-01.txt
Purpose: validate instrumentation and scorer agreement, not domain-generality.

## Design

Use 24 matched arithmetic/algebra tasks: 8 easy, 8 medium, 8 hard. Each task has a unique answer, a frozen decomposition, and a dependency map. Generate two isomorphic forms per task and counterbalance them across conditions.

Conditions:
- C0 — normal unconstrained solving
- C2 — decomposition only
- C3 — Reduction Operator Protocol

Randomize task-form/condition assignment with a fixed seed before execution. Do not expose the condition label to scorers.

## Pre-registered hypotheses

H1: C3 reduces effective search cost versus C0 and C2 while preserving correctness.

H2: C3 does not reduce correctness by more than 5 percentage points versus the best control.

H3: two independent scorers agree on component classification and dependency-preservation decisions at Cohen's kappa >= 0.70.

## Per-task record

Record, before seeing the answer:
1. task_id, form_id, condition, participant/agent_id
2. full initial representation
3. candidate components and dependency edges
4. classification for every component:
   UNRESOLVED | RESOLVED | IRRELEVANT | REDUNDANT | DEPENDENCY-BEARING | UNKNOWN
5. every removal decision and reason
6. residual snapshot before mechanism identification
7. mechanism statement and reconstructed solution
8. correctness, confidence (0–100), time, steps, reversals, errors

No post-hoc reclassification is allowed. Corrections are appended as an audit event.

## Primary analysis

Correctness is binary and scored against the answer key. Effective search cost is:
ESC = z(time) + z(steps) + z(reversals) + z(errors)

Report paired condition differences with 95% confidence intervals. Report raw components as well as the composite; do not select the favorable metric after execution.

Dependency preservation is binary per required edge. Scorer agreement is measured before adjudication.

## Kill / stop rules

- Stop the run if task leakage, answer-key error, or condition blinding failure affects more than 1 task; quarantine affected tasks.
- Stop protocol progression if C3 correctness is >5 points below the best control, or if dependency preservation is below 95%.
- Stop progression to ROP-R02/R07 if scorer kappa <0.70 or if independent scorers cannot reproduce the removal decision on >=90% of audited decisions.
- Stop a reduction pass whenever materiality is UNKNOWN; retain the component.
- Do not alter hypotheses or task inclusion after inspecting outcomes.

## Deliverables

- frozen task set and seed
- assignment manifest
- per-task event log
- blinded scorer sheets
- adjudication log
- analysis output with raw and composite metrics
- deviation log and final go/no-go decision
