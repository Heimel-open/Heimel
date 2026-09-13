# NJAL-R01 — Reversible Workspace Run v0.1

Registration status: PREREGISTERED
Execution status: NOT STARTED / DESIGN FROZEN
Evidence status: NO OUTCOME EVIDENCE
Parent observation: ROP-R01 NO_GO, where explicit irreversible reduction increased ESC, reduced correctness, and degraded dependency preservation.

## Purpose

Test whether the failure mode observed in ROP-R01 is caused primarily by irreversible model-local pruning rather than decomposition itself, and whether a governed reversible workspace can reduce active cognitive load without destroying downstream dependencies.

This is a new experiment. ROP-R01 remains unchanged and is not repaired post hoc.

## Core method

The Njål Method under test is:

1. Define what the current problem requires.
2. Check whether required state is active.
3. If not active, check whether it exists in latent state.
4. If absent from both, identify the missing dependency explicitly.
5. Activate only what is required for the current step.
6. Never let a model-local relevance judgment irreversibly delete potentially material state.
7. Keep candidate removals recoverable until downstream dispensability is evidenced.
8. Reconcile final output with lineage, dependency preservation, and restore history.

Primary invariant:

`CLASSIFICATION_IS_NOT_DELETION_AUTHORITY`

Supporting invariant:

`ABSENCE_FROM_ACTIVE_WORKSPACE_DOES_NOT_IMPLY_ABSENCE_FROM_SYSTEM_STATE`

## Experimental question

Can reversible latent-state organization preserve correctness and dependency structure while reducing the active workspace compared with decomposition-only reasoning, and avoid the failure observed under irreversible pruning?

## Conditions

Use three matched conditions on isomorphic tasks.

### C2 — Decomposition only

- Decompose the problem into components and dependencies.
- Keep all components available in the active workspace.
- No removal operation is permitted.

### C3-I — Irreversible pruning

- Decompose and classify components.
- Components classified as irrelevant, redundant, or resolved may be removed from the active and recoverable state.
- Removed components cannot be restored during the task.
- This condition operationalizes the failure mode observed in ROP-R01.

### C3-R — Reversible latent workspace

- Decompose and classify components.
- Candidate removals are moved from active state to latent state, never deleted during the task.
- Latent components remain addressable but are not presented in the active workspace.
- The solver may issue a restore request when a missing dependency is detected.
- Every restore is logged with trigger, component id, and downstream use.
- UNKNOWN materiality must remain active or latent; it cannot be permanently removed.

## Equivalence boundary

Across all three conditions, hold constant:

- model and model version
- provider/backend
- temperature and sampling settings
- task semantics and difficulty distribution
- answer-key and dependency map
- maximum generation budget
- scoring logic
- execution hardware class where material
- scorer blinding

Only workspace policy may differ.

No condition may receive additional factual information unavailable to the others. C3-R receives only a different state-access policy: latent state remains recoverable.

## Task design

Use a fresh task set. Do not reuse ROP-R01 task instances.

Minimum 36 matched task families, with two isomorphic forms per family, balanced across three tiers:

- 12 local / short-horizon tasks
- 12 delayed-dependency tasks where an apparently low-value component becomes material later
- 12 reactivation tasks where a component must leave the active workspace and later be required again

Each task must have before execution:

- unique answer
- frozen decomposition
- frozen dependency graph
- frozen set of material components
- at least one downstream dependency opportunity in the delayed-dependency and reactivation tiers
- a condition-neutral scoring representation

Randomize task-form/condition assignment with a frozen seed before execution.

## Primary hypotheses

H1 — Dependency preservation

C3-R dependency preservation is at least 25 percentage points higher than C3-I.

H2 — Correctness preservation

C3-R correctness is no more than 5 percentage points below C2.

H3 — Active workspace reduction

C3-R reduces mean active workspace size by at least 20% versus C2 while satisfying H2.

H4 — Mechanism localization

Among C3-R cases where a component is moved to latent state and later becomes material, at least 80% are restored before the first consequence-bearing step that requires that component.

These are risky predictions. Failure of any threshold narrows or rejects the corresponding claim.

## Secondary measures

Record per task:

- correctness
- dependency preservation
- active workspace component count at each step
- active workspace token count where measurable
- latent component count
- number of candidate removals
- false-removal candidates
- restore count
- restore success rate
- time to restore after dependency need becomes detectable
- reconstruction attempts
- steps
- reversals
- errors
- wall-clock time
- total tokens where available
- effective search cost (ESC), reported using the same composite definition as ROP-R01 for comparability

## Required event types

The executor must emit immutable events for:

- NEED_DECLARED
- COMPONENT_ACTIVATED
- COMPONENT_MARKED_CANDIDATE_REMOVE
- COMPONENT_MOVED_LATENT
- COMPONENT_REMOVED_IRREVERSIBLE
- DEPENDENCY_MISSING
- RESTORE_REQUESTED
- COMPONENT_RESTORED
- CONSEQUENCE_STEP
- FINAL_ANSWER

Each state transition must include task id, blinded run id, component id where applicable, timestamp/order index, and reason code.

## Blinding

The scorer must not receive condition labels, prompts, workspace-policy names, raw structural headings, executor session identity, or restore/removal labels.

Scorer input must be normalized into condition-neutral fields sufficient to score:

- final correctness
- required dependency preservation
- whether each frozen material dependency was available before its first consequence-bearing use

Workspace-policy metrics are joined only after blind scoring is sealed.

## Analysis

Primary comparisons:

- C3-R vs C3-I for dependency preservation
- C3-R vs C2 for correctness
- C3-R vs C2 for active workspace size

Report absolute differences, 95% confidence intervals, raw counts, and per-tier results.

Do not infer successful cognitive offloading from fewer visible steps alone.

A reduction in active workspace counts as beneficial only if correctness and dependency-preservation gates are satisfied.

## Kill / stop rules

Stop and quarantine affected tasks if answer-key leakage, dependency-map leakage, or scorer condition leakage affects more than one task.

Stop progression if:

- C3-R correctness is more than 5 percentage points below C2
- C3-R dependency preservation is below 90%
- C3-R fails to improve dependency preservation over C3-I
- latent restore failures cause a material dependency to be unavailable before consequence in more than 20% of eligible cases
- UNKNOWN is treated as dispensable or permanently deleted

Do not modify thresholds, task inclusion, dependency maps, or hypotheses after outcome inspection.

## Interpretation boundary

A positive result would support only the claim that reversible workspace management outperforms irreversible pruning under the tested harness and task distribution.

It would not establish that the method generalizes to open-domain reasoning, long-horizon agents, legal text, code, memory systems, or other models without further testing.

A negative result must be retained as evidence and must not be repaired by changing the current run.

## Deliverables

- frozen task set
- frozen dependency map
- frozen randomization seed and assignment manifest
- execution receipt with model/provider/version/settings
- immutable event log
- normalized blinded scorer input
- blinded scorer outputs
- analysis report
- deviation log
- final GO / NO_GO decision
