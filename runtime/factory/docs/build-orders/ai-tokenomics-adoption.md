# Build Order: AI Tokenomics for Governed Software Engineering

Status: implemented in PR #46
Source: Google Cloud, “Guide to AI tokenomics: eleven principles for token-efficient software engineering”

## Canonical rule

Context is a budgeted runtime resource.

The factory optimizes cost of cognition, not token count in isolation. Cost of cognition includes tokens, model cost, latency, human attention, retries, context reconstruction, verification, and error/rework.

Efficiency must never weaken authority, REHT boundaries, QC, evidence, receipts, or deterministic verification.

## Adopted operating rules

1. Start with the lowest sufficient model/reasoning capability and escalate only when required.
2. Move repeated instructions into repository rules, skills, scripts, or contracts.
3. Use deterministic tools for mechanical work instead of spending model reasoning on it.
4. Delegate bounded work and return result plus evidence, not the worker’s full trajectory.
5. Separate analysis from execution when analysis would pollute the execution context.
6. Run cheap deterministic checks early; reserve expensive end-to-end checks for handoff.
7. Revert or restart a stuck trajectory instead of accumulating corrective prompts.
8. Load only owned files, required contracts, dependencies, and acceptance evidence.
9. If the same correction occurs twice, change the rule/skill rather than adding more corrective prompts.
10. Every autonomous loop has a budget, stop condition, and exception path.
11. A new goal gets a new session; the same goal may reuse context only while it remains relevant.

## Runtime implementation

`config/tokenomics-policy.json` is the canonical machine-readable policy.

`valo-run` refuses to start if that policy is missing, malformed, non-canonical, or does not contain exactly eleven operating rules.

Every non-dry worker run writes `WORK_BUDGET.json` into the isolated worktree. The budget binds the run to:

- issue scope
- base SHA and branch
- targeted context retrieval
- owned-file declaration
- required contracts
- bounded repeated corrections and retries
- revert/restart behavior for stuck trajectories
- result-plus-evidence worker handoff
- session reset on goal change
- cheap-checks-before-E2E verification
- cost-of-cognition dimensions

The budget is created before worker changes and is therefore included in the delivery when the orchestrator stages the worktree.

## Acceptance gates

- canonical policy contains exactly 11 rules
- every worker run can resolve the canonical policy
- every non-dry worker run materializes `WORK_BUDGET.json`
- retry and repeated-correction limits are explicit
- targeted retrieval is explicit
- authority/QC/evidence invariants remain unchanged
- tests cover policy validity and budget materialization

## Non-goals

This does not give token-budget logic authority over execution. Tokenomics is an efficiency and work-shaping control. REHT and the existing governance chain remain authoritative.
