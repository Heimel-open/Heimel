# Hamzaish reference architecture

Source: https://github.com/hamza-ali-shahjahan/hamzaish
Reviewed: 2026-08-04
License: AGPL-3.0-or-later

## Classification

Hamzaish is a personal AI co-builder and startup operating system for one operator managing a portfolio of products. It separates shared knowledge, factory behavior, product metadata, improvement mechanisms, stack defaults and scaffolding.

Treat it as reference architecture and study material. Do not copy AGPL source code into proprietary VALO repositories. General ideas and architectural patterns may be independently reimplemented using VALO-owned contracts, code and terminology.

## Relevant patterns

1. Shared factory brain
   - Markdown as source of truth.
   - Derived searchable index.
   - Operator identity, principles, decisions, learnings and anti-patterns are available across product sessions.

2. Portfolio metadata separated from product code
   - One product workspace per product.
   - Product scope, state, decisions and learnings remain outside the source repository.
   - Cross-product changes require explicit ownership and scope.

3. Model-independent operating contract
   - AGENTS.md is the common context contract.
   - Thin adapters route Claude Code, Codex, Cursor and other tools to the same source of truth.
   - Tool-specific instructions extend rather than replace the shared contract.

4. Factory-improves-factory loop
   - Real work produces durable learning.
   - Repeated mistakes become anti-patterns or guardrails.
   - Sprint completion produces retrospectives and factory updates.

5. Eval and regression harness
   - Deterministic criteria are evaluated before an LLM judge.
   - The LLM judge acts as a veto, not an oracle.
   - Outcomes distinguish PASS, buildable failure, specification gap and uncertainty.
   - Baseline regression checks protect previously proven behavior.

6. Reversible autonomy
   - Fast, cheap and reversible work can proceed by default.
   - Destructive, external, expensive or materially ambiguous actions require an explicit boundary.
   - Auto-commit is local by default; push requires separate opt-in and secret scanning.

7. Portfolio routing
   - Work is routed by product state and development lifecycle.
   - The factory supports idea, MVP, launch, scale and portfolio-level decisions.

## VALO adoption decision

Adopt the patterns, not the implementation.

### Adopt into VALO Factory

- Shared factory memory with canonical source and derived search index.
- Product metadata layer separated from product source code.
- Thin model/tool adapters pointing to one canonical factory contract.
- Durable learning loop: observations -> learning -> anti-pattern/guardrail -> eval.
- Agent-blind eval cases and deterministic-first judging.
- Explicit PASS / FAIL_BUILDABLE / GAP / UNCERTAIN outcome taxonomy for factory work.
- Regression floor that cannot silently weaken.
- Portfolio pulse with continue, maintain, defer and stop decisions.
- Local restore-point commits, opt-in push and secret scan patterns.

### Modify for VALO

- Instructions are not authority. AGENTS.md, skills and prompts remain guidance only.
- Every consequential action must cross an ACEG execution boundary.
- VAIG may evaluate evidence and uncertainty but has no authority.
- REHT clears or denies the concrete action using identity, authority, mandate, scope, state, policy and admissible evidence.
- Gateway/adapter mechanically enforces the result.
- Veritas records execution and produces the receipt.
- RACS expresses the deterministic decision outcome; it does not evaluate, authorize or learn.
- Baseline PASS degrading to GAP, UNCERTAIN or SKIP must not be silently accepted for safety-critical gates. The applicable policy must explicitly decide whether to block, step up or quarantine.
- Autonomous workflow contracts must be internally consistent. A command cannot claim no gates while its invoked orchestrator requires approval at every phase.

### Reject

- Copying AGPL code into VALO proprietary codebases.
- Treating prompt compliance as enforcement.
- Allowing an agent or LLM judge to attest its own correctness.
- Using an LLM judge to create PASS without deterministic evidence.
- Global auto-push or cross-repository mutation without explicit ownership, authority and scope.

## Canonical distinction

Hamzaish organizes how agents build and operate a portfolio.

VALO adds the independent decision boundary that determines whether a proposed action should be allowed to produce consequences.

Canonical chain:

Agent proposes action -> VAIG evaluates -> REHT clears or denies -> gateway enforces -> execution occurs -> Veritas records -> RACS outcome and receipt remain auditable.

## Implementation order

1. Inventory current VALO Factory memory, product metadata, skills, evals and retrospectives.
2. Map each adopted pattern to an existing subsystem; do not create duplicate frameworks.
3. Add a canonical factory context contract with thin adapters for active agent tools.
4. Add durable learning promotion rules and anti-pattern/guardrail lifecycle.
5. Extend evals with agent-blind cases and explicit four-outcome classification.
6. Put all factory mutations, pushes, deployments and external actions behind REHT clearance and Veritas receipts.
7. Add portfolio pulse and product-state routing only after the underlying metadata is canonical.

## Acceptance criteria

- No copied Hamzaish code or text beyond necessary attribution and factual description.
- Every adopted item has a VALO owner, target subsystem and executable acceptance test.
- Guidance, evaluation, authorization, enforcement and evidence are represented as separate layers.
- No agent can approve or attest its own work.
- Safety-critical regression weakening fails closed or requires explicit human step-up.
- External or irreversible action requires a governed execution receipt.
