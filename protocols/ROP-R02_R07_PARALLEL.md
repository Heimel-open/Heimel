# ROP-R02 + ROP-R07 — Parallel Run Design v0.1

Status: preregistered / ready after ROP-R01 instrumentation gate
Parent protocol: drafts/reduction-operator-01.txt

## Shared design

Use unfamiliar constraint-satisfaction problems with decoy facts, explicit cross-dependencies, and a unique verifiable solution. Build 20 matched task pairs per run:
- ROP-R02: 10 ordinary-decoy tasks + 10 mixed-coupling tasks
- ROP-R07: 10 adversarial relational tasks + 10 matched ordinary tasks

Conditions are C0, C2, and C3. Assign task forms and conditions using one fixed seed; counterbalance order. Executors see only the task and condition instructions. Scorers see only the final solution and the frozen dependency map.

Primary outcomes:
1. solution correctness
2. required-relation preservation
3. effective search cost
4. false-removal rate
5. confidence calibration

## ROP-R02 — normal generalization

Decoys are facts that do not participate in the solution. Necessary relations are distributed across the task and may not be inferred from any single statement. The expected C3 behavior is removal of decoys while retaining all edges in the dependency map.

Pre-registered failure criterion: C3 fails ROP-R02 if correctness is >5 percentage points below the best control, or false-removal rate exceeds 5%.

## ROP-R07 — adversarial kill test

Construct each task so that at least one pair of individually removable-looking statements jointly encodes a necessary relation. Examples include:
- two constraints whose intersection excludes the only invalid candidate
- a repeated-looking qualifier that changes scope
- a symmetric-looking pair whose ordering carries direction
- a decoy-like fact that becomes necessary only after one legitimate reduction

The adversarial generator and answer key must be frozen before execution. Include a hidden trap-edge label for analysis, not for executors.

Pre-registered failure criterion: any C3 false removal of a trap edge is a protocol failure for that task; aggregate failure if trap-edge preservation is <95% or correctness is >5 points below the best control.

## Blinding and adjudication

Scorers are blind to condition and executor identity. A second scorer independently marks:
- whether each required relation survived
- whether every removed item was safely removable
- whether the final answer follows from the residual plus reconstruction

Disagreements are recorded and adjudicated by a third reviewer. Adjudication cannot rewrite the executor event log.

## Parallelization rule

Run ROP-R02 and ROP-R07 with separate task pools, executor sessions, and scorer sheets. Analyze each run separately first. Only then produce a combined comparison. A positive ROP-R02 result cannot offset an ROP-R07 trap-edge failure.

## Go/no-go

- GO to ROP-R08 only if ROP-R01 passes instrumentation and both ROP-R02 and ROP-R07 meet their criteria.
- NARROW the claim if ROP-R02 passes but ROP-R07 fails: reduction helps on separable tasks but is unsafe under hidden relational coupling.
- STOP and record FAILURE if the task generator, blinding, or dependency map is not auditable.
