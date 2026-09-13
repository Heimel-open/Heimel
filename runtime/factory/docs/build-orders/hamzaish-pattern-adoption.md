# Build order: adopt validated Hamzaish patterns

Status: proposed
Owner: VALO Factory coordinator
Reference: `docs/reference-architectures/hamzaish.md`

## Goal

Independently implement the useful factory patterns identified in Hamzaish while preserving VALO's separation of guidance, evaluation, authorization, enforcement and evidence.

## Work packages

### 1. Current-state inventory

Identify the canonical locations for:

- shared factory context and memory
- product portfolio metadata
- agent/tool adapters
- learnings, retrospectives and anti-patterns
- eval cases, baselines and regression gates
- mutation, push, merge, deploy and external-action boundaries

Deliverable: one mapping document showing reuse, gaps and duplicate candidates.

Acceptance:

- Every adopted pattern maps to an existing subsystem or an explicit justified gap.
- No new framework is introduced where an owned equivalent already exists.

### 2. Canonical factory context contract

Create or consolidate one tool-independent context contract. Tool-specific files must be thin adapters that point to the canonical contract and may only extend it with tool mechanics.

Acceptance:

- Claude, Codex, Antigravity and Hermes resolve the same canonical operating rules.
- Contradictory adapter rules fail a consistency check.
- Instructions remain explicitly non-authoritative.

### 3. Durable learning promotion

Implement the lifecycle:

observation -> candidate learning -> validated learning -> anti-pattern or guardrail -> executable eval.

Acceptance:

- Repeated failure patterns can be promoted without rewriting historical records.
- Each guardrail links to the evidence and eval that justify it.
- An agent cannot promote its own unverified claim directly to a canonical guardrail.

### 4. Agent-blind eval taxonomy

Extend the factory eval harness with:

- PASS
- FAIL_BUILDABLE
- GAP
- UNCERTAIN

Run deterministic checks first. Model judges may veto or escalate but never create PASS.

Acceptance:

- Systems under test cannot read their own cases or rubric.
- Previously proven safety-critical behavior cannot degrade to GAP, UNCERTAIN or SKIP without policy-directed block, quarantine or human step-up.
- Baseline changes require independent QC and an evidence receipt.

### 5. Govern factory actions through ACEG

Route consequential factory actions through the canonical chain:

Agent proposes -> VAIG evaluates -> REHT clears/denies -> gateway enforces -> action executes -> Veritas records.

Minimum governed actions:

- cross-repository mutation
- commit and push
- pull-request creation and merge
- deployment
- secret-bearing operations
- external communication or publication
- destructive filesystem or infrastructure changes

Acceptance:

- Identity, authority, mandate, scope, target, payload hash and state are bound before execution.
- Denials and step-ups are recorded.
- Successful actions produce execution receipts tied to the exact commit or artifact.
- Guidance files cannot bypass the boundary.

### 6. Portfolio pulse

Add canonical product-state routing with explicit outcomes:

- continue
- maintain
- defer
- stop

Acceptance:

- Decisions use current product evidence and preserve decision history.
- Portfolio routing has no execution authority.
- Any resulting mutation or external action returns to REHT for clearance.

## Non-goals

- No Hamzaish code import.
- No AGPL-derived implementation.
- No replacement of existing VALO subsystems merely to match Hamzaish naming.
- No autonomous self-attestation.

## Delivery gates

- Exact base SHA and owned files declared before implementation.
- Tests and evals added with each work package.
- Independent QC on exact head SHA.
- Green agreed gates proceed to merge; improvements outside active scope go to backlog.
