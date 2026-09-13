# Build order: governed self-improving factory loop

Owner: Factory OS
Target repo: `nsolland/valo-factory`
Canonical base SHA: `2c438ed4c6b63c350b8fa0be2fb4edf98dbc3dc4`
Delivery branch: `feat/adopt-fluent-factory-patterns`
Source pattern: `mrinalwadhwa/fluent` (Apache-2.0, knowledge reference only)

## Active delivery

Implement the durable Observation -> WorkItem -> Attempt -> MergeCandidate -> post-merge Observation loop while preserving existing REHT, VAIG, RACS, QC, claim, mode and separation-of-duties boundaries.

## Required contracts

Add versioned schemas for:

- `ObservationV1`
- `BriefV1`
- `BehaviorSpecV1`
- `TechnicalApproachV1`
- `ImplementationPlanV1`
- `AuthorityEnvelopeV1`
- `WorkItemV1`
- `AttemptV1`
- `TesterEvidenceV1`
- `ReviewFindingV1`
- `ReviewReportV1`
- `LearnerHandoffV1`
- `MergeCandidateV1`
- `PostMergeObservationV1`

Every consequential artifact must bind `run_id`, repository, base SHA or candidate SHA, actor identity, timestamps and content digest.

## Required runtime behavior

1. Intake records Observations without granting execution authority.
2. Shaping produces four explicit layers and a separate Authority Envelope.
3. A Work Item is immutable after authorization; revisions create a new version.
4. Every execution creates a distinct Attempt and isolated worktree.
5. Human-attention work and executable work use separate queues.
6. The Writer may commit candidates but may not produce QC, approve or merge.
7. A deterministic Tester runs repository-declared commands and produces normalized SHA-bound evidence.
8. Independent reviewers run in parallel after Tester evidence exists.
9. Blocking findings return to the Writer; minor findings become follow-up Observations unless explicitly included.
10. Correction rounds are capped at three by default.
11. A Learner runs only after required gates pass and emits provenance-bound expertise proposals plus follow-up Observations.
12. A Merge Candidate is immutable and bound to exact evidence digests and candidate SHA.
13. Landing rechecks mode, claims, CI, target drift, REHT clearance, RACS decision and current head SHA.
14. Post-merge findings return as Observations and cannot silently trigger authority-bearing execution.

## Storage

Extend the existing SQLite-backed orchestration state rather than creating file-based mutable truth.

Minimum tables:

- `observations`
- `shape_artifacts`
- `work_items`
- `attempts`
- `human_queue`
- `execution_queue`
- `tester_evidence`
- `review_reports`
- `review_findings`
- `learner_handoffs`
- `merge_candidates`
- `post_merge_observations`

Store immutable payload digests and append-only transitions. Mutable projections may be rebuilt from the event history.

## CLI surface

Extend `valo-orchestrator` or add narrowly scoped commands:

```text
valo-observe add|show|list
valo-shape start|record|approve|show
valo-work create|queue|show|supersede
valo-attempt start|status|resume|cancel
valo-review status|show
valo-candidate show|land
valo-learn show|accept|reject
```

Commands that change execution state must call `mode_check()` immediately before the write and must validate the current authority envelope.

## Tester contract

Use repository-owned test configuration. The deterministic runner must capture:

- exact command
- working directory
- environment profile digest
- start/end timestamps
- duration
- exit code
- bounded stdout/stderr digest and retained artifact reference
- normalized test counts and failures where an extractor exists

The result must be signed or otherwise integrity-bound to candidate SHA. The Writer's report is never accepted as test evidence.

## Reviewer contract

Run reviewers independently and in parallel:

- behavior
- architecture/boundary
- tests
- documentation
- security/authority
- skills when applicable

Each report must identify evidence, exact file/line references when possible, severity, status and whether human judgment is required. Reviewers are read-only.

## Learner contract

Learner output is `proposed_expertise`, never authority. Each proposal includes source Attempt, supporting evidence, confidence, scope and expiry/review date. Acceptance must be separate from generation. Canonical Index updates require the Index repository's own contract and authority path.

## Gates

Mandatory tests:

- Observation cannot authorize or queue itself.
- Work Item mutation after authorization fails closed.
- Attempt cannot start from expired or mismatched authority.
- Writer cannot approve, QC or merge its own candidate.
- Tester evidence with a different SHA is rejected.
- Reviewer output cannot mutate candidate files.
- Three failed correction rounds transition to `NEEDS_HUMAN`.
- Learner output cannot change policy, authority or canonical expertise directly.
- Merge Candidate becomes invalid after head or target drift.
- Landing fails when mode is not `NORMAL`.
- Landing fails without current REHT clearance and RACS permit.
- Post-merge findings create Observations only.
- Independent Work Items can proceed while another waits in the human queue.

## Definition of done

- Contracts and migrations committed.
- CLI/runtime path implemented.
- Existing dispatcher, claim, QC and merge tests remain green.
- New boundary and state-machine tests green.
- One end-to-end integration proves:

```text
Observation
-> shaped Work Item
-> authorized Attempt
-> isolated Writer candidate
-> deterministic Tester evidence
-> parallel independent review
-> Learner handoff
-> Merge Candidate
-> governed landing
-> post-merge Observation
```

- Exact head SHA, test evidence and governance receipts are attached to the PR.

## Non-blocking later work

- Remote worker placement and capacity optimization.
- UI for the two queues.
- Automatic production-log connectors.
- Expertise ranking and decay.
- Cross-repository Work Item graphs.

These do not block the first governed vertical slice.