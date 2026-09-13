# Fluent pattern adoption for VALO Factory

Status: adopted pattern set
Source: `mrinalwadhwa/fluent` (Apache-2.0)
Adoption mode: clean-room architectural adaptation; external repository remains `knowledge_ref_only` and is not an authority source.

## Why this belongs in VALO Factory

Fluent models a software factory as a persistent loop from observations to shaped work, isolated attempts, independent testing and review, reusable learning, merge candidates, and post-merge feedback. This belongs in `nsolland/valo-factory`, because it concerns orchestration, work-state, worker separation, evidence flow, learning and landing. It does not belong in REHT, VAIG, RACS or Core.

VALO keeps its stricter boundary:

- Factory OS orchestrates but does not authorize consequence-bearing execution.
- VAIG evaluates; REHT clears; RACS enforces.
- Human authority is explicit and cannot be inferred from prompts, credentials, queue membership, prior approval or agent confidence.
- Tests, reviews and learner output are evidence, not authority.
- Merge remains SHA-bound, policy-bound and subject to separation of duties.

## Adopted concepts

### 1. Observation as durable intake

Any idea, defect, user signal, production trace, review finding or operational anomaly enters the factory as an `Observation` before it becomes work.

An Observation records:

- source and timestamp
- affected repository and files when known
- evidence references
- confidence and uncertainty
- proposed owner
- whether it concerns code, policy, authority, security or operations
- links to earlier related observations

An Observation creates no execution authority.

### 2. Shaping before delegation

Work is shaped through four explicit artifacts:

1. `Brief`: what should change, why, scope, constraints and unknowns.
2. `BehaviorSpec`: externally observable behavior and verification reference.
3. `TechnicalApproach`: approved interfaces, boundaries and technical decisions.
4. `ImplementationPlan`: independently reviewable work items, dependencies and evidence gates.

VALO adds mandatory authority fields to the handoff:

- principal
- authority basis
- repository and path scope
- allowed action classes
- expiry
- risk class
- required REHT/VAIG/RACS path
- required human decision points

### 3. Work Item and Attempt separation

A `WorkItem` is the approved contract for a bounded delivery. An `Attempt` is one concrete execution of that contract.

This prevents retry history, failed runs and agent behavior from mutating the approved task definition. Every Attempt receives its own:

- isolated worktree
- run identifier
- exact base SHA
- worker identity
- bounded credentials
- progress record
- test evidence
- review evidence
- terminal receipt

### 4. Separate human-attention and compute queues

Factory OS maintains two independent queues:

- `human_queue`: authority decisions, missing context, ambiguous conflicts, policy changes and unresolved reviewer uncertainty
- `execution_queue`: authorized work waiting for a suitable worker, model, environment, budget or hardware profile

Work waiting on a human decision does not block unrelated authorized work.

### 5. Independent deterministic tester

The Writer never attests its own correctness. A separate deterministic Tester executes repository-declared commands and emits a normalized, immutable result artifact bound to:

- attempt ID
- candidate commit SHA
- test configuration digest
- command, exit code and duration
- normalized per-test result when available
- environment identity

Reviewers may run targeted checks, but the shared test artifact is the canonical suite evidence for that Attempt.

### 6. Parallel specialist reviewers

After testing, independent reviewers run in parallel where file and responsibility boundaries do not collide.

Initial VALO reviewer set:

- behavior reviewer
- architecture and boundary reviewer
- test-quality reviewer
- documentation reviewer
- security and authority-boundary reviewer
- agent-skill reviewer when skills change

Each finding is one of:

- `blocking`
- `minor`
- `uncertain`

Each reviewer returns `pass`, `fail` or `uncertain`. Uncertainty that requires authority or product judgment goes to the human queue. Reviewers cannot modify candidate code.

### 7. Bounded correction rounds

A failed review returns concrete blocking findings to the Writer. The Writer produces a new candidate SHA; the deterministic Tester reruns; affected reviewers reassess.

Default maximum: three correction rounds. At the limit, the Attempt transitions to `NEEDS_HUMAN` with all evidence preserved. It must not continue recursively without a new authorization decision.

### 8. Learner with no authority

After all required gates pass, a separate Learner extracts reusable project expertise and follow-up Observations.

The Learner may propose:

- repository conventions
- recurrent failure patterns
- test strategies
- architectural constraints
- operational lessons
- candidate follow-up work

The Learner may not:

- alter policy or authority
- widen scope
- mark its own output as trusted truth
- queue consequence-bearing work without the configured authorization path
- overwrite canonical Index knowledge

Learned material is provenance-bound and enters as evidence pending acceptance.

### 9. Merge Candidate as a first-class object

A passing Attempt produces a `MergeCandidate`, not an automatic merge.

The Merge Candidate binds:

- Work Item contract digest
- Attempt ID
- exact head SHA
- target branch and current target SHA
- test artifact digest
- review artifact digests
- learner handoff digest
- risk class
- required landing policy
- REHT clearance and RACS decision references where applicable

Landing must revalidate target drift, clean worktrees, policy mode, CI and SHA-bound attestations.

### 10. Post-merge observation loop

Optional post-merge checks examine deployment jobs, runtime traces and production outcomes. New findings return as Observations. They do not silently mutate the merged task or create authority for corrective execution.

## Canonical VALO flow

```text
Signal / idea / trace / finding
  -> Observation
  -> Shaping
       Brief
       BehaviorSpec
       TechnicalApproach
       ImplementationPlan
       AuthorityEnvelope
  -> WorkItem
  -> REHT clearance for attempt start
  -> Attempt in isolated worktree
       Writer
       Deterministic Tester
       Parallel independent Reviewers
       bounded correction rounds
       Learner
  -> MergeCandidate
  -> REHT clearance for landing
  -> RACS enforcement
  -> Merge receipt
  -> Deployment / production observation
  -> new Observation
```

## State model extension

Existing orchestration states remain valid. Add these domain states without weakening current safety gates:

```text
OBSERVED
SHAPING
AWAITING_SHAPE_DECISION
WORK_ITEM_READY
QUEUED
ATTEMPT_RUNNING
TESTING
REVIEWING
REVISION_REQUIRED
LEARNING
MERGE_CANDIDATE_READY
AWAITING_LAND_AUTHORITY
LANDED
POST_MERGE_OBSERVING
```

Terminal or exception states:

```text
BLOCKED
NEEDS_HUMAN
CANCELLED
INCIDENT_HOLD
SUPERSEDED
```

## Non-adopted assumptions

VALO does not adopt the following as authority rules:

- conversation confirmation as sufficient authorization
- queue admission as authorization
- automatic corrective execution based only on learner confidence
- agent-resolved merge conflicts without bounded authority and independent verification
- project expertise as canonical truth
- possession of repository credentials as permission

## Attribution and license

The source repository is Apache-2.0. This document adopts architectural patterns and vocabulary with attribution. No source code has been copied into VALO Factory in this change.